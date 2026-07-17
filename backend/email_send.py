"""Resend integration. If RESEND_API_KEY isn't set, send_email() is a no-op
and returns {"sent": False, "reason": "..."} so callers can fall back to
showing the link/credentials in-app.

send_email() is for transactional mail (password resets, imported-account
credentials). Anything promotional (nurture drip, invites, reminders) must go
through send_marketing_email(), which enforces the suppression list and adds
the CAN-SPAM unsubscribe footer + List-Unsubscribe headers."""

import os
import httpx
from typing import Optional

import email_layout
import suppression

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
EMAIL_FROM = os.getenv("EMAIL_FROM", "Intro Connect <hello@intro-connect.com>").strip()
RESEND_URL = "https://api.resend.com/emails"


def is_configured() -> bool:
    return bool(RESEND_API_KEY)


async def send_email(
    to: str,
    subject: str,
    html: str,
    text: Optional[str] = None,
    reply_to: Optional[str] = None,
    headers: Optional[dict] = None,
) -> dict:
    if not RESEND_API_KEY:
        return {"sent": False, "reason": "RESEND_API_KEY not set"}
    # A hard-bounced address never delivers; retrying it on any path (even
    # transactional mail) only burns sender reputation. Enforced centrally
    # here so no call site can forget it.
    if await suppression.is_suppressed(to, marketing=False):
        return {"sent": False, "reason": "suppressed"}
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
    if headers:
        payload["headers"] = headers
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


_FOOTER_HTML = (
    '<p style="color:#8a8a8a;font-size:12px;margin-top:24px">'
    "You can stop these emails any time. "
    '<a href="{url}" style="color:#8a8a8a">Unsubscribe</a></p>'
)
_FOOTER_TEXT = "\n\nYou can stop these emails any time. Unsubscribe: {url}"


async def send_branded(
    to: str,
    subject: str,
    *,
    heading: str,
    paragraphs,
    button: Optional[dict] = None,
    marketing: bool = True,
    reply_to: Optional[str] = None,
) -> dict:
    """Render structured content through the branded, email-client-safe layout
    and send it. Marketing mail is suppression-checked and carries the
    unsubscribe footer + List-Unsubscribe headers; transactional mail is not
    (only a hard bounce blocks it, enforced in send_email)."""
    if not RESEND_API_KEY:
        return {"sent": False, "reason": "RESEND_API_KEY not set"}
    if marketing:
        if await suppression.is_suppressed(to):
            return {"sent": False, "reason": "suppressed"}
        unsub = suppression.unsubscribe_url(to)
        html = email_layout.render(
            heading=heading, paragraphs=paragraphs, button=button, unsubscribe_url=unsub
        )
        text = email_layout.to_text(paragraphs, button, unsub)
        return await send_email(
            to,
            subject,
            html,
            text=text,
            reply_to=reply_to,
            headers={
                "List-Unsubscribe": f"<{unsub}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            },
        )
    html = email_layout.render(heading=heading, paragraphs=paragraphs, button=button)
    text = email_layout.to_text(paragraphs, button)
    return await send_email(to, subject, html, text=text, reply_to=reply_to)


async def send_template_branded(
    to: str,
    rendered: dict,
    *,
    button_label: Optional[str] = None,
    button_url: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> dict:
    """Send an admin-editable template ({"subject","body"} from
    render_email_template) through the branded layout as transactional mail.
    The body splits on blank lines into paragraphs; a paragraph that is exactly
    the button URL becomes the bulletproof button instead of a raw link. The
    plain-text alternative keeps the raw URL so every client has a usable copy."""
    body = rendered["body"]
    paragraphs = [p.strip("\n") for p in body.split("\n\n") if p.strip()]
    button = None
    if button_url and button_label:
        paragraphs = [p for p in paragraphs if p.strip() != button_url]
        button = {"label": button_label, "url": button_url}
    html = email_layout.render(
        heading=rendered["subject"], paragraphs=paragraphs, button=button
    )
    text = email_layout.to_text(paragraphs, button)
    return await send_email(to, rendered["subject"], html, text=text, reply_to=reply_to)


async def send_marketing_email(
    to: str,
    subject: str,
    html: str,
    text: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> dict:
    """send_email for promotional mail: skips suppressed addresses and adds a
    one-click unsubscribe footer plus the List-Unsubscribe headers (RFC 8058)
    that Gmail/Yahoo require for bulk senders."""
    if not RESEND_API_KEY:
        return {"sent": False, "reason": "RESEND_API_KEY not set"}
    if await suppression.is_suppressed(to):
        return {"sent": False, "reason": "suppressed"}
    url = suppression.unsubscribe_url(to)
    return await send_email(
        to,
        subject,
        html + _FOOTER_HTML.format(url=url),
        text=(text + _FOOTER_TEXT.format(url=url)) if text else None,
        reply_to=reply_to,
        headers={
            "List-Unsubscribe": f"<{url}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        },
    )
