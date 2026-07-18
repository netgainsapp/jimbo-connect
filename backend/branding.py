"""Host branding (Pro): a host's logo and accent color, applied only to that
host's own event surfaces (directory pages, join flow, guest emails) beside
Intro Connect chrome. Not white-label.

Zero-approval guardrails live here:
- Uploads must be real raster images (PNG/JPEG/WEBP), max 1 MB. SVG never.
- Every upload is re-encoded through Pillow: metadata stripped, resized to fit
  512x512, saved as PNG. Only clean pixels survive.
- Accent colors are strict #RRGGBB. A contrast-safe dark variant is derived
  automatically so white button text always meets WCAG 4.5:1; nobody has to
  review anyone's taste.
- Activation is plan-gated (pro or platform admin) and admin-lockable.
"""
import io
import re

from PIL import Image

import billing
from suppression import API_PUBLIC_URL

ACCENT_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
MAX_UPLOAD_BYTES = 1024 * 1024
MAX_LOGO_DIM = 512
ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP"}
WHITE_TEXT_CONTRAST = 4.5

# Cap decode size well below Pillow's default bomb threshold: a 512px logo
# never needs a 30 megapixel source.
Image.MAX_IMAGE_PIXELS = 30_000_000


def normalize_accent(raw) -> str:
    """Return '#rrggbb' (lowercase) or raise ValueError."""
    value = (raw or "").strip()
    if not ACCENT_RE.match(value):
        raise ValueError("Pick a color as a 6 digit hex value, like #2563eb.")
    return value.lower()


def _srgb_channel(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _luminance(hex_color: str) -> float:
    r = _srgb_channel(int(hex_color[1:3], 16))
    g = _srgb_channel(int(hex_color[3:5], 16))
    b = _srgb_channel(int(hex_color[5:7], 16))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_with_white(hex_color: str) -> float:
    return 1.05 / (_luminance(hex_color) + 0.05)


def derive_accent_dark(accent: str) -> str:
    """The accent actually used under white text. If the picked color already
    carries 4.5:1 against white it passes through; otherwise darken it evenly
    until it does. Converges because black is 21:1."""
    accent = accent.lower()
    r, g, b = int(accent[1:3], 16), int(accent[3:5], 16), int(accent[5:7], 16)
    while contrast_with_white(f"#{r:02x}{g:02x}{b:02x}") < WHITE_TEXT_CONTRAST:
        r, g, b = int(r * 0.9), int(g * 0.9), int(b * 0.9)
        if r == 0 and g == 0 and b == 0:
            break
    return f"#{r:02x}{g:02x}{b:02x}"


def process_logo(data: bytes) -> bytes:
    """Validate and neutralize an uploaded logo. Returns clean PNG bytes or
    raises ValueError with a user-facing message (brand voice: no dashes)."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("That file is too large. Logos can be up to 1 MB.")
    try:
        img = Image.open(io.BytesIO(data))
        img_format = (img.format or "").upper()
        if img_format not in ALLOWED_FORMATS:
            raise ValueError("Use a PNG, JPEG, or WebP image.")
        img = img.convert("RGBA")
        img.thumbnail((MAX_LOGO_DIM, MAX_LOGO_DIM))
        out = io.BytesIO()
        # Re-encoding drops every byte that is not pixels: EXIF, ICC quirks,
        # trailing payloads, the lot.
        img.save(out, format="PNG", optimize=True)
        return out.getvalue()
    except ValueError:
        raise
    except Exception:
        raise ValueError("Use a PNG, JPEG, or WebP image.")


def plan_allows(user: dict) -> bool:
    return bool(user.get("is_admin")) or billing.plan_of(user) == "pro"


def branding_active(user: dict) -> bool:
    """Branding renders only while the host's plan allows it and no admin lock
    is set. Downgrades make it dormant automatically; nothing is deleted."""
    if not user:
        return False
    if user.get("branding_locked"):
        return False
    b = user.get("branding") or {}
    if not (b.get("accent") or b.get("logo")):
        return False
    return plan_allows(user)


def logo_url(user: dict) -> str:
    b = user.get("branding") or {}
    if not b.get("logo"):
        return ""
    version = ""
    if b.get("logo_updated_at"):
        version = f"?v={int(b['logo_updated_at'].timestamp())}"
    return f"{API_PUBLIC_URL}/api/branding/{str(user['_id'])}/logo.png{version}"


def public_branding(user: dict):
    """The shape shipped to event pages and email renderers, or None when the
    host has no active branding."""
    if not branding_active(user):
        return None
    b = user.get("branding") or {}
    return {
        "logo_url": logo_url(user),
        "accent": b.get("accent") or "",
        "accent_dark": b.get("accent_dark") or b.get("accent") or "",
    }


def email_brand(user: dict):
    """Brand dict for email_layout.render, or None for platform default."""
    pb = public_branding(user)
    if not pb:
        return None
    return {"logo_url": pb["logo_url"], "accent_dark": pb["accent_dark"]}
