"""Agenda Builder API.

Phase 1 exposes exactly one route, and it is public: the builder is a free
acquisition tool that has to work before anyone has an account. Nothing is
persisted, so the request body carries the whole agenda and the response is the
finished document.
"""
from __future__ import annotations

import base64

from fastapi import APIRouter, HTTPException, Request, Response

import branding
import rate_limit
from agenda.docx import build_docx
from agenda.schema import AgendaExportRequest, slugify_filename

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
