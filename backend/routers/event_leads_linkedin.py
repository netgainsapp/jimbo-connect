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
import sys
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
SKIPPED_HEADER = "X-Linkedin-Skipped"


def require_webhook_secret(secret: Optional[str] = Query(None)):
    """Shared-secret gate for the Linked Helper webhook. Fails closed: with no
    secret configured nothing can authenticate. A dependency, so it runs before
    the body is read."""
    configured = os.getenv(WEBHOOK_SECRET_ENV)
    if not configured or not secret or not hmac.compare_digest(
        secret.encode(), configured.encode()
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _log_skip(lead, exc):
    """Name the lead by id and the failure by type only: no contact data."""
    print(f"[event_leads] linkedin export skipped lead {lead['_id']}: "
          f"{type(exc).__name__}", file=sys.stderr)


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


def _build_rows(leads, note, followup, now):
    """(lead, row) for every lead whose row could be built, and how many
    failed. A failing lead is skipped and stays queued."""
    built, skipped = [], 0
    for lead in leads:
        if not queue.has_url(lead):
            continue
        try:
            built.append((lead, queue.queue_row(lead, note["body"], followup["body"], now)))
        except Exception as exc:  # one bad lead must not lose the whole export
            _log_skip(lead, exc)
            skipped += 1
    return built, skipped


async def _claim_rows(built, now, mark):
    """Rows to return, with each queued lead marked exported first. A lead
    that cannot be marked (lost race, write error) is left out and stays
    queued; an already exported lead is listed without re-marking."""
    rows, skipped = [], 0
    for lead, row in built:
        needs_mark = mark and (lead.get("linkedin") or {}).get("status") == "queued"
        try:
            if needs_mark and not await _mark_exported(lead, now):
                continue
        except Exception as exc:  # leave it queued, keep the other leads
            _log_skip(lead, exc)
            skipped += 1
            continue
        rows.append(row)
    return rows, skipped


@router.get("/api/admin/event-leads/linkedin-queue.csv")
async def linkedin_queue_csv(
    dry_run: bool = False,
    include_exported: bool = False,
    admin: dict = Depends(get_current_admin),
):
    """Build every row first, then mark only the leads whose rows were built,
    so a failure can never leave a lead exported without being in a file."""
    now = datetime.now(timezone.utc)
    note = await stored_or_seed(copy.NOTE_KEY)
    followup = await stored_or_seed(copy.FOLLOWUP_KEY)
    leads = await store.list_linkedin_queue(include_exported)
    built, failed = _build_rows(leads, note, followup, now)
    rows, unmarked = await _claim_rows(built, now, mark=not dry_run)
    headers = {
        "Content-Disposition": f'attachment; filename="{queue.export_filename(now)}"',
        SKIPPED_HEADER: str(failed + unmarked),
    }
    return Response(content=queue.to_csv(rows), media_type="text/csv", headers=headers)


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
    content_type = request.headers.get("content-type", "").lower()
    is_json = content_type.startswith("application/json")
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
