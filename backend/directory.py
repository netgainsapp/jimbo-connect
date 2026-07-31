"""Cross-event directory: attendees who chose to be discoverable beyond the
single event they came to.

This is the one feature that introduces people who were never in a room
together, so the defaults are the whole design.

**Opt in, per event, off by default.** The flag lives on the `event_attendees`
link row rather than on the user, because attending a client's conference and
attending a neighbourhood meetup are not the same decision and should not share
a switch. Someone can be listed through one event and invisible through
another. A missing flag reads as False, so every row that existed before this
shipped is opted out rather than silently published.

**No email addresses, ever.** A directory entry is a profile and nothing more;
contact goes through the existing messaging, which keeps a record and can be
rate limited. `serialize_person` is deliberately its own function rather than a
reuse of `serialize_attendee`, which carries an email field: sharing that
serializer is how an address ends up somewhere nobody intended.

**Messaging needs both sides opted in.** Browsing does not require being listed,
but reaching out does. Otherwise the directory becomes a way to read everyone
while showing nothing, and the people who did opt in would be carrying the whole
exposure. See `both_discoverable`, which `core._users_connected` consults.
"""
from __future__ import annotations

from database import event_attendees, users

#: A directory read is a browse, not an export. The cap is here so a scripted
#: caller walking the list still cannot pull the whole platform in one request.
MAX_RESULTS = 200


def serialize_person(user: dict) -> dict:
    """Profile only. No email, by design; see the module docstring."""
    profile = user.get("profile") or {}
    return {
        "id": str(user["_id"]),
        "profile": {
            "name": profile.get("name", ""),
            "role": profile.get("role", ""),
            "company": profile.get("company", ""),
            "industry": profile.get("industry", ""),
            "bio": profile.get("bio", ""),
            "looking_for": profile.get("looking_for", ""),
            "linkedin": profile.get("linkedin", ""),
            "photo_url": profile.get("photo_url", ""),
        },
    }


async def set_discoverable(event_oid, user_id, discoverable: bool) -> bool:
    """Opt this person in or out for ONE event.

    Returns False when the person has no link row for the event. A host who
    never joined their own event has no row, and inventing one here would add
    them to the guest list and the attendee count as a side effect of flipping
    a privacy switch.
    """
    result = await event_attendees.update_one(
        {"event_id": event_oid, "user_id": user_id},
        {"$set": {"discoverable": bool(discoverable)}},
    )
    return result.matched_count > 0


async def get_discoverable(event_oid, user_id) -> bool:
    link = await event_attendees.find_one({"event_id": event_oid, "user_id": user_id})
    return bool(link.get("discoverable")) if link else False


async def is_discoverable(user_id) -> bool:
    """True when this person opted in through at least one event."""
    return (
        await event_attendees.find_one({"user_id": user_id, "discoverable": True})
    ) is not None


async def both_discoverable(a_id, b_id) -> bool:
    """The messaging condition. Both sides, deliberately.

    Consulted by core._users_connected, which is the gate for messaging and
    cross-user profile reads. One-sided would let someone who is invisible
    message people who are listed.
    """
    if a_id == b_id:
        return False
    return await is_discoverable(a_id) and await is_discoverable(b_id)


async def has_any_attendance(user_id) -> bool:
    """Whether the viewer may browse at all.

    The directory is a benefit of having turned up to something, not a people
    search that any fresh signup can open.
    """
    return (await event_attendees.find_one({"user_id": user_id})) is not None


async def list_people(viewer_id, query: str = "", industry: str = "") -> list:
    """Everyone discoverable except the viewer and admins.

    Filtering happens in Python rather than in Mongo because the candidate set
    is the opted-in population, not the whole user table, and a regex query
    against user-supplied text is a denial-of-service waiting to happen.
    """
    links = await event_attendees.find({"discoverable": True}).to_list(None)
    ids = []
    seen = set()
    for link in links:
        uid = link.get("user_id")
        if uid is None or uid == viewer_id or uid in seen:
            continue
        seen.add(uid)
        ids.append(uid)
    if not ids:
        return []

    docs = await users.find({"_id": {"$in": ids}}).to_list(None)
    needle = " ".join(str(query or "").split()).lower()
    want_industry = str(industry or "").strip().lower()

    out = []
    for doc in docs:
        if doc.get("is_admin"):
            continue
        person = serialize_person(doc)
        p = person["profile"]
        if want_industry and want_industry not in ("", "all"):
            if (p.get("industry") or "").lower() != want_industry:
                continue
        if needle:
            haystack = " ".join(
                str(p.get(f) or "")
                for f in ("name", "role", "company", "industry", "looking_for", "bio")
            ).lower()
            if needle not in haystack:
                continue
        out.append(person)

    out.sort(key=lambda person: (person["profile"].get("name") or "").lower())
    return out[:MAX_RESULTS]
