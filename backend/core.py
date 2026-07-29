"""Shared non-route code for the Intro Connect API: env constants,
serializers, cookie helpers, token helpers, email-template rendering,
email verification, cross-user authorization gates, and seed/migration
routines. Moved verbatim from server.py (M13)."""
import hashlib
import hmac
import os
import re
import secrets
import string
import sys
from datetime import datetime, timezone

from fastapi import Response
from dotenv import load_dotenv
from app_url import APP_URL  # noqa: F401  (re-exported for routers)

from database import (
    app_flags,
    users,
    events,
    event_attendees,
    saved_contacts,
    messages,
    email_templates,
)
import email_send
import nurture
import suppression
from template_seeds import DEFAULT_TEMPLATES
from auth import hash_password, COOKIE_NAME
from models import Profile

load_dotenv()

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@intro-connect.com")
# No fallback: a hardcoded default would become a guessable live admin password
# if the env var is ever unset. When missing, admin bootstrap is skipped (see
# seed_data) rather than falling back to a known literal.
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def generate_join_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


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
        "email_verified": bool(user.get("email_verified")),
        "plan": user.get("plan") or "free",
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


def serialize_event(event: dict, attendee_count: int = 0, host_branding=None) -> dict:
    out = {
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
    # Host branding (Pro) rides along only where the caller resolved it, so
    # list endpoints stay cheap and existing consumers see no shape change.
    if host_branding is not None:
        out["host_branding"] = host_branding
    return out


async def seed_data():
    """Ensure the platform admin exists, then seed sample data on first run only.

    ADMIN_EMAIL / ADMIN_PASSWORD define the single platform admin. The admin is
    created once if missing; we never overwrite its password on boot (so a
    password rotated from the dashboard persists across restarts) and never
    blanket-demote other admins (which could silently lock out a deliberately
    promoted operator). If ADMIN_PASSWORD is not configured, admin bootstrap is
    skipped rather than falling back to a guessable default.
    """
    admin = await users.find_one({"email": ADMIN_EMAIL}) if ADMIN_EMAIL else None
    if admin:
        # Ensure the admin flag is set, but leave the password untouched.
        if not admin.get("is_admin"):
            await users.update_one({"_id": admin["_id"]}, {"$set": {"is_admin": True}})
        return

    if not (ADMIN_EMAIL and ADMIN_PASSWORD):
        print(
            "WARNING: ADMIN_EMAIL/ADMIN_PASSWORD not set; skipping admin bootstrap. "
            "Set them in the environment to create the platform admin.",
            file=sys.stderr,
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


SYSTEM_TEMPLATE_REPAIR_FLAG = "system_templates_repaired_2026_07"


def _seed_for(template_id: str):
    for t in DEFAULT_TEMPLATES:
        if t["template_id"] == template_id:
            return t
    return None


async def repair_system_templates():
    """One-time, idempotent: restore the SERVER-SENT templates (password reset,
    invitation) to the current seed copy.

    Those rows drifted from the code: they carried em dashes (against brand
    voice) and a host name baked in as literal text, and because the send path
    prefers the stored row, every outgoing email used the stale copy no matter
    what the seeds said. Gated on an app_flags marker so it runs exactly once
    and never fights an intentional admin edit afterwards. Only `system`
    templates are touched; the copy-paste library is left alone.
    """
    flag = await app_flags.find_one({"_id": SYSTEM_TEMPLATE_REPAIR_FLAG})
    if flag:
        return {"skipped": "already_repaired"}
    repaired = []
    for seed in DEFAULT_TEMPLATES:
        if not seed.get("system"):
            continue
        doc = await email_templates.find_one({"template_id": seed["template_id"]})
        if not doc:
            continue
        if doc.get("subject") == seed["subject"] and doc.get("body") == seed["body"]:
            continue
        await email_templates.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "subject": seed["subject"],
                    "body": seed["body"],
                    "title": seed["title"],
                    "blurb": seed["blurb"],
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        repaired.append(seed["template_id"])
    await app_flags.update_one(
        {"_id": SYSTEM_TEMPLATE_REPAIR_FLAG},
        {"$set": {"ran_at": datetime.now(timezone.utc), "repaired": repaired}},
        upsert=True,
    )
    if repaired:
        print(f"[migration] repaired system templates: {repaired}", file=sys.stderr)
    return {"repaired": repaired}


_origins = [o.strip() for o in FRONTEND_URL.split(",") if o.strip()]
if "http://localhost:3000" not in _origins:
    _origins.append("http://localhost:3000")


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


# A bcrypt hash to verify against when an email is unknown, so the login path
# takes the same time whether or not the account exists (defeats the timing
# oracle that would otherwise reveal which emails are registered).
_DUMMY_PW_HASH = hash_password("not-a-real-password-timing-equalizer")


from datetime import timedelta as _td


def _new_reset_token() -> str:
    return secrets.token_urlsafe(32)


def _hash_token(token: str) -> str:
    """Store only a hash of reset/magic tokens so a DB or backup read cannot be
    replayed as a live account-takeover token. The raw token is emailed once."""
    return hashlib.sha256((token or "").encode()).hexdigest()


# ---------- Email verification (M6, soft: nothing is gated on it yet) ----------

_VERIFY_EXPIRY_DAYS = 7


VERIFY_HEADING = "Confirm your email"


def verify_email_paragraphs(name: str) -> list:
    return [
        f"Hi {name or 'there'},",
        "Please confirm this email address so we know it is really yours. One "
        "click does it.",
        "The link works for seven days. If you did not create an Intro Connect "
        "account, you can ignore this email.",
        "Scott",
    ]


async def issue_email_verification(user: dict) -> None:
    """Create a one-time verification token and email the link. Dormant without
    Resend. The token is stored hashed, same as reset tokens."""
    if not email_send.is_configured():
        return
    raw = _new_reset_token()
    await users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "verify_token": _hash_token(raw),
                "verify_token_expires": datetime.now(timezone.utc)
                + _td(days=_VERIFY_EXPIRY_DAYS),
            }
        },
    )
    verify_url = f"{suppression.API_PUBLIC_URL}/api/auth/verify-email?token={raw}"
    profile = user.get("profile") or {}
    # Transactional (not marketing): branded layout, no unsubscribe footer.
    await email_send.send_branded(
        to=user["email"],
        subject="confirm your email for Intro Connect",
        heading=VERIFY_HEADING,
        paragraphs=verify_email_paragraphs(profile.get("name") or ""),
        button={"label": "Confirm my email", "url": verify_url},
        marketing=False,
    )


