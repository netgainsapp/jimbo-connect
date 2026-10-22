"""A message to an inactive attendee is their activation email (spec section 7).

One email in the event host's name, within a minute of the message, naming who
wrote and where they met, with one button that signs the guest in and opens
the thread. Nothing from the message itself is ever read into the email.
Rules, in order: recipient not yet active; a real message exists; one email
per sender per Denver day; then the sender waits for a reply; senders inside
an hour share one email; COALESCE_SECONDS folds near-simultaneous senders.

State: message_notify_state, one document per recipient per event { senders,
window_opened_at, window_id, sent_at, last_notified, version }. Pure rules sit
at the top, Mongo and sleep plumbing below. Writes are version compare-and-set;
a delivery claims its window by window_id, never by datetime equality (Mongo
keeps milliseconds). The button token goes on users.magic_tokens (hashed,
newest MAGIC_TOKENS_KEPT), consumed once by routers/auth.magic_login; it never
touches users.reset_token.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError

import core
import email_send
import host_templates
from database import event_attendees, events, message_notify_state, messages, users

log = logging.getLogger(__name__)

DENVER = ZoneInfo("America/Denver")
COALESCE_SECONDS = 60
SHARE_WINDOW = timedelta(hours=1)
TOKEN_DAYS = 7
MAGIC_TOKENS_KEPT = 5
SAVE_ATTEMPTS = 3
ONE_SENDER_TEMPLATE = "message-waiting"
MANY_SENDERS_TEMPLATE = "messages-waiting"
ONE_SENDER_BUTTON = "Read the message"
MANY_SENDERS_BUTTON = "Read your messages"
NO_COMPANY = "the guest list"
NO_NAME = "there"
SOMEONE = "Someone"


# ---------------------------------------------------------------------------
# Pure rules
# ---------------------------------------------------------------------------

def _utc(moment: datetime) -> datetime:
    """Mongo hands datetimes back naive; they are UTC."""
    return moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment


def _millis(moment: datetime) -> datetime:
    """UTC at the millisecond precision Mongo stores, so a time this module
    writes reads back equal to the one it kept."""
    moment = _utc(moment).astimezone(timezone.utc)
    return moment.replace(microsecond=moment.microsecond // 1000 * 1000)


def _denver_day(moment: datetime):
    return _utc(moment).astimezone(DENVER).date()


def last_notified_at(state: dict | None, sender_id: str):
    return ((state or {}).get("last_notified") or {}).get(sender_id)


def gate(state: dict | None, sender_id: str, now: datetime, replied: bool) -> str | None:
    """Why this sender may not trigger an email now, or None when they may.
    `replied` says the recipient has written back since the sender's last
    email."""
    last = last_notified_at(state, sender_id)
    if last is None:
        return None
    if _denver_day(last) == _denver_day(now):
        return "daily_cap"
    if not replied:
        return "awaiting_reply"
    return None


def _window_open(state: dict, now: datetime) -> bool:
    opened = state.get("window_opened_at")
    if state.get("sent_at") or opened is None:
        return False
    return _utc(now) - _utc(opened) < timedelta(seconds=COALESCE_SECONDS)


def _carried_senders(state: dict | None, now: datetime) -> list:
    """Senders a new window still names: everyone from an email sent inside the
    last hour, or from a window whose delivery never ran (a restart dropped the
    task), since those people were never named to the recipient."""
    if not state:
        return []
    sent_at = state.get("sent_at")
    if sent_at is None or _utc(now) - _utc(sent_at) <= SHARE_WINDOW:
        return list(state.get("senders") or [])
    return []


def _with_sender(senders: list, card: dict) -> list:
    if any(s["sender_id"] == card["sender_id"] for s in senders):
        return senders
    return [*senders, card]


def next_state(state: dict | None, card: dict, now: datetime):
    """(new_state, action) for a sender who passed the gate. action "open"
    starts a window whose delivery the caller schedules; "coalesced" joins the
    window already waiting to send."""
    last = {**((state or {}).get("last_notified") or {}), card["sender_id"]: now}
    if state and _window_open(state, now):
        senders = _with_sender(list(state.get("senders") or []), card)
        return {**state, "senders": senders, "last_notified": last}, "coalesced"
    senders = _with_sender(_carried_senders(state, now), card)
    new = {"senders": senders, "window_opened_at": now, "sent_at": None,
           "last_notified": last}
    return new, "open"


def pick_event(candidates: list, now: datetime) -> dict | None:
    """The soonest upcoming event, or else the most recent one."""
    dated = [e for e in candidates if isinstance(e.get("date"), datetime)]
    upcoming = [e for e in dated if _utc(e["date"]) >= _utc(now)]
    if upcoming:
        return min(upcoming, key=lambda e: _utc(e["date"]))
    if dated:
        return max(dated, key=lambda e: _utc(e["date"]))
    return candidates[0] if candidates else None


def _first_name(profile: dict, fallback: str) -> str:
    parts = (profile.get("name") or "").split()
    return parts[0] if parts else fallback


def sender_card(sender: dict) -> dict:
    """What the email may say about a sender. Only an https photo is kept: an
    uploaded photo is a data URL no email client renders, and the public photo
    route serves hosts only."""
    profile = sender.get("profile") or {}
    photo = (profile.get("photo_url") or "").strip()
    return {
        "sender_id": str(sender["_id"]),
        "first_name": _first_name(profile, SOMEONE),
        "company": (profile.get("company") or "").strip(),
        "role": (profile.get("role") or "").strip(),
        "photo_url": photo if photo.startswith("https://") else "",
    }


def _describe(card: dict) -> str:
    """"Marcus (Founder at Ramble Labs)", dropping whatever is missing."""
    role, company = card.get("role"), card.get("company")
    detail = f"{role} at {company}" if role and company else role or company
    return f"{card['first_name']} ({detail})" if detail else card["first_name"]


def _join_names(parts: list) -> str:
    return parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} and {parts[-1]}"


def _event_date(event: dict) -> str:
    when = event.get("date")
    return f"{when:%B} {when.day}, {when.year}" if isinstance(when, datetime) else ""


def email_context(senders: list, event: dict, recipient: dict, host_name: str) -> dict:
    """Merge variables for both message templates. No message text exists
    anywhere in here: the senders are cards, not messages."""
    first = senders[0]
    others = len(senders) - 1
    second = senders[1]["first_name"] if others == 1 else f"{others} others"
    return {
        "attendee_name": _first_name(recipient.get("profile") or {}, NO_NAME),
        "host_name": host_name,
        "event_name": event.get("name") or "",
        "event_date": _event_date(event),
        "sender_first": first["first_name"],
        "sender_company": first.get("company") or NO_COMPANY,
        "sender_role": first.get("role") or "",
        "sender_line": _describe(first),
        "sender2_first": second if others else "",
        "senders_line": _join_names([_describe(s) for s in senders]),
    }


def button_for(senders: list, token: str) -> tuple:
    """(label, url): one sender opens their thread, several open the inbox."""
    if len(senders) == 1:
        target = f"/messages/{senders[0]['sender_id']}"
        label = ONE_SENDER_BUTTON
    else:
        target, label = "/messages", MANY_SENDERS_BUTTON
    return label, f"{core.APP_URL}/reset-password/{token}?next={target}"


# ---------------------------------------------------------------------------
# Plumbing: Mongo reads and writes, the window sleep, the send
# ---------------------------------------------------------------------------

_sleep = asyncio.sleep
_background: set = set()


def _result(reason: str | None = None) -> dict:
    return {"sent": True} if reason is None else {"sent": False, "reason": reason}


async def _has_message(sender_id, recipient_id) -> bool:
    found = await messages.find_one({"from_user_id": sender_id,
                                     "to_user_id": recipient_id,
                                     "text": {"$regex": r"\S"}}, {"_id": 1})
    return found is not None


async def _replied_since(recipient_id, sender_id, since) -> bool:
    if since is None:
        return False
    found = await messages.find_one({"from_user_id": recipient_id,
                                     "to_user_id": sender_id,
                                     "sent_at": {"$gt": since}}, {"_id": 1})
    return found is not None


STATE_FIELDS = ("senders", "last_notified", "window_opened_at", "sent_at", "window_id")


async def _save(key: dict, prev: dict | None, new: dict) -> bool:
    """Compare-and-set on `version`. False when someone else wrote first.
    Writes only the state fields, never _id or the key."""
    fields = {k: new[k] for k in STATE_FIELDS if k in new}
    if prev is None:
        try:
            await message_notify_state.insert_one({**key, **fields, "version": 1})
        except DuplicateKeyError:
            return False
        return True
    version = prev.get("version", 0)
    res = await message_notify_state.update_one(
        {**key, "version": version}, {"$set": {**fields, "version": version + 1}})
    return res.matched_count == 1


async def _record(sender: dict, recipient_id, event_id, now: datetime) -> tuple:
    """Apply the gate and next_state against the stored row: (reason or
    action, window_id). A window this call opens gets a fresh window_id, which
    is what its delivery claims it by."""
    key = {"recipient_id": recipient_id, "event_id": event_id}
    card = sender_card(sender)
    for _ in range(SAVE_ATTEMPTS):
        state = await message_notify_state.find_one(key)
        since = last_notified_at(state, card["sender_id"])
        replied = await _replied_since(recipient_id, sender["_id"], since)
        reason = gate(state, card["sender_id"], now, replied)
        if reason:
            return reason, None
        new, action = next_state(state, card, now)
        if action == "open":
            new = {**new, "window_id": uuid.uuid4().hex}
        if await _save(key, state, new):
            return action, new.get("window_id")
    return "busy", None


async def _claim(key: dict, window_id: str, send_at: datetime) -> list | None:
    """Close the window this delivery owns and take its senders, or None when
    another delivery or a newer window owns it."""
    for _ in range(SAVE_ATTEMPTS):
        state = await message_notify_state.find_one(key)
        if not state or state.get("sent_at") or state.get("window_id") != window_id:
            return None
        if await _save(key, state, {"sent_at": send_at}):
            return list(state.get("senders") or [])
    return None


async def _still_inactive(recipient_id, event_id) -> dict | None:
    recipient = await users.find_one({"_id": recipient_id})
    membership = await event_attendees.find_one(
        {"event_id": event_id, "user_id": recipient_id})
    if not recipient or not membership or core.is_active(recipient, membership):
        return None
    return recipient


async def _host_user(event: dict) -> dict | None:
    """created_by is stored as an ObjectId or a string (see _can_manage_event)."""
    try:
        host_id = ObjectId(str(event.get("created_by")))
    except (InvalidId, TypeError):
        return None
    return await users.find_one({"_id": host_id})


async def _send(recipient: dict, event: dict, senders: list, send_at: datetime) -> dict:
    host_user = await _host_user(event)
    host = core.host_block(host_user)
    ctx = email_context(senders, event, recipient, (host or {}).get("name", ""))
    template = ONE_SENDER_TEMPLATE if len(senders) == 1 else MANY_SENDERS_TEMPLATE
    rendered = await host_templates.render_for_host(
        template, ctx, (host_user or {}).get("_id"))
    if not rendered:
        return _result("template_missing")
    token = core._new_reset_token()
    entry = {"hash": core._hash_token(token),
             "expires_at": send_at + timedelta(days=TOKEN_DAYS)}
    await users.update_one({"_id": recipient["_id"]}, {"$push": {
        "magic_tokens": {"$each": [entry], "$slice": -MAGIC_TOKENS_KEPT}}})
    label, url = button_for(senders, token)
    avatars = [{"url": s["photo_url"], "alt": s["first_name"]}
               for s in senders if s.get("photo_url")]
    return await email_send.send_template_branded(
        recipient["email"], rendered, button_label=label, button_url=url,
        host=host, avatars=avatars)


async def _deliver_after_window(key: dict, event: dict, window_id: str,
                                opened_at: datetime) -> None:
    """Background task: wait out the window, then send one email naming every
    sender it collected. Logs carry no address and no message text."""
    try:
        await _sleep(COALESCE_SECONDS)
        send_at = _utc(opened_at) + timedelta(seconds=COALESCE_SECONDS)
        senders = await _claim(key, window_id, send_at)
        recipient = await _still_inactive(key["recipient_id"], key["event_id"])
        if not senders or not recipient or not recipient.get("email"):
            return
        result = await _send(recipient, event, senders, send_at)
        if not result.get("sent"):
            log.info("message notify email not sent for event %s", key["event_id"])
    except Exception as exc:  # never let a background task die loudly with data
        log.warning("message notify send failed (%s)", type(exc).__name__)


def _spawn(coro) -> None:
    task = asyncio.create_task(coro)
    _background.add(task)
    task.add_done_callback(_background.discard)


async def _maybe_notify(sender: dict, recipient: dict, event: dict, now: datetime) -> dict:
    membership = await event_attendees.find_one(
        {"event_id": event["_id"], "user_id": recipient["_id"]})
    if core.is_active(recipient, membership):
        return _result("recipient_active")
    if not await _has_message(sender["_id"], recipient["_id"]):
        return _result("no_message")
    action, window_id = await _record(sender, recipient["_id"], event["_id"], now)
    if action != "open":
        return _result(action)
    key = {"recipient_id": recipient["_id"], "event_id": event["_id"]}
    _spawn(_deliver_after_window(key, event, window_id, now))
    return _result()


async def maybe_notify(sender: dict, recipient: dict, event: dict, now: datetime) -> dict:
    """{sent: True} when an email is on its way (it leaves when the window
    closes), else {sent: False, reason}. Never raises."""
    try:
        return await _maybe_notify(sender, recipient, event, _millis(now))
    except Exception as exc:
        log.warning("message notify failed (%s)", type(exc).__name__)
        return _result("error")


async def _event_ids(query: dict) -> set:
    return {link["event_id"] async for link in event_attendees.find(query, {"event_id": 1})}


async def resolve_event(sender_id, recipient_id, now: datetime) -> dict | None:
    """The event the two share where the recipient is not yet active: the
    sender is a member too, or hosts it."""
    waiting = await _event_ids({"user_id": recipient_id, "activated": False})
    if not waiting:
        return None
    shared = waiting & await _event_ids({"user_id": sender_id})
    candidates = []
    async for event in events.find({"_id": {"$in": list(waiting)}}):
        if event["_id"] in shared or str(event.get("created_by")) == str(sender_id):
            candidates.append(event)
    return pick_event(candidates, now)


async def notify_for_message(sender: dict, recipient: dict, now: datetime) -> dict:
    """What POST /api/messages calls after the insert. Never raises."""
    try:
        event = await resolve_event(sender["_id"], recipient["_id"], now)
    except Exception as exc:
        log.warning("message notify lookup failed (%s)", type(exc).__name__)
        return _result("error")
    if event is None:
        return _result("no_shared_event")
    return await maybe_notify(sender, recipient, event, now)
