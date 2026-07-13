"""Application assembly for the Intro Connect API (M13 router split).

All route handlers live in routers/* and shared non-route code lives in
core.py / ogfetch.py. This module owns the FastAPI app object, lifespan,
middleware, router registration, and backward-compatible re-exports so
existing imports of `server.<name>` keep working.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

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

# Backward-compat re-exports: helpers that lived in server.py before the M13
# split. Callers may keep importing them from server; monkeypatching in tests
# must target the owning module (core / ogfetch).
from core import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    FRONTEND_URL,
    generate_join_code,
    merge_vars,
    get_email_template,
    render_email_template,
    body_to_html,
    serialize_template,
    serialize_sponsor,
    serialize_user,
    serialize_attendee,
    serialize_event,
    seed_data,
    seed_email_templates,
    _rebrand_text,
    migrate_template_branding,
    _origins,
    _cookie_secure,
    set_auth_cookie,
    _DUMMY_PW_HASH,
    _new_reset_token,
    _hash_token,
    _VERIFY_EXPIRY_DAYS,
    verify_email_body,
    issue_email_verification,
    apply_email_verification,
    _VERIFY_OK_HTML,
    _VERIFY_BAD_HTML,
    get_user_event_history,
    _attended_event_ids,
    users_share_event,
    _users_connected,
    FREE_EVENT_LIMIT,
    _can_manage_event,
    _hard_delete_user,
    _thread_id,
    _tick_authorized,
)
from ogfetch import (
    _resolve_public_ip,
    _pin_url,
    _safe_fetch_html,
    fetch_og_metadata,
)
from error_hub import report_error

from routers.auth import router as auth_router
from routers.events import router as events_router
from routers.people import router as people_router
from routers.sponsors import router as sponsors_router
from routers.admin import router as admin_router
from routers.public import router as public_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_indexes()
    await seed_data()
    await seed_email_templates()
    await migrate_template_branding()
    yield


app = FastAPI(title="Intro Connect API", lifespan=lifespan)

# Scope to this project's own Render services, the production intro-connect.com
# domain, and the legacy frontrangedev.co staging domain. A broad `.*\.onrender\.com`
# would match EVERY Render tenant's app, which with allow_credentials=True is a risk.
CORS_ORIGIN_REGEX = (
    r"^https://(jimbo-connect-[a-z0-9-]+\.onrender\.com"
    r"|([a-z0-9-]+\.)?intro-connect\.com"
    r"|([a-z0-9-]+\.)?frontrangedev\.co)$"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin"],
    expose_headers=[],
)


@app.middleware("http")
async def _error_hub_reporter(request: Request, call_next):
    # Unhandled exceptions only: HTTPException and validation errors are
    # resolved by FastAPI's handlers before they reach this middleware.
    try:
        return await call_next(request)
    except Exception as exc:
        report_error("server", exc, fatal=False, url=str(request.url))
        raise


@app.get("/api/errors/hub-test")
async def error_hub_self_test(request: Request):
    """Deliberately raise an unhandled exception to e2e-test the error-hub
    reporter. Gated on the ERROR_HUB_KEY itself (constant-time compare) so
    only the hub operator can trigger it; 404 for everyone else."""
    import hmac
    import os

    key = os.environ.get("ERROR_HUB_KEY", "")
    auth = request.headers.get("authorization", "")
    presented = auth[7:] if auth.lower().startswith("bearer ") else ""
    if not key or not presented or not hmac.compare_digest(presented, key):
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Unauthorized")
    raise RuntimeError("error hub e2e self-test (intentional)")


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
    )
    # Production terminates TLS at the Render proxy (X-Forwarded-Proto: https).
    # HSTS is ignored by browsers over plain HTTP, so setting it is safe for
    # local dev while enforcing HTTPS in production (defends against SSL strip).
    if (
        request.headers.get("x-forwarded-proto") == "https"
        or request.url.scheme == "https"
    ):
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains; preload",
        )
    # Tight CSP for the server-rendered blog HTML. Those pages carry no
    # executable JS, only inline <style>, Google Fonts, and a JSON-LD block
    # (ld+json is data, never executed), all server-controlled and HTML-escaped.
    # script-src 'none' means an injected inline <script> would not run even if
    # escaping ever regressed. 'unsafe-inline' remains only under style-src.
    if request.url.path == "/blog" or request.url.path.startswith("/blog/"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "script-src 'none'; object-src 'none'; "
            "base-uri 'self'; frame-ancestors 'none'"
        )
    return response


app.include_router(auth_router)
app.include_router(people_router)
app.include_router(events_router)
app.include_router(sponsors_router)
app.include_router(admin_router)
app.include_router(public_router)
