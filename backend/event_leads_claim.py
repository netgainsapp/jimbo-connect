"""The claim link: how a prospect host takes over the event Approve built.

GET previews (writes nothing, signs nobody in). POST completes:

1. A hosted lead (Approve found or made the host account) signs that host in.
   The link was sent to that host's own address, so holding it is the proof,
   exactly like a magic login link.
2. A pending-host lead (LinkedIn only, no account yet) needs an email. A new
   email gets a new host account built by event_leads_approve.create_lead_host.
   An email that already has an account is attached only when that account is
   the one signed in: typing someone's address on a claim page must never sign
   the typist in as them.
3. Every completion marks the event claimed (which makes it public, see
   routers.events.is_unclaimed_lead_event) and the host activated, each only
   where absent. The first completion alone marks the lead claimed and asks
   the caller to tell Signal Scout; the write is conditional, so two devices
   racing produce one notify.

The claim token is not consumed: it works until it expires.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

import billing
import core
import event_leads_store as store
from database import events, users
from event_leads_approve import create_lead_host
from routers.events import plan_limit_detail

# The HTTP status a dead link answers a POST with. GET always answers 200.
DEAD_LINK_STATUS = {"unknown": 404, "expired": 410}
EMAIL_REQUIRED = "Enter the email you want to sign in with."
SIGN_IN_FIRST = (
    "That email already has an account. Log in with it, then open this link again."
)
CLAIM_RACE = "This event was just claimed. Open the link again."


class DeadLink(Exception):
    """The link is unknown (or archived) or expired. Nothing was written."""

    def __init__(self, state):
        super().__init__(state)
        self.state = state


@dataclass(frozen=True)
class Claimed:
    lead: dict
    event: dict
    user: dict
    first: bool  # this completion was the first; notify Signal Scout


def redirect_for(event) -> str:
    return f"/events/{event['_id']}?claimed=1"


def _aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _expired(lead, now):
    """No stored expiry fails closed: Approve always writes one."""
    expires = lead.get("claim_expires_at")
    return not isinstance(expires, datetime) or _aware(expires) <= now


async def _by_id(collection, raw_id):
    try:
        oid = ObjectId(raw_id)
    except (InvalidId, TypeError):
        return None
    return await collection.find_one({"_id": oid})


async def _load(token, now):
    """(lead, event, host) for a live link; host is None for a pending host."""
    lead = await store.get_lead_by_claim_hash(core._hash_token(token))
    if lead is None:
        raise DeadLink("unknown")
    if _expired(lead, now):
        raise DeadLink("expired")
    event = await _by_id(events, lead.get("event_id"))
    if event is None:
        raise DeadLink("unknown")
    host = None
    if lead.get("host_user_id"):
        host = await _by_id(users, lead["host_user_id"])
        if host is None:
            raise DeadLink("unknown")
    return lead, event, host


def _event_view(event):
    return {
        "id": str(event["_id"]),
        "name": event.get("name") or "",
        "date": event.get("date"),
        "location": event.get("location") or "",
    }


def _host_name(lead, host):
    """A display name only. Never an email, not even as a fallback."""
    contact_name = (lead.get("contact") or {}).get("name") or ""
    if host is None:
        return contact_name
    return (host.get("profile") or {}).get("name") or contact_name


async def preview(token, now):
    """GET: what the claim page shows. Reads only."""
    try:
        lead, event, host = await _load(token, now)
    except DeadLink as dead:
        return {"state": dead.state}
    return {
        "state": "ok" if host else "needs_email",
        "event": _event_view(event),
        "host": {"name": _host_name(lead, host)},
    }


# ---------- pending host ----------

async def _refuse_at_plan_limit(user, event):
    """An existing account at its event limit cannot take on this event.
    The event itself does not count: it is the one being attached."""
    limit = billing.event_limit_for(user)
    if limit is None:
        return
    hosted = await events.count_documents(
        {"created_by": user["_id"], "_id": {"$ne": event["_id"]}}
    )
    if hosted >= limit:
        raise HTTPException(status_code=409, detail=plan_limit_detail(user, limit))


async def _host_for_email(lead, email, name, session_user, now):
    user = await users.find_one({"email": email})
    if user is not None:
        if not session_user or session_user["_id"] != user["_id"]:
            raise HTTPException(status_code=409, detail=SIGN_IN_FIRST)
        return user, False
    contact_name = (lead.get("contact") or {}).get("name") or ""
    display = (name or "").strip() or contact_name or lead.get("organizer_name") or ""
    try:
        return await create_lead_host(email, display, now, email_verified=False), True
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail=CLAIM_RACE) from None


async def _attach_pending_host(lead, event, payload, session_user, now):
    email = payload.email if payload else None
    if not email:
        raise HTTPException(status_code=422, detail=EMAIL_REQUIRED)
    user, created = await _host_for_email(lead, email, payload.name, session_user, now)
    if not created:
        await _refuse_at_plan_limit(user, event)
    attached = await events.update_one(
        {"_id": event["_id"], "created_by": None},
        {"$set": {"created_by": user["_id"], "provenance.pending_host": False}},
    )
    if attached.matched_count == 0:
        raise HTTPException(status_code=409, detail=CLAIM_RACE)
    await store.update_lead(lead["_id"], {"host_user_id": str(user["_id"])})
    return user


# ---------- every completion ----------

async def _mark_event_claimed(event, now):
    await events.update_one(
        {"_id": event["_id"], "provenance.claimed_at": {"$exists": False}},
        {"$set": {"provenance.claimed_at": now}},
    )


async def _mark_activated(user, now):
    await users.update_one(
        {"_id": user["_id"], "activated_at": {"$exists": False}},
        {"$set": {"activated_at": now}},
    )


async def _mark_first_claim(lead, now):
    """True for the one completion that moved the lead to claimed."""
    return await store.update_lead_if(
        lead["_id"],
        {"status": {"$ne": "claimed"}},
        {"status": "claimed", "funnel.claimed_at": now},
    )


async def complete(token, payload, session_user, now):
    """POST: attach the host if pending, mark everything claimed, and return
    who to sign in. Raises DeadLink (nothing written) for a dead link."""
    lead, event, host = await _load(token, now)
    if host is None:
        host = await _attach_pending_host(lead, event, payload, session_user, now)
    await _mark_event_claimed(event, now)
    await _mark_activated(host, now)
    first = await _mark_first_claim(lead, now)
    return Claimed(lead=lead, event=event, user=host, first=first)
