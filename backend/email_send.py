"""Resend integration. If RESEND_API_KEY isn't set, send_email() is a no-op
and returns {"sent": False, "reason": "..."} so callers can fall back to
showing the link/credentials in-app."""

import os
import httpx
from typing import Optional

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
EMAIL_FROM = os.getenv("EMAIL_FROM", "Intro Connect <onboarding@resend.dev>").strip()
RESEND_URL = "https://api.resend.com/emails"


def is_configured() -> bool:
    return bool(RESEND_API_KEY)


async def send_email(
    to: str,
    subject: str,
    html: str,
    text: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> dict:
    if not RESEND_API_KEY:
        return {"sent": False, "reason": "RESEND_API_KEY not set"}
    payload = {
        "from": EMAIL_FROM,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if text:
        payload["text"] = text
    if reply_to:
        payload["reply_to"] = reply_to
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                RESEND_URL,
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if r.status_code >= 400:
            return {"sent": False, "reason": r.text[:300]}
        return {"sent": True, "id": r.json().get("id", "")}
    except Exception as e:
        return {"sent": False, "reason": str(e)[:300]}
