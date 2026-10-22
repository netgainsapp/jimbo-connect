"""The thin Outreach cockpit. Intro Connect stages a host-acquisition lead list
here, then hands it to signal-scout (the outreach engine) either by CSV export
(works today: download and upload to signal-scout's import) or by a live API
push (dormant until SIGNAL_SCOUT_URL + SIGNAL_SCOUT_API_KEY are set AND the
signal-scout Intro Connect import endpoint exists).

signal-scout owns sending, warmup, reporting, and compliance. Intro Connect only
holds the staging list + a status per lead.
"""
import csv
import io
import os
import re
import sys
from datetime import datetime, timezone

from database import outreach_leads

SIGNAL_SCOUT_URL = os.getenv("SIGNAL_SCOUT_URL", "").rstrip("/")
SIGNAL_SCOUT_API_KEY = os.getenv("SIGNAL_SCOUT_API_KEY", "")
PUSH_TIMEOUT_SECONDS = 30
# How much of a Signal Scout body reaches the server log.
LOG_BODY_CHARS = 500

# Columns signal-scout's CSV import understands (agency/import shape). The
# operator can upload this file directly on the signal-scout dashboard.
CSV_FIELDS = [
    "first_name",
    "last_name",
    "company",
    "email",
    "title",
    "linkedin_url",
    "source",
]


def is_configured() -> bool:
    """True when a live push to signal-scout is possible."""
    return bool(SIGNAL_SCOUT_URL and SIGNAL_SCOUT_API_KEY)


def _split_name(name: str):
    name = (name or "").strip()
    if not name:
        return "", ""
    first, _, last = name.partition(" ")
    return first, last


def _csv_safe(value) -> str:
    """Prevent CSV formula injection: a cell starting with = + - @ (or a control
    char) is prefixed with a single quote so a spreadsheet treats it as text."""
    s = str(value or "")
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


def lead_to_row(lead: dict) -> dict:
    first, last = _split_name(lead.get("name", ""))
    return {
        "first_name": _csv_safe(first),
        "last_name": _csv_safe(last),
        "company": _csv_safe(lead.get("company", "")),
        "email": lead.get("email", "") or "",
        "title": _csv_safe(lead.get("role", "")),
        "linkedin_url": _csv_safe(lead.get("source", "")),
        "source": "intro_connect",
    }


