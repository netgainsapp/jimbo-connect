"""/api/events*, /api/my-events*, /api/my-hosted-events, /api/my-attendees
routes. Moved verbatim from server.py (M13). Route registration order is
preserved from the original file."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Request, Response
from bson import ObjectId

from database import users, events, event_attendees, event_sponsors, messages
import announcements
import branding
import email_send
import invites
import rate_limit
from auth import get_current_user, get_current_admin
from models import (
    AnnouncementCreateRequest,
    EventCreateRequest,
    EventUpdateRequest,
    RequestInviteRequest,
    InviteGuestsRequest,
)
from core import (
    APP_URL,
    generate_join_code,
    assert_event_has_room,
    serialize_event,
    serialize_attendee,
    FREE_EVENT_LIMIT,
    _can_manage_event,
    _thread_id,
)

router = APIRouter()


# ---------- Events ----------

async def create_event_for(user: dict, payload: EventCreateRequest) -> dict:
    """Create an event on behalf of `user`.

    Shared by POST /api/events and the Agenda Builder handoff so that the plan
    limit and join-code generation live in exactly one place. A second creation
    path that forgot the limit check would be a silent way to hand out free
    events.
    """
    import billing

    limit = billing.event_limit_for(user)
    if limit is not None:
        hosted = await events.count_documents({"created_by": user["_id"]})
        if hosted >= limit:
            plan = billing.plan_of(user)
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Your {plan} plan includes {limit} "
                    f"event{'s' if limit != 1 else ''}. Upgrade to host more."
                ),
            )
    code = generate_join_code()
    while await events.find_one({"join_code": code}):
        code = generate_join_code()
    now = datetime.now(timezone.utc)
    doc = {
        "name": payload.name,
        "date": payload.date,
        "location": payload.location or "",
        "industry_tags": payload.industry_tags or [],
        "join_code": code,
        "created_by": user["_id"],
        "created_at": now,
        "description": payload.description or "",
        "end_date": payload.end_date,
    }
    result = await events.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_event(doc, 0)


@router.post("/api/events")
async def create_event(
    payload: EventCreateRequest, user: dict = Depends(get_current_user)
):
    return await create_event_for(user, payload)


@router.get("/api/my-hosted-events")
async def my_hosted_events(user: dict = Depends(get_current_user)):
    """Events this user created (the self-serve host view)."""
    hosted = (
        await events.find({"created_by": user["_id"]}).sort("date", -1).to_list(200)
    )
    if not hosted:
        return []
    event_ids = [e["_id"] for e in hosted]
    counts: dict = {}
    async for row in event_attendees.aggregate(
        [
            {"$match": {"event_id": {"$in": event_ids}}},
            {"$group": {"_id": "$event_id", "n": {"$sum": 1}}},
        ]
    ):
        counts[row["_id"]] = row["n"]
    return [serialize_event(e, counts.get(e["_id"], 0)) for e in hosted]


@router.get("/api/events")
async def list_events(_: dict = Depends(get_current_admin)):
    out = []
    async for e in events.find().sort("date", -1):
        count = await event_attendees.count_documents({"event_id": e["_id"]})
        out.append(serialize_event(e, count))
    return out


@router.get("/api/events/{event_id}")
async def get_event(event_id: str, user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    e = await events.find_one({"_id": oid})
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    if not _can_manage_event(user, e):
        joined = await event_attendees.find_one(
            {"event_id": oid, "user_id": user["_id"]}
        )
        if not joined:
            raise HTTPException(status_code=403, detail="Not joined to this event")
    count = await event_attendees.count_documents({"event_id": oid})
    host = await users.find_one({"_id": e["created_by"]}) if e.get("created_by") else None
    # The ceiling goes only to whoever manages the event, so the host can see
    # the cap approaching instead of discovering it when a guest is turned away.
    limit = None
    if _can_manage_event(user, e) and host:
        import billing

        limit = billing.attendee_limit_for(host)
    return serialize_event(
        e,
        count,
        host_branding=branding.public_branding(host) if host else None,
        attendee_limit=limit,
    )


@router.put("/api/events/{event_id}")
async def update_event(
    event_id: str,
    payload: EventUpdateRequest,
    user: dict = Depends(get_current_user),
):
    try:
        oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    e = await events.find_one({"_id": oid})
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    if not _can_manage_event(user, e):
        raise HTTPException(status_code=403, detail="Not your event")
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if updates:
        await events.update_one({"_id": oid}, {"$set": updates})
        e = await events.find_one({"_id": oid})
    count = await event_attendees.count_documents({"event_id": oid})
    return serialize_event(e, count)


async def _require_event_view(event_id: str, user: dict):
    """Event access for reading: the host, an admin, or someone who joined.

    Extracted after the same block appeared in a third route. A view check
    copied by hand is a view check that eventually differs by hand.
    """
    try:
        oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    e = await events.find_one({"_id": oid})
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    if not _can_manage_event(user, e):
        joined = await event_attendees.find_one(
            {"event_id": oid, "user_id": user["_id"]}
        )
        if not joined:
            raise HTTPException(status_code=403, detail="Not joined to this event")
    return oid, e


async def _require_event_host(event_id: str, user: dict):
    """Stricter: only the host or an admin. Posting to everyone's event page is
    not something a fellow attendee gets to do."""
    try:
        oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    e = await events.find_one({"_id": oid})
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    if not _can_manage_event(user, e):
        raise HTTPException(status_code=403, detail="Not your event")
    return oid, e


@router.get("/api/events/{event_id}/announcements")
async def list_announcements(event_id: str, user: dict = Depends(get_current_user)):
    oid, _ = await _require_event_view(event_id, user)
    return await announcements.list_for_event(oid, user["_id"])


@router.post("/api/events/{event_id}/announcements")
async def create_announcement(
    event_id: str,
    payload: AnnouncementCreateRequest,
    user: dict = Depends(get_current_user),
):
    oid, _ = await _require_event_host(event_id, user)
    try:
        return await announcements.create(oid, user, payload.title, payload.body)
    except announcements.AnnouncementError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/events/{event_id}/announcements/read")
async def mark_announcements_read(
    event_id: str, user: dict = Depends(get_current_user)
):
    """Called when the attendee has actually seen the list, so 'new' means new
    to this reader rather than new to the world."""
    oid, _ = await _require_event_view(event_id, user)
    await announcements.mark_read(oid, user["_id"])
    return {"ok": True}


@router.delete("/api/events/{event_id}/announcements/{announcement_id}")
async def delete_announcement(
    event_id: str, announcement_id: str, user: dict = Depends(get_current_user)
):
    oid, _ = await _require_event_host(event_id, user)
    if not await announcements.delete(oid, announcement_id):
        raise HTTPException(status_code=404, detail="Announcement not found")
    return {"ok": True}


@router.get("/api/events/{event_id}/calendar.ics")
async def get_event_ics(event_id: str, user: dict = Depends(get_current_user)):
    """The event as a calendar file, for anyone who can see the event."""
    import calendar_ics
    from app_url import APP_URL

    try:
        oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    e = await events.find_one({"_id": oid})
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    if not _can_manage_event(user, e):
        joined = await event_attendees.find_one(
            {"event_id": oid, "user_id": user["_id"]}
        )
        if not joined:
            raise HTTPException(status_code=403, detail="Not joined to this event")

    e["id"] = str(e["_id"])
    body = calendar_ics.build_event_ics(e, url=f"{APP_URL}/events/{event_id}")
    return Response(
        content=body,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{calendar_ics.filename_for(e)}"'
            )
        },
    )


@router.get("/api/events/{event_id}/agenda")
async def get_event_agenda(event_id: str, user: dict = Depends(get_current_user)):
    """The agenda for an event, readable by anyone who can see the event.

    Gated on event access rather than agenda ownership: the whole point is that
    attendees can read the schedule, and they do not own the agenda. Private
    per-session notes are stripped by the store before this returns.
    """
    from agenda import store as agenda_store

    try:
        oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    e = await events.find_one({"_id": oid})
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    if not _can_manage_event(user, e):
        joined = await event_attendees.find_one(
            {"event_id": oid, "user_id": user["_id"]}
        )
        if not joined:
            raise HTTPException(status_code=403, detail="Not joined to this event")
    agenda = await agenda_store.get_for_event(oid)
    if not agenda:
        raise HTTPException(status_code=404, detail="No agenda for this event")
    return agenda


@router.delete("/api/events/{event_id}")
async def delete_event(event_id: str, user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    e = await events.find_one({"_id": oid})
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    if not _can_manage_event(user, e):
        raise HTTPException(status_code=403, detail="Not your event")
    await event_attendees.delete_many({"event_id": oid})
    await event_sponsors.delete_many({"event_id": oid})
    # Detach any agenda that was converted into this event. Leaving the link
    # behind strands the organizer: the agenda still says "converted" while the
    # event is gone, and /convert refuses to run twice, so they can neither
    # open it nor make a new event from it.
    from agenda import store as agenda_store

    await agenda_store.unlink_event(oid)
    await events.delete_one({"_id": oid})
    return {"ok": True}


@router.delete("/api/events/{event_id}/attendees/{user_id}")
async def admin_remove_attendee(
    event_id: str, user_id: str, user: dict = Depends(get_current_user)
):
    try:
        e_oid = ObjectId(event_id)
        u_oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    e = await events.find_one({"_id": e_oid})
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    if not _can_manage_event(user, e):
        raise HTTPException(status_code=403, detail="Not your event")
    result = await event_attendees.delete_one(
        {"event_id": e_oid, "user_id": u_oid}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Attendee not on this event")
    return {"ok": True}


@router.delete("/api/my-events/{event_id}")
async def leave_event(event_id: str, user: dict = Depends(get_current_user)):
    try:
        e_oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    result = await event_attendees.delete_one(
        {"event_id": e_oid, "user_id": user["_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not joined to this event")
    return {"ok": True}


@router.post("/api/events/join/{code}")
async def join_event(code: str, user: dict = Depends(get_current_user)):
    e = await events.find_one({"join_code": code.upper()})
    if not e:
        raise HTTPException(status_code=404, detail="Invalid join code")
    existing = await event_attendees.find_one(
        {"event_id": e["_id"], "user_id": user["_id"]}
    )
    if not existing:
        # Guest-facing wording on purpose: the person hitting this cannot
        # upgrade anything, it is the host's plan. Telling a guest to upgrade
        # would be confusing and slightly insulting.
        await assert_event_has_room(
            e,
            message=(
                "This event is full. Ask the host to make room for you."
            ),
        )
        await event_attendees.insert_one(
            {
                "event_id": e["_id"],
                "user_id": user["_id"],
                "joined_at": datetime.now(timezone.utc),
            }
        )
    # Stop any pending invite reminders for this guest on this event.
    await invites.mark_joined(e["_id"], user.get("email", ""))
    count = await event_attendees.count_documents({"event_id": e["_id"]})
    host = await users.find_one({"_id": e["created_by"]}) if e.get("created_by") else None
    return serialize_event(e, count, host_branding=branding.public_branding(host) if host else None)


@router.post("/api/events/{event_id}/invite")
async def invite_guests(
    event_id: str,
    payload: InviteGuestsRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Self-serve: a host emails their guest list a join link."""
    rate_limit.guard(request, "invite", limit=5, window_seconds=3600)
    try:
        oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    e = await events.find_one({"_id": oid})
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    if not _can_manage_event(user, e):
        raise HTTPException(status_code=403, detail="Not your event")
    host_name = (user.get("profile") or {}).get("name") or ""
    return await invites.send_event_invites(
        e, payload.emails, host_name, host_brand=branding.email_brand(user)
    )


