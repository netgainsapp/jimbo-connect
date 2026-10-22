"""The nightly status poll for event leads.

Signal Scout owns the sending, so it is also the source of truth for when an
email went out, was opened, clicked, answered or bounced. Once a day this asks
it about every approved lead that has not claimed yet and copies those times
onto the lead's `funnel`. First occurrence wins: a time already on the lead is
never replaced, so the funnel keeps the moment something first happened.

The same pass does three things that come from our own data instead:

* rolls the pre-built event to the new anchor when Signal Scout rolled it
  before a send, as long as the host has not claimed the event;
* stamps `funnel.event_passed_at` once the anchor is in the past;
* stamps `funnel.converted_at` for claimed hosts with a second event or a paid
  plan. That runs even when Signal Scout is down.

Nothing here logs or returns an email address.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from bson import ObjectId
from bson.errors import InvalidId

import billing
import event_leads_rules as rules
import event_leads_store as store
import outreach
from database import events, users
from event_leads_approve import CLAIM_VALID_DAYS, NAME_MAX_CHARS

CHUNK_SIZE = 200
# Signal Scout status field -> where it lands on the lead.
STATUS_FIELDS = {
    "sent_at": "funnel.emailed_at",
    "opened_at": "funnel.opened_at",
    "clicked_at": "funnel.clicked_at",
    "replied_at": "funnel.replied_at",
    "bounced_at": "funnel.bounced_at",
    "unsubscribed_at": "funnel.unsubscribed_at",
    "next_step_at": "signal_scout.next_step_at",
}
POLLED_AT = "signal_scout.polled_at"
UNCLAIMED_EVENT = {"provenance.claimed_at": {"$exists": False}}
FREE_PLAN = "free"
EVENTS_FOR_CONVERSION = 2


def _present(doc, dotted):
    for part in dotted.split("."):
        doc = doc.get(part) if isinstance(doc, dict) else None
    return doc is not None


def funnel_updates(lead, prospect):
    """Dotted fields to `$set` from one Signal Scout prospect. A field is
    written only when the lead has no value yet and Signal Scout sent a
    readable, non-null one."""
    out = {}
    for source, dotted in STATUS_FIELDS.items():
        moment = rules.as_utc(prospect.get(source))
        if moment is not None and not _present(lead, dotted):
            out[dotted] = moment
    return out


def _object_id(value):
    try:
        return ObjectId(value) if value else None
    except (InvalidId, TypeError):
        return None


def _anchor_zone(lead):
    try:
        return ZoneInfo((lead.get("anchor") or {}).get("timezone") or "")
    except (ZoneInfoNotFoundError, ValueError):
        return rules.DENVER


def _instant(iso, zone):
    """An ISO string as an aware datetime, naive ones read in `zone`."""
    try:
        moment = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment.replace(tzinfo=zone) if moment.tzinfo is None else moment


def _roll_target(lead, prospect):
    """(name, date text, start) when Signal Scout moved the anchor to a date
    different from the lead's, else None."""
    if not prospect.get("anchor_rolled_since_last_send"):
        return None
    anchor = prospect.get("anchor") or {}
    zone = _anchor_zone(lead)
    start = _instant(anchor.get("date"), zone)
    name = (anchor.get("name") or "").strip()
    if start is None or not name:
        return None
    current = _instant((lead.get("anchor") or {}).get("start"), zone)
    if current is not None and current == start:
        return None
    return name, anchor["date"], start


async def _roll_event(lead, target, now):
    """Rename and re-date the lead's event, only while it is unclaimed (the
    host owns it after that), and return the lead fields to set, or None."""
    name, date_text, start = target
    event_oid = _object_id(lead.get("event_id"))
    if event_oid is None:
        return None
    moved = await events.update_one(
        {"_id": event_oid, **UNCLAIMED_EVENT},
        {"$set": {"name": name[:NAME_MAX_CHARS], "date": start}},
    )
    if moved.matched_count == 0:
        return None
    expires = (start + timedelta(days=CLAIM_VALID_DAYS)).astimezone(timezone.utc)
    return {
        "anchor.title": name,
        "anchor.start": date_text,
        "anchor.rolled_at": now,
        "claim_expires_at": expires,
    }