async def apply_email_verification(token: str) -> bool:
    """Consume a verification token. Returns True if a user was verified."""
    if not token:
        return False
    user = await users.find_one({"verify_token": _hash_token(token)})
    if not user:
        return False
    expires = user.get("verify_token_expires")
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if not expires or expires < datetime.now(timezone.utc):
        return False
    await users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"email_verified": True},
            "$unset": {"verify_token": "", "verify_token_expires": ""},
        },
    )
    return True


_VERIFY_OK_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Email confirmed</title></head>
<body style="font-family:system-ui,sans-serif;max-width:480px;margin:80px auto;text-align:center;color:#222">
<h1 style="font-size:22px">Email confirmed</h1>
<p style="color:#555">You are all set. You can close this tab and head back to the app.</p>
</body></html>"""

_VERIFY_BAD_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Link expired</title></head>
<body style="font-family:system-ui,sans-serif;max-width:480px;margin:80px auto;text-align:center;color:#222">
<h1 style="font-size:22px">This link is not valid</h1>
<p style="color:#555">It may have expired or already been used. Log in and request a new
confirmation email from your profile.</p>
</body></html>"""


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


async def _attended_event_ids(user_id) -> set:
    """Event ids where this user is a joined attendee."""
    ids = set()
    async for link in event_attendees.find({"user_id": user_id}, {"event_id": 1}):
        ids.add(link["event_id"])
    return ids


async def users_share_event(user_a_id, user_b_id) -> bool:
    """True if two users are connected through an event: both joined the same
    event, or one hosts an event the other joined. This is the trust boundary
    for viewing another attendee's profile, saving them, or messaging them.
    created_by is compared as a string because it can be stored as either an
    ObjectId or a string (see _can_manage_event)."""
    a_events = await _attended_event_ids(user_a_id)
    b_events = await _attended_event_ids(user_b_id)
    if a_events & b_events:
        return True
    a_str, b_str = str(user_a_id), str(user_b_id)
    # B hosts an event A attends?
    if a_events:
        async for e in events.find({"_id": {"$in": list(a_events)}}, {"created_by": 1}):
            if e.get("created_by") is not None and str(e["created_by"]) == b_str:
                return True
    # A hosts an event B attends?
    if b_events:
        async for e in events.find({"_id": {"$in": list(b_events)}}, {"created_by": 1}):
            if e.get("created_by") is not None and str(e["created_by"]) == a_str:
                return True
    return False


async def _users_connected(requester: dict, target_oid) -> bool:
    """Authorization gate for cross-user reads and messaging. Allowed when the
    requester is the target, an admin, shares an event with the target, has
    already saved them as a contact, or has an existing message thread with
    them. Everything else is treated as no relationship so callers can return
    an opaque 404 (no id enumeration)."""
    if requester.get("is_admin"):
        return True
    rid = requester["_id"]
    if rid == target_oid:
        return True
    if await users_share_event(rid, target_oid):
        return True
    if await saved_contacts.find_one({"owner_id": rid, "contact_id": target_oid}):
        return True
    if await messages.find_one({"thread_id": _thread_id(rid, target_oid)}):
        return True
    return False


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


def _thread_id(a, b) -> str:
    a, b = str(a), str(b)
    return f"{a}:{b}" if a < b else f"{b}:{a}"


def _tick_authorized(provided) -> bool:
    """The tick runs only with the configured shared secret (the GitHub Actions
    cron sends it). Disabled entirely when no secret is set."""
    secret = os.getenv("BLOG_TICK_SECRET")
    if not secret or not provided:
        return False
    return hmac.compare_digest(provided, secret)
