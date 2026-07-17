"""Sales & outreach email template library for the team to copy and send by
hand. Distinct from email_templates (transactional, sent by the app) and from
signal-scout's automated drip. Plain reusable copy the team grabs when reaching
out to a prospective host.

Bodies use {first_name} / {company} / {event_name} placeholders and follow the
brand voice: no dashes, no emoji.
"""
from datetime import datetime, timezone
from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from database import db

sales_templates = db["sales_templates"]

CATEGORIES = ["cold", "follow_up", "partnership", "re_engage"]
CATEGORY_LABELS = {
    "cold": "Cold outreach",
    "follow_up": "Follow up",
    "partnership": "Partnership",
    "re_engage": "Re-engagement",
}


class SalesTemplateInput(BaseModel):
    title: str = Field(min_length=2, max_length=140)
    category: str = Field(default="cold")
    subject: str = Field(min_length=2, max_length=200)
    body: str = Field(min_length=2, max_length=8000)

    @property
    def safe_category(self) -> str:
        return self.category if self.category in CATEGORIES else "cold"


# Starter set seeded on first boot. Solid host-acquisition copy the team can use
# as is or fork. Placeholders: {first_name}, {company}, {event_name}.
STARTERS = [
    {
        "key": "cold-afterlife",
        "category": "cold",
        "title": "Cold: your events deserve an afterlife",
        "subject": "the week after {company}'s next event",
        "body": (
            "Hi {first_name},\n\n"
            "You put real work into your events. The problem is what happens the "
            "week after, when everyone who met goes quiet and the connections "
            "fade.\n\n"
            "Intro Connect turns each event you host into a private, searchable "
            "directory of everyone who came. Attendees save the people they met, "
            "keep a private note, and message each other long after the night "
            "ends.\n\n"
            "It is free to try and takes about five minutes to set up for your "
            "next {company} event. Worth a quick look?\n\n"
            "Scott"
        ),
    },
    {
        "key": "cold-directory",
        "category": "cold",
        "title": "Cold: the directory your attendees keep asking for",
        "subject": "a private directory for {event_name}",
        "body": (
            "Hi {first_name},\n\n"
            "Most people leave an event with a stack of names they never follow "
            "up on. For {event_name}, Intro Connect gives every attendee one "
            "private place to find each other, save contacts, and pick up the "
            "conversations they started in the room.\n\n"
            "Hosts set it up in minutes and share a single join code. Free to "
            "start. Happy to send a two minute walkthrough if it is useful.\n\n"
            "Scott"
        ),
    },
    {
        "key": "followup-nudge",
        "category": "follow_up",
        "title": "Follow up: gentle nudge after no reply",
        "subject": "quick follow up, {first_name}",
        "body": (
            "Hi {first_name},\n\n"
            "Floating this back to the top of your inbox. If keeping your "
            "attendees connected after an event is on your list, I would love to "
            "get {company} set up before your next one.\n\n"
            "No pressure at all. A yes, a no, or a not right now all work.\n\n"
            "Scott"
        ),
    },
    {
        "key": "partnership-venue",
        "category": "partnership",
        "title": "Partnership: venues and community builders",
        "subject": "a networking layer for {company}",
        "body": (
            "Hi {first_name},\n\n"
            "You bring people together at {company}. Intro Connect adds the layer "
            "that keeps them together after they leave: a private directory per "
            "event where attendees save and message each other.\n\n"
            "For partners who run a lot of rooms, we can set this up across every "
            "event and make it part of what makes {company} worth showing up to. "
            "Open to a short call to see if it fits?\n\n"
            "Scott"
        ),
    },
    {
        "key": "reengage-signed-up",
        "category": "re_engage",
        "title": "Re-engage: signed up, never hosted",
        "subject": "want a hand setting up your first event?",
        "body": (
            "Hi {first_name},\n\n"
            "You created an Intro Connect account a little while back and have "
            "not set up an event yet. That is the one step that makes everything "
            "click, and it takes about five minutes.\n\n"
            "If you tell me the event you have coming up, I am glad to set the "
            "first one up with you so all you have to do is share the join "
            "code.\n\n"
            "Scott"
        ),
    },
]


def serialize(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "title": doc.get("title", ""),
        "category": doc.get("category", "cold"),
        "category_label": CATEGORY_LABELS.get(doc.get("category", "cold"), "Cold outreach"),
        "subject": doc.get("subject", ""),
        "body": doc.get("body", ""),
        "updated_at": doc.get("updated_at"),
    }


async def seed_starters() -> None:
    """Insert any starter templates that are not present yet (idempotent, keyed
    on `seed_key`)."""
    now = datetime.now(timezone.utc)
    for t in STARTERS:
        existing = await sales_templates.find_one({"seed_key": t["key"]})
        if existing:
            continue
        await sales_templates.insert_one(
            {
                "seed_key": t["key"],
                "title": t["title"],
                "category": t["category"],
                "subject": t["subject"],
                "body": t["body"],
                "created_at": now,
                "updated_at": now,
            }
        )


async def list_all() -> list:
    cursor = sales_templates.find({}).sort([("category", 1), ("title", 1)])
    return [serialize(d) async for d in cursor]


async def create(item: SalesTemplateInput) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "title": item.title,
        "category": item.safe_category,
        "subject": item.subject,
        "body": item.body,
        "created_at": now,
        "updated_at": now,
    }
    res = await sales_templates.insert_one(doc)
    doc["_id"] = res.inserted_id
    return serialize(doc)


def _oid(tid: str):
    try:
        return ObjectId(tid)
    except Exception:
        return None


async def update(tid: str, item: SalesTemplateInput) -> Optional[dict]:
    oid = _oid(tid)
    if oid is None:
        return None
    doc = await sales_templates.find_one({"_id": oid})
    if not doc:
        return None
    patch = {
        "title": item.title,
        "category": item.safe_category,
        "subject": item.subject,
        "body": item.body,
        "updated_at": datetime.now(timezone.utc),
    }
    await sales_templates.update_one({"_id": oid}, {"$set": patch})
    doc.update(patch)
    return serialize(doc)


async def duplicate(tid: str) -> Optional[dict]:
    oid = _oid(tid)
    if oid is None:
        return None
    doc = await sales_templates.find_one({"_id": oid})
    if not doc:
        return None
    now = datetime.now(timezone.utc)
    copy = {
        "title": f"{doc.get('title','')} (copy)",
        "category": doc.get("category", "cold"),
        "subject": doc.get("subject", ""),
        "body": doc.get("body", ""),
        "created_at": now,
        "updated_at": now,
    }
    res = await sales_templates.insert_one(copy)
    copy["_id"] = res.inserted_id
    return serialize(copy)


async def delete(tid: str) -> bool:
    oid = _oid(tid)
    if oid is None:
        return False
    res = await sales_templates.delete_one({"_id": oid})
    return res.deleted_count > 0
