"""Cloudflare Web Analytics beacon for the server-rendered public pages.

intro-connect.com sits on Render's own Cloudflare edge, not on a Cloudflare
zone we control, so the automatic (proxied) setup is unavailable. The manual
JS snippet with a site token is the only route. The token lives in the
CF_BEACON_TOKEN env var; unset or malformed means no beacon at all and the
/blog CSP stays exactly as strict as before.
"""
import json
import os
import re

BEACON_SRC = "https://static.cloudflareinsights.com/beacon.min.js"
BEACON_SCRIPT_ORIGIN = "https://static.cloudflareinsights.com"
BEACON_CONNECT_ORIGIN = "https://cloudflareinsights.com"

#: Site tokens are short alphanumeric strings. The value lands in an HTML
#: attribute, so anything else is refused rather than escaped.
_TOKEN_RE = re.compile(r"^[A-Za-z0-9]{16,64}$")

_CSP_HEAD = (
    "default-src 'self'; img-src 'self' data: https:; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
)
_CSP_TAIL = "object-src 'none'; base-uri 'self'; frame-ancestors 'none'"


def token() -> str:
    """The configured site token, or "" when unset or malformed."""
    raw = (os.getenv("CF_BEACON_TOKEN") or "").strip()
    return raw if _TOKEN_RE.match(raw) else ""


def beacon_tag() -> str:
    """The <script> tag for <head>, or "" when no valid token is configured."""
    t = token()
    if not t:
        return ""
    cfg = json.dumps({"token": t})
    return f"<script defer src=\"{BEACON_SRC}\" data-cf-beacon='{cfg}'></script>"


def blog_csp() -> str:
    """CSP for /blog pages. With no token: script-src 'none' (no JS at all).
    With a token: only the Cloudflare beacon host may load script, so an
    injected inline <script> is still blocked."""
    if not token():
        return _CSP_HEAD + "script-src 'none'; " + _CSP_TAIL
    return (
        _CSP_HEAD
        + f"script-src {BEACON_SCRIPT_ORIGIN}; "
        + f"connect-src 'self' {BEACON_CONNECT_ORIGIN}; "
        + _CSP_TAIL
    )
