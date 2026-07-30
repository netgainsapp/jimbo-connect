"""Agenda Builder API.

Phase 1 exposes exactly one route, and it is public: the builder is a free
acquisition tool that has to work before anyone has an account. Nothing is
persisted, so the request body carries the whole agenda and the response is the
finished document.
"""
from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, HTTPException, Request, Response

import branding
import rate_limit
from agenda import store
from agenda.docx import build_docx
from agenda.schema import AgendaExportRequest, slugify_filename
from auth import get_current_user

router = APIRouter()

DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

# Generous enough that someone iterating on an agenda never notices, tight
# enough that an anonymous caller cannot use document generation as a cheap way
# to burn CPU on a single worker instance.
EXPORT_LIMIT = 30
EXPORT_WINDOW_SECONDS = 3600


def _decode_logo(data_url: str | None) -> bytes | None:
    """Decode a data URL into sanitized PNG bytes, or None.

    Reuses branding.process_logo, which re-encodes through Pillow and so strips
    metadata and trailing payloads. A bad logo must never cost the user their
    export, so anything unusable is reported as a 400 with a readable message
    rather than silently producing a document with a broken image.
    """
    if not data_url:
        return None
    if "," not in data_url or not data_url.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="Use a PNG, JPEG, or WebP image.")
    _, encoded = data_url.split(",", 1)
    try:
        raw = base64.b64decode(encoded, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="That logo could not be read.")
    try:
        return branding.process_logo(raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Declared sync on purpose. python-docx and Pillow are blocking CPU work, and
# the API runs a single uvicorn worker; a plain `def` endpoint is handed to the
# threadpool by FastAPI, so one slow export cannot stall the event loop for
# every other request.
@router.post("/api/agenda/export")
def export_agenda(payload: AgendaExportRequest, request: Request):
    rate_limit.guard(
        request,
        "agenda_export",
        limit=EXPORT_LIMIT,
        window_seconds=EXPORT_WINDOW_SECONDS,
    )
    logo_png = _decode_logo(payload.logo)
    document = build_docx(payload, logo_png)
    filename = f"{slugify_filename(payload.event_name)}-agenda.docx"
    return Response(
        content=document,
        media_type=DOCX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Saved agendas. Signed-in only: an anonymous visitor's draft stays in their
# own browser, so these routes never create a row nobody owns.
# ---------------------------------------------------------------------------

SAVE_LIMIT = 240
SAVE_WINDOW_SECONDS = 3600


def _not_found():
    return HTTPException(status_code=404, detail="Agenda not found")


@router.post("/api/agenda")
async def create_agenda(
    payload: AgendaExportRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Create, or claim a draft built before signing in."""
    rate_limit.guard(
        request, "agenda_write", limit=SAVE_LIMIT,
        window_seconds=SAVE_WINDOW_SECONDS, identifier=user.get("email"),
    )
    try:
        return await store.create(user["_id"], payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/agenda")
async def list_agendas(user: dict = Depends(get_current_user)):
    return await store.list_for_user(user["_id"])


@router.get("/api/agenda/{agenda_id}")
async def get_agenda(agenda_id: str, user: dict = Depends(get_current_user)):
    try:
        return await store.get(agenda_id, user["_id"])
    except store.AgendaNotFound:
        raise _not_found()


@router.put("/api/agenda/{agenda_id}")
async def update_agenda(
    agenda_id: str,
    payload: AgendaExportRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    # Autosave hits this often by design, so the budget is generous; it exists
    # to stop a runaway client, not to police normal editing.
    rate_limit.guard(
        request, "agenda_write", limit=SAVE_LIMIT,
        window_seconds=SAVE_WINDOW_SECONDS, identifier=user.get("email"),
    )
    try:
        return await store.update(
            agenda_id, user["_id"], payload,
            # An omitted logo means "leave it alone"; an explicit null means
            # "remove it". Both arrive as None, so ask pydantic which happened.
            logo_provided="logo" in payload.model_fields_set,
        )
    except store.AgendaNotFound:
        raise _not_found()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/api/agenda/{agenda_id}")
async def delete_agenda(agenda_id: str, user: dict = Depends(get_current_user)):
    try:
        await store.delete(agenda_id, user["_id"])
    except store.AgendaNotFound:
        raise _not_found()
    return {"ok": True}


@router.post("/api/agenda/{agenda_id}/convert")
async def convert_agenda_to_event(
    agenda_id: str, user: dict = Depends(get_current_user)
):
    """Create an event from a saved agenda and link the two.

    Done server side in one call so join-code uniqueness and the plan limit
    stay in a single place (routers.events.create_event_for), and so the client
    never has to re-send data the server already holds.
    """
    from bson import ObjectId

    from database import events as events_col
    from models import EventCreateRequest
    from routers.events import create_event_for

    try:
        agenda = await store.get(agenda_id, user["_id"])
    except store.AgendaNotFound:
        raise _not_found()

    if agenda.get("event_id"):
        raise HTTPException(
            status_code=409, detail="This agenda already has an event."
        )

    start = _event_datetime(agenda)
    if not start:
        raise HTTPException(
            status_code=400,
            detail="Add a date to your agenda before creating an event.",
        )

    location = ", ".join(
        p for p in (agenda.get("venue_name"), agenda.get("venue_address")) if p
    ) or agenda.get("virtual_url", "")

    # Raises 403 with the upgrade message when the host is at their plan limit.
    event = await create_event_for(
        user,
        EventCreateRequest(
            name=agenda.get("event_name") or "Untitled event",
            date=start,
            location=location[:200],
            description=agenda.get("description", ""),
            end_date=_parse_date(agenda.get("end_date")),
        ),
    )

    await events_col.update_one(
        {"_id": ObjectId(event["id"])},
        {"$set": {"agenda_id": ObjectId(agenda_id)}},
    )
    event["agenda_id"] = agenda_id
    await store.attach_event(agenda_id, user["_id"], ObjectId(event["id"]))
    return event


def _parse_date(value):
    """Stored dates are plain "YYYY-MM-DD" strings, because an agenda is wall
    clock local to its venue. The event model wants a datetime."""
    from datetime import datetime

    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def _event_datetime(agenda: dict):
    """The event's single `date`, built from the agenda's start date and, when
    given, its start time. Falls back to the earliest dated session so an
    agenda that only ever set times on its rows still converts."""
    from datetime import datetime

    day = _parse_date(agenda.get("start_date"))
    if not day:
        dates = sorted(i["date"] for i in agenda.get("items", []) if i.get("date"))
        day = _parse_date(dates[0]) if dates else None
    if not day:
        return None
    start_time = agenda.get("start_time") or ""
    if len(start_time) == 5:
        try:
            return day.replace(
                hour=int(start_time[:2]), minute=int(start_time[3:5])
            )
        except ValueError:
            return day
    return day