def _has_passed(lead, rolled_start, now):
    if _present(lead, "funnel.event_passed_at"):
        return False
    start = rolled_start or _instant(
        (lead.get("anchor") or {}).get("start"), _anchor_zone(lead)
    )
    return start is not None and start < now


async def _poll_lead(lead, prospect, now, result):
    """Work out and write everything this poll learns about one lead."""
    fields, rolled_start = {}, None
    if prospect is not None:
        fields.update(funnel_updates(lead, prospect))
        target = _roll_target(lead, prospect)
        rolled = await _roll_event(lead, target, now) if target else None
        if rolled:
            fields.update(rolled)
            rolled_start = target[2]
            result["rolled"] += 1
        result["polled"] += 1
    if _has_passed(lead, rolled_start, now):
        fields["funnel.event_passed_at"] = now
        result["passed"] += 1
    if prospect is not None:
        fields[POLLED_AT] = now
    if not fields:
        return
    await store.update_lead(lead["_id"], fields)
    if set(fields) - {POLLED_AT}:
        result["updated"] += 1


async def _fetch_chunk(number, prospect_ids, errors):
    """The prospects for one chunk, or [] with the reason added to `errors`."""
    try:
        reply = await outreach.fetch_status(prospect_ids)
    except Exception as exc:  # fetch_status never raises; belt and braces
        errors.append(f"status chunk {number}: failed ({type(exc).__name__})")
        return []
    if not reply.get("ok"):
        errors.append(f"status chunk {number}: {reply.get('error') or 'failed'}")
        return []
    return reply.get("prospects") or []


async def _fetch_all(prospect_ids, errors):
    """prospect_id -> status for every chunk that came back."""
    found = {}
    for start in range(0, len(prospect_ids), CHUNK_SIZE):
        chunk = prospect_ids[start:start + CHUNK_SIZE]
        for prospect in await _fetch_chunk(start // CHUNK_SIZE + 1, chunk, errors):
            if prospect.get("prospect_id"):
                found[str(prospect["prospect_id"])] = prospect
    return found


async def _poll_signal_scout(now, result):
    leads = await store.list_pollable_leads()
    ids = list(dict.fromkeys(
        str(lead["signal_scout"]["prospect_id"]) for lead in leads
    ))
    prospects = await _fetch_all(ids, result["errors"])
    failed = 0
    for lead in leads:
        prospect = prospects.get(str(lead["signal_scout"]["prospect_id"]))
        try:
            await _poll_lead(lead, prospect, now, result)
        except Exception:  # one bad lead must not stop the rest
            failed += 1
    if failed:
        result["errors"].append(f"{failed} lead write(s) failed")


async def _has_converted(host_oid):
    """A second event, or any plan other than free."""
    host = await users.find_one({"_id": host_oid})
    if host and billing.plan_of(host) != FREE_PLAN:
        return True
    hosted = await events.count_documents({"created_by": host_oid})
    return hosted >= EVENTS_FOR_CONVERSION


async def _stamp_conversions(now, errors):
    converted = 0
    for lead in await store.list_claimed_unconverted():
        host_oid = _object_id(lead.get("host_user_id"))
        try:
            if host_oid and await _has_converted(host_oid):
                absent = {"funnel.converted_at": {"$exists": False}}
                if await store.update_lead_if(
                    lead["_id"], absent, {"funnel.converted_at": now}
                ):
                    converted += 1
        except Exception as exc:  # the next host still gets checked
            errors.append(f"conversion check failed ({type(exc).__name__})")
    return converted


async def poll_status(now):
    """One nightly pass. Returns the counts and any short, email free errors."""
    result = {"polled": 0, "updated": 0, "rolled": 0, "passed": 0,
              "converted": 0, "errors": []}
    try:
        await _poll_signal_scout(now, result)
    except Exception as exc:  # the conversion pass below still runs
        result["errors"].append(f"status poll failed ({type(exc).__name__})")
    result["converted"] = await _stamp_conversions(now, result["errors"])
    return result
