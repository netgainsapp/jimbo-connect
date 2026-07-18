"""Host branding (Pro): accent validation and contrast derivation, logo
processing guardrails, plan gating and dormancy, and the email layout's
host-brand rendering.
Run from backend/: python -m pytest tests/test_branding.py
"""
import io
from datetime import datetime, timezone

import pytest
from PIL import Image

import branding
import email_layout


def _png_bytes(size=(600, 400), color=(30, 90, 200, 255)):
    img = Image.new("RGBA", size, color)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def _jpeg_with_exif(size=(300, 300)):
    img = Image.new("RGB", size, (200, 40, 40))
    exif = Image.Exif()
    exif[271] = "SecretCamera Make"  # Make tag
    out = io.BytesIO()
    img.save(out, format="JPEG", exif=exif)
    return out.getvalue()


# ---------- accent ----------

def test_accent_normalizes_and_lowercases():
    assert branding.normalize_accent(" #2563EB ") == "#2563eb"


@pytest.mark.parametrize("bad", ["", None, "2563eb", "#25e", "#25636b1", "#zzzzzz", "red"])
def test_accent_rejects_non_hex(bad):
    with pytest.raises(ValueError):
        branding.normalize_accent(bad)


def test_dark_accent_passes_through():
    dark = "#0d1b2a"  # brand ink, far past 4.5:1 on white
    assert branding.derive_accent_dark(dark) == dark


def test_light_accent_darkens_until_readable():
    derived = branding.derive_accent_dark("#a5d8ff")
    assert derived != "#a5d8ff"
    assert branding.contrast_with_white(derived) >= branding.WHITE_TEXT_CONTRAST


def test_even_white_converges():
    derived = branding.derive_accent_dark("#ffffff")
    assert branding.contrast_with_white(derived) >= branding.WHITE_TEXT_CONTRAST


# ---------- logo processing ----------

def test_logo_resized_and_reencoded_png():
    clean = branding.process_logo(_png_bytes(size=(600, 400)))
    img = Image.open(io.BytesIO(clean))
    assert img.format == "PNG"
    assert max(img.size) <= branding.MAX_LOGO_DIM


def test_logo_metadata_stripped():
    clean = branding.process_logo(_jpeg_with_exif())
    img = Image.open(io.BytesIO(clean))
    assert img.format == "PNG"
    assert not img.getexif()


def test_logo_rejects_oversize():
    blob = b"0" * (branding.MAX_UPLOAD_BYTES + 1)
    with pytest.raises(ValueError, match="too large"):
        branding.process_logo(blob)


def test_logo_rejects_svg_and_garbage():
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    with pytest.raises(ValueError, match="PNG, JPEG, or WebP"):
        branding.process_logo(svg)
    with pytest.raises(ValueError, match="PNG, JPEG, or WebP"):
        branding.process_logo(b"not an image at all")


def test_small_logo_not_upscaled():
    clean = branding.process_logo(_png_bytes(size=(64, 64)))
    img = Image.open(io.BytesIO(clean))
    assert img.size == (64, 64)


# ---------- plan gating and dormancy ----------

def _host(plan="pro", *, admin=False, locked=False, with_branding=True):
    user = {"_id": "abc123", "plan": plan, "is_admin": admin}
    if locked:
        user["branding_locked"] = True
    if with_branding:
        user["branding"] = {
            "accent": "#2563eb",
            "accent_dark": "#2563eb",
            "logo": b"png-bytes",
            "logo_updated_at": datetime(2026, 7, 17, tzinfo=timezone.utc),
        }
    return user


def test_pro_host_is_active():
    assert branding.branding_active(_host("pro"))


def test_admin_is_active_regardless_of_plan():
    assert branding.branding_active(_host("free", admin=True))


def test_free_and_starter_are_dormant():
    assert not branding.branding_active(_host("free"))
    assert not branding.branding_active(_host("starter"))


def test_downgrade_goes_dormant_without_deleting():
    host = _host("pro")
    assert branding.branding_active(host)
    host["plan"] = "free"  # Stripe webhook downgrade
    assert not branding.branding_active(host)
    assert host["branding"]["logo"]  # nothing deleted


def test_locked_host_is_dormant():
    assert not branding.branding_active(_host("pro", locked=True))


def test_no_branding_set_is_inactive():
    assert not branding.branding_active(_host("pro", with_branding=False))


def test_public_branding_shape_and_none():
    pb = branding.public_branding(_host("pro"))
    assert pb["accent"] == "#2563eb"
    assert pb["accent_dark"] == "#2563eb"
    assert "/api/branding/abc123/logo.png" in pb["logo_url"]
    assert "?v=" in pb["logo_url"]
    assert branding.public_branding(_host("free")) is None
    assert branding.public_branding(None) is None


def test_email_brand_none_for_inactive():
    assert branding.email_brand(_host("free")) is None
    brand = branding.email_brand(_host("pro"))
    assert brand["logo_url"] and brand["accent_dark"]


# ---------- email layout ----------

def test_render_without_brand_is_platform_default():
    html = email_layout.render(heading="H", paragraphs=["p"], button={"label": "Go", "url": "https://x.test"})
    assert email_layout.LOGO_URL in html
    assert f'bgcolor="{email_layout.BLUE}"' in html
    assert "via Intro Connect" not in html


def test_render_with_brand_swaps_header_and_button_color():
    brand = {"logo_url": "https://api.test/api/branding/abc/logo.png?v=1", "accent_dark": "#0a5c36"}
    html = email_layout.render(
        heading="H", paragraphs=["p"], button={"label": "Go", "url": "https://x.test"}, brand=brand
    )
    assert brand["logo_url"] in html
    assert 'bgcolor="#0a5c36"' in html
    assert "via Intro Connect" in html
    assert email_layout.LOGO_URL not in html  # host lockup replaces platform header
