import hmac
import ipaddress
import os
import re
import secrets
import socket
import string
import sys
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import FastAPI, HTTPException, Depends, Response, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from bson import ObjectId
from dotenv import load_dotenv

from database import (
    users,
    events,
    event_attendees,
    saved_contacts,
    event_sponsors,
    messages,
    email_templates,
    outreach_leads,
    ensure_indexes,
)
import email_send
import invites
import nurture
import outreach
import rate_limit
from blog import render as blog_render
from blog.store import list_published, get_by_slug
from template_seeds import DEFAULT_TEMPLATES, CATEGORIES as TEMPLATE_CATEGORIES
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    get_current_admin,
    COOKIE_NAME,
)
from models import (
    Profile,
    RegisterRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ProfileUpdateRequest,
    PhotoUploadRequest,
    UserPublic,
    AttendeePublic,
    EventCreateRequest,
    EventUpdateRequest,
    EventPublic,
    SaveContactRequest,
    NoteUpdateRequest,
    SavedContactPublic,
    StatsResponse,
    BulkImportRequest,
    SponsorCreateRequest,
    SponsorUpdateRequest,
    SponsorPublic,
    SendMessageRequest,
    BlogFlagRequest,
    RequestInviteRequest,
    CheckEmailsRequest,
    TemplateUpdateRequest,
    InviteGuestsRequest,
    OutreachAddRequest,
)

load_dotenv()

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@jimboconnect.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def generate_join_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


_OG_RE = re.compile(
    r'<meta\s+(?:[^>]*?\b(?:property|name)\s*=\s*["\']([^"\']+)["\'][^>]*?\bcontent\s*=\s*["\']([^"\']*)["\']'
    r'|[^>]*?\bcontent\s*=\s*["\']([^"\']*)["\'][^>]*?\b(?:property|name)\s*=\s*["\']([^"\']+)["\'])',
    re.IGNORECASE,
)
_TITLE_RE = re.compile(r"<title[^>]*>([^<]+)</title>", re.IGNORECASE)


def _assert_public_url(url: str) -> None:
    """Raise ValueError if the URL points at a non-public address. Prevents the
    server-side fetch from being abused to reach internal services (SSRF), e.g.
    cloud metadata endpoints (169.254.169.254) or localhost/private ranges."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("unsupported scheme")
    host = parsed.hostname
    if not host:
        raise ValueError("missing host")
    # Resolve every address the host maps to and reject any non-public one.
    infos = socket.getaddrinfo(host, None)
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ValueError(f"blocked non-public address: {ip}")


async def _safe_fetch_html(url: str, max_redirects: int = 3) -> str:
    """Fetch HTML while validating the target (and each redirect hop) is a
    public host. Redirects are followed manually so an internal target cannot
    be reached via a 3xx bounce."""
    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=8.0,
        headers={"User-Agent": "Mozilla/5.0 (compatible; IntroConnectBot/1.0)"},
    ) as client:
        for _ in range(max_redirects + 1):
            _assert_public_url(url)
            resp = await client.get(url)
            location = resp.headers.get("location")
            if resp.is_redirect and location:
                url = urljoin(url, location)
                continue
            return resp.text[:300_000]  # cap
    raise ValueError("too many redirects")


async def fetch_og_metadata(url: str) -> dict:
    """Fetch a URL and return open-graph-ish metadata. Best-effort, never raises."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    out = {
        "title": "",
        "description": "",
        "image_url": "",
        "site_name": "",
    }
    try:
        html = await _safe_fetch_html(url)
    except Exception:
        host = urlparse(url).hostname or url
        out["title"] = host
        out["site_name"] = host
        return out

    meta: dict = {}
    for m in _OG_RE.finditer(html):
        key = (m.group(1) or m.group(4) or "").lower()
        val = m.group(2) if m.group(2) is not None else m.group(3)
        if key and val and key not in meta:
            meta[key] = val.strip()

    out["title"] = (
        meta.get("og:title")
        or meta.get("twitter:title")
        or (_TITLE_RE.search(html).group(1).strip() if _TITLE_RE.search(html) else "")
    )
    out["description"] = (
        meta.get("og:description")
        or meta.get("twitter:description")
        or meta.get("description")
        or ""
    )
    image = (
        meta.get("og:image")
        or meta.get("twitter:image")
        or meta.get("twitter:image:src")
        or ""
    )
    if image:
        out["image_url"] = urljoin(url, image)
    out["site_name"] = meta.get("og:site_name") or (urlparse(url).hostname or "")
    if not out["title"]:
        out["title"] = out["site_name"] or url
    return out


_VAR_RE = re.compile(r"\{(\w+)\}")


def merge_vars(text: str, ctx: dict) -> str:
    if not text:
        return ""
    return _VAR_RE.sub(
        lambda m: str(ctx.get(m.group(1), m.group(0))) if ctx.get(m.group(1)) is not None else m.group(0),
        text,
    )


async def get_email_template(template_id: str) -> dict:
    doc = await email_templates.find_one({"template_id": template_id})
    if doc:
        return doc
    for t in DEFAULT_TEMPLATES:
        if t["template_id"] == template_id:
            return t
    return None


async def render_email_template(template_id: str, ctx: dict) -> dict:
    t = await get_email_template(template_id)
    if not t:
        return None
    return {
        "subject": merge_vars(t["subject"], ctx),
        "body": merge_vars(t["body"], ctx),
    }


def body_to_html(body: str) -> str:
    """Very lightweight plain-text → HTML conversion for transactional emails."""
    safe = (
        body.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    paragraphs = "".join(f"<p>{p.replace(chr(10), '<br>')}</p>" for p in safe.split("\n\n"))
    return (
        "<!doctype html><html><body style=\"font-family:Calibri,Segoe UI,system-ui,sans-serif;"
        "color:#0a0c10;background:#f7f8fa;padding:24px\">"
        "<div style=\"max-width:560px;margin:0 auto;background:#fff;border:1px solid #E4E6EA;"
        "border-radius:8px;padding:28px;line-height:1.5\">"
        f"{paragraphs}"
        "</div></body></html>"
    )


def serialize_template(doc: dict) -> dict:
    return {
        "id": doc["template_id"],
        "category": doc.get("category", "event"),
        "title": doc.get("title", ""),
        "blurb": doc.get("blurb", ""),
        "subject": doc.get("subject", ""),
        "body": doc.get("body", ""),
        "system": bool(doc.get("system", False)),
    }


def serialize_sponsor(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "event_id": str(doc["event_id"]),
        "url": doc.get("url", ""),
        "title": doc.get("title", ""),
        "description": doc.get("description", ""),
        "image_url": doc.get("image_url", ""),
        "site_name": doc.get("site_name", ""),
        "active": bool(doc.get("active", True)),
        "added_at": doc.get("added_at"),
    }


def serialize_user(user: dict) -> dict:
    profile = user.get("profile") or {}
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "is_admin": bool(user.get("is_admin")),
        "profile": Profile(**profile).model_dump(),
        "created_at": user.get("created_at", datetime.now(timezone.utc)),
    }


