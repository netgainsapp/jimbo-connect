"""/api/profile*, /api/contacts*, /api/messages* routes. Moved verbatim from
server.py (M13). Route registration order is preserved from the original file."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Response, Request
from bson import ObjectId

from database import users, saved_contacts, messages
import directory
import rate_limit
from auth import get_current_user, COOKIE_NAME
from models import (
    Profile,
    ProfileUpdateRequest,
    PhotoUploadRequest,
    SaveContactRequest,
    NoteUpdateRequest,
    SendMessageRequest,
)
from core import (
    serialize_user,
    serialize_attendee,
    get_user_event_history,
    _users_connected,
    _hard_delete_user,
    _cookie_secure,
    _thread_id,
)

router = APIRouter()


# ---------- Cross-event directory ----------

@router.get("/api/directory")
async def browse_directory(
    request: Request,
    q: str = "",
    industry: str = "",
    user: dict = Depends(get_current_user),
):
    """People who opted into the cross-event directory.

    Browsing requires having attended something. The directory is a benefit of
    having turned up, not a people search any fresh signup can open, and that
    check is what stops a throwaway account being a scraping tool.

    Entries carry no email address. Contact runs through messaging, which needs
    BOTH sides opted in; see directory.both_discoverable.
    """
    if not await directory.has_any_attendance(user["_id"]):
        raise HTTPException(
            status_code=403,
            detail="Join an event first. The directory is for people who have attended one.",
        )
    rate_limit.guard(
        request, "directory", limit=60, window_seconds=60,
        identifier=str(user["_id"]),
    )
    people = await directory.list_people(user["_id"], query=q, industry=industry)
    return {
        "people": people,
        # So the UI can tell someone why they are not in their own results, and
        # why messaging may refuse, without a second round trip.
        "i_am_listed": await directory.is_discoverable(user["_id"]),
    }


# ---------- Profile ----------

@router.get("/api/profile")
async def get_my_profile(user: dict = Depends(get_current_user)):
    return serialize_user(user)


@router.put("/api/profile")
async def update_my_profile(
    payload: ProfileUpdateRequest, user: dict = Depends(get_current_user)
):
    current = Profile(**(user.get("profile") or {})).model_dump()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    current.update(updates)
    await users.update_one({"_id": user["_id"]}, {"$set": {"profile": current}})
    user["profile"] = current
    return serialize_user(user)


@router.post("/api/profile/photo")
async def upload_photo(
    payload: PhotoUploadRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    rate_limit.guard(request, "photo", limit=20, window_seconds=300)
    profile = user.get("profile") or {}
    profile["photo_url"] = payload.photo_data
    await users.update_one({"_id": user["_id"]}, {"$set": {"profile": profile}})
    user["profile"] = profile
    return serialize_user(user)


@router.get("/api/profile/{user_id}")
async def get_profile_by_id(user_id: str, user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")
    # Enforce the event-gated privacy model: only reveal a profile to someone
    # with a relationship to the target. Return an identical 404 for both
    # "no such user" and "not permitted" so ids cannot be enumerated.
    if not await _users_connected(user, oid):
        raise HTTPException(status_code=404, detail="User not found")
    target = await users.find_one({"_id": oid})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    data = serialize_attendee(target)
    data["events"] = await get_user_event_history(oid)
    return data


@router.delete("/api/profile")
async def delete_my_account(
    response: Response, user: dict = Depends(get_current_user)
):
    if user.get("is_admin"):
        # Don't allow the admin user to nuke themselves and lock everyone out
        raise HTTPException(
            status_code=400,
            detail="Admin accounts can't be self-deleted from the app",
        )
    await _hard_delete_user(user["_id"])
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        samesite="none" if _cookie_secure() else "lax",
        secure=_cookie_secure(),
    )
    return {"ok": True}


# ---------- Contacts ----------

@router.post("/api/contacts/save")
async def save_contact(
    payload: SaveContactRequest, user: dict = Depends(get_current_user)
):
    try:
        contact_oid = ObjectId(payload.contact_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid contact id")
    if contact_oid == user["_id"]:
        raise HTTPException(status_code=400, detail="Cannot save yourself")
    # Only allow saving someone you actually share an event with (or already
    # have a relationship with). Opaque 404 so ids cannot be enumerated.
    if not await _users_connected(user, contact_oid):
        raise HTTPException(status_code=404, detail="Contact not found")
    target = await users.find_one({"_id": contact_oid})
    if not target:
        raise HTTPException(status_code=404, detail="Contact not found")
    existing = await saved_contacts.find_one(
        {"owner_id": user["_id"], "contact_id": contact_oid}
    )
    if existing:
        if payload.note is not None:
            await saved_contacts.update_one(
                {"_id": existing["_id"]}, {"$set": {"note": payload.note}}
            )
            existing["note"] = payload.note
        return {
            "id": str(existing["_id"]),
            "contact_id": str(contact_oid),
            "note": existing.get("note", ""),
            "saved_at": existing["saved_at"],
            "contact": serialize_attendee(target),
        }
    now = datetime.now(timezone.utc)
    doc = {
        "owner_id": user["_id"],
        "contact_id": contact_oid,
        "note": payload.note or "",
        "saved_at": now,
    }
    result = await saved_contacts.insert_one(doc)
    return {
        "id": str(result.inserted_id),
        "contact_id": str(contact_oid),
        "note": doc["note"],
        "saved_at": now,
        "contact": serialize_attendee(target),
    }


@router.delete("/api/contacts/{contact_id}")
async def delete_saved_contact(
    contact_id: str, user: dict = Depends(get_current_user)
):
    try:
        contact_oid = ObjectId(contact_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid contact id")
    result = await saved_contacts.delete_one(
        {"owner_id": user["_id"], "contact_id": contact_oid}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Saved contact not found")
    return {"ok": True}


@router.get("/api/contacts")
async def list_saved_contacts(user: dict = Depends(get_current_user)):
    out = []
    async for sc in saved_contacts.find({"owner_id": user["_id"]}).sort("saved_at", -1):
        target = await users.find_one({"_id": sc["contact_id"]})
        if target:
            out.append(
                {
                    "id": str(sc["_id"]),
                    "contact_id": str(sc["contact_id"]),
                    "note": sc.get("note", ""),
                    "saved_at": sc["saved_at"],
                    "contact": serialize_attendee(target),
                }
            )
    return out


@router.put("/api/contacts/{contact_id}/note")
async def update_contact_note(
    contact_id: str,
    payload: NoteUpdateRequest,
    user: dict = Depends(get_current_user),
):
    try:
        contact_oid = ObjectId(contact_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid contact id")
    result = await saved_contacts.update_one(
        {"owner_id": user["_id"], "contact_id": contact_oid},
        {"$set": {"note": payload.note}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Saved contact not found")
    return {"ok": True, "note": payload.note}


@router.get("/api/contacts/{contact_id}/is-saved")
async def is_contact_saved(
    contact_id: str, user: dict = Depends(get_current_user)
):
    try:
        contact_oid = ObjectId(contact_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid contact id")
    sc = await saved_contacts.find_one(
        {"owner_id": user["_id"], "contact_id": contact_oid}
    )
    if not sc:
        return {"saved": False}
    return {
        "saved": True,
        "id": str(sc["_id"]),
        "note": sc.get("note", ""),
    }


# ---------- Messages ----------

def _serialize_message(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "thread_id": doc.get("thread_id", ""),
        "from_user_id": str(doc["from_user_id"]),
        "to_user_id": str(doc["to_user_id"]),
        "text": doc.get("text", ""),
        "sent_at": doc.get("sent_at"),
        "read_at": doc.get("read_at"),
    }


@router.post("/api/messages")
async def send_message(
    payload: SendMessageRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    rate_limit.guard(
        request, "messages", limit=30, window_seconds=60, identifier=str(user["_id"])
    )
    try:
        to_oid = ObjectId(payload.to_user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid recipient")
    if to_oid == user["_id"]:
        raise HTTPException(status_code=400, detail="Cannot message yourself")
    # Only allow messaging someone you share an event with (or already have a
    # thread with). Opaque 404 so ids cannot be enumerated. Hosts remain
    # reachable via POST /api/events/{event_id}/request-invite.
    if not await _users_connected(user, to_oid):
        raise HTTPException(status_code=404, detail="Recipient not found")
    target = await users.find_one({"_id": to_oid})
    if not target:
        raise HTTPException(status_code=404, detail="Recipient not found")

    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message is empty")

    doc = {
        "thread_id": _thread_id(user["_id"], to_oid),
        "from_user_id": user["_id"],
        "to_user_id": to_oid,
        "text": text,
        "sent_at": datetime.now(timezone.utc),
        "read_at": None,
    }
    result = await messages.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _serialize_message(doc)


@router.get("/api/messages/threads")
async def list_threads(user: dict = Depends(get_current_user)):
    """List all threads the user participates in, with last message
    and unread count from the other party."""
    out = []
    seen_threads = set()
    cursor = messages.find(
        {"$or": [{"from_user_id": user["_id"]}, {"to_user_id": user["_id"]}]}
    ).sort("sent_at", -1)
    async for doc in cursor:
        tid = doc.get("thread_id")
        if tid in seen_threads:
            continue
        seen_threads.add(tid)
        other_id = (
            doc["to_user_id"]
            if doc["from_user_id"] == user["_id"]
            else doc["from_user_id"]
        )
        other = await users.find_one({"_id": other_id})
        if not other:
            continue
        unread = await messages.count_documents(
            {
                "thread_id": tid,
                "to_user_id": user["_id"],
                "read_at": None,
            }
        )
        out.append(
            {
                "thread_id": tid,
                "other": serialize_attendee(other),
                "last_message": _serialize_message(doc),
                "unread": unread,
            }
        )
    return out


@router.get("/api/messages/with/{user_id}")
async def messages_with(
    user_id: str, user: dict = Depends(get_current_user)
):
    try:
        other_oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")
    other = await users.find_one({"_id": other_oid})
    if not other:
        raise HTTPException(status_code=404, detail="User not found")
    tid = _thread_id(user["_id"], other_oid)
    out = []
    async for doc in messages.find({"thread_id": tid}).sort("sent_at", 1):
        out.append(_serialize_message(doc))
    # mark inbound messages as read
    await messages.update_many(
        {"thread_id": tid, "to_user_id": user["_id"], "read_at": None},
        {"$set": {"read_at": datetime.now(timezone.utc)}},
    )
    return {
        "messages": out,
        "other": serialize_attendee(other),
    }


@router.get("/api/messages/unread-count")
async def unread_count(user: dict = Depends(get_current_user)):
    n = await messages.count_documents(
        {"to_user_id": user["_id"], "read_at": None}
    )
    return {"unread": n}
