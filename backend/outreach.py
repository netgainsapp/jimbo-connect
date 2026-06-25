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

from database import outreach_leads

SIGNAL_SCOUT_URL = os.getenv("SIGNAL_SCOUT_URL", "").rstrip("/")
SIGNAL_SCOUT_API_KEY = os.getenv("SIGNAL_SCOUT_API_KEY", "")

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


def lead_to_row(lead: dict) -> dict:
    first, last = _split_name(lead.get("name", ""))
    return {
        "first_name": first,
        "last_name": last,
        "company": lead.get("company", "") or "",
        "email": lead.get("email", "") or "",
        "title": lead.get("role", "") or "",
        "linkedin_url": lead.get("source", "") or "",
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
    """Live push to signal-scout's Intro Connect import endpoint. Dormant until
    configured; expects a signal-scout endpoint that accepts the CSV with the
    Intro Connect brand. Returns an outcome dict (never raises on config gaps)."""
    if not is_configured():
        return {"ok": False, "skipped": "not_configured"}
    if not leads:
        return {"ok": False, "skipped": "no_leads"}
    import httpx

    csv_text = to_csv(leads)
    url = f"{SIGNAL_SCOUT_URL}/api/leads/import?brand=intro_connect"
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {SIGNAL_SCOUT_API_KEY}",
                    "Content-Type": "text/csv",
                },
                content=csv_text,
            )
        ok = resp.status_code < 300
        return {
            "ok": ok,
            "status_code": resp.status_code,
            "pushed": len(leads) if ok else 0,
            "detail": resp.text[:500],
        }
    except Exception as exc:  # network / DNS / timeout
        return {"ok": False, "error": str(exc)[:300]}
