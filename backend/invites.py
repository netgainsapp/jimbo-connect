"""Self-serve guest invitations. A host emails their guest list a join link, and
a scheduled tick reminds anyone who has not joined yet. Each invite points at the
existing /join/{code} flow, so the guest signs up (or logs in) and lands in the
event with no pre-created accounts or temp passwords.

Dormant-safe: every send is gated on email_send.is_configured(), so with no
Resend key this is a no-op. Plain voice, no dashes, no emoji.

Every invite and reminder ends with a remove-me link, because the host put the
guest on the list, not the guest. The link is signed over one event and one
address, so it takes that guest off that event and nothing else, and the
`removed_at` it leaves on the invite row keeps them off: reminders, re-invites
and re-imports all skip it.
"""
import base64
import hashlib
import hmac
import html
import os
import re
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from database import event_attendees, event_invites, events, users
import branding
import core
import email_send
import suppression
from event_leads_rules import days_until

from app_url import APP_URL
from send_report import tally_failure

# Reminder cadence for guests who have not joined: days after the invite.
REMINDER_DAYS = [2, 5]
MAX_REMINDERS = len(REMINDER_DAYS)
# Reminders stop once the event is less than this many Denver calendar days
# away, so the last one a guest can get lands the day before.
REMINDER_CUTOFF_DAYS = 1

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_OBJECT_ID_RE = re.compile(r"^[0-9a-f]{24}$")
# Signed into every remove token so an unsubscribe signature, which covers a
# bare address with the same secret, can never pass as one of these.
_REMOVE_PURPOSE = "invite-remove"


def _join_url(code: str) -> str:
    return f"{APP_URL}/join/{code}"


def _html(body: str) -> str:
    # Escape first: event names and host names are attacker-controlled and must
    # not inject markup into the platform-branded email.
    body = html.escape(body)
    paras = [p.strip() for p in body.split("\n\n") if p.strip()]
    return "".join("<p>" + p.replace("\n", "<br>") + "</p>" for p in paras)


def normalize_emails(raw) -> list:
    """Lowercase, trim, de-dupe, keep only well-formed addresses. Accepts a list
    or a free-text blob split on commas / whitespace / newlines."""
    if isinstance(raw, str):
        parts = re.split(r"[\s,;]+", raw)
    else:
        parts = list(raw or [])
    seen = set()
    out = []
    for p in parts:
        e = str(p).strip().lower()
        if e and _EMAIL_RE.match(e) and e not in seen:
            seen.add(e)
            out.append(e)
    return out


def _sign_removal(payload: str) -> str:
    message = f"{_REMOVE_PURPOSE}:{payload}".encode()
    return hmac.new(suppression._unsub_secret(), message, hashlib.sha256).hexdigest()


def make_remove_token(event_id, email: str) -> str:
    """b64url("{event_id}:{email}").hmac_hex, the unsubscribe token's shape."""
    payload = f"{event_id}:{(email or '').strip().lower()}"
    body = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    return f"{body}.{_sign_removal(payload)}"


def verify_remove_token(token):
    """Return (event ObjectId, email) for a genuine token, or None. Never raises."""
    if not token or not isinstance(token, str) or "." not in token:
        return None
    body, sig = token.rsplit(".", 1)
    try:
        padded = body + "=" * (-len(body) % 4)
        payload = base64.urlsafe_b64decode(padded.encode()).decode()
    except Exception:
        return None
    event_id, _, email = payload.partition(":")
    if not _OBJECT_ID_RE.match(event_id) or not _EMAIL_RE.match(email):
        return None
    # Bytes, not str: compare_digest raises on a non ASCII string.
    if not hmac.compare_digest(sig.encode(), _sign_removal(payload).encode()):
        return None
    return ObjectId(event_id), email


def remove_url(event_id, email: str) -> str:
    token = make_remove_token(event_id, email)
    return f"{suppression.API_PUBLIC_URL}/api/invites/remove/{token}"


def remove_paragraph(url: str) -> str:
    return f"If you would rather not be on this list, remove yourself: {url}"


async def removed_emails(event_id, emails) -> set:
    """The addresses among `emails` that used the remove link for this event."""
    rows = await event_invites.find(
        {
            "event_id": event_id,
            "email": {"$in": list(emails)},
            "removed_at": {"$ne": None},
        },
        {"email": 1},
    ).to_list(None)
    return {r["email"] for r in rows}


