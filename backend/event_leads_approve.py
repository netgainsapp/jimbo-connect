"""Approve: the one code path that turns an event lead into a live prospect.

Used by the admin Approve button and by auto-approve on ingest. Six steps, each
run only when its result is absent, so a second Approve (or a resume after a
crash part way through) reports what exists and changes nothing:

1. host account: the user owning the contact email, else a new one. A
   LinkedIn-only lead has no account yet; its event waits for a pending host.
2. event, through routers.events.create_event_for (never around it).
3. claim token: only its hash is stored, plus the expiry and the claim URL.
4. Signal Scout push for leads with an email. A failure is recorded on the
   lead and the lead is still approved; retry_outreach re-runs this step.
5. LinkedIn queue when the contact has a profile URL.
6. status approved.

Every lead write is a `$set` of named keys on `event_leads._id`.

Races: an Approve that has work to do first takes a lease on the lead
(`approving_at`), so a double click or an admin click during auto-approve gets
a 409 instead of a second run. The event is found again by
`provenance.event_lead_id` (unique index) and the claim hash is written only
where none exists, so even a crash between steps resumes onto the same event
and the same claim link.
"""
import asyncio
import secrets
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from pydantic import ValidationError

import billing
import core
import event_leads_rules as rules
import event_leads_store as store
import outreach
from app_url import APP_URL
from auth import hash_password
from database import events, users
from models import EventCreateRequest, Profile
from routers.events import create_event_for

CLAIM_VALID_DAYS = 30
# An Approve lease older than this belongs to a run that crashed.
APPROVE_LEASE_TTL = timedelta(minutes=5)
NAME_MAX_CHARS = 200
LOCATION_MAX_CHARS = 200
DESCRIPTION_MAX_CHARS = 5000
PLAN_LIMIT_STATUS = 403

REFUSED_STATUSES = {
    "existing_customer": "This organizer is already an Intro Connect customer.",
    "archived": "This lead is archived. Unarchive it before approving.",
}
EXISTING_HOST = "This contact already hosts on Intro Connect. Reach out to them directly."
UNREACHABLE = "This lead has no email or LinkedIn to reach."
BAD_ANCHOR = "The anchor event needs a title and a start date before it can be approved."
NOT_RETRYABLE = "Only an approved lead whose Signal Scout push failed can be retried."
LEASE_HELD = "Approve is already running for this lead"


def _conflict(message):
    return HTTPException(status_code=409, detail=message)


def _contact(lead):
    contact = lead.get("contact") or {}
    email = (contact.get("email") or "").strip().lower()
    return email, (contact.get("linkedin_url") or "").strip(), contact.get("name") or ""


def _with(lead, fields):
    """A copy of `lead` with `$set`-style fields applied, dotted keys included."""
    out = dict(lead)
    for key, value in fields.items():
        head, _, rest = key.partition(".")
        out[head] = {**(out.get(head) or {}), rest: value} if rest else value
    return out