def serialize_attendee(user: dict) -> dict:
    profile = user.get("profile") or {}
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "profile": Profile(**profile).model_dump(),
    }


def serialize_event(event: dict, attendee_count: int = 0) -> dict:
    return {
        "id": str(event["_id"]),
        "name": event["name"],
        "date": event["date"],
        "location": event.get("location", ""),
        "industry_tags": event.get("industry_tags", []),
        "join_code": event["join_code"],
        "created_by": str(event["created_by"]),
        "created_at": event["created_at"],
        "attendee_count": attendee_count,
    }


async def seed_data():
    """Reconcile the canonical admin from env (the source of truth), then
    seed sample data on first run only.

    ADMIN_EMAIL / ADMIN_PASSWORD define the single platform admin. On every
    boot we (1) demote any other lingering admin accounts so old or default
    credentials cannot retain access, and (2) force-set the configured
    admin's password so it can be rotated from the dashboard. Accounts are
    demoted, never deleted, so their history is preserved.
    """
    # Retire any stale admins (e.g. a previous default admin) without deleting.
    await users.update_many(
        {"is_admin": True, "email": {"$ne": ADMIN_EMAIL}},
        {"$set": {"is_admin": False}},
    )

    admin = await users.find_one({"email": ADMIN_EMAIL})
    if admin:
        # Env is authoritative: keep the admin flag and rotate the password
        # on every boot so credentials are managed from the dashboard.
        await users.update_one(
            {"_id": admin["_id"]},
            {"$set": {
                "is_admin": True,
                "password_hash": hash_password(ADMIN_PASSWORD),
            }},
        )
        return

    now = datetime.now(timezone.utc)

    admin_doc = {
        "email": ADMIN_EMAIL,
        "password_hash": hash_password(ADMIN_PASSWORD),
        "is_admin": True,
        "created_at": now,
        "profile": {
            "name": "Intro Admin",
            "role": "Platform Host",
            "company": "Intro Connect",
            "industry": "Events",
            "bio": "Running the show.",
            "looking_for": "",
            "phone": "",
            "linkedin": "",
            "photo_url": "",
        },
    }
    admin_result = await users.insert_one(admin_doc)
    admin_id = admin_result.inserted_id

    sample_attendees = [
        {
            "email": "ava@example.com",
            "profile": {
                "name": "Ava Reynolds",
                "role": "Founder & CEO",
                "company": "Trailhead Labs",
                "industry": "SaaS",
                "bio": "Building developer tools for outdoor brands.",
                "looking_for": "Seed investors, design partners",
                "phone": "303-555-0101",
                "linkedin": "linkedin.com/in/avareynolds",
                "photo_url": "",
            },
        },
        {
            "email": "ben@example.com",
            "profile": {
                "name": "Ben Carter",
                "role": "VP of Engineering",
                "company": "Summit Robotics",
                "industry": "Hardware",
                "bio": "Robotics nerd. Coffee snob.",
                "looking_for": "Senior engineers",
                "phone": "303-555-0102",
                "linkedin": "linkedin.com/in/bencarter",
                "photo_url": "",
            },
        },
        {
            "email": "cara@example.com",
            "profile": {
                "name": "Cara Liu",
                "role": "Product Designer",
                "company": "Aspen Studio",
                "industry": "Design",
                "bio": "Designing calm interfaces.",
                "looking_for": "Freelance projects",
                "phone": "303-555-0103",
                "linkedin": "linkedin.com/in/caraliu",
                "photo_url": "",
            },
        },
        {
            "email": "diego@example.com",
            "profile": {
                "name": "Diego Martinez",
                "role": "Operating Partner",
                "company": "Range Capital",
                "industry": "Venture Capital",
                "bio": "Backing operators in the mountain west.",
                "looking_for": "Pre-seed founders",
                "phone": "303-555-0104",
                "linkedin": "linkedin.com/in/diegomartinez",
                "photo_url": "",
            },
        },
        {
            "email": "elena@example.com",
            "profile": {
                "name": "Elena Park",
                "role": "Head of Marketing",
                "company": "Foothill Foods",
                "industry": "CPG",
                "bio": "Brand and growth in food and beverage.",
                "looking_for": "Agency referrals",
                "phone": "303-555-0105",
                "linkedin": "linkedin.com/in/elenapark",
                "photo_url": "",
            },
        },
    ]

    sample_ids = []
    for s in sample_attendees:
        doc = {
            "email": s["email"],
            "password_hash": hash_password("password123"),
            "is_admin": False,
            "created_at": now,
            "profile": s["profile"],
        }
        result = await users.insert_one(doc)
        sample_ids.append(result.inserted_id)

    event_doc = {
        "name": "Denver Founders Dinner",
        "date": datetime(2026, 6, 15, 18, 30, tzinfo=timezone.utc),
        "location": "Denver, CO",
        "industry_tags": ["SaaS", "Hardware", "Venture Capital", "CPG"],
        "join_code": "DENVER01",
        "created_by": admin_id,
        "created_at": now,
    }
    event_result = await events.insert_one(event_doc)
    event_id = event_result.inserted_id

    for uid in sample_ids:
        await event_attendees.insert_one(
            {"event_id": event_id, "user_id": uid, "joined_at": now}
        )

    if len(sample_ids) >= 3:
        await saved_contacts.insert_one(
            {
                "owner_id": sample_ids[0],
                "contact_id": sample_ids[3],
                "note": "Great fit for our seed round. Follow up Monday.",
                "saved_at": now,
            }
        )
        await saved_contacts.insert_one(
            {
                "owner_id": sample_ids[1],
                "contact_id": sample_ids[2],
                "note": "Interested in design contract for Q3.",
                "saved_at": now,
            }
        )
        await saved_contacts.insert_one(
            {
                "owner_id": sample_ids[2],
                "contact_id": sample_ids[4],
                "note": "Wants to swap notes on brand strategy.",
                "saved_at": now,
            }
        )


