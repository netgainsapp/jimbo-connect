"""Self-serve guest invitations. A host emails their guest list a join link, and
a scheduled tick reminds anyone who has not joined yet. Each invite points at the
existing /join/{code} flow, so the guest signs up (or logs in) and lands in the
event with no pre-created accounts or temp passwords.

Dormant-safe: every send is gated on email_send.is_configured(), so with no
Resend key this is a no-op. Plain voice, no dashes, no emoji.
"""
import html
import os
import re
from datetime import datetime, timedelta, timezone

from database import event_invites, events
import email_send

APP_URL = os.getenv("FRONTEND_URL", "https://jimbo.frontrangedev.co").split(",")[0].rstrip("/")

# Reminder cadence for guests who have not joined: days after the invite.
REMINDER_DAYS = [2, 5]
MAX_REMINDERS = len(REMINDER_DAYS)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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


def invite_subject(event_name: str) -> str:
    return f"You are invited to {event_name}"


def invite_body(event_name: str, host_name: str, join_url: str) -> str:
    host = host_name or "Your host"
    return (
        f"Hi,\n\n"
        f"{host} invited you to {event_name} on Intro Connect. After the event, "
        "everyone who came is in one private, searchable directory, so you can "
        "save the people you meet, keep a private note, and message them later.\n\n"
        f"Join here: {join_url}\n\n"
        "It takes a minute and it is free for guests.\n\n"
        "See you there."
    )


def reminder_body(event_name: str, host_name: str, join_url: str) -> str:
    host = host_name or "your host"
    return (
        f"Hi,\n\n"
        f"A quick nudge: you were invited to {event_name} by {host}, and you have "
        "not joined yet. Joining puts you in the event directory so you can find "
        "and message the people you meet.\n\n"
        f"Join here: {join_url}\n\n"
        "Free for guests, takes a minute."
    )


async def send_event_invites(event: dict, raw_emails, host_name: str) -> dict:
    """Record and email invites for an event. Dormant when Resend is not
    configured (no records written either), so the invite + reminder state never
    gets ahead of actually-sent mail."""
    emails = normalize_emails(raw_emails)
    if not emails:
        return {"invited": 0, "sent": 0}
    if not email_send.is_configured():
        return {"invited": 0, "sent": 0, "skipped": "email_not_configured"}
    now = datetime.now(timezone.utc)
    # Anti-abuse: skip any address invited to ANY event in the last 24h, so the
    # same person cannot be re-blasted across events.
    cutoff = now - timedelta(hours=24)
    recent = await event_invites.find(
        {"email": {"$in": emails}, "invited_at": {"$gte": cutoff}}, {"email": 1}
    ).to_list(None)
    recent_set = {r["email"] for r in recent}
    to_send = [e for e in emails if e not in recent_set]
    join_url = _join_url(event["join_code"])
    sent = 0
    for email in to_send:
        await event_invites.update_one(
            {"event_id": event["_id"], "email": email},
            {
                "$setOnInsert": {
                    "event_id": event["_id"],
                    "email": email,
                    "host_name": host_name or "",
                    "invited_at": now,
                    "joined_at": None,
                    "reminder_step": 0,
                }
            },
            upsert=True,
        )
        result = await email_send.send_email(
            to=email,
            subject=invite_subject(event["name"]),
            html=_html(invite_body(event["name"], host_name, join_url)),
            text=invite_body(event["name"], host_name, join_url),
        )
        if result.get("sent"):
            sent += 1
    return {
        "invited": len(to_send),
        "skipped_recent": len(emails) - len(to_send),
        "sent": sent,
    }


async def mark_joined(event_id, email: str) -> None:
    """Mark an invite as joined so the reminder drip stops. No-op if not invited."""
    await event_invites.update_one(
        {"event_id": event_id, "email": (email or "").lower()},
        {"$set": {"joined_at": datetime.now(timezone.utc)}},
    )


async def run_invite_reminder_tick() -> dict:
    """Send one due reminder per pending invite. Idempotent: reminder_step only
    moves forward, capped at MAX_REMINDERS."""
    if not email_send.is_configured():
        return {"ok": False, "skipped": "email_not_configured"}
    now = datetime.now(timezone.utc)
    processed = sent = 0
    cursor = event_invites.find(
        {"joined_at": None, "reminder_step": {"$lt": MAX_REMINDERS}}
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
        # Atomically claim this reminder slot so a concurrent tick can't
        # double-send. If it doesn't match, another tick already handled it.
        claimed = await event_invites.find_one_and_update(
            {"_id": inv["_id"], "reminder_step": step, "joined_at": None},
            {"$set": {"reminder_step": step + 1, "reminder_last_sent": now}},
        )
        if claimed is None:
            continue
        join_url = _join_url(e["join_code"])
        result = await email_send.send_email(
            to=inv["email"],
            subject=invite_subject(e["name"]),
            html=_html(reminder_body(e["name"], inv.get("host_name", ""), join_url)),
            text=reminder_body(e["name"], inv.get("host_name", ""), join_url),
        )
        if result.get("sent"):
            sent += 1
    return {"ok": True, "processed": processed, "sent": sent}
