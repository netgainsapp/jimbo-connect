"""Site analytics: the Cloudflare Web Analytics beacon on the server-rendered
public pages (blog, agenda, news) and the /blog CSP that has to admit it.

The beacon is env driven (CF_BEACON_TOKEN). Unset or malformed means nothing is
emitted and the CSP stays exactly as tight as before.

Run from backend/: python -m pytest tests/test_analytics.py
"""
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import analytics
import pageshell

TOKEN = "0123456789abcdef0123456789abcdef"

STRICT_BLOG_CSP = (
    "default-src 'self'; img-src 'self' data: https:; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "script-src 'none'; object-src 'none'; "
    "base-uri 'self'; frame-ancestors 'none'"
)


def test_no_beacon_when_token_unset(monkeypatch):
    monkeypatch.delenv("CF_BEACON_TOKEN", raising=False)
    assert analytics.beacon_tag() == ""
    assert "cloudflareinsights" not in pageshell.page("T", "<p>b</p>", canonical_path="/blog")


def test_beacon_emitted_on_shared_page_shell_when_token_set(monkeypatch):
    monkeypatch.setenv("CF_BEACON_TOKEN", TOKEN)
    html = pageshell.page("T", "<p>b</p>", canonical_path="/blog")
    assert 'src="https://static.cloudflareinsights.com/beacon.min.js"' in html
    assert f'data-cf-beacon=\'{{"token": "{TOKEN}"}}\'' in html
    # Inside <head>, so it loads on every server-rendered public page.
    assert html.index("beacon.min.js") < html.index("</head>")


def test_malformed_token_is_ignored_not_injected(monkeypatch):
    for bad in ['abc"><script>alert(1)</script>', "has space", "x" * 200, "  "]:
        monkeypatch.setenv("CF_BEACON_TOKEN", bad)
        assert analytics.beacon_tag() == "", bad
        assert analytics.token() == "", bad


def test_blog_csp_unchanged_without_token(monkeypatch):
    monkeypatch.delenv("CF_BEACON_TOKEN", raising=False)
    assert analytics.blog_csp() == STRICT_BLOG_CSP


def test_blog_csp_admits_only_cloudflare_beacon_with_token(monkeypatch):
    monkeypatch.setenv("CF_BEACON_TOKEN", TOKEN)
    csp = analytics.blog_csp()
    assert "script-src https://static.cloudflareinsights.com;" in csp
    assert "connect-src 'self' https://cloudflareinsights.com;" in csp
    # Inline script stays blocked: no 'unsafe-inline' or wildcard under script-src.
    script_src = csp.split("script-src", 1)[1].split(";", 1)[0]
    assert "unsafe-inline" not in script_src and "*" not in script_src
    assert "object-src 'none'" in csp and "frame-ancestors 'none'" in csp