def to_csv(leads) -> str:
    """signal-scout import-ready CSV for the given lead dicts."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
    writer.writeheader()
    for lead in leads:
        writer.writerow(lead_to_row(lead))
    return buf.getvalue()


async def push_to_signal_scout(leads) -> dict:
    """Live push to signal-scout's Intro Connect import endpoint
    (POST /api/intro-connect/import, JSON). Dormant until SIGNAL_SCOUT_URL +
    SIGNAL_SCOUT_API_KEY are set (the key is signal-scout's CRON_SECRET). Returns
    an outcome dict (never raises on config gaps)."""
    if not is_configured():
        return {"ok": False, "skipped": "not_configured"}
    if not leads:
        return {"ok": False, "skipped": "no_leads"}
    import httpx

    payload = {
        "leads": [
            {
                "email": lead.get("email", ""),
                "name": lead.get("name", ""),
                "company": lead.get("company", ""),
                "role": lead.get("role", ""),
            }
            for lead in leads
        ]
    }
    url = f"{SIGNAL_SCOUT_URL}/api/intro-connect/import"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {SIGNAL_SCOUT_API_KEY}"},
                json=payload,
            )
        http_ok = resp.status_code < 300
        if not http_ok:
            # Log the raw body server-side; do not forward it to the admin UI
            # (it could carry signal-scout internal diagnostics).
            print(
                f"[outreach] signal-scout push {resp.status_code}: {resp.text[:500]}",
                file=sys.stderr,
            )
            return {
                "ok": False,
                "status_code": resp.status_code,
                "pushed": 0,
                "detail": f"HTTP {resp.status_code}",
            }
        # A 200 does NOT mean the leads landed: signal-scout reports per-lead
        # outcomes in the body ({imported, sequences_scheduled, errors}) and
        # still returns 200 when every lead errored. Trust the body, not the
        # status, or the cockpit shows a green "pushed" for a no-op import.
        try:
            body = resp.json()
        except ValueError:
            print(
                f"[outreach] signal-scout push 200 with unparseable body: {resp.text[:300]}",
                file=sys.stderr,
            )
            return {
                "ok": False,
                "status_code": resp.status_code,
                "pushed": 0,
                "detail": "signal-scout returned an unreadable response",
            }
        imported = int(body.get("imported") or 0)
        errors = body.get("errors") or []
        if errors:
            print(f"[outreach] signal-scout import errors: {str(errors)[:500]}", file=sys.stderr)
        return {
            "ok": imported > 0 and not errors,
            "status_code": resp.status_code,
            "pushed": imported,
            "sequences_scheduled": int(body.get("sequences_scheduled") or 0),
            "already_scheduled": int(body.get("already_scheduled") or 0),
            "error_count": len(errors),
            "detail": (
                f"imported {imported}/{len(leads)}"
                + (f", {len(errors)} error(s)" if errors else "")
            ),
        }
    except Exception as exc:  # network / DNS / timeout
        return {"ok": False, "error": str(exc)[:300]}


# ---------- Event lead push (the Approve button, one lead with its event) ----------

def _event_summary(event: dict) -> dict:
    """One event in the shape Signal Scout's import contract expects."""
    event = event or {}
    return {
        "name": event.get("title") or "",
        "date": event.get("start") or "",
        "venue": event.get("venue") or "",
        "city": event.get("city") or "",
        "source_url": event.get("source_url") or "",
    }


def _starts_on_or_after(event: dict, now: datetime) -> bool:
    try:
        start = datetime.fromisoformat((event or {}).get("start") or "")
    except ValueError:
        return False
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return start >= now


def event_lead_payload(lead: dict, claim_url: str, now: datetime) -> dict:
    contact = lead.get("contact") or {}
    upcoming = [e for e in lead.get("events") or [] if _starts_on_or_after(e, now)]
    return {
        "leads": [
            {
                "email": contact.get("email") or "",
                "name": contact.get("name") or "",
                "company": lead.get("organizer_name") or "",
                "role": "",
                "event": {
                    "anchor": _event_summary(lead.get("anchor")),
                    "upcoming": [_event_summary(e) for e in upcoming],
                    "claim_url": claim_url,
                    "lead_id": str(lead["_id"]),
                },
            }
        ]
    }


def _redact(text, email: str) -> str:
    """Server log copy of a Signal Scout body with the lead's email removed."""
    text = str(text or "")[:LOG_BODY_CHARS]
    return re.sub(re.escape(email), "[email]", text, flags=re.I) if email else text


def _first_result(resp, email: str) -> dict:
    """Read results[0] from a Signal Scout reply into the push outcome."""
    if resp.status_code >= 300:
        print(f"[outreach] event lead push {resp.status_code}: {_redact(resp.text, email)}",
              file=sys.stderr)
        return {"ok": False, "error": f"Signal Scout returned HTTP {resp.status_code}"}
    try:
        results = resp.json().get("results")
        result = results[0] if isinstance(results, list) and results else None
    except (ValueError, AttributeError):
        result = None
    if not isinstance(result, dict):
        print(f"[outreach] event lead push unreadable body: {_redact(resp.text, email)}",
              file=sys.stderr)
        return {"ok": False, "error": "Signal Scout returned an unreadable response"}
    outcome, prospect_id = result.get("outcome"), result.get("prospect_id")
    if outcome == "error" or not prospect_id:
        print(f"[outreach] event lead push rejected: {_redact(result, email)}",
              file=sys.stderr)
        return {"ok": False, "outcome": outcome,
                "error": "Signal Scout did not import the lead"}
    return {"ok": True, "prospect_id": str(prospect_id), "outcome": outcome}


async def push_event_lead(lead: dict, claim_url: str, now: datetime = None) -> dict:
    """Push one approved event lead to Signal Scout's Intro Connect import.

    Returns {ok, prospect_id?, outcome?, error?} from results[0]. Never raises:
    a config gap, HTTP error, network error or malformed body is ok False with
    a short error the admin may see. Raw bodies go to stderr with the lead's
    email redacted, never to the caller."""
    if not is_configured():
        return {"ok": False, "error": "Signal Scout is not configured"}
    import httpx

    email = (lead.get("contact") or {}).get("email") or ""
    payload = event_lead_payload(lead, claim_url, now or datetime.now(timezone.utc))
    try:
        async with httpx.AsyncClient(timeout=PUSH_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{SIGNAL_SCOUT_URL}/api/intro-connect/import",
                headers={"Authorization": f"Bearer {SIGNAL_SCOUT_API_KEY}"},
                json=payload,
            )
    except Exception as exc:  # network / DNS / timeout
        print(f"[outreach] event lead push failed: {_redact(exc, email)}", file=sys.stderr)
        return {"ok": False, "error": f"Signal Scout unreachable ({type(exc).__name__})"}
    return _first_result(resp, email)


# ---------- Claimed (the host claimed the event Approve built) ----------

async def notify_claimed(lead: dict) -> dict:
    """Tell Signal Scout the host claimed, so it stops the drip.

    POSTs the claimed contract {prospect_id, lead_id, email}. Skipped when
    Signal Scout is not configured or the lead was never imported (no
    prospect_id, e.g. a LinkedIn-only lead). Never raises; logs never carry
    the email."""
    if not is_configured():
        return {"ok": False, "skipped": "not_configured"}
    prospect_id = (lead.get("signal_scout") or {}).get("prospect_id")
    if not prospect_id:
        return {"ok": False, "skipped": "no_prospect"}
    import httpx

    email = (lead.get("contact") or {}).get("email") or ""
    payload = {"prospect_id": prospect_id, "lead_id": str(lead["_id"]), "email": email}
    try:
        async with httpx.AsyncClient(timeout=PUSH_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{SIGNAL_SCOUT_URL}/api/intro-connect/claimed",
                headers={"Authorization": f"Bearer {SIGNAL_SCOUT_API_KEY}"},
                json=payload,
            )
    except Exception as exc:  # network / DNS / timeout
        print(f"[outreach] claimed notify failed: {_redact(exc, email)}", file=sys.stderr)
        return {"ok": False, "error": f"Signal Scout unreachable ({type(exc).__name__})"}
    if resp.status_code >= 300:
        print(f"[outreach] claimed notify {resp.status_code}: {_redact(resp.text, email)}",
              file=sys.stderr)
        return {"ok": False, "error": f"Signal Scout returned HTTP {resp.status_code}"}
    return {"ok": True}
