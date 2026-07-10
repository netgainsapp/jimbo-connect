"""/api/events/{event_id}/sponsors* routes. Moved verbatim from server.py (M13)."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

from database import events, event_attendees, event_sponsors
from auth import get_current_user, get_current_admin
from models import SponsorCreateRequest, SponsorUpdateRequest
from core import serialize_sponsor, _can_manage_event
from ogfetch import fetch_og_metadata

router = APIRouter()


# ---------- Sponsors ----------

async def _require_event_access(event_id: str, user: dict):
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


@router.get("/api/events/{event_id}/sponsors")
async def list_event_sponsors(event_id: str, user: dict = Depends(get_current_user)):
    oid, _ = await _require_event_access(event_id, user)
    out = []
    cursor = event_sponsors.find({"event_id": oid}).sort("added_at", 1)
    async for doc in cursor:
        if user.get("is_admin") or doc.get("active", True):
            out.append(serialize_sponsor(doc))
    return out


@router.post("/api/events/{event_id}/sponsors")
async def create_event_sponsor(
    event_id: str,
    payload: SponsorCreateRequest,
    admin: dict = Depends(get_current_admin),
):
    try:
        oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    if not await events.find_one({"_id": oid}):
        raise HTTPException(status_code=404, detail="Event not found")

    url = payload.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    meta = await fetch_og_metadata(url)
    doc = {
        "event_id": oid,
        "url": url,
        "title": payload.title or meta["title"],
        "description": payload.description or meta["description"],
        "image_url": payload.image_url or meta["image_url"],
        "site_name": meta["site_name"],
        "active": True if payload.active is None else bool(payload.active),
        "added_at": datetime.now(timezone.utc),
    }
    result = await event_sponsors.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_sponsor(doc)


@router.put("/api/events/{event_id}/sponsors/{sponsor_id}")
async def update_event_sponsor(
    event_id: str,
    sponsor_id: str,
    payload: SponsorUpdateRequest,
    admin: dict = Depends(get_current_admin),
):
    try:
        e_oid = ObjectId(event_id)
        s_oid = ObjectId(sponsor_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if updates:
        await event_sponsors.update_one(
            {"_id": s_oid, "event_id": e_oid}, {"$set": updates}
        )
    doc = await event_sponsors.find_one({"_id": s_oid, "event_id": e_oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Sponsor not found")
    return serialize_sponsor(doc)


@router.post("/api/events/{event_id}/sponsors/{sponsor_id}/refresh")
async def refresh_event_sponsor(
    event_id: str,
    sponsor_id: str,
    admin: dict = Depends(get_current_admin),
):
    try:
        e_oid = ObjectId(event_id)
        s_oid = ObjectId(sponsor_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    doc = await event_sponsors.find_one({"_id": s_oid, "event_id": e_oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Sponsor not found")
    meta = await fetch_og_metadata(doc["url"])
    updates = {
        "title": meta["title"] or doc.get("title", ""),
        "description": meta["description"] or doc.get("description", ""),
        "image_url": meta["image_url"] or doc.get("image_url", ""),
        "site_name": meta["site_name"] or doc.get("site_name", ""),
    }
    await event_sponsors.update_one({"_id": s_oid}, {"$set": updates})
    doc.update(updates)
    return serialize_sponsor(doc)


@router.delete("/api/events/{event_id}/sponsors/{sponsor_id}")
async def delete_event_sponsor(
    event_id: str,
    sponsor_id: str,
    admin: dict = Depends(get_current_admin),
):
    try:
        e_oid = ObjectId(event_id)
        s_oid = ObjectId(sponsor_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    await event_sponsors.delete_one({"_id": s_oid, "event_id": e_oid})
    return {"ok": True}
