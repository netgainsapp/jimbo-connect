"""CAN-SPAM compliance layer: signed one-click unsubscribe tokens, a
suppression list fed by unsubscribes and by Resend bounce/complaint webhooks,
and the svix signature verification those webhooks require.

Reasons and what they block:
  unsubscribe  blocks marketing mail only (the person can still reset a password)
  complaint    blocks marketing mail only (spam report; transactional stays open)
  bounce       blocks everything (the address does not deliver)

Dormant-safe like the rest of the mail stack: with no Resend key nothing sends,
and with no RESEND_WEBHOOK_SECRET the webhook endpoint refuses all requests.
"""
import base64
import hashlib
import hmac
import os
import re
import time
from datetime import datetime, timezone
from typing import Optional

from auth import JWT_SECRET
from database import suppressed_emails, users

# Public base URL of this API (unsubscribe links must be absolute and point at
# the backend, not the SPA). Defaults to the live Render service.
API_PUBLIC_URL = os.getenv(
    "API_PUBLIC_URL", "https://jimbo-connect-api-rdkp.onrender.com"
).rstrip("/")

# Reasons that make an address undeliverable for ALL mail, not just marketing.
_HARD_REASONS = {"bounce"}

_WEBHOOK_TOLERANCE_SECONDS = 300  # svix default: reject stale/replayed payloads

# Defense in depth: a verified token payload must still look like an email
# before anything downstream (DB queries, logs) trusts it.
_EMAIL_SHAPE_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _unsub_secret() -> bytes:
    """Dedicated signing secret for unsubscribe links, falling back to the JWT
    secret so the feature works with no extra configuration. A leaked link
    token only lets someone unsubscribe that one address."""
    return (os.getenv("UNSUBSCRIBE_SECRET") or JWT_SECRET).encode()


def _sign_email(email: str) -> str:
    return hmac.new(_unsub_secret(), email.encode(), hashlib.sha256).hexdigest()


def make_unsub_token(email: str) -> str:
    """Opaque token embedding the lowercased address: b64url(email).hmac_hex."""
    e = (email or "").strip().lower()
    body = base64.urlsafe_b64encode(e.encode()).decode().rstrip("=")
    return f"{body}.{_sign_email(e)}"


def verify_unsub_token(token) -> Optional[str]:
    """Return the verified email for a token, or None. Never raises."""
    if not token or not isinstance(token, str) or "." not in token:
        return None
    body, sig = token.rsplit(".", 1)
    try:
        padded = body + "=" * (-len(body) % 4)
        email = base64.urlsafe_b64decode(padded.encode()).decode()
    except Exception:
        return None
    if not email or not _EMAIL_SHAPE_RE.match(email):
        return None
    if not hmac.compare_digest(sig, _sign_email(email)):
        return None
    return email


def unsubscribe_url(email: str) -> str:
    return f"{API_PUBLIC_URL}/api/unsubscribe?token={make_unsub_token(email)}"


async def suppress(email: str, reason: str, source: str = "") -> None:
    """Add an address to the suppression list. First reason wins, except a
    bounce upgrades an existing entry (bounce also blocks transactional)."""
    e = (email or "").strip().lower()
    if not e:
        return
    await suppressed_emails.update_one(
        {"email": e},
        {
            "$setOnInsert": {
                "email": e,
                "reason": reason,
                "source": source,
                "created_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )
    if reason in _HARD_REASONS:
        await suppressed_emails.update_one({"email": e}, {"$set": {"reason": reason}})


async def is_suppressed(email: str, marketing: bool = True) -> bool:
    """Marketing mail is blocked by any suppression; transactional mail (password
    resets, imported-account credentials) only by a hard bounce."""
    e = (email or "").strip().lower()
    if not e:
        return True
    doc = await suppressed_emails.find_one({"email": e})
    if not doc:
        return False
    return marketing or doc.get("reason") in _HARD_REASONS


async def apply_unsubscribe(email: str) -> None:
    """One-click unsubscribe: suppress marketing mail and switch off the nurture
    drip for a matching account. Invite reminders stop via the suppression check
    in send_marketing_email, so no invite state needs touching here."""
    e = (email or "").strip().lower()
    await suppress(e, "unsubscribe", source="link")
    await users.update_one({"email": e}, {"$set": {"nurture_enabled": False}})


# ---------- Resend webhook (svix signature scheme) ----------

def verify_resend_signature(secret, msg_id, timestamp, signature_header, body: bytes) -> bool:
    """Verify a Resend webhook per the svix scheme: HMAC-SHA256 over
    "{id}.{timestamp}.{body}" keyed with the base64 part of the whsec_ secret,
    compared against each space-delimited "v1,<b64>" entry in the header.
    Rejects stale timestamps to stop replays. Never raises."""
    if not secret or not msg_id or not timestamp or not signature_header:
        return False
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(time.time() - ts) > _WEBHOOK_TOLERANCE_SECONDS:
        return False
    try:
        key = base64.b64decode(secret.split("whsec_")[-1])
        signed = f"{msg_id}.{timestamp}.{body.decode()}".encode()
        expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    except Exception:
        return False
    for part in signature_header.split(" "):
        if "," not in part:
            continue
        version, _, sig = part.partition(",")
        if version == "v1" and hmac.compare_digest(sig, expected):
            return True
    return False


_EVENT_REASONS = {
    "email.bounced": "bounce",
    "email.complained": "complaint",
}


async def handle_resend_event(payload: dict) -> dict:
    """Ingest a verified Resend event. Bounces and complaints feed the
    suppression list; everything else is acknowledged and ignored."""
    event_type = (payload or {}).get("type", "")
    reason = _EVENT_REASONS.get(event_type)
    if not reason:
        return {"ok": True, "ignored": event_type}
    to = ((payload or {}).get("data") or {}).get("to") or []
    if isinstance(to, str):
        to = [to]
    count = 0
    for address in to:
        e = str(address or "").strip().lower()
        if e:
            await suppress(e, reason, source="resend_webhook")
            count += 1
    return {"ok": True, "suppressed": count}