async def apply_removal(event_id, email: str):
    """Take this guest off this one event and keep them off. Returns the event
    (None if it was deleted) so the page can name it."""
    person = await users.find_one({"email": email})
    if person:
        await event_attendees.delete_one(
            {"event_id": event_id, "user_id": person["_id"]}
        )
    # Upsert: an imported guest has no invite row yet, and the marker is what
    # a later import checks.
    await event_invites.update_one(
        {"event_id": event_id, "email": email},
        {
            "$set": {"removed_at": datetime.now(timezone.utc)},
            "$setOnInsert": {"joined_at": None, "reminder_step": MAX_REMINDERS},
        },
        upsert=True,
    )
    return await events.find_one({"_id": event_id})


async def removal_event(event_id):
    """The event a remove link names, read only, for the confirm page."""
    return await events.find_one({"_id": event_id})


def _too_close_to_remind(event_date, now) -> bool:
    """Less than a Denver calendar day to go, or already past. A date Mongo
    hands back naive is UTC."""
    if not isinstance(event_date, datetime):
        return False
    if event_date.tzinfo is None:
        event_date = event_date.replace(tzinfo=timezone.utc)
    return days_until(event_date.isoformat(), now) < REMINDER_CUTOFF_DAYS


def invite_subject(event_name: str) -> str:
    return f"{event_name}: you are invited"


def reminder_subject(event_name: str) -> str:
    return f"{event_name}: your host is waiting for you"


def invite_heading(event_name: str) -> str:
    return f"You are invited to {event_name}"


def invite_paragraphs(event_name: str, host_name: str) -> list:
    host = host_name or "Your host"
    return [
        f"{host} invited you to {event_name}. After the event, everyone who came "
        "is in one private, searchable directory, so you can save the people you "
        "meet, keep a private note, and message them later.",
        "It takes a minute and it is free for guests. See you there.",
    ]


def reminder_paragraphs(event_name: str, host_name: str) -> list:
    host = host_name or "your host"
    return [
        f"A quick nudge: you were invited to {event_name} by {host}, and you have "
        "not joined yet. Joining puts you in the event directory so you can find "
        "and message the people you meet.",
        "Free for guests, takes a minute.",
    ]


def _summary(
    attempted: int, sent: int, skipped_recent: int, failures: dict, removed: int = 0
) -> dict:
    """`invited` stays the attempted count it has always been. `sent` is the
    only number that means mail actually left. `removed` counts guests who
    took themselves off this event's list and were left alone."""
    return {
        "invited": attempted,
        "skipped_recent": skipped_recent,
        "removed": removed,
        "sent": sent,
        "failed": attempted - sent,
        "failures": failures,
    }


async def send_event_invites(
    event: dict,
    raw_emails,
    host_name: str,
    host_brand: dict | None = None,
    host: dict | None = None,
) -> dict:
    """Record and email invites for an event. Dormant when Resend is not
    configured (no records written either), so the invite + reminder state never
    gets ahead of actually-sent mail. `host` (core.host_block) sends each invite
    as the host: their name, photo and reply-to."""
    emails = normalize_emails(raw_emails)
    if not emails:
        return _summary(0, 0, 0, {})
    if not email_send.is_configured():
        return {**_summary(0, 0, 0, {}), "skipped": "email_not_configured"}
    now = datetime.now(timezone.utc)
    # Anti-abuse: skip any address invited to ANY event in the last 24h, so the
    # same person cannot be re-blasted across events.
    cutoff = now - timedelta(hours=24)
    recent = await event_invites.find(
        {"email": {"$in": emails}, "invited_at": {"$gte": cutoff}}, {"email": 1}
    ).to_list(None)
    recent_set = {r["email"] for r in recent}
    removed = await removed_emails(event["_id"], emails)
    to_send = [e for e in emails if e not in recent_set and e not in removed]
    skipped_recent = sum(1 for e in emails if e in recent_set and e not in removed)
    join_url = _join_url(event["join_code"])
    sent = 0
    failures: dict = {}
    for email in to_send:
        # Send first. invited_at is what the 24h window above is keyed on, so
        # stamping it before the send means one rejected message locks the
        # address out of any retry for a day, and the reminder drip starts for
        # mail that never left.
        result = await email_send.send_branded(
            to=email,
            subject=invite_subject(event["name"]),
            heading=invite_heading(event["name"]),
            paragraphs=invite_paragraphs(event["name"], host_name)
            + [remove_paragraph(remove_url(event["_id"], email))],
            button={"label": "Join the event", "url": join_url},
            marketing=True,
            brand=host_brand,
            host=host,
        )
        if not result.get("sent"):
            tally_failure(failures, result.get("reason"))
            continue
        sent += 1
        await event_invites.update_one(
            {"event_id": event["_id"], "email": email},
            {
                # $set, not $setOnInsert: an address invited once must still be
                # protected the next time, and only a landed send moves the
                # window forward.
                "$set": {"invited_at": now},
                "$setOnInsert": {
                    "event_id": event["_id"],
                    "email": email,
                    "host_name": host_name or "",
                    "joined_at": None,
                    "reminder_step": 0,
                },
            },
            upsert=True,
        )
    return _summary(len(to_send), sent, skipped_recent, failures, len(removed))


