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

from database import users, events, event_attendees
import email_send

# App links (where a host sets up an event) and the marketing pricing page.
from app_url import APP_URL

MARKETING_URL = os.getenv("MARKETING_URL", "https://intro-connect.com").rstrip("/")
FIRST_EVENT_URL = f"{APP_URL}/events"
# Deep link that opens the create form on arrival (see MyEvents ?host=1).
HOST_EVENT_URL = f"{APP_URL}/events?host=1"


def _html(body: str) -> str:
    # Escape first: the attendee name is interpolated into the body and must not
    # inject markup into the email.
    body = html.escape(body)
    paras = [p.strip() for p in body.split("\n\n") if p.strip()]
    return "".join("<p>" + p.replace("\n", "<br>") + "</p>" for p in paras)


def _name(user: dict) -> str:
    return (user.get("profile") or {}).get("name") or "there"


WELCOME_SUBJECT = "welcome to Intro Connect"
WELCOME_HEADING = "Welcome to Intro Connect"


def welcome_paragraphs(name: str) -> list:
    return [
        f"Hi {name},",
        "You are in. Intro Connect turns each event you host into a private, "
        "searchable directory of everyone who came, so the connections keep "
        "going after the night ends.",
        "The fastest way to feel it is to set up your first event. It takes "
        "about five minutes and you get a join code to share.",
        "Reply to this email any time. A real person reads it.",
        "Scott",
    ]


# Drip steps after the welcome. Gates, mutually exclusive for the first three
# so nobody gets two host pitches in one lifecycle:
#   "cold_host" they host nothing and have joined nothing (signed up on spec)
#   "attendee"  they host nothing but have been a guest in someone else's room
#   "has_event" they host at least one event
#   "always"    everyone
# A step whose gate does not match is skipped (advanced without sending). Each
# step supplies a heading, paragraph list, and a button rendered by the branded
# email layout.
STEPS = [
    {
        "after_days": 2,
        "gate": "cold_host",
        "subject": "the five minute setup",
        "heading": "The five minute setup",
        "paragraphs": lambda name: [
            f"Hi {name},",
            "If you have five minutes, here is all it takes to get your first "
            "event live: name the event and pick a date and we generate the join "
            "code, share the code or link with your guests, and ask people to add "
            "a photo when they join so the room remembers them.",
            "You can even paste your guest list from any tool and we will create "
            "the accounts for you.",
            "Scott",
        ],
        "button": {"label": "Start your first event", "url": FIRST_EVENT_URL},
    },
    {
        # The attendee to host loop. Guests have already felt the directory
        # work, so this speaks from that experience instead of pitching cold.
        "after_days": 3,
        "gate": "attendee",
        "subject": "the room you were just in",
        "heading": "The room you were just in",
        "paragraphs": lambda name: [
            f"Hi {name},",
            "You joined an event on Intro Connect, so you have already seen the "
            "part that matters. The directory stays live after the night ends, "
            "and the people you met are still there next week when you actually "
            "need them.",
            "If you run anything of your own, a dinner, a meetup, a class, a "
            "chamber morning, you can give your guests the same thing. It takes "
            "about five minutes to set up and your first event is free.",
            "Scott",
        ],
        "button": {"label": "Host your own event", "url": HOST_EVENT_URL},
    },
    {
        "after_days": 5,
        "gate": "always",
        "subject": "the part that happens after the event",
        "heading": "The part that happens after the event",
        "paragraphs": lambda name: [
            f"Hi {name},",
            "The night itself is only half the value. The other half is the week "
            "after, when your attendees open the directory, save the people they "
            "met, and send the messages they meant to send.",
            "A few things that help it land: remind guests at the event that the "
            "directory is live, add a short welcome note so the room feels like "
            "yours, and drop in any speakers or sponsors so attendees can find "
            "them too.",
            "Scott",
        ],
        "button": {"label": "Open your event", "url": FIRST_EVENT_URL},
    },
    {
        # Every reason to upgrade named here has to be a real plan gate, and
        # there are exactly three: event count and attendees per event
        # (billing.event_limit_for / attendee_limit_for) and host branding
        # (branding.plan_allows, pro only). Everything else works on free, so
        # it cannot be sold as an unlock. Rewritten 2026-08-02: this email had
        # been promising a directory that expires after a month, permanent
        # directories as a paid upgrade, and a cross event network. No expiry
        # exists, so the first two sold a difference that is not there, and the
        # cross event directory is a free feature.
        "after_days": 10,
        "gate": "has_event",
        "subject": "when you are ready for more rooms",
        "heading": "When you are ready for more rooms",
        "paragraphs": lambda name: [
            f"Hi {name},",
            "Glad to see Intro Connect working for you. The free plan covers "
            "one event with up to 50 guests, and the parts you have been using "
            "stay free either way: the directory, messaging, saved contacts, "
            "sponsors and the agenda builder.",
            "Hosts move up for three reasons and that is all of them: more "
            "events, bigger rooms, or your own brand on the page. Starter, 39 "
            "dollars a month: up to 3 events and 250 guests in each. Pro, 99 "
            "dollars a month: unlimited events, up to 2,000 guests in each, "
            "and your logo and color on your event pages and guest emails.",
            "No rush, the free plan is yours for as long as you want it.",
            "Scott",
        ],
        "button": {"label": "See the plans", "url": f"{MARKETING_URL}/#pricing"},
    },
]


