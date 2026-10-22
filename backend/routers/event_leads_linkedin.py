"""LinkedIn routes of the event lead engine: the queue CSV Linked Helper reads,
the results import (CSV upload or parsed rows) and the Linked Helper webhook.

Included in server.py before routers.event_leads, whose `/{lead_id}` GET would
otherwise match `linkedin-queue.csv`. Row mapping and the forward-only rule are
in linkedin_results; applying them is in linkedin_sync.
"""
import csv
import hmac
import io
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from starlette.datastructures import UploadFile

import event_leads_copy as copy
import event_leads_store as store
import linkedin_queue as queue
import linkedin_sync as sync
from auth import get_current_admin
from routers.event_leads import stored_or_seed

router = APIRouter()

MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_ROWS = 5000
WEBHOOK_SECRET_ENV = "LINKED_HELPER_WEBHOOK_SECRET"


def require_webhook_secret(secret: Optional[str] = Query(None)):
    """Shared-secret gate for the Linked Helper webhook. Fails closed: with no
    secret configured nothing can authenticate. A dependency, so it runs before
    the body is read."""
    configured = os.getenv(WEBHOOK_SECRET_ENV)
    if not configured or not secret or not hmac.compare_digest(
        secret.encode(), configured.encode()
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")


async def _mark_exported(lead, now):
    """Move one lead from queued to exported. False when another export got
    there first, so the same lead is never handed out twice."""
    return await store.update_lead_if(
        lead["_id"],
        {"linkedin.status": "queued"},
        {
            "linkedin.status": "exported",
            "linkedin.exported_at": now,
            "linkedin.updated_at": now,
        },
    )


@router.get("/api/admin/event-leads/linkedin-queue.csv")
async def linkedin_queue_csv(
    dry_run: bool = False, admin: dict = Depends(get_current_admin)
):
    now = datetime.now(timezone.utc)
    note = await stored_or_seed(copy.NOTE_KEY)
    followup = await stored_or_seed(copy.FOLLOWUP_KEY)
    rows = []
    for lead in await store.list_linkedin_queue():
        if not queue.has_url(lead):
            continue
        row = queue.queue_row(lead, note["body"], followup["body"], now)
        if dry_run or await _mark_exported(lead, now):
            rows.append(row)
    disposition = f'attachment; filename="{queue.export_filename(now)}"'
    return Response(
        content=queue.to_csv(rows),
        media_type="text/csv",
        headers={"Content-Disposition": disposition},
    )


def _bad_request(detail):
    return HTTPException(status_code=400, detail=detail)


async def _json_rows(request):
    try:
        body = await request.json()
    except ValueError:
        raise _bad_request("Body is not valid JSON")
    rows = body.get("rows") if isinstance(body, dict) else None
    if not isinstance(rows, list):
        raise _bad_request("Send a CSV file or a JSON body with a rows list")
    return rows


async def _csv_rows(request):
    upload = (await request.form()).get("file")
    if not isinstance(upload, UploadFile):
        raise _bad_request("Send a CSV file or a JSON body with a rows list")
    data = await upload.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="CSV file is too large")
    try:
        return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
    except (UnicodeDecodeError, csv.Error):
        raise _bad_request("File is not a readable UTF-8 CSV")


async def _read_rows(request):
    is_json = request.headers.get("content-type", "").startswith("application/json")
    rows = await (_json_rows(request) if is_json else _csv_rows(request))
    if len(rows) > MAX_ROWS:
        raise _bad_request(f"At most {MAX_ROWS} rows per import")
    return rows


@router.post("/api/admin/event-leads/linkedin-results")
async def import_linkedin_results(
    request: Request, admin: dict = Depends(get_current_admin)
):
    rows = await _read_rows(request)
    result = await sync.import_rows(rows, datetime.now(timezone.utc))
    return {"ok": True, **result}


async def _webhook_rows(request):
    try:
        body = await request.json()
    except ValueError:
        raise _bad_request("Body is not valid JSON")
    rows = body if isinstance(body, list) else [body]
    if len(rows) > MAX_ROWS or not all(isinstance(row, dict) for row in rows):
        raise _bad_request("Send one JSON object or a list of objects")
    return rows


@router.post(
    "/api/admin/event-leads/linkedin-webhook",
    dependencies=[Depends(require_webhook_secret)],
)
async def linkedin_webhook(request: Request):
    rows = await _webhook_rows(request)
    result = await sync.import_rows(rows, datetime.now(timezone.utc))
    return {"ok": True, **{k: result[k] for k in ("updated", "unchanged", "unknown")}}
