"""/api/auth/* routes. Moved verbatim from server.py (M13)."""
import asyncio
import sys
from datetime import datetime, timezone
from datetime import timedelta as _td

from fastapi import APIRouter, HTTPException, Depends, Response, Request
from fastapi.responses import HTMLResponse

from database import users
import email_send
import nurture
import rate_limit
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    COOKIE_NAME,
)
from models import (
    Profile,
    RegisterRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from core import (
    FRONTEND_URL,
    serialize_user,
    set_auth_cookie,
    _cookie_secure,
    _DUMMY_PW_HASH,
    _new_reset_token,
    _hash_token,
    issue_email_verification,
    apply_email_verification,
    render_email_template,
    body_to_html,
    _VERIFY_OK_HTML,
    _VERIFY_BAD_HTML,
)

router = APIRouter()


# ---------- Auth ----------

@router.post("/api/auth/register")
async def register(payload: RegisterRequest, response: Response, request: Request):
    rate_limit.guard(
        request, "register", limit=10, window_seconds=3600, identifier=payload.email
    )
    existing = await users.find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    now = datetime.now(timezone.utc)
    doc = {
        "email": payload.email,
        # bcrypt is ~100ms of CPU; run it off the event loop so a burst of
        # signups cannot stall every other request.
        "password_hash": await asyncio.to_thread(hash_password, payload.password),
        "is_admin": False,
        "created_at": now,
        "profile": Profile(name=payload.name or "").model_dump(),
        # Self-registered users are enrolled in the nurture drip (bulk-imported
        # attendees are not). Step 0 = welcome sent below.
        "nurture_enabled": True,
        "nurture_step": 0,
        "email_verified": False,
    }
    result = await users.insert_one(doc)
    doc["_id"] = result.inserted_id
    try:
        await nurture.send_welcome(doc)
    except Exception as exc:  # never block signup on a mail hiccup
        print(f"[register] welcome email failed: {exc}", file=sys.stderr)
    try:
        await issue_email_verification(doc)
    except Exception as exc:
        print(f"[register] verification email failed: {exc}", file=sys.stderr)
    token = create_access_token(str(result.inserted_id))
    set_auth_cookie(response, token)
    return {"user": serialize_user(doc), "token": token}


@router.post("/api/auth/login")
async def login(payload: LoginRequest, response: Response, request: Request):
    rate_limit.guard(
        request, "login", limit=10, window_seconds=300, identifier=payload.email
    )
    user = await users.find_one({"email": payload.email})
    if not user:
        # Run a dummy verify so the unknown-email path costs the same as a
        # wrong-password path (no user-enumeration timing signal).
        await asyncio.to_thread(verify_password, payload.password, _DUMMY_PW_HASH)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not await asyncio.to_thread(
        verify_password, payload.password, user["password_hash"]
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(str(user["_id"]))
    set_auth_cookie(response, token)
    return {"user": serialize_user(user), "token": token}


@router.post("/api/auth/logout")
async def logout(response: Response):
    secure = _cookie_secure()
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        samesite="none" if secure else "lax",
        secure=secure,
    )
    return {"ok": True}


@router.get("/api/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return serialize_user(user)


@router.post("/api/auth/refresh")
async def refresh(response: Response, user: dict = Depends(get_current_user)):
    token = create_access_token(str(user["_id"]))
    set_auth_cookie(response, token)
    return {"token": token}


@router.get("/api/auth/verify-email", response_class=HTMLResponse)
async def verify_email(token: str, request: Request):
    rate_limit.guard(request, "verify_email", limit=30, window_seconds=3600)
    ok = await apply_email_verification(token)
    return HTMLResponse(
        _VERIFY_OK_HTML if ok else _VERIFY_BAD_HTML, status_code=200 if ok else 400
    )


@router.post("/api/auth/resend-verification")
async def resend_verification(request: Request, user: dict = Depends(get_current_user)):
    rate_limit.guard(request, "resend_verification", limit=3, window_seconds=3600)
    if user.get("email_verified"):
        return {"ok": True, "already_verified": True}
    await issue_email_verification(user)
    return {"ok": True, "sent": email_send.is_configured()}


@router.post("/api/auth/forgot-password")
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
            {"$set": {"reset_token": _hash_token(token), "reset_token_expires": expires}},
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


@router.post("/api/auth/reset-password")
async def reset_password(payload: ResetPasswordRequest, response: Response, request: Request):
    rate_limit.guard(request, "reset", limit=15, window_seconds=900)
    user = await users.find_one({"reset_token": _hash_token(payload.token)})
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


@router.get("/api/auth/magic/{token}")
async def magic_login(token: str, response: Response, request: Request):
    """One-tap login via a reset token. Single-use: the token is cleared
    after a successful login so the link cannot be replayed if it leaks
    (e.g. via referrer headers, logs, or shared history)."""
    rate_limit.guard(request, "magic", limit=10, window_seconds=300)
    user = await users.find_one({"reset_token": _hash_token(token)})
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
