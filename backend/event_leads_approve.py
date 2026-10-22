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
"""
import asyncio
import secrets
from datetime import timedelta, timezone

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

async def _refuse_existing_host(user):
    hosts = await events.count_documents({"created_by": user["_id"]}) > 0
    if hosts or billing.plan_of(user) != "free" or user.get("is_admin"):
        raise _conflict(EXISTING_HOST)


async def _create_host(email, name, now):
    """A normal free host account with an unusable random password. The claim
    link is how its owner gets in; nothing here emails them."""
    doc = {
        "email": email,
        "password_hash": await asyncio.to_thread(hash_password, secrets.token_urlsafe(32)),
        "is_admin": False,
        "created_at": now,
        "profile": Profile(name=name).model_dump(),
        "plan": "free",
        "nurture_enabled": False,
        "host_origin": "event_lead",
        "email_verified": True,
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
        await _refuse_existing_host(user)
        return user
    return await _create_host(email, name, now)


# ---------- step 2: event ----------

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
    }
    await store.update_lead(lead["_id"], fields)
    return _with(lead, fields)


# ---------- step 3: claim token ----------

def _claim_expiry(lead):
    start = _event_payload(lead).date
    if start.tzinfo is None:
        start = start.replace(tzinfo=rules.DENVER)
    return (start + timedelta(days=CLAIM_VALID_DAYS)).astimezone(timezone.utc)


async def _mint_claim(lead):
    if lead.get("claim_token_hash"):
        return lead
    token = core._new_reset_token()
    fields = {
        "claim_token_hash": core._hash_token(token),
        "claim_expires_at": _claim_expiry(lead),
        "claim_url": f"{APP_URL}/claim/{token}",
    }
    await store.update_lead(lead["_id"], fields)
    return _with(lead, fields)


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
        error = result.get("error") or "Signal Scout push failed"
        signal_scout = {"error": error, "pushed_at": now}
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


async def approve(lead_id, actor, now):
    """Approve one lead. `actor` is the admin user dict or "ingest"."""
    lead = await _load(lead_id)
    _refuse(lead)
    if not lead.get("event_id"):
        payload = _event_payload(lead)
        host = await _resolve_host(lead, now)
        lead = await _create_event(lead, host, payload)
    lead = await _mint_claim(lead)
    lead = await _push_once(lead, now)
    lead = await _finish(lead, actor, now)
    return _response(lead)


async def retry_outreach(lead_id, now):
    """Re-run step 4 for an approved email lead that has no prospect yet."""
    lead = await _load(lead_id)
    email, _, _ = _contact(lead)
    prospect_id = (lead.get("signal_scout") or {}).get("prospect_id")
    if lead.get("status") != "approved" or not email or prospect_id:
        raise _conflict(NOT_RETRYABLE)
    return _response(await _push(lead, now))