async def seed_email_templates():
    for t in DEFAULT_TEMPLATES:
        existing = await email_templates.find_one({"template_id": t["template_id"]})
        if existing:
            continue
        await email_templates.insert_one({**t, "updated_at": datetime.now(timezone.utc)})


def _rebrand_text(text):
    """Replace legacy 'Jimbo Connect' / 'Jimbo' branding with 'Intro Connect'.
    Returns (new_text, changed). 'Jimbo Connect' is replaced first so we never
    produce 'Intro Connect Connect'."""
    if not text or "Jimbo" not in text:
        return text, False
    new = text.replace("Jimbo Connect", "Intro Connect").replace("Jimbo", "Intro Connect")
    return new, new != text


async def migrate_template_branding():
    """One-time, idempotent: rename legacy 'Jimbo' branding in stored email
    templates to 'Intro Connect'. Targeted string replacement, so admin
    customizations are preserved (only the brand name changes). The query only
    matches templates that still contain the old name, so once renamed this is
    a no-op on every subsequent boot."""
    cursor = email_templates.find(
        {"$or": [
            {"subject": {"$regex": "Jimbo"}},
            {"title": {"$regex": "Jimbo"}},
            {"body": {"$regex": "Jimbo"}},
        ]}
    )
    async for doc in cursor:
        updates = {}
        for field in ("subject", "title", "body"):
            new, changed = _rebrand_text(doc.get(field))
            if changed:
                updates[field] = new
        if updates:
            updates["updated_at"] = datetime.now(timezone.utc)
            await email_templates.update_one({"_id": doc["_id"]}, {"$set": updates})


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_indexes()
    await seed_data()
    await seed_email_templates()
    await migrate_template_branding()
    yield


app = FastAPI(title="Intro Connect API", lifespan=lifespan)

_origins = [o.strip() for o in FRONTEND_URL.split(",") if o.strip()]
if "http://localhost:3000" not in _origins:
    _origins.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    # Scope to this project's own Render services and the frontrangedev.co
    # domain only. The previous `.*\.onrender\.com` matched EVERY Render
    # tenant's app, which with allow_credentials=True is a cross-origin risk.
    allow_origin_regex=r"https://(jimbo-connect-[a-z0-9-]+\.onrender\.com|([a-z0-9-]+\.)?frontrangedev\.co)",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin"],
    expose_headers=[],
)


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
    )
    # Tight CSP for the server-rendered blog HTML. Those pages carry no
    # executable JS, only inline <style>, Google Fonts, and a JSON-LD block, all
    # server-controlled and HTML-escaped. 'unsafe-inline' covers the JSON-LD and
    # inline styles without opening an XSS path on already-escaped content.
    if request.url.path == "/blog" or request.url.path.startswith("/blog/"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "script-src 'self' 'unsafe-inline'; object-src 'none'; "
            "base-uri 'self'; frame-ancestors 'none'"
        )
    return response


def _cookie_secure() -> bool:
    return any(o.startswith("https://") for o in _origins)


def set_auth_cookie(response: Response, token: str):
    secure = _cookie_secure()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="none" if secure else "lax",
        secure=secure,
        max_age=60 * 60 * 24 * 7,
        path="/",
    )


# ---------- Auth ----------

# A bcrypt hash to verify against when an email is unknown, so the login path
# takes the same time whether or not the account exists (defeats the timing
# oracle that would otherwise reveal which emails are registered).
_DUMMY_PW_HASH = hash_password("not-a-real-password-timing-equalizer")


@app.post("/api/auth/register")
async def register(payload: RegisterRequest, response: Response, request: Request):
    rate_limit.guard(request, "register", limit=10, window_seconds=3600)
    existing = await users.find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    now = datetime.now(timezone.utc)
    doc = {
        "email": payload.email,
        "password_hash": hash_password(payload.password),
        "is_admin": False,
        "created_at": now,
        "profile": Profile(name=payload.name or "").model_dump(),
        # Self-registered users are enrolled in the nurture drip (bulk-imported
        # attendees are not). Step 0 = welcome sent below.
        "nurture_enabled": True,
        "nurture_step": 0,
    }
    result = await users.insert_one(doc)
    doc["_id"] = result.inserted_id
    try:
        await nurture.send_welcome(doc)
    except Exception as exc:  # never block signup on a mail hiccup
        print(f"[register] welcome email failed: {exc}", file=sys.stderr)
    token = create_access_token(str(result.inserted_id))
    set_auth_cookie(response, token)
    return {"user": serialize_user(doc), "token": token}


@app.post("/api/auth/login")
async def login(payload: LoginRequest, response: Response, request: Request):
    rate_limit.guard(
        request, "login", limit=10, window_seconds=300, identifier=payload.email
    )
    user = await users.find_one({"email": payload.email})
    if not user:
        # Run a dummy verify so the unknown-email path costs the same as a
        # wrong-password path (no user-enumeration timing signal).
        verify_password(payload.password, _DUMMY_PW_HASH)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(str(user["_id"]))
    set_auth_cookie(response, token)
    return {"user": serialize_user(user), "token": token}


@app.post("/api/auth/logout")
async def logout(response: Response):
    secure = _cookie_secure()
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        samesite="none" if secure else "lax",
        secure=secure,
    )
    return {"ok": True}


