"""Public and shared-secret routes: /api/health, the server-rendered blog,
cron ticks, CAN-SPAM unsubscribe, and the Resend webhook. Moved verbatim from
server.py (M13)."""
import json
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

import invites
import nurture
import rate_limit
import suppression
from blog import render as blog_render
from blog.store import list_published, get_by_slug
from core import _tick_authorized

router = APIRouter()


@router.get("/api/health")
async def health():
    return {"ok": True}


# ---------- Public blog (server-rendered; surfaced at the marketing domain
# via a Vercel rewrite). Only published posts are shown. ----------

# Edge-cacheable so the Vercel proxy serves these without round-tripping to
# Render on every hit (avoids cold-start latency on the public blog).
_BLOG_INDEX_CACHE = "public, s-maxage=300, stale-while-revalidate=600"
_BLOG_POST_CACHE = "public, s-maxage=3600, stale-while-revalidate=86400"


@router.get("/blog", response_class=HTMLResponse)
async def blog_index():
    posts = await list_published(limit=50)
    return HTMLResponse(
        blog_render.render_index(posts),
        headers={"Cache-Control": _BLOG_INDEX_CACHE},
    )


@router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(slug: str):
    doc = await get_by_slug(slug)
    if not doc:
        return HTMLResponse(blog_render.render_404(), status_code=404)
    return HTMLResponse(
        blog_render.render_post(doc),
        headers={"Cache-Control": _BLOG_POST_CACHE},
    )


# ---------- Blog pipeline: cron tick + admin controls ----------

@router.post("/api/blog/tick")
async def blog_tick(request: Request):
    """Run the blog pipeline once. Secret-gated for the scheduled cron."""
    if not _tick_authorized(request.headers.get("x-tick-secret")):
        raise HTTPException(status_code=401, detail="Unauthorized")
    from blog.generate import run_once

    return await run_once()


@router.post("/api/nurture/tick")
async def nurture_tick(request: Request):
    """Advance the free-signup nurture drip once. Secret-gated for the cron."""
    if not _tick_authorized(request.headers.get("x-tick-secret")):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await nurture.run_nurture_tick()


@router.post("/api/invites/tick")
async def invites_tick(request: Request):
    """Send due guest-invite reminders. Secret-gated for the cron."""
    if not _tick_authorized(request.headers.get("x-tick-secret")):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await invites.run_invite_reminder_tick()


# ---------- CAN-SPAM: unsubscribe + Resend bounce/complaint webhook ----------

_UNSUB_OK_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Unsubscribed</title></head>
<body style="font-family:system-ui,sans-serif;max-width:480px;margin:80px auto;text-align:center;color:#222">
<h1 style="font-size:22px">You are unsubscribed</h1>
<p style="color:#555">We will not send you any more emails like that one.
If this was a mistake, reply to any email from us and a real person will fix it.</p>
</body></html>"""

_UNSUB_BAD_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Invalid link</title></head>
<body style="font-family:system-ui,sans-serif;max-width:480px;margin:80px auto;text-align:center;color:#222">
<h1 style="font-size:22px">This link is not valid</h1>
<p style="color:#555">The unsubscribe link looks incomplete or altered.
Reply to any email from us and a real person will take you off the list.</p>
</body></html>"""


@router.get("/api/unsubscribe", response_class=HTMLResponse)
async def unsubscribe_get(token: str, request: Request):
    """Human click from the email footer. The token is HMAC-signed over the
    address, so no auth is needed and the link only unsubscribes that address."""
    rate_limit.guard(request, "unsubscribe", limit=30, window_seconds=3600)
    email = suppression.verify_unsub_token(token)
    if not email:
        return HTMLResponse(_UNSUB_BAD_HTML, status_code=400)
    await suppression.apply_unsubscribe(email)
    return HTMLResponse(_UNSUB_OK_HTML)


@router.post("/api/unsubscribe")
async def unsubscribe_post(token: str, request: Request):
    """RFC 8058 one-click unsubscribe (mailbox providers POST to the
    List-Unsubscribe URL with no body and expect a 2xx)."""
    rate_limit.guard(request, "unsubscribe", limit=30, window_seconds=3600)
    email = suppression.verify_unsub_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid unsubscribe token")
    await suppression.apply_unsubscribe(email)
    return {"ok": True}


@router.post("/api/webhooks/resend")
async def resend_webhook(request: Request):
    """Ingest Resend bounce/complaint events into the suppression list.
    Signature-verified (svix scheme); disabled entirely until
    RESEND_WEBHOOK_SECRET is set."""
    secret = os.getenv("RESEND_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=401, detail="Unauthorized")
    body = await request.body()
    if not suppression.verify_resend_signature(
        secret,
        request.headers.get("svix-id"),
        request.headers.get("svix-timestamp"),
        request.headers.get("svix-signature"),
        body,
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = json.loads(body)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    return await suppression.handle_resend_event(payload)
