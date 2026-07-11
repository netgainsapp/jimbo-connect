"""Tests for the shared SEO helpers: canonical origin, head fragments, sitemap
XML, robots, JSON-LD escaping. Pure functions, no DB.

Run from backend/: python -m pytest tests/test_seo.py
"""
import os
from datetime import datetime, timezone

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import seo


def test_content_base_prefers_public_content_url(monkeypatch):
    monkeypatch.setenv("PUBLIC_CONTENT_URL", "https://intro-connect.com/")
    assert seo.content_base() == "https://intro-connect.com"


def test_content_base_falls_back_to_default(monkeypatch):
    monkeypatch.delenv("PUBLIC_CONTENT_URL", raising=False)
    monkeypatch.delenv("BLOG_BASE_URL", raising=False)
    assert seo.content_base() == "https://intro-connect.com"


def test_content_base_is_not_the_stale_vercel_domain(monkeypatch):
    monkeypatch.delenv("PUBLIC_CONTENT_URL", raising=False)
    monkeypatch.delenv("BLOG_BASE_URL", raising=False)
    assert "vercel.app" not in seo.content_base()


def test_abs_url_joins_and_passes_through(monkeypatch):
    monkeypatch.setenv("PUBLIC_CONTENT_URL", "https://intro-connect.com")
    assert seo.abs_url("/news/x") == "https://intro-connect.com/news/x"
    assert seo.abs_url("news/x") == "https://intro-connect.com/news/x"
    assert seo.abs_url("https://other.com/y") == "https://other.com/y"


def test_head_seo_has_canonical_og_twitter(monkeypatch):
    monkeypatch.setenv("PUBLIC_CONTENT_URL", "https://intro-connect.com")
    h = seo.head_seo(path="/news/x", title="T & Co", description="D")
    assert '<link rel="canonical" href="https://intro-connect.com/news/x"/>' in h
    assert 'property="og:url" content="https://intro-connect.com/news/x"' in h
    assert 'name="twitter:card" content="summary_large_image"' in h
    # attribute values are escaped
    assert "T &amp; Co" in h


def test_json_ld_escapes_angle_brackets():
    out = seo.json_ld({"x": "</script><b>"})
    # The payload's </script> must be neutralized so it cannot close the script
    # early; the only real </script> is the wrapper's own closing tag.
    assert out.count("</script>") == 1
    assert "\\u003c/script>" in out


def test_breadcrumb_ld_positions_and_urls(monkeypatch):
    monkeypatch.setenv("PUBLIC_CONTENT_URL", "https://intro-connect.com")
    out = seo.breadcrumb_ld([("Home", "/"), ("News", "/news")])
    assert '"@type":"BreadcrumbList"' in out
    assert '"position":1' in out and '"position":2' in out
    assert "https://intro-connect.com/news" in out


def test_render_sitemap_is_valid_xml(monkeypatch):
    monkeypatch.setenv("PUBLIC_CONTENT_URL", "https://intro-connect.com")
    import xml.dom.minidom as md

    xml = seo.render_sitemap(
        [
            {"path": "/", "priority": "1.0", "changefreq": "weekly"},
            {"path": "/news/x", "lastmod": datetime(2026, 7, 10, tzinfo=timezone.utc)},
        ]
    )
    assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    md.parseString(xml)  # raises if malformed
    assert "<loc>https://intro-connect.com/</loc>" in xml
    assert "<loc>https://intro-connect.com/news/x</loc>" in xml
    assert "<lastmod>2026-07-10</lastmod>" in xml


def test_render_sitemap_escapes_ampersand(monkeypatch):
    monkeypatch.setenv("PUBLIC_CONTENT_URL", "https://intro-connect.com")
    xml = seo.render_sitemap([{"path": "/news/a?b=1&c=2"}])
    assert "&amp;" in xml
    assert "&c=2" not in xml.replace("&amp;", "")  # raw & does not survive


def test_render_robots_points_at_sitemap(monkeypatch):
    monkeypatch.setenv("PUBLIC_CONTENT_URL", "https://intro-connect.com")
    r = seo.render_robots()
    assert "User-agent: *" in r
    assert "Disallow: /api/" in r
    assert "Sitemap: https://intro-connect.com/sitemap.xml" in r