async def mark_joined(event_id, email: str) -> None:
    """Mark an invite as joined so the reminder drip stops. No-op if not invited."""
    await event_invites.update_one(
        {"event_id": event_id, "email": (email or "").lower()},
        {"$set": {"joined_at": datetime.now(timezone.utc)}},
    )


async def _send_reminder(inv: dict, e: dict) -> bool:
    """One reminder for an invite whose slot the tick has already claimed."""
    host = await users.find_one({"_id": e["created_by"]}) if e.get("created_by") else None
    result = await email_send.send_branded(
        to=inv["email"],
        subject=reminder_subject(e["name"]),
        heading=invite_heading(e["name"]),
        paragraphs=reminder_paragraphs(e["name"], inv.get("host_name", ""))
        + [remove_paragraph(remove_url(e["_id"], inv["email"]))],
        button={"label": "Join the event", "url": _join_url(e["join_code"])},
        marketing=True,
        brand=branding.email_brand(host) if host else None,
        # A host who has since been deleted falls back to the platform layout.
        host=core.host_block(host),
    )
    return bool(result.get("sent"))


async def run_invite_reminder_tick(now: datetime | None = None) -> dict:
    """Send one due reminder per pending invite. Idempotent: reminder_step only
    moves forward, capped at MAX_REMINDERS. `now` is for tests."""
    if not email_send.is_configured():
        return {"ok": False, "skipped": "email_not_configured"}
    now = now or datetime.now(timezone.utc)
    processed = sent = 0
    cursor = event_invites.find(
        {
            "joined_at": None,
            "reminder_step": {"$lt": MAX_REMINDERS},
            "removed_at": None,
        }
    )
    async for inv in cursor:
        processed += 1
        step = inv.get("reminder_step", 0)
        if step >= MAX_REMINDERS:
            continue
        invited_at = inv.get("invited_at")
        if not invited_at:
            continue
        if invited_at.tzinfo is None:
            invited_at = invited_at.replace(tzinfo=timezone.utc)
        age_days = (now - invited_at).total_seconds() / 86400
        if age_days < REMINDER_DAYS[step]:
            continue
        e = await events.find_one({"_id": inv["event_id"]})
        if not e:
            # Event was deleted; stop reminding.
            await event_invites.update_one(
                {"_id": inv["_id"]}, {"$set": {"reminder_step": MAX_REMINDERS}}
            )
            continue
        if _too_close_to_remind(e.get("date"), now):
            # Left at its step on purpose: nothing goes out this close to the
            # event, and an event moved later can still pick the drip back up.
            continue
        # Atomically claim this reminder slot so a concurrent tick can't
        # double-send. If it doesn't match, another tick already handled it.
        claimed = await event_invites.find_one_and_update(
            {"_id": inv["_id"], "reminder_step": step, "joined_at": None},
            {"$set": {"reminder_step": step + 1, "reminder_last_sent": now}},
        )
        if claimed is None:
            continue
        if await _send_reminder(inv, e):
            sent += 1
    return {"ok": True, "processed": processed, "sent": sent}
