"""Host announcements: a short notice from the organizer, shown on the event
page to everyone who can see the event.

Deliberately in-app only. Sending these as bulk email from the platform would
put announcement complaints on the same domain as password resets and invites,
and the product already has an established pattern for host-to-attendee email:
compose here, send from the host's own mail client. See the "Open in mail"
path in the templates screen.

Read state is tracked as ONE row per user per event carrying last_read_at,
rather than a read receipt per announcement per user. On an event with 2000
attendees the second shape grows by 2000 rows every time a host posts, which
buys nothing: what the UI actually needs is "is there anything newer than the
last time I looked".
"""
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId

from database import announcement_reads, event_announcements

MAX_BODY = 5000
MAX_TITLE = 200
#: A host posting more than this on one event is either testing or spamming
#: their own attendees. Cheap guard against both.
MAX_PER_EVENT = 200


class AnnouncementError(Exception):
    """Bad input, with a message intended for the person who typed it."""


def _serialize(doc: dict, *, unread: bool = False) -> dict:
    return {
        "id": str(doc["_id"]),
        "event_id": str(doc["event_id"]),
        "title": doc.get("title", ""),
        "body": doc.get("body", ""),
        "author_name": doc.get("author_name", ""),
        "created_at": doc.get("created_at"),
        "unread": unread,
    }


def clean(value, limit: int) -> str:
    text = " ".join(str(value or "").split()) if limit == MAX_TITLE else str(value or "").strip()
    return text[:limit]


async def create(event_id: ObjectId, author: dict, title: str, body: str) -> dict:
    title = clean(title, MAX_TITLE)
    body = clean(body, MAX_BODY)
    if not body:
        raise AnnouncementError("An announcement needs something to say.")
    if await event_announcements.count_documents({"event_id": event_id}) >= MAX_PER_EVENT:
        raise AnnouncementError(
            f"This event already has {MAX_PER_EVENT} announcements. "
            "Delete an old one first."
        )
    doc = {
        "event_id": event_id,
        "author_id": author["_id"],
        # Denormalised so the list does not need a user lookup per row, and so
        # a deleted host does not blank out the history.
        "author_name": (author.get("profile") or {}).get("name", "") or "The host",
        "title": title,
        "body": body,
        "created_at": datetime.now(timezone.utc),
    }
    result = await event_announcements.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _serialize(doc, unread=False)


async def list_for_event(event_id: ObjectId, user_id) -> list:
    """Newest first, each flagged unread relative to this reader."""
    read = await announcement_reads.find_one({"event_id": event_id, "user_id": user_id})
    last_read = read.get("last_read_at") if read else None
    # Secondary sort on _id, because two announcements written in the same
    # instant share a created_at and would otherwise come back in arbitrary
    # order. ObjectId embeds a timestamp and a counter, so it breaks the tie
    # in real insertion order.
    rows = await event_announcements.find({"event_id": event_id}).sort(
        [("created_at", -1), ("_id", -1)]
    ).to_list(MAX_PER_EVENT)
    out = []
    for doc in rows:
        created = doc.get("created_at")
        # Both sides are stored timezone-aware; guard anyway, since a naive
        # datetime compared against an aware one raises rather than sorting.
        if last_read is not None and created is not None:
            a = created if created.tzinfo else created.replace(tzinfo=timezone.utc)
            b = last_read if last_read.tzinfo else last_read.replace(tzinfo=timezone.utc)
            # >= not >. An announcement posted in the same clock tick as a
            # reader marking the page read is ambiguous, and the two failure
            # directions are not equal: treating it as read HIDES it from that
            # reader for good, treating it as unread merely shows a badge for
            # something they may already have seen. Windows clock resolution is
            # around 15ms, so this collision is ordinary, not theoretical.
            unread = a >= b
        else:
            unread = True
        out.append(_serialize(doc, unread=unread))
    return out


async def unread_count(event_id: ObjectId, user_id) -> int:
    read = await announcement_reads.find_one({"event_id": event_id, "user_id": user_id})
    if not read or not read.get("last_read_at"):
        return await event_announcements.count_documents({"event_id": event_id})
    # $gte, matching list_for_event: see the note there on why an exact tie
    # must count as unread rather than read.
    return await event_announcements.count_documents(
        {"event_id": event_id, "created_at": {"$gte": read["last_read_at"]}}
    )


async def mark_read(event_id: ObjectId, user_id) -> None:
    await announcement_reads.update_one(
        {"event_id": event_id, "user_id": user_id},
        {"$set": {"last_read_at": datetime.now(timezone.utc)}},
        upsert=True,
    )


async def delete(event_id: ObjectId, announcement_id: str) -> bool:
    try:
        oid = ObjectId(announcement_id)
    except Exception:
        return False
    result = await event_announcements.delete_one(
        {"_id": oid, "event_id": event_id}
    )
    return result.deleted_count > 0