async def _load(lead_id):
    lead = await store.get_lead(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


def _refuse(lead):
    """Refusals that must happen before any write."""
    message = REFUSED_STATUSES.get(lead.get("status"))
    if message:
        raise _conflict(message)
    email, linkedin_url, _ = _contact(lead)
    if not lead.get("event_id") and not email and not linkedin_url:
        raise _conflict(UNREACHABLE)


def _event_payload(lead):
    anchor = lead.get("anchor") or {}
    title = (anchor.get("title") or "").strip()
    place = ", ".join(p for p in (anchor.get("venue"), anchor.get("city")) if p)
    vertical = (lead.get("score") or {}).get("vertical")
    if not title:
        raise _conflict(BAD_ANCHOR)
    try:
        return EventCreateRequest(
            name=title[:NAME_MAX_CHARS],
            date=anchor.get("start"),
            location=place[:LOCATION_MAX_CHARS],
            description=(anchor.get("description") or "")[:DESCRIPTION_MAX_CHARS],
            industry_tags=[vertical] if vertical else [],
        )
    except ValidationError:
        raise _conflict(BAD_ANCHOR) from None


# ---------- step 1: host account ----------

async def _is_existing_host(user, lead_id):
    """A real customer. The event this same lead's Approve made does not
    count, so a resume after a crash is not refused by its own work."""
    hosts = await events.count_documents({
        "created_by": user["_id"],
        "provenance.event_lead_id": {"$ne": lead_id},
    }) > 0
    return bool(hosts or billing.plan_of(user) != "free" or user.get("is_admin"))


async def _refuse_existing_host(user, lead):
    """409 for a real customer, after marking the lead existing_customer so
    its badge shows and Approve disables (plan Review Focus 2). That status
    write is the only one: no user, event, claim token or push."""
    if not await _is_existing_host(user, str(lead["_id"])):
        return
    await store.update_lead(lead["_id"], {
        "status": "existing_customer",
        "existing_user_id": str(user["_id"]),
    })
    raise _conflict(EXISTING_HOST)


def is_preexisting_host(user):
    """Did this account exist before Approve? One Approve made (host_origin
    event_lead, never activated) is empty until claimed, so its claim link
    may sign in. Anything else belongs to a real person, and the claim then
    needs that person's own session (event_leads_claim)."""
    return bool(user) and (
        user.get("host_origin") != "event_lead" or bool(user.get("activated_at"))
    )


async def create_lead_host(email, name, now, email_verified=True):
    """A normal free host account with an unusable random password. The claim
    link is how its owner gets in; nothing here emails them. Approve and the
    claim flow both build hosts here so the shape lives in one place. Approve's
    email came from sourcing; a claim's was typed on the claim page and nobody
    has confirmed it, so the claim passes email_verified=False."""
    doc = {
        "email": email,
        "password_hash": await asyncio.to_thread(hash_password, secrets.token_urlsafe(32)),
        "is_admin": False,
        "created_at": now,
        "profile": Profile(name=name).model_dump(),
        "plan": "free",
        "nurture_enabled": False,
        "host_origin": "event_lead",
        "email_verified": email_verified,
    }
    result = await users.insert_one(doc)
    return {**doc, "_id": result.inserted_id}


async def _resolve_host(lead, now):
    """The host user, or None for a LinkedIn-only lead (pending host)."""
    email, _, name = _contact(lead)
    if not email:
        return None
    user = await users.find_one({"email": email})
    if user:
        await _refuse_existing_host(user, lead)
        return user
    # Never an empty name: other users would otherwise see nothing (or, in
    # older code paths, the email) where the host's name belongs.
    return await create_lead_host(email, name or lead.get("organizer_name") or "", now)


# ---------- step 2: event ----------

async def _adopt_existing_event(lead):
    """Record an event an earlier, interrupted Approve already created."""
    event = await events.find_one({"provenance.event_lead_id": str(lead["_id"])})
    if event is None:
        return None
    host_id = event.get("created_by")
    host = await users.find_one({"_id": host_id}) if host_id else None
    fields = {
        "event_id": str(event["_id"]),
        "host_user_id": str(host_id) if host_id else None,
        **_preexisting_fields(host),
    }
    await store.update_lead(lead["_id"], fields)
    return _with(lead, fields)


def _preexisting_fields(host):
    return {"host_user_preexisting": True} if is_preexisting_host(host) else {}


async def _create_event(lead, host, payload):
    anchor = lead.get("anchor") or {}
    provenance = {
        "source": anchor.get("source") or "",
        "source_url": anchor.get("source_url") or "",
        "event_lead_id": str(lead["_id"]),
        "pending_host": host is None,
    }
    try:
        event = await create_event_for(host, payload, provenance=provenance)
    except HTTPException as exc:
        if exc.status_code == PLAN_LIMIT_STATUS:
            raise _conflict(exc.detail) from None
        raise
    fields = {
        "event_id": event["id"],
        "host_user_id": str(host["_id"]) if host else None,
        **_preexisting_fields(host),
    }
    await store.update_lead(lead["_id"], fields)
    return _with(lead, fields)


# ---------- step 3: claim token ----------

def _anchor_zone(lead):
    """The anchor's own timezone for a naive start, Denver when it has none."""
    try:
        return ZoneInfo((lead.get("anchor") or {}).get("timezone") or "")
    except (ZoneInfoNotFoundError, ValueError):
        return rules.DENVER


def _claim_expiry(lead):
    start = _event_payload(lead).date
    if start.tzinfo is None:
        start = start.replace(tzinfo=_anchor_zone(lead))
    return (start + timedelta(days=CLAIM_VALID_DAYS)).astimezone(timezone.utc)


async def _mint_claim(lead):
    """Mint the claim once. The write only lands where no hash exists, so a
    racing or resumed Approve can never replace a link already handed out;
    the loser re-reads and uses the stored one."""
    if lead.get("claim_token_hash"):
        return lead
    token = core._new_reset_token()
    fields = {
        "claim_token_hash": core._hash_token(token),
        "claim_expires_at": _claim_expiry(lead),
        "claim_url": f"{APP_URL}/claim/{token}",
    }
    unclaimed = {"claim_token_hash": {"$exists": False}}
    if await store.update_lead_if(lead["_id"], unclaimed, fields):
        return _with(lead, fields)
    return await _load(str(lead["_id"]))


# ---------- step 4: Signal Scout ----------

async def _push(lead, now):
    result = await outreach.push_event_lead(lead, lead.get("claim_url"), now=now)
    if result.get("ok"):
        signal_scout = {
            "prospect_id": result.get("prospect_id"),
            "outcome": result.get("outcome"),
            "pushed_at": now,
        }
    else:
        signal_scout = {
            "error": result.get("error") or "Signal Scout push failed",
            "outcome": result.get("outcome"),
            "pushed_at": now,
        }
    fields = {"signal_scout": signal_scout}
    await store.update_lead(lead["_id"], fields)
    return _with(lead, fields)


async def _push_once(lead, now):
    """Push an email lead the first time only; a retry is retry_outreach."""
    email, _, _ = _contact(lead)
    if not email or (lead.get("signal_scout") or {}).get("pushed_at"):
        return lead
    return await _push(lead, now)


# ---------- steps 5 and 6: LinkedIn queue, approved ----------

def _linkedin_fields(lead, now):
    _, linkedin_url, _ = _contact(lead)
    status = (lead.get("linkedin") or {}).get("status") or "none"
    if not linkedin_url or status != "none":
        return {}
    return {"linkedin.status": "queued", "linkedin.updated_at": now}


def _approval_fields(lead, actor, now):
    if lead.get("status") != "new":
        return {}
    return {
        "status": "approved",
        "funnel.approved_at": now,
        "approved_by": str(actor["_id"]) if isinstance(actor, dict) else str(actor),
        "event_id": lead.get("event_id"),
        "host_user_id": lead.get("host_user_id"),
    }


async def _finish(lead, actor, now):
    fields = {**_linkedin_fields(lead, now), **_approval_fields(lead, actor, now)}
    if not fields:
        return lead
    await store.update_lead(lead["_id"], fields)
    return _with(lead, fields)


def _response(lead):
    signal_scout = lead.get("signal_scout") or {}
    return {
        "status": lead.get("status"),
        "event_id": lead.get("event_id"),
        "host_user_id": lead.get("host_user_id"),
        "claim_url": lead.get("claim_url"),
        "signal_scout": {
            "prospect_id": signal_scout.get("prospect_id"),
            "outcome": signal_scout.get("outcome"),
            "error": signal_scout.get("error"),
        },
    }


def _needs_work(lead, actor, now):
    """Would any step write? A finished lead is answered without a lease, so a
    second Approve writes nothing at all."""
    email, _, _ = _contact(lead)
    return bool(
        not lead.get("event_id")
        or not lead.get("claim_token_hash")
        or (email and not (lead.get("signal_scout") or {}).get("pushed_at"))
        or _linkedin_fields(lead, now)
        or _approval_fields(lead, actor, now)
    )


async def _run_steps(lead, actor, now):
    if not lead.get("event_id"):
        adopted = await _adopt_existing_event(lead)
        if adopted is not None:
            lead = adopted
        else:
            payload = _event_payload(lead)
            host = await _resolve_host(lead, now)
            lead = await _create_event(lead, host, payload)
    lead = await _mint_claim(lead)
    lead = await _push_once(lead, now)
    return await _finish(lead, actor, now)


async def approve(lead_id, actor, now):
    """Approve one lead. `actor` is the admin user dict or "ingest"."""
    lead = await _load(lead_id)
    _refuse(lead)
    if not _needs_work(lead, actor, now):
        return _response(lead)
    if not lead.get("event_id"):
        _event_payload(lead)  # a bad anchor is refused before the lease
    if not await store.take_approve_lease(lead["_id"], now, APPROVE_LEASE_TTL):
        raise _conflict(LEASE_HELD)
    try:
        lead = await _load(lead_id)  # the state as of winning the lease
        _refuse(lead)
        lead = await _run_steps(lead, actor, now)
    finally:
        await store.release_approve_lease(lead["_id"], now)
    return _response(lead)


async def retry_outreach(lead_id, now):
    """Re-run step 4 for an approved email lead that has no prospect yet."""
    lead = await _load(lead_id)
    email, _, _ = _contact(lead)
    prospect_id = (lead.get("signal_scout") or {}).get("prospect_id")
    if lead.get("status") != "approved" or not email or prospect_id:
        raise _conflict(NOT_RETRYABLE)
    if not await store.take_approve_lease(lead["_id"], now, APPROVE_LEASE_TTL):
        raise _conflict(LEASE_HELD)
    try:
        lead = await _push(lead, now)
    finally:
        await store.release_approve_lease(lead["_id"], now)
    return _response(lead)
