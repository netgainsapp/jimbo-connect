"""Public and shared-secret routes: /api/health, the server-rendered blog,
cron ticks, CAN-SPAM unsubscribe, and the Resend webhook. Moved verbatim from
server.py (M13)."""
import json
import os
import re
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

import database
import email_send
import invites
import nurture
import rate_limit
import seo
import suppression
from agenda import landing as agenda_landing_render
from blog import render as blog_render
from blog.store import list_published, get_by_slug
from news import render as news_render
from news import store as news_store
from core import ADMIN_EMAIL, _tick_authorized

router = APIRouter()


@router.get("/api/health")
async def health():
    """Liveness plus the build that is serving. Render injects
    RENDER_GIT_COMMIT, so `commit` makes it possible to tell from outside
    whether a push has actually rolled out instead of guessing from timing.
    The repo is public, so the SHA discloses nothing."""
    return {
        "ok": True,
        "commit": (os.getenv("RENDER_GIT_COMMIT") or "")[:7],
    }


# ---------- robots.txt + sitemap.xml (canonical origin from seo.content_base) ----------

_SEO_CACHE = "public, s-maxage=3600, stale-while-revalidate=86400"


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    return PlainTextResponse(seo.render_robots(), headers={"Cache-Control": _SEO_CACHE})


@router.get("/sitemap.xml")
async def sitemap_xml():
    # Stable marketing surfaces first, then every published blog + news URL.
    entries = [
        {"path": "/", "changefreq": "weekly", "priority": "1.0"},
        # The free Agenda Builder landing page: a linkable tool page is the
        # strongest organic surface the site has, so it ranks just under home.
        {"path": "/agenda", "changefreq": "monthly", "priority": "0.9"},
        {"path": "/blog", "changefreq": "weekly", "priority": "0.7"},
        {"path": "/news", "changefreq": "daily", "priority": "0.7"},
    ]
    for p in await list_published(limit=1000):
        entries.append(
            {
                "path": f"/blog/{p.get('slug')}",
                "lastmod": p.get("published_at"),
                "changefreq": "monthly",
                "priority": "0.6",
            }
        )
    for a in await news_store.list_published(limit=1000):
        entries.append(
            {
                "path": f"/news/{a.get('slug')}",
                "lastmod": a.get("modified_at") or a.get("published_at"),
                "changefreq": "monthly",
                "priority": "0.6",
            }
        )
    return Response(
        content=seo.render_sitemap(entries),
        media_type="application/xml",
        headers={"Cache-Control": _SEO_CACHE},
    )


# ---------- Public blog (server-rendered; surfaced at the marketing domain
# via a Vercel rewrite). Only published posts are shown. ----------

# Edge-cacheable so the Vercel proxy serves these without round-tripping to
# Render on every hit (avoids cold-start latency on the public blog).
_BLOG_INDEX_CACHE = "public, s-maxage=300, stale-while-revalidate=600"
_BLOG_POST_CACHE = "public, s-maxage=3600, stale-while-revalidate=86400"


@router.get("/agenda", response_class=HTMLResponse)
async def agenda_landing():
    """Marketing landing page for the free Agenda Builder.

    Static content, so it caches hard. Served on the marketing domain through
    the same rewrite as /blog and /news; the interactive builder lives in the
    app at APP_URL/agenda/new.
    """
    return HTMLResponse(
        agenda_landing_render.render_landing(),
        headers={"Cache-Control": _BLOG_POST_CACHE},
    )


@router.get("/blog", response_class=HTMLResponse)
async def blog_index():
    posts = await list_published(limit=50)
    return HTMLResponse(
        blog_render.render_index(posts),
        headers={"Cache-Control": _BLOG_INDEX_CACHE},
    )


# Two path segments, so this cannot be shadowed by /blog/{slug} above it.
@router.get("/blog/cover/{filename}")
async def blog_cover(filename: str):
    """Serve a post's generated cover. Immutable: a new post is a new slug and
    therefore a new URL, so this never needs revalidating."""
    from blog import covers

    slug = filename[:-4] if filename.endswith(".jpg") else filename
    data = await covers.load(slug)
    if not data:
        raise HTTPException(status_code=404, detail="No cover")
    return Response(
        content=bytes(data),
        media_type=covers.CONTENT_TYPE,
        headers={"Cache-Control": covers.CACHE_CONTROL},
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


# ---------- Public news (server-rendered, same shell as the blog) ----------


@router.get("/news", response_class=HTMLResponse)
async def news_index():
    articles = await news_store.list_published(limit=50)
    return HTMLResponse(
        news_render.render_index(articles),
        headers={"Cache-Control": _BLOG_INDEX_CACHE},
    )


@router.get("/news/{slug}", response_class=HTMLResponse)
async def news_article(slug: str):
    doc = await news_store.get_by_slug(slug)
    if not doc:
        return HTMLResponse(news_render.render_404(), status_code=404)
    return HTMLResponse(
        news_render.render_article(doc),
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


@router.post("/api/news/tick")
async def news_tick(request: Request):
    """Write up one real trade-press story. Secret-gated for the weekly cron."""
    if not _tick_authorized(request.headers.get("x-tick-secret")):
        raise HTTPException(status_code=401, detail="Unauthorized")
    from news.generate import run_once

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


# ---------- one pager lead capture (marketing site form) ----------

_LEAD_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

ONE_PAGER_URL = "https://intro-connect.com/intro-connect-one-pager.pdf"


class OnePagerRequest(BaseModel):
    email: str
    name: str = ""
    # Honeypot. The form hides this field, so a value here means a bot filled
    # in every input it found.
    website: str = ""


@router.post("/api/one-pager")
async def request_one_pager(payload: OnePagerRequest, request: Request):
    """Store the lead, email the one pager link with the founding host offer,
    and copy the admin inbox. The PDF itself is public on the marketing site;
    the form is a soft gate whose real product is the lead."""
    email = (payload.email or "").strip().lower()
    if not _LEAD_EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    if payload.website.strip():
        # Pretend success so the bot learns nothing.
        return {"ok": True, "url": ONE_PAGER_URL}
    rate_limit.guard(
        request, "one_pager", limit=5, window_seconds=3600, identifier=email
    )
    now = datetime.now(timezone.utc)
    await database.one_pager_leads.update_one(
        {"email": email},
        {
            "$set": {"name": (payload.name or "").strip()[:120], "last_requested_at": now},
            "$setOnInsert": {
                "email": email,
                "created_at": now,
                "source": "marketing_one_pager",
            },
        },
        upsert=True,
    )
    result = await email_send.send_branded(
        email,
        "Your Intro Connect one pager",
        heading="Here is the one pager",
        paragraphs=[
            "Intro Connect is an online platform that connects guests after "
            "the event ends. The one pager fits the whole story on a single "
            "page: how it works, what you get, and pricing.",
            "Founding host special: your first year of Starter for $199 "
            "instead of $390, for the first 20 founding hosts. Reply to this "
            "email to claim a spot.",
        ],
        button={"label": "Open the one pager", "url": ONE_PAGER_URL},
        marketing=True,
    )
    if ADMIN_EMAIL:
        who = email + (f" ({payload.name.strip()})" if (payload.name or "").strip() else "")
        await email_send.send_email(
            ADMIN_EMAIL,
            f"One pager request: {email}",
            f"<p>{who} requested the one pager from the marketing site.</p>",
        )
    return {"ok": True, "sent": bool(result.get("sent")), "url": ONE_PAGER_URL}


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
