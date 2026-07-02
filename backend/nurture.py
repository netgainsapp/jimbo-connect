"""Free-signup nurture sequence. A welcome email on register, then a paced drip
advanced by a scheduled tick (POST /api/nurture/tick). Only self-registered
users are enrolled (nurture_enabled), so bulk-imported attendees are excluded.

Dormant-safe: every send is gated on email_send.is_configured(), so with no
Resend key configured the welcome and the tick are harmless no-ops. Copy mirrors
growth/free-signup-nurture.md (plain voice, no dashes, no emoji).
"""
import html
import os
from datetime import datetime, timezone

from database import users, events
import email_send

# App links (where a host sets up an event) and the marketing pricing page.
APP_URL = os.getenv("FRONTEND_URL", "https://jimbo.frontrangedev.co").split(",")[0].rstrip("/")
MARKETING_URL = os.getenv("MARKETING_URL", "https://jimbo-connect.vercel.app").rstrip("/")
FIRST_EVENT_URL = f"{APP_URL}/events"


def _html(body: str) -> str:
    # Escape first: the attendee name is interpolated into the body and must not
    # inject markup into the email.
    body = html.escape(body)
    paras = [p.strip() for p in body.split("\n\n") if p.strip()]
    return "".join("<p>" + p.replace("\n", "<br>") + "</p>" for p in paras)


def _name(user: dict) -> str:
    return (user.get("profile") or {}).get("name") or "there"


WELCOME_SUBJECT = "welcome to Intro Connect"


def welcome_body(name: str) -> str:
    return (
        f"Hi {name},\n\n"
        "You are in. Intro Connect turns each event you host into a private, "
        "searchable directory of everyone who came, so the connections keep "
        "going after the night ends.\n\n"
        "The fastest way to feel it is to set up your first event. It takes "
        "about five minutes and you get a join code to share.\n\n"
        f"Set up your first event: {FIRST_EVENT_URL}\n\n"
        "Reply to this email any time. A real person reads it.\n\n"
        "Scott"
    )


# Drip steps after the welcome. gate: "no_event" only sends if they have not
# hosted yet; "has_event" only if they have; "always" regardless. A step whose
# gate does not match is skipped (advanced without sending).
STEPS = [
    {
        "after_days": 2,
        "gate": "no_event",
        "subject": "the five minute setup",
        "body": lambda name: (
            f"Hi {name},\n\n"
            "If you have five minutes, here is all it takes to get your first "
            "event live:\n\n"
            "1. Name the event and pick a date. We generate the join code.\n"
            "2. Share the code or link with your guests.\n"
            "3. Ask people to add a photo when they join, so the room remembers "
            "them.\n\n"
            "You can even paste your guest list from any tool and we will create "
            "the accounts for you.\n\n"
            f"Start here: {FIRST_EVENT_URL}\n\n"
            "Scott"
        ),
    },
    {
        "after_days": 5,
        "gate": "always",
        "subject": "the part that happens after the event",
        "body": lambda name: (
            f"Hi {name},\n\n"
            "The night itself is only half the value. The other half is the week "
            "after, when your attendees open the directory, save the people they "
            "met, and send the messages they meant to send.\n\n"
            "A few things that help it land:\n\n"
            "Remind guests at the event that the directory is live. Add a short "
            "welcome note so the room feels like yours. Drop in any speakers or "
            "sponsors so attendees can find them too.\n\n"
            f"Open your event: {FIRST_EVENT_URL}\n\n"
            "Scott"
        ),
    },
    {
        "after_days": 10,
        "gate": "has_event",
        "subject": "when you are ready for more rooms",
        "body": lambda name: (
            f"Hi {name},\n\n"
            "Glad to see Intro Connect working for you. The free plan covers one "
            "event and a directory that stays live for a month. When you are "
            "ready to run more rooms, keep directories permanent, or connect "
            "attendees across every event you host, the paid plans open that "
            "up.\n\n"
            "Starter, 39 dollars a month: a few events and bigger rooms.\n"
            "Pro, 99 dollars a month: unlimited events, your whole network in "
            "one place, and your own custom domain.\n\n"
            f"See the plans: {MARKETING_URL}/#pricing\n\n"
            "No rush, the free plan is yours for as long as you want it.\n\n"
            "Scott"
        ),
    },
]


async def _send(user: dict, subject: str, body: str) -> bool:
    if not email_send.is_configured():
        return False
    result = await email_send.send_email(
        to=user["email"], subject=subject, html=_html(body), text=body
    )
    return bool(result.get("sent"))


async def send_welcome(user: dict) -> bool:
    """Best-effort welcome on register. No-op without Resend."""
    return await _send(user, WELCOME_SUBJECT, welcome_body(_name(user)))


async def _has_event(user_id) -> bool:
    return (await events.count_documents({"created_by": user_id})) > 0


async def run_nurture_tick() -> dict:
    """Advance each enrolled user by at most one step, when due. Idempotent: the
    user's nurture_step only moves forward, so re-running is safe."""
    if not email_send.is_configured():
        return {"ok": False, "skipped": "email_not_configured"}
    now = datetime.now(timezone.utc)
    processed = sent = advanced = 0
    cursor = users.find(
        {"nurture_enabled": True, "nurture_step": {"$lt": len(STEPS)}}
    )
    async for u in cursor:
        processed += 1
        idx = u.get("nurture_step", 0)
        if idx >= len(STEPS):
            continue
        step = STEPS[idx]
        created = u.get("created_at")
        if not created:
            continue
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age_days = (now - created).total_seconds() / 86400
        if age_days < step["after_days"]:
            continue
        has_evt = await _has_event(u["_id"])
        gate = step["gate"]
        if (gate == "no_event" and has_evt) or (gate == "has_event" and not has_evt):
            await users.update_one({"_id": u["_id"]}, {"$set": {"nurture_step": idx + 1}})
            advanced += 1
            continue
        # Atomically claim this step (filter on the current step value) so a
        # concurrent tick can't send the same email twice. If the claim doesn't
        # match, another tick already advanced this user.
        claimed = await users.find_one_and_update(
            {"_id": u["_id"], "nurture_step": idx},
            {"$set": {"nurture_step": idx + 1, "nurture_last_sent": now}},
        )
        if claimed is None:
            continue
        if await _send(u, step["subject"], step["body"](_name(u))):
            sent += 1
    return {"ok": True, "processed": processed, "sent": sent, "advanced": advanced}