@app.get("/api/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return serialize_user(user)


@app.post("/api/auth/refresh")
async def refresh(response: Response, user: dict = Depends(get_current_user)):
    token = create_access_token(str(user["_id"]))
    set_auth_cookie(response, token)
    return {"token": token}


from datetime import timedelta as _td


def _new_reset_token() -> str:
    return secrets.token_urlsafe(32)


@app.post("/api/auth/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, request: Request):
    """Generate a one-time reset token. Always returns success
    (even if the email is unknown) to avoid account enumeration.
    Sends a real email if RESEND_API_KEY is configured; otherwise
    returns the reset_url so the user can copy it."""
    rate_limit.guard(
        request, "forgot", limit=5, window_seconds=900, identifier=payload.email
    )
    user = await users.find_one({"email": payload.email.lower().strip()})
    if user:
        token = _new_reset_token()
        expires = datetime.now(timezone.utc) + _td(hours=2)
        await users.update_one(
            {"_id": user["_id"]},
            {"$set": {"reset_token": token, "reset_token_expires": expires}},
        )
        reset_url = f"{FRONTEND_URL}/reset-password/{token}"
        profile = user.get("profile") or {}
        rendered = await render_email_template(
            "password-reset",
            {
                "attendee_name": profile.get("name") or "",
                "attendee_email": user["email"],
                "host_name": "Intro Connect",
                "site_url": FRONTEND_URL,
                "reset_url": reset_url,
            },
        )
        sent = False
        if email_send.is_configured() and rendered:
            result = await email_send.send_email(
                to=user["email"],
                subject=rendered["subject"],
                html=body_to_html(rendered["body"]),
                text=rendered["body"],
            )
            sent = bool(result.get("sent"))
        # Never return the reset link in the response body (that would let anyone
        # request a reset for a victim's email and read the link). When email is
        # not sent (dev, or a send failure), log it server-side instead.
        if not sent:
            print(
                f"[forgot-password] reset link for {user['email']}: {reset_url}",
                file=sys.stderr,
            )
    # Identical response whether or not the account exists, to avoid enumeration.
    return {"ok": True}


@app.post("/api/auth/reset-password")
async def reset_password(payload: ResetPasswordRequest, response: Response, request: Request):
    rate_limit.guard(request, "reset", limit=15, window_seconds=900)
    user = await users.find_one({"reset_token": payload.token})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired link")
    expires = user.get("reset_token_expires")
    if not expires or (
        expires.replace(tzinfo=timezone.utc) if expires.tzinfo is None else expires
    ) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Link has expired")
    await users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"password_hash": hash_password(payload.new_password)},
            "$unset": {"reset_token": "", "reset_token_expires": ""},
        },
    )
    token = create_access_token(str(user["_id"]))
    set_auth_cookie(response, token)
    user["password_hash"] = ""  # don't leak
    return {"ok": True, "user": serialize_user(user), "token": token}


@app.get("/api/auth/magic/{token}")
async def magic_login(token: str, response: Response, request: Request):
    """One-tap login via a reset token. Single-use: the token is cleared
    after a successful login so the link cannot be replayed if it leaks
    (e.g. via referrer headers, logs, or shared history)."""
    rate_limit.guard(request, "magic", limit=10, window_seconds=300)
    user = await users.find_one({"reset_token": token})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired link")
    expires = user.get("reset_token_expires")
    if not expires or (
        expires.replace(tzinfo=timezone.utc) if expires.tzinfo is None else expires
    ) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Link has expired")
    # Invalidate the token now that it has been consumed.
    await users.update_one(
        {"_id": user["_id"]},
        {"$unset": {"reset_token": "", "reset_token_expires": ""}},
    )
    access = create_access_token(str(user["_id"]))
    set_auth_cookie(response, access)
    return {"ok": True, "user": serialize_user(user), "token": access}


# ---------- Profile ----------

@app.get("/api/profile")
async def get_my_profile(user: dict = Depends(get_current_user)):
    return serialize_user(user)


@app.put("/api/profile")
async def update_my_profile(
    payload: ProfileUpdateRequest, user: dict = Depends(get_current_user)
):
    current = Profile(**(user.get("profile") or {})).model_dump()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    current.update(updates)
    await users.update_one({"_id": user["_id"]}, {"$set": {"profile": current}})
    user["profile"] = current
    return serialize_user(user)


@app.post("/api/profile/photo")
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


async def get_user_event_history(user_id):
    out = []
    async for link in event_attendees.find({"user_id": user_id}).sort("joined_at", -1):
        e = await events.find_one({"_id": link["event_id"]})
        if e:
            out.append(
                {
                    "id": str(e["_id"]),
                    "name": e["name"],
                    "date": e["date"],
                    "location": e.get("location", ""),
                }
            )
    return out