@router.get("/api/events/{event_id}/attendees")
async def get_event_attendees(event_id: str, user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    e = await events.find_one({"_id": oid})
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    if not _can_manage_event(user, e):
        joined = await event_attendees.find_one(
            {"event_id": oid, "user_id": user["_id"]}
        )
        if not joined:
            raise HTTPException(status_code=403, detail="Not joined to this event")
    out = []
    links = await event_attendees.find({"event_id": oid}).to_list(None)
    user_ids = [link["user_id"] for link in links]
    if user_ids:
        by_id = {
            u["_id"]: u
            for u in await users.find({"_id": {"$in": user_ids}}).to_list(None)
        }
        for link in links:
            attendee = by_id.get(link["user_id"])
            if attendee and not attendee.get("is_admin"):
                out.append(serialize_attendee(attendee))
    return out


@router.get("/api/events/discoverable")
async def discoverable_events(user: dict = Depends(get_current_user)):
    """Upcoming events the user hasn't joined yet."""
    now = datetime.now(timezone.utc)
    joined_ids = set()
    async for link in event_attendees.find({"user_id": user["_id"]}):
        joined_ids.add(link["event_id"])
    candidates = [
        e
        for e in await events.find({"date": {"$gte": now}}).sort("date", 1).to_list(None)
        if e["_id"] not in joined_ids
    ]
    event_ids = [e["_id"] for e in candidates]
    counts: dict = {}
    if event_ids:
        async for row in event_attendees.aggregate(
            [
                {"$match": {"event_id": {"$in": event_ids}}},
                {"$group": {"_id": "$event_id", "n": {"$sum": 1}}},
            ]
        ):
            counts[row["_id"]] = row["n"]
    host_ids = list({e.get("created_by") for e in candidates if e.get("created_by")})
    hosts: dict = {}
    if host_ids:
        for h in await users.find({"_id": {"$in": host_ids}}).to_list(None):
            hosts[h["_id"]] = h
    out = []
    for e in candidates:
        host = hosts.get(e.get("created_by"))
        host_profile = (host or {}).get("profile") or {}
        out.append(
            {
                "id": str(e["_id"]),
                "name": e["name"],
                "date": e["date"],
                "location": e.get("location", ""),
                "industry_tags": e.get("industry_tags", []),
                "attendee_count": counts.get(e["_id"], 0),
                "host_name": host_profile.get("name")
                or (host or {}).get("email", "")
                or "",
            }
        )
    return out


@router.post("/api/events/{event_id}/request-invite")
async def request_invite(
    event_id: str,
    payload: RequestInviteRequest,
    user: dict = Depends(get_current_user),
):
    try:
        oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    e = await events.find_one({"_id": oid})
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    host = await users.find_one({"_id": e.get("created_by")})
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    existing = await event_attendees.find_one(
        {"event_id": oid, "user_id": user["_id"]}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already joined")

    note = (payload.message or "").strip()
    profile = user.get("profile") or {}
    name = profile.get("name") or user["email"]
    role_company = " · ".join(
        [s for s in [profile.get("role"), profile.get("company")] if s]
    )

    text = f"Invite request: {name}"
    if role_company:
        text += f" ({role_company})"
    text += f' would like to join "{e["name"]}".'
    if note:
        text += f"\n\n\"{note}\""

    await messages.insert_one(
        {
            "thread_id": _thread_id(user["_id"], host["_id"]),
            "from_user_id": user["_id"],
            "to_user_id": host["_id"],
            "text": text,
            "sent_at": datetime.now(timezone.utc),
            "read_at": None,
        }
    )

    if email_send.is_configured():
        await email_send.send_branded(
            to=host["email"],
            subject=f"Invite request: {e['name']}",
            heading="New invite request",
            paragraphs=text.split("\n\n"),
            button={
                "label": "Reply",
                "url": f"{APP_URL}/messages/{str(user['_id'])}",
            },
            marketing=False,
            brand=branding.email_brand(host),
        )

    return {"ok": True}


@router.get("/api/my-attendees")
async def my_attendees(user: dict = Depends(get_current_user)):
    """Every unique attendee from every event the user has joined."""
    my_event_ids = []
    async for link in event_attendees.find({"user_id": user["_id"]}):
        my_event_ids.append(link["event_id"])
    if not my_event_ids:
        return []
    seen: set = set()
    uids = []
    async for link in event_attendees.find({"event_id": {"$in": my_event_ids}}):
        uid = link["user_id"]
        if uid == user["_id"]:
            continue
        key = str(uid)
        if key in seen:
            continue
        seen.add(key)
        uids.append(uid)
    out = []
    if uids:
        docs = {
            u["_id"]: u
            for u in await users.find({"_id": {"$in": uids}}).to_list(None)
        }
        for uid in uids:
            u = docs.get(uid)
            if u and not u.get("is_admin"):
                out.append(serialize_attendee(u))
    return out


@router.get("/api/my-events")
async def my_events(user: dict = Depends(get_current_user)):
    links = (
        await event_attendees.find({"user_id": user["_id"]})
        .sort("joined_at", -1)
        .to_list(None)
    )
    event_ids = [link["event_id"] for link in links]
    if not event_ids:
        return []
    events_by_id = {
        e["_id"]: e
        for e in await events.find({"_id": {"$in": event_ids}}).to_list(None)
    }
    counts: dict = {}
    async for row in event_attendees.aggregate(
        [
            {"$match": {"event_id": {"$in": event_ids}}},
            {"$group": {"_id": "$event_id", "n": {"$sum": 1}}},
        ]
    ):
        counts[row["_id"]] = row["n"]
    out = []
    for link in links:
        e = events_by_id.get(link["event_id"])
        if e:
            out.append(serialize_event(e, counts.get(e["_id"], 0)))
    return out
