"""Resend integration. If RESEND_API_KEY isn't set, send_email() is a no-op
and returns {"sent": False, "reason": "..."} so callers can fall back to
showing the link/credentials in-app."""

import os
import httpx
from typing import Optional

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
EMAIL_FROM = os.getenv("EMAIL_FROM", "Jimbo Connect <onboarding@resend.dev>").strip()
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


def render_reset_email(reset_url: str, recipient_name: str = "") -> tuple[str, str]:
    greeting = f"Hi {recipient_name}," if recipient_name else "Hi,"
    text = f"""{greeting}

Tap the link below to set a new password (or just log in — same link works either way):

{reset_url}

This link expires in 2 hours.

— Jimbo Connect"""
    html = f"""<!doctype html><html><body style="font-family:Calibri,Segoe UI,system-ui,sans-serif;color:#0a0c10;background:#f7f8fa;padding:24px">
<div style="max-width:520px;margin:0 auto;background:#fff;border:1px solid #E4E6EA;border-radius:8px;padding:28px">
<div style="font-weight:bold;color:#0A66C2;font-size:20px;margin-bottom:12px">Jimbo Connect</div>
<p>{greeting}</p>
<p>Tap the button below to set a new password — or just log in (same link works for both).</p>
<p style="margin:24px 0">
  <a href="{reset_url}" style="display:inline-block;background:#0A66C2;color:#fff;text-decoration:none;padding:12px 22px;border-radius:24px;font-weight:bold">Open my reset link</a>
</p>
<p style="font-size:12px;color:#6B7280">This link expires in 2 hours. If you didn't ask for this, you can ignore the email.</p>
</div></body></html>"""
    return html, text


def render_invitation_email(
    event_name: str,
    event_date: str,
    event_location: str,
    site_url: str,
    email: str,
    temp_password: str,
    host_name: str = "Jim",
) -> tuple[str, str]:
    where = f" in {event_location}" if event_location else ""
    text = f"""Hi,

You're invited to {event_name}{where} on {event_date}.

Log in to your private attendee directory:
  {site_url}
  Email:    {email}
  Password: {temp_password}

The directory fills in as more people join. After the event you can save contacts and add private notes.

— {host_name}"""
    html = f"""<!doctype html><html><body style="font-family:Calibri,Segoe UI,system-ui,sans-serif;color:#0a0c10;background:#f7f8fa;padding:24px">
<div style="max-width:520px;margin:0 auto;background:#fff;border:1px solid #E4E6EA;border-radius:8px;padding:28px">
<div style="font-weight:bold;color:#0A66C2;font-size:20px;margin-bottom:12px">You're invited to {event_name}</div>
<p>{event_date}{where}.</p>
<p>Log in to your private attendee directory:</p>
<div style="background:#F7F8FA;border-radius:8px;padding:12px;font-family:monospace;font-size:13px">
  Email: {email}<br>
  Password: {temp_password}
</div>
<p style="margin:24px 0">
  <a href="{site_url}" style="display:inline-block;background:#0A66C2;color:#fff;text-decoration:none;padding:12px 22px;border-radius:24px;font-weight:bold">Open the directory</a>
</p>
<p style="font-size:12px;color:#6B7280">After the event you can save contacts and add private notes for follow-up. Always free.</p>
<p style="font-size:12px;color:#6B7280">— {host_name}</p>
</div></body></html>"""
    return html, text