@app.get("/api/profile/{user_id}")
async def get_profile_by_id(user_id: str, _: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")
    target = await users.find_one({"_id": oid})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    data = serialize_attendee(target)
    data["events"] = await get_user_event_history(oid)
    return data


# ---------- Events ----------

# Self-serve hosting: any signup can host, the free plan covers one event.
# Admins are unlimited. (Guest cap and directory expiry are separate follow-ups.)
FREE_EVENT_LIMIT = 1


def _can_manage_event(user: dict, event: dict) -> bool:
    """An event is managed by a platform admin or by the host who created it.
    Compare as strings so an ObjectId-vs-string storage mismatch can't silently
    grant or revoke access."""
    if user.get("is_admin"):
        return True
    created_by = event.get("created_by")
    return created_by is not None and str(created_by) == str(user.get("_id"))


@app.post("/api/events")
async def create_event(
    payload: EventCreateRequest, user: dict = Depends(get_current_user)
):
    if not user.get("is_admin"):
        hosted = await events.count_documents({"created_by": user["_id"]})
        if hosted >= FREE_EVENT_LIMIT:
            raise HTTPException(
                status_code=403,
                detail="Your free plan includes one event. Upgrade to host more.",
            )
    code = generate_join_code()
    while await events.find_one({"join_code": code}):
        code = generate_join_code()
    now = datetime.now(timezone.utc)
    doc = {
        "name": payload.name,
        "date": payload.date,
        "location": payload.location or "",
        "industry_tags": payload.industry_tags or [],
        "join_code": code,
        "created_by": user["_id"],
        "created_at": now,
    }
    result = await events.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_event(doc, 0)


@app.get("/api/my-hosted-events")
async def my_hosted_events(user: dict = Depends(get_current_user)):
    """Events this user created (the self-serve host view)."""
    hosted = (
        await events.find({"created_by": user["_id"]}).sort("date", -1).to_list(200)
    )
    if not hosted:
        return []
    event_ids = [e["_id"] for e in hosted]
    counts: dict = {}
    async for row in event_attendees.aggregate(
        [
            {"$match": {"event_id": {"$in": event_ids}}},
            {"$group": {"_id": "$event_id", "n": {"$sum": 1}}},
        ]
    ):
        counts[row["_id"]] = row["n"]
    return [serialize_event(e, counts.get(e["_id"], 0)) for e in hosted]


@app.get("/api/events")
async def list_events(_: dict = Depends(get_current_admin)):
    out = []
    async for e in events.find().sort("date", -1):
        count = await event_attendees.count_documents({"event_id": e["_id"]})
        out.append(serialize_event(e, count))
    return out


@app.get("/api/events/{event_id}")
async def get_event(event_id: str, user: dict = Depends(get_current_user)):
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
    count = await event_attendees.count_documents({"event_id": oid})
    return serialize_event(e, count)


@app.put("/api/events/{event_id}")
async def update_event(
    event_id: str,
    payload: EventUpdateRequest,
    user: dict = Depends(get_current_user),
):
    try:
        oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    e = await events.find_one({"_id": oid})
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    if not _can_manage_event(user, e):
        raise HTTPException(status_code=403, detail="Not your event")
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if updates:
        await events.update_one({"_id": oid}, {"$set": updates})
        e = await events.find_one({"_id": oid})
    count = await event_attendees.count_documents({"event_id": oid})
    return serialize_event(e, count)


@app.delete("/api/events/{event_id}")
async def delete_event(event_id: str, user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    e = await events.find_one({"_id": oid})
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    if not _can_manage_event(user, e):
        raise HTTPException(status_code=403, detail="Not your event")
    await event_attendees.delete_many({"event_id": oid})
    await event_sponsors.delete_many({"event_id": oid})
    await events.delete_one({"_id": oid})
    return {"ok": True}


@app.delete("/api/events/{event_id}/attendees/{user_id}")
async def admin_remove_attendee(
    event_id: str, user_id: str, user: dict = Depends(get_current_user)
):
    try:
        e_oid = ObjectId(event_id)
        u_oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    e = await events.find_one({"_id": e_oid})
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    if not _can_manage_event(user, e):
        raise HTTPException(status_code=403, detail="Not your event")
    result = await event_attendees.delete_one(
        {"event_id": e_oid, "user_id": u_oid}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Attendee not on this event")
    return {"ok": True}


@app.delete("/api/my-events/{event_id}")
async def leave_event(event_id: str, user: dict = Depends(get_current_user)):
    try:
        e_oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    result = await event_attendees.delete_one(
        {"event_id": e_oid, "user_id": user["_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not joined to this event")
    return {"ok": True}


async def _hard_delete_user(user_oid):
    """Cascade: remove from events, saved contacts (both sides),
    messages (both sides), then the user record itself."""
    await event_attendees.delete_many({"user_id": user_oid})
    await saved_contacts.delete_many(
        {"$or": [{"owner_id": user_oid}, {"contact_id": user_oid}]}
    )
    await messages.delete_many(
        {"$or": [{"from_user_id": user_oid}, {"to_user_id": user_oid}]}
    )
    await users.delete_one({"_id": user_oid})


@app.delete("/api/admin/users/{user_id}")
async def admin_delete_user(
    user_id: str, admin: dict = Depends(get_current_admin)
):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")
    if oid == admin["_id"]:
        raise HTTPException(status_code=400, detail="Use 'delete my account' for self")
    target = await users.find_one({"_id": oid})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    await _hard_delete_user(oid)
    return {"ok": True}


@app.delete("/api/profile")
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


@app.post("/api/events/join/{code}")
async def join_event(code: str, user: dict = Depends(get_current_user)):
    e = await events.find_one({"join_code": code.upper()})
    if not e:
        raise HTTPException(status_code=404, detail="Invalid join code")
    existing = await event_attendees.find_one(
        {"event_id": e["_id"], "user_id": user["_id"]}
    )
    if not existing:
        await event_attendees.insert_one(
            {
                "event_id": e["_id"],
                "user_id": user["_id"],
                "joined_at": datetime.now(timezone.utc),
            }
        )
    # Stop any pending invite reminders for this guest on this event.
    await invites.mark_joined(e["_id"], user.get("email", ""))
    count = await event_attendees.count_documents({"event_id": e["_id"]})
    return serialize_event(e, count)


@app.post("/api/events/{event_id}/invite")
async def invite_guests(
    event_id: str,
    payload: InviteGuestsRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Self-serve: a host emails their guest list a join link."""
    rate_limit.guard(request, "invite", limit=5, window_seconds=3600)
    try:
        oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    e = await events.find_one({"_id": oid})
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    if not _can_manage_event(user, e):
        raise HTTPException(status_code=403, detail="Not your event")
    host_name = (user.get("profile") or {}).get("name") or ""
    return await invites.send_event_invites(e, payload.emails, host_name)


@app.get("/api/events/{event_id}/attendees")
async def get_event_attendees(event_id: str, user: dict = Depends(get_current_user)):
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
    out = []
    links = await event_attendees.find({"event_id": oid}).to_list(None)
    user_ids = [link["user_id"] for link in links]
    if user_ids:
        by_id = {
            u["_id"]: u
            for u in await users.find({"_id": {"$in": user_ids}}).to_list(None)
        }
        for link in links:
            attendee = by_id.get(link["user_id"])
            if attendee and not attendee.get("is_admin"):
                out.append(serialize_attendee(attendee))
    return out


@app.get("/api/events/discoverable")
async def discoverable_events(user: dict = Depends(get_current_user)):
    """Upcoming events the user hasn't joined yet."""
    now = datetime.now(timezone.utc)
    joined_ids = set()
    async for link in event_attendees.find({"user_id": user["_id"]}):
        joined_ids.add(link["event_id"])
    candidates = [
        e
        for e in await events.find({"date": {"$gte": now}}).sort("date", 1).to_list(None)
        if e["_id"] not in joined_ids
    ]
    event_ids = [e["_id"] for e in candidates]
    counts: dict = {}
    if event_ids:
        async for row in event_attendees.aggregate(
            [
                {"$match": {"event_id": {"$in": event_ids}}},
                {"$group": {"_id": "$event_id", "n": {"$sum": 1}}},
            ]
        ):
            counts[row["_id"]] = row["n"]
    host_ids = list({e.get("created_by") for e in candidates if e.get("created_by")})
    hosts: dict = {}
    if host_ids:
        for h in await users.find({"_id": {"$in": host_ids}}).to_list(None):
            hosts[h["_id"]] = h
    out = []
    for e in candidates:
        host = hosts.get(e.get("created_by"))
        host_profile = (host or {}).get("profile") or {}
        out.append(
            {
                "id": str(e["_id"]),
                "name": e["name"],
                "date": e["date"],
                "location": e.get("location", ""),
                "industry_tags": e.get("industry_tags", []),
                "attendee_count": counts.get(e["_id"], 0),
                "host_name": host_profile.get("name")
                or (host or {}).get("email", "")
                or "",
            }
        )
    return out


@app.post("/api/events/{event_id}/request-invite")
async def request_invite(
    event_id: str,
    payload: RequestInviteRequest,
    user: dict = Depends(get_current_user),
):
    try:
        oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    e = await events.find_one({"_id": oid})
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    host = await users.find_one({"_id": e.get("created_by")})
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    existing = await event_attendees.find_one(
        {"event_id": oid, "user_id": user["_id"]}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already joined")

    note = (payload.message or "").strip()
    profile = user.get("profile") or {}
    name = profile.get("name") or user["email"]
    role_company = " · ".join(
        [s for s in [profile.get("role"), profile.get("company")] if s]
    )

    text = f"📬 Invite request: {name}"
    if role_company:
        text += f" ({role_company})"
    text += f' would like to join "{e["name"]}".'
    if note:
        text += f"\n\n\"{note}\""

    await messages.insert_one(
        {
            "thread_id": _thread_id(user["_id"], host["_id"]),
            "from_user_id": user["_id"],
            "to_user_id": host["_id"],
            "text": text,
            "sent_at": datetime.now(timezone.utc),
            "read_at": None,
        }
    )

    if email_send.is_configured():
        await email_send.send_email(
            to=host["email"],
            subject=f"Invite request: {e['name']}",
            html=body_to_html(
                text + f"\n\nReply: {FRONTEND_URL}/messages/{str(user['_id'])}"
            ),
            text=text,
        )

    return {"ok": True}


@app.get("/api/my-attendees")
async def my_attendees(user: dict = Depends(get_current_user)):
    """Every unique attendee from every event the user has joined."""
    my_event_ids = []
    async for link in event_attendees.find({"user_id": user["_id"]}):
        my_event_ids.append(link["event_id"])
    if not my_event_ids:
        return []
    seen: set = set()
    uids = []
    async for link in event_attendees.find({"event_id": {"$in": my_event_ids}}):
        uid = link["user_id"]
        if uid == user["_id"]:
            continue
        key = str(uid)
        if key in seen:
            continue
        seen.add(key)
        uids.append(uid)
    out = []
    if uids:
        docs = {
            u["_id"]: u
            for u in await users.find({"_id": {"$in": uids}}).to_list(None)
        }
        for uid in uids:
            u = docs.get(uid)
            if u and not u.get("is_admin"):
                out.append(serialize_attendee(u))
    return out


@app.get("/api/my-events")
async def my_events(user: dict = Depends(get_current_user)):
    links = (
        await event_attendees.find({"user_id": user["_id"]})
        .sort("joined_at", -1)
        .to_list(None)
    )
    event_ids = [link["event_id"] for link in links]
    if not event_ids:
        return []
    events_by_id = {
        e["_id"]: e
        for e in await events.find({"_id": {"$in": event_ids}}).to_list(None)
    }
    counts: dict = {}
    async for row in event_attendees.aggregate(
        [
            {"$match": {"event_id": {"$in": event_ids}}},
            {"$group": {"_id": "$event_id", "n": {"$sum": 1}}},
        ]
    ):
        counts[row["_id"]] = row["n"]
    out = []
    for link in links:
        e = events_by_id.get(link["event_id"])
        if e:
            out.append(serialize_event(e, counts.get(e["_id"], 0)))
    return out


# ---------- Contacts ----------

@app.post("/api/contacts/save")
async def save_contact(
    payload: SaveContactRequest, user: dict = Depends(get_current_user)
):
    try:
        contact_oid = ObjectId(payload.contact_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid contact id")
    if contact_oid == user["_id"]:
        raise HTTPException(status_code=400, detail="Cannot save yourself")
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


@app.delete("/api/contacts/{contact_id}")
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


@app.get("/api/contacts")
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


@app.put("/api/contacts/{contact_id}/note")
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


@app.get("/api/contacts/{contact_id}/is-saved")
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


# ---------- Admin ----------

@app.get("/api/admin/users")
async def admin_list_users(_: dict = Depends(get_current_admin)):
    all_users = (
        await users.find({"is_admin": {"$ne": True}})
        .sort("created_at", -1)
        .to_list(None)
    )
    links_by_user: dict = {}
    if all_users:
        async for link in event_attendees.find(
            {"user_id": {"$in": [u["_id"] for u in all_users]}}
        ):
            links_by_user.setdefault(link["user_id"], []).append(
                str(link["event_id"])
            )
    out = []
    for u in all_users:
        event_ids = links_by_user.get(u["_id"], [])
        out.append(
            {
                "id": str(u["_id"]),
                "email": u["email"],
                "profile": Profile(**(u.get("profile") or {})).model_dump(),
                "event_count": len(event_ids),
                "event_ids": event_ids,
                "created_at": u.get("created_at"),
            }
        )
    return out


@app.api_route("/api/admin/reseed-templates", methods=["GET", "POST"])
async def admin_reseed_templates(_: dict = Depends(get_current_admin)):
    """Force-seed any missing default templates. Idempotent: only inserts
    missing rows. Admin-only (it writes to the DB)."""
    inserted = 0
    for t in DEFAULT_TEMPLATES:
        existing = await email_templates.find_one({"template_id": t["template_id"]})
        if existing:
            continue
        await email_templates.insert_one(
            {**t, "updated_at": datetime.now(timezone.utc)}
        )
        inserted += 1
    return {"inserted": inserted}


@app.get("/api/admin/stats")
async def admin_stats(_: dict = Depends(get_current_admin)):
    total_users = await users.count_documents({"is_admin": {"$ne": True}})
    total_events = await events.count_documents({})
    total_connections = await saved_contacts.count_documents({})
    return {
        "total_users": total_users,
        "total_events": total_events,
        "total_connections": total_connections,
    }


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


@app.get("/api/events/{event_id}/sponsors")
async def list_event_sponsors(event_id: str, user: dict = Depends(get_current_user)):
    oid, _ = await _require_event_access(event_id, user)
    out = []
    cursor = event_sponsors.find({"event_id": oid}).sort("added_at", 1)
    async for doc in cursor:
        if user.get("is_admin") or doc.get("active", True):
            out.append(serialize_sponsor(doc))
    return out


@app.post("/api/events/{event_id}/sponsors")
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


@app.put("/api/events/{event_id}/sponsors/{sponsor_id}")
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


@app.post("/api/events/{event_id}/sponsors/{sponsor_id}/refresh")
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


@app.delete("/api/events/{event_id}/sponsors/{sponsor_id}")
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


@app.post("/api/admin/users/check-emails")
async def admin_check_emails(
    payload: CheckEmailsRequest, _: dict = Depends(get_current_admin)
):
    emails = [str(e).lower().strip() for e in payload.emails if e]
    matches = []
    found_set = set()
    if emails:
        cursor = users.find({"email": {"$in": emails}})
        async for u in cursor:
            profile = u.get("profile") or {}
            matches.append(
                {
                    "id": str(u["_id"]),
                    "email": u["email"],
                    "is_admin": bool(u.get("is_admin")),
                    "profile": {
                        "name": profile.get("name", ""),
                        "role": profile.get("role", ""),
                        "company": profile.get("company", ""),
                        "photo_url": profile.get("photo_url", ""),
                    },
                }
            )
            found_set.add(u["email"])
    not_found = [e for e in emails if e not in found_set]
    return {"matches": matches, "not_found": not_found}


@app.get("/api/email-templates")
async def list_email_templates_api(_: dict = Depends(get_current_admin)):
    out = []
    async for doc in email_templates.find().sort("_id", 1):
        out.append(serialize_template(doc))
    return {"templates": out, "categories": TEMPLATE_CATEGORIES}


@app.put("/api/email-templates/{template_id}")
async def update_email_template_api(
    template_id: str,
    payload: TemplateUpdateRequest,
    _: dict = Depends(get_current_admin),
):
    updates = {}
    if payload.subject is not None:
        updates["subject"] = payload.subject
    if payload.body is not None:
        updates["body"] = payload.body
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")
    updates["updated_at"] = datetime.now(timezone.utc)
    result = await email_templates.update_one(
        {"template_id": template_id}, {"$set": updates}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    doc = await email_templates.find_one({"template_id": template_id})
    return serialize_template(doc)


@app.post("/api/email-templates/{template_id}/reset")
async def reset_email_template_api(
    template_id: str, _: dict = Depends(get_current_admin)
):
    default = next(
        (t for t in DEFAULT_TEMPLATES if t["template_id"] == template_id), None
    )
    if not default:
        raise HTTPException(status_code=404, detail="No default for this template")
    await email_templates.update_one(
        {"template_id": template_id},
        {"$set": {**default, "updated_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    doc = await email_templates.find_one({"template_id": template_id})
    return serialize_template(doc)


@app.post("/api/admin/users/bulk-import")
async def admin_bulk_import(
    payload: BulkImportRequest, admin: dict = Depends(get_current_admin)
):
    event_oid = None
    event_doc = None
    if payload.event_id:
        try:
            event_oid = ObjectId(payload.event_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid event id")
        event_doc = await events.find_one({"_id": event_oid})
        if not event_doc:
            raise HTTPException(status_code=404, detail="Event not found")

    now = datetime.now(timezone.utc)
    created = 0
    skipped = 0
    added_to_event = 0
    accounts: list = []
    errors: list = []

    for row in payload.rows:
        email = row.email.lower().strip()
        try:
            existing = await users.find_one({"email": email})
            if existing:
                skipped += 1
                user_id = existing["_id"]
            else:
                temp_password = (
                    payload.default_password
                    or "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
                )
                profile = {
                    "name": row.name or "",
                    "role": row.role or "",
                    "company": row.company or "",
                    "industry": row.industry or "",
                    "bio": row.bio or "",
                    "looking_for": row.looking_for or "",
                    "phone": row.phone or "",
                    "linkedin": row.linkedin or "",
                    "photo_url": "",
                }
                doc = {
                    "email": email,
                    "password_hash": hash_password(temp_password),
                    "is_admin": False,
                    "created_at": now,
                    "profile": profile,
                }
                result = await users.insert_one(doc)
                user_id = result.inserted_id
                created += 1
                accounts.append({"email": email, "password": temp_password})

                # Send invitation email if Resend is configured
                if email_send.is_configured():
                    admin_profile = admin.get("profile") or {}
                    rendered = await render_email_template(
                        "invitation",
                        {
                            "attendee_name": row.name or "",
                            "attendee_email": email,
                            "temp_password": temp_password,
                            "event_name": event_doc["name"] if event_doc else "",
                            "event_date": event_doc["date"].strftime("%B %d, %Y")
                            if event_doc
                            else "",
                            "event_location": event_doc.get("location", "")
                            if event_doc
                            else "",
                            "host_name": admin_profile.get("name") or "Jim",
                            "site_url": FRONTEND_URL,
                        },
                    )
                    if rendered:
                        await email_send.send_email(
                            to=email,
                            subject=rendered["subject"],
                            html=body_to_html(rendered["body"]),
                            text=rendered["body"],
                        )

            if event_oid:
                already = await event_attendees.find_one(
                    {"event_id": event_oid, "user_id": user_id}
                )
                if not already:
                    await event_attendees.insert_one(
                        {
                            "event_id": event_oid,
                            "user_id": user_id,
                            "joined_at": now,
                        }
                    )
                    added_to_event += 1
        except Exception as e:
            errors.append({"email": email, "error": str(e)})

    return {
        "created": created,
        "skipped": skipped,
        "added_to_event": added_to_event,
        "errors": errors,
        "accounts": accounts,
    }


# ---------- Messages ----------

def _thread_id(a, b) -> str:
    a, b = str(a), str(b)
    return f"{a}:{b}" if a < b else f"{b}:{a}"


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


@app.post("/api/messages")
async def send_message(
    payload: SendMessageRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    rate_limit.guard(request, "messages", limit=30, window_seconds=60)
    try:
        to_oid = ObjectId(payload.to_user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid recipient")
    if to_oid == user["_id"]:
        raise HTTPException(status_code=400, detail="Cannot message yourself")
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


@app.get("/api/messages/threads")
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


@app.get("/api/messages/with/{user_id}")
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


@app.get("/api/messages/unread-count")
async def unread_count(user: dict = Depends(get_current_user)):
    n = await messages.count_documents(
        {"to_user_id": user["_id"], "read_at": None}
    )
    return {"unread": n}


@app.get("/api/health")
async def health():
    return {"ok": True}


# ---------- Public blog (server-rendered; surfaced at the marketing domain
# via a Vercel rewrite). Only published posts are shown. ----------

# Edge-cacheable so the Vercel proxy serves these without round-tripping to
# Render on every hit (avoids cold-start latency on the public blog).
_BLOG_INDEX_CACHE = "public, s-maxage=300, stale-while-revalidate=600"
_BLOG_POST_CACHE = "public, s-maxage=3600, stale-while-revalidate=86400"


@app.get("/blog", response_class=HTMLResponse)
async def blog_index():
    posts = await list_published(limit=50)
    return HTMLResponse(
        blog_render.render_index(posts),
        headers={"Cache-Control": _BLOG_INDEX_CACHE},
    )


@app.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(slug: str):
    doc = await get_by_slug(slug)
    if not doc:
        return HTMLResponse(blog_render.render_404(), status_code=404)
    return HTMLResponse(
        blog_render.render_post(doc),
        headers={"Cache-Control": _BLOG_POST_CACHE},
    )


# ---------- Blog pipeline: cron tick + admin controls ----------

def _tick_authorized(provided) -> bool:
    """The tick runs only with the configured shared secret (the GitHub Actions
    cron sends it). Disabled entirely when no secret is set."""
    secret = os.getenv("BLOG_TICK_SECRET")
    if not secret or not provided:
        return False
    return hmac.compare_digest(provided, secret)


def _serialize_blog_post(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "slug": doc.get("slug", ""),
        "title": doc.get("title", ""),
        "summary": doc.get("summary", ""),
        "status": doc.get("status", "draft"),
        "guardrail_reasons": doc.get("guardrail_reasons", []),
        "topic_id": doc.get("topic_id"),
        "created_at": doc.get("created_at"),
        "published_at": doc.get("published_at"),
    }


@app.post("/api/blog/tick")
async def blog_tick(request: Request):
    """Run the blog pipeline once. Secret-gated for the scheduled cron."""
    if not _tick_authorized(request.headers.get("x-tick-secret")):
        raise HTTPException(status_code=401, detail="Unauthorized")
    from blog.generate import run_once

    return await run_once()


@app.post("/api/nurture/tick")
async def nurture_tick(request: Request):
    """Advance the free-signup nurture drip once. Secret-gated for the cron."""
    if not _tick_authorized(request.headers.get("x-tick-secret")):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await nurture.run_nurture_tick()


@app.post("/api/invites/tick")
async def invites_tick(request: Request):
    """Send due guest-invite reminders. Secret-gated for the cron."""
    if not _tick_authorized(request.headers.get("x-tick-secret")):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await invites.run_invite_reminder_tick()


# ---------- Outreach cockpit (stages host-acquisition leads, hands off to
# signal-scout for sending). Admin only. ----------

def _serialize_lead(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "email": doc.get("email", ""),
        "name": doc.get("name", ""),
        "company": doc.get("company", ""),
        "role": doc.get("role", ""),
        "source": doc.get("source", ""),
        "status": doc.get("status", "new"),
        "created_at": doc.get("created_at"),
        "pushed_at": doc.get("pushed_at"),
    }


@app.get("/api/admin/outreach/status")
async def outreach_status(_: dict = Depends(get_current_admin)):
    total = await outreach_leads.count_documents({})
    pushed = await outreach_leads.count_documents({"status": "pushed"})
    return {
        "configured": outreach.is_configured(),
        "signal_scout_url": outreach.SIGNAL_SCOUT_URL or None,
        "total": total,
        "pushed": pushed,
        "new": total - pushed,
    }


@app.get("/api/admin/outreach/leads")
async def outreach_list(_: dict = Depends(get_current_admin)):
    docs = await outreach_leads.find({}).sort("created_at", -1).to_list(1000)
    return [_serialize_lead(d) for d in docs]


@app.post("/api/admin/outreach/leads")
async def outreach_add(
    payload: OutreachAddRequest, _: dict = Depends(get_current_admin)
):
    now = datetime.now(timezone.utc)
    added = 0
    for lead in payload.leads:
        email = str(lead.email).lower().strip()
        res = await outreach_leads.update_one(
            {"email": email},
            {
                "$setOnInsert": {
                    "email": email,
                    "name": lead.name or "",
                    "company": lead.company or "",
                    "role": lead.role or "",
                    "source": lead.source or "",
                    "status": "new",
                    "created_at": now,
                }
            },
            upsert=True,
        )
        if res.upserted_id is not None:
            added += 1
    return {"added": added, "received": len(payload.leads)}


@app.delete("/api/admin/outreach/leads/{lead_id}")
async def outreach_remove(lead_id: str, _: dict = Depends(get_current_admin)):
    try:
        oid = ObjectId(lead_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    res = await outreach_leads.delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"ok": True}


@app.get("/api/admin/outreach/leads.csv")
async def outreach_csv(_: dict = Depends(get_current_admin)):
    docs = await outreach_leads.find({}).sort("created_at", -1).to_list(None)
    return Response(
        content=outreach.to_csv(docs),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=intro-connect-leads.csv"
        },
    )


@app.post("/api/admin/outreach/push")
async def outreach_push(_: dict = Depends(get_current_admin)):
    docs = await outreach_leads.find({"status": {"$ne": "pushed"}}).to_list(None)
    if not docs:
        return {"ok": False, "skipped": "no_new_leads"}
    result = await outreach.push_to_signal_scout(docs)
    if result.get("ok"):
        now = datetime.now(timezone.utc)
        await outreach_leads.update_many(
            {"_id": {"$in": [d["_id"] for d in docs]}},
            {"$set": {"status": "pushed", "pushed_at": now}},
        )
    return result


@app.post("/api/admin/blog/run")
async def admin_blog_run(_: dict = Depends(get_current_admin)):
    from blog.generate import run_once

    return await run_once()


@app.get("/api/admin/blog/flags")
async def admin_blog_flags(_: dict = Depends(get_current_admin)):
    from blog.flags import get_flags

    return await get_flags()


@app.put("/api/admin/blog/flags")
async def admin_blog_set_flag(
    payload: BlogFlagRequest, _: dict = Depends(get_current_admin)
):
    from blog.flags import set_flag, get_flags

    try:
        await set_flag(payload.name, payload.value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Unknown flag")
    return await get_flags()


@app.get("/api/admin/blog/posts")
async def admin_blog_posts(_: dict = Depends(get_current_admin)):
    from blog.store import list_all

    posts = await list_all()
    return [_serialize_blog_post(p) for p in posts]


@app.post("/api/admin/blog/posts/{post_id}/publish")
async def admin_blog_publish(post_id: str, _: dict = Depends(get_current_admin)):
    from blog.store import publish_post

    res = await publish_post(post_id)
    if res is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if res.get("error"):
        raise HTTPException(
            status_code=400,
            detail={"error": res["error"], "reasons": res.get("reasons", [])},
        )
    return _serialize_blog_post(res)


@app.post("/api/admin/blog/posts/{post_id}/unpublish")
async def admin_blog_unpublish(post_id: str, _: dict = Depends(get_current_admin)):
    from blog.store import unpublish_post

    res = await unpublish_post(post_id)
    if res is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return _serialize_blog_post(res)
