"""Tests for the public news HTML renderer. Pure string builders, no DB.
Run from backend/: python -m pytest tests/test_news_render.py
"""
import os
from datetime import datetime, timezone

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")
os.environ.setdefault("PUBLIC_CONTENT_URL", "https://intro-connect.com")

from news.render import render_index, render_article, render_404

ARTICLE = {
    "slug": "networking-tool-launch",
    "headline": "A New Tool Changes How Hosts Follow Up",
    "summary": "What the launch means for event organizers.",
    "sections": [
        {"heading": "What happened", "body": "The company announced it today.\n\nHere is the second paragraph."},
        {"heading": "Why it matters", "body": "Hosts get a faster path to their attendees."},
    ],
    "source_url": "https://example.com/press-release",
    "sources": ["https://example.org/coverage"],
    "event_date": "July 10, 2026",
    "published_at": datetime(2026, 7, 10, tzinfo=timezone.utc),
}


def test_index_empty_shows_placeholder():
    out = render_index([])
    assert "No news yet" in out
    assert "<title>" in out and "Intro Connect" in out
    assert 'rel="canonical" href="https://intro-connect.com/news"' in out


def test_index_lists_articles_with_links():
    out = render_index([ARTICLE])
    assert "A New Tool Changes How Hosts Follow Up" in out
    assert "/news/networking-tool-launch" in out
    assert "July 10, 2026" in out


def test_article_renders_sections_and_newsarticle_jsonld():
    out = render_article(ARTICLE)
    assert "What happened" in out
    assert "The company announced it today" in out
    assert "Here is the second paragraph" in out  # \n\n split
    assert 'application/ld+json' in out
    assert '"@type":"NewsArticle"' in out
    assert '"datePublished":"2026-07-10' in out


def test_article_has_canonical_og_breadcrumb():
    out = render_article(ARTICLE)
    assert 'rel="canonical" href="https://intro-connect.com/news/networking-tool-launch"' in out
    assert 'property="og:type" content="article"' in out
    assert '"@type":"BreadcrumbList"' in out


def test_article_shows_source_attribution():
    out = render_article(ARTICLE)
    assert "Sources" in out
    assert "https://example.com/press-release" in out
    assert "https://example.org/coverage" in out
    assert 'rel="nofollow noopener"' in out


def test_article_escapes_html_in_content():
    evil = {**ARTICLE, "headline": "<script>alert('x')</script>", "sections": [], "sources": []}
    out = render_article(evil)
    assert "<script>alert('x')</script>" not in out
    assert "&lt;script&gt;" in out


def test_404_page():
    out = render_404()
    assert "not found" in out.lower()
    assert "/news" in out
