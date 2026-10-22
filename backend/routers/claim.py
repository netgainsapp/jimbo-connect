"""/api/claim/{token}: the public claim link a prospect host opens.

Thin on purpose; event_leads_claim holds the rules. Public by design (the
host has no session yet) and rate limited per IP, one bucket for both verbs.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Request, Response
from fastapi.responses import JSONResponse

import event_leads_claim as claim
import outreach
import rate_limit
from auth import create_access_token, get_current_user_optional
from core import set_auth_cookie
from models import ClaimCompleteRequest

router = APIRouter()

RATE_BUCKET = "claim"
RATE_LIMIT = 10
RATE_WINDOW_SECONDS = 300


def _guard(request):
    rate_limit.guard(request, RATE_BUCKET, limit=RATE_LIMIT, window_seconds=RATE_WINDOW_SECONDS)


@router.get("/api/claim/{token}")
async def preview_claim(token: str, request: Request):
    _guard(request)
    return await claim.preview(token, datetime.now(timezone.utc))


@router.post("/api/claim/{token}")
async def complete_claim(
    token: str,
    request: Request,
    response: Response,
    background: BackgroundTasks,
    payload: Optional[ClaimCompleteRequest] = None,
):
    _guard(request)
    session_user = await get_current_user_optional(request)
    try:
        done = await claim.complete(token, payload, session_user, datetime.now(timezone.utc))
    except claim.DeadLink as dead:
        # A fresh response, so no cookie rides along.
        return JSONResponse({"state": dead.state}, status_code=claim.DEAD_LINK_STATUS[dead.state])
    if done.first:
        # After the response: the host never waits on Signal Scout.
        background.add_task(outreach.notify_claimed, done.lead)
    access = create_access_token(str(done.user["_id"]))
    set_auth_cookie(response, access)
    return {
        "ok": True,
        "state": "ok",
        "redirect": claim.redirect_for(done.event),
        "event": {"id": str(done.event["_id"]), "name": done.event.get("name") or ""},
        "token": access,
    }
