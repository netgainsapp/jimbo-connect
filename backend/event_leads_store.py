"""Thin Mongo layer for event_leads and event_lead_runs.

Collections are imported by name so tests can monkeypatch the module
attributes. Rules live in event_leads_rules; nothing here decides anything.
"""
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId

from database import app_flags, event_leads, event_lead_runs

# app_flags row holding the auto-approve threshold. Absent means off.
AUTO_APPROVE_FLAG_ID = "event_leads_auto_approve_min_score"
# Every linkedin.status a lead can hold once Approve has queued it.
LINKEDIN_TRACKED = ["queued", "exported", "invited", "connected", "replied", "failed"]


async def get_by_organizer_key(organizer_key):
    return await event_leads.find_one({"organizer_key": organizer_key})


async def upsert_lead(doc):
    """Replace the lead for `doc["organizer_key"]`, inserting it if absent."""
    await event_leads.replace_one(
        {"organizer_key": doc["organizer_key"]}, doc, upsert=True
    )


async def get_lead(lead_id):
    try:
        oid = ObjectId(lead_id)
    except (InvalidId, TypeError):
        return None
    return await event_leads.find_one({"_id": oid})


async def get_lead_by_claim_hash(token_hash):
    """The live lead a claim link points at. An archived lead's link is dead,
    so it is not found here."""
    if not token_hash:
        return None
    return await event_leads.find_one(
        {"claim_token_hash": token_hash, "status": {"$ne": "archived"}}
    )


async def list_leads(show_c):
    """All leads, tier C only when asked. Archived leads are not filtered here."""
    query = {} if show_c else {"score.tier": {"$ne": "C"}}
    return await event_leads.find(query).to_list(None)


async def list_linkedin_queue(include_exported=False):
    """Approved leads whose LinkedIn step is still `queued`, plus the already
    `exported` ones when asked (to recover a lost download). The caller drops
    the ones without a profile URL."""
    wanted = ["queued", "exported"] if include_exported else ["queued"]
    return await event_leads.find(
        {"status": "approved", "linkedin.status": {"$in": wanted}}
    ).to_list(None)


async def list_linkedin_tracked():
    """Every lead that has entered the LinkedIn queue, for matching results."""
    return await event_leads.find(
        {"linkedin.status": {"$in": LINKEDIN_TRACKED}}
    ).to_list(None)


async def update_lead(oid, fields, unset=()):
    """Set `fields` and drop the `unset` keys on one lead, keyed on `_id`.
    Every write bumps `updated_at`."""
    update = {"$set": {**fields, "updated_at": datetime.now(timezone.utc)}}
    if unset:
        update["$unset"] = {key: "" for key in unset}
    await event_leads.update_one({"_id": oid}, update)


async def update_lead_if(oid, condition, fields):
    """Set `fields` on one lead only while `condition` still holds. Returns
    whether it matched, so a caller that lost a race can re-read instead."""
    update = {"$set": {**fields, "updated_at": datetime.now(timezone.utc)}}
    result = await event_leads.update_one({"_id": oid, **condition}, update)
    return result.matched_count > 0


async def take_approve_lease(oid, now, ttl):
    """Mark one lead as being approved. Wins when no Approve holds it or the
    holder's lease is older than `ttl` (it crashed). Bookkeeping only, so it
    does not bump `updated_at`."""
    free = {"$or": [
        {"approving_at": {"$exists": False}},
        {"approving_at": {"$lt": now - ttl}},
    ]}
    result = await event_leads.update_one(
        {"_id": oid, **free}, {"$set": {"approving_at": now}}
    )
    return result.matched_count > 0


async def release_approve_lease(oid, held_at):
    """Drop the lease taken at `held_at`, never one a later Approve took over."""
    await event_leads.update_one(
        {"_id": oid, "approving_at": held_at}, {"$unset": {"approving_at": ""}}
    )


async def record_run(run):
    await event_lead_runs.insert_one(
        {**run, "received_at": datetime.now(timezone.utc)}
    )


async def get_auto_approve_min_score():
    """The auto-approve threshold, or None when auto-approve is off."""
    doc = await app_flags.find_one({"_id": AUTO_APPROVE_FLAG_ID}) or {}
    value = doc.get("value")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


async def set_auto_approve_min_score(value):
    """Store the threshold; None deletes the row, which turns auto-approve off."""
    if value is None:
        await app_flags.delete_one({"_id": AUTO_APPROVE_FLAG_ID})
        return
    await app_flags.update_one(
        {"_id": AUTO_APPROVE_FLAG_ID}, {"$set": {"value": value}}, upsert=True
    )
