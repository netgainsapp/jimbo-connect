"""Mongo persistence for saved agendas.

Only signed-in users get rows here. An anonymous visitor's draft stays in their
own browser, so there is nothing to expire, orphan or clean up; a document is
created the moment they sign in and claim it.

Agenda items are EMBEDDED rather than kept in a second collection. They are
always read and written with their parent and never queried on their own, so
embedding buys an atomic autosave in a single update (no half-written states)
and ordering straight from array position, which is what the builder's drag and
drop actually manipulates.
"""
from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId

import branding
from database import agendas

from .schema import AgendaExportRequest

# A saved agenda keeps its logo inline as a sanitized PNG data URL rather than
# in a separate blob route. One storage location keeps the export path, the
# preview and cross device loading on a single code path. The 1 MB upload cap
# means the field tops out near 1.4 MB after base64, comfortably inside
# Mongo's 16 MB document limit.
_LOGO_PREFIX = "data:image/png;base64,"


class AgendaNotFound(Exception):
    """Missing, or owned by somebody else. Deliberately one exception: telling
    a caller which of the two it was would confirm that an id exists."""


def sanitize_logo(data_url: Optional[str]) -> Optional[str]:
    """Re-encode a client supplied data URL through Pillow and return a clean
    PNG data URL, or None. Raises ValueError with a user-facing message.

    Never store the bytes the client sent. branding.process_logo strips
    metadata and trailing payloads and caps the decoded size, and it is the
    same hardening the Pro branding upload uses.
    """
    if not data_url:
        return None
    if "," not in data_url or not data_url.startswith("data:image/"):
        raise ValueError("Use a PNG, JPEG, or WebP image.")
    try:
        raw = base64.b64decode(data_url.split(",", 1)[1], validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("That logo could not be read.")
    clean = branding.process_logo(raw)
    return _LOGO_PREFIX + base64.b64encode(clean).decode()


def _doc_to_public(doc: dict) -> dict:
    out = {
        "id": str(doc["_id"]),
        "event_name": doc.get("event_name", ""),
        "description": doc.get("description", ""),
        "start_date": doc.get("start_date", ""),
        "end_date": doc.get("end_date", ""),
        "start_time": doc.get("start_time", ""),
        "end_time": doc.get("end_time", ""),
        "venue_name": doc.get("venue_name", ""),
        "venue_address": doc.get("venue_address", ""),
        "virtual_url": doc.get("virtual_url", ""),
        "organizer_name": doc.get("organizer_name", ""),
        "organizer_company": doc.get("organizer_company", ""),
        "organizer_email": doc.get("organizer_email", ""),
        "event_website": doc.get("event_website", ""),
        "logo": doc.get("logo"),
        "items": doc.get("items", []),
        "status": doc.get("status", "draft"),
        "event_id": str(doc["event_id"]) if doc.get("event_id") else None,
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }
    return out


def _summary(doc: dict) -> dict:
    """List view. Deliberately omits items and the logo: a list of ten agendas
    should not ship ten logos."""
    return {
        "id": str(doc["_id"]),
        "event_name": doc.get("event_name", ""),
        "start_date": doc.get("start_date", ""),
        "end_date": doc.get("end_date", ""),
        "item_count": len(doc.get("items", [])),
        "status": doc.get("status", "draft"),
        "event_id": str(doc["event_id"]) if doc.get("event_id") else None,
        "updated_at": doc.get("updated_at"),
    }


def _fields_from(payload: AgendaExportRequest) -> dict:
    """Everything the client owns, normalised. Dates and times are already
    validated by the schema; they are stored as plain strings because an agenda
    is wall clock local to its venue."""
    return {
        "event_name": payload.event_name,
        "description": payload.description,
        "start_date": payload.start_date.isoformat() if payload.start_date else "",
        "end_date": payload.end_date.isoformat() if payload.end_date else "",
        "start_time": payload.start_time,
        "end_time": payload.end_time,
        "venue_name": payload.venue_name,
        "venue_address": payload.venue_address,
        "virtual_url": payload.virtual_url,
        "organizer_name": payload.organizer_name,
        "organizer_company": payload.organizer_company,
        "organizer_email": payload.organizer_email,
        "event_website": payload.event_website,
        "items": [
            {**item.model_dump(), "date": item.date.isoformat()}
            for item in payload.items
        ],
    }


async def create(user_id, payload: AgendaExportRequest) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        **_fields_from(payload),
        "logo": sanitize_logo(payload.logo),
        "status": "draft",
        "event_id": None,
        "created_at": now,
        "updated_at": now,
    }
    result = await agendas.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _doc_to_public(doc)


async def list_for_user(user_id, limit: int = 100) -> list:
    cursor = agendas.find({"user_id": user_id}).sort("updated_at", -1)
    return [_summary(d) for d in await cursor.to_list(limit)]


async def _owned(agenda_id: str, user_id) -> dict:
    try:
        oid = ObjectId(agenda_id)
    except Exception:
        raise AgendaNotFound()
    doc = await agendas.find_one({"_id": oid})
    # Compare as strings: an ObjectId-versus-string storage mismatch must not
    # silently grant or revoke access. Same trap _can_manage_event was
    # hardened against.
    if not doc or str(doc.get("user_id")) != str(user_id):
        raise AgendaNotFound()
    return doc


async def get(agenda_id: str, user_id) -> dict:
    return _doc_to_public(await _owned(agenda_id, user_id))


async def update(
    agenda_id: str, user_id, payload: AgendaExportRequest, *, logo_provided: bool
) -> dict:
    doc = await _owned(agenda_id, user_id)
    updates = {**_fields_from(payload), "updated_at": datetime.now(timezone.utc)}
    # The logo is rewritten only when the client explicitly sent the field.
    # Autosave omits it entirely, so a debounced save every few keystrokes does
    # not re-upload and re-encode a megabyte of image. `logo_provided` comes
    # from pydantic's model_fields_set, because an omitted field and an
    # explicit null both arrive as None and they mean different things: leave
    # it alone, versus remove it.
    if logo_provided:
        updates["logo"] = sanitize_logo(payload.logo) if payload.logo else None
    await agendas.update_one({"_id": doc["_id"]}, {"$set": updates})
    doc.update(updates)
    return _doc_to_public(doc)


async def delete(agenda_id: str, user_id) -> None:
    doc = await _owned(agenda_id, user_id)
    await agendas.delete_one({"_id": doc["_id"]})


async def attach_event(agenda_id: str, user_id, event_id) -> dict:
    """Phase 4 hook: link a saved agenda to the event created from it."""
    doc = await _owned(agenda_id, user_id)
    updates = {
        "event_id": event_id,
        "status": "converted",
        "updated_at": datetime.now(timezone.utc),
    }
    await agendas.update_one({"_id": doc["_id"]}, {"$set": updates})
    doc.update(updates)
    return _doc_to_public(doc)
