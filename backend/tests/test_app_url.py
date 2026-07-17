"""The canonical app URL must never leak *.onrender.com into user-facing
links, whatever shape FRONTEND_URL takes.
Run from backend/: python -m pytest tests/test_app_url.py
"""
from app_url import _canonical_app_url


def test_bare_render_url_prefers_custom_domain():
    assert (
        _canonical_app_url("https://jimbo-connect-web-huph.onrender.com")
        == "https://app.intro-connect.com"
    )


def test_comma_list_picks_custom_domain_regardless_of_order():
    raw = "https://jimbo-connect-web-huph.onrender.com,https://app.intro-connect.com"
    assert _canonical_app_url(raw) == "https://app.intro-connect.com"
    assert (
        _canonical_app_url("https://app.intro-connect.com/," + raw)
        == "https://app.intro-connect.com"
    )


def test_localhost_dev_passes_through():
    assert _canonical_app_url("http://localhost:3000") == "http://localhost:3000"


def test_empty_falls_back_to_localhost():
    assert _canonical_app_url("") == "http://localhost:3000"


def test_trailing_slash_stripped():
    assert (
        _canonical_app_url("https://app.intro-connect.com/")
        == "https://app.intro-connect.com"
    )