async def _send(user: dict, subject: str, heading: str, paragraphs: list, button: dict) -> bool:
    if not email_send.is_configured():
        return False
    # Marketing send: branded layout + suppression list + unsubscribe footer
    # and List-Unsubscribe headers.
    result = await email_send.send_branded(
        to=user["email"],
        subject=subject,
        heading=heading,
        paragraphs=paragraphs,
        button=button,
        marketing=True,
    )
    return bool(result.get("sent"))


async def send_welcome(user: dict) -> bool:
    """Best-effort welcome on register. No-op without Resend."""
    return await _send(
        user,
        WELCOME_SUBJECT,
        WELCOME_HEADING,
        welcome_paragraphs(_name(user)),
        {"label": "Set up your first event", "url": FIRST_EVENT_URL},
    )


async def _has_event(user_id) -> bool:
    return (await events.count_documents({"created_by": user_id})) > 0


async def _has_joined_others(user_id) -> bool:
    """True when the user has joined an event somebody else hosts. That is the
    attendee signal: they have experienced the directory as a guest, which is
    what the attendee to host step speaks to."""
    ids = [
        link["event_id"]
        async for link in event_attendees.find({"user_id": user_id}, {"event_id": 1})
    ]
    if not ids:
        return False
    return (
        await events.count_documents(
            {"_id": {"$in": ids}, "created_by": {"$ne": user_id}}
        )
    ) > 0


def gate_matches(gate: str, has_event: bool, joined_others: bool) -> bool:
    """Whether a step applies to this user. Pure so the routing is testable
    without a database. Unknown gates never send (fail closed)."""
    if gate == "always":
        return True
    if gate == "has_event":
        return has_event
    if gate == "attendee":
        return not has_event and joined_others
    if gate == "cold_host":
        return not has_event and not joined_others
    return False


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
        # Only the attendee/cold_host split needs the join lookup, so skip the
        # extra queries for steps that cannot care.
        joined = (
            await _has_joined_others(u["_id"])
            if step["gate"] in ("attendee", "cold_host")
            else False
        )
        if not gate_matches(step["gate"], has_evt, joined):
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
        name = _name(u)
        if await _send(
            u, step["subject"], step["heading"], step["paragraphs"](name), step["button"]
        ):
            sent += 1
    return {"ok": True, "processed": processed, "sent": sent, "advanced": advanced}
