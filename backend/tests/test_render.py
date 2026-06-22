"""Tests for the public blog HTML renderer. Pure string builders, no DB.
Run from backend/: python -m pytest tests/test_render.py
"""
from datetime import datetime, timezone

from blog.render import render_index, render_post, render_404

POST = {
    "slug": "how-to-network-at-conferences",
    "title": "How to Network at Conferences",
    "summary": "A practical guide to making conferences pay off.",
    "sections": [
        {"heading": "Before you go", "body": "Pick a few people you want to meet.\n\nDo a little homework."},
        {"heading": "During the event", "body": "Ask better questions than what do you do."},
    ],
    "cta": "Keep your conference connections alive with Intro Connect.",
    "published_at": datetime(2026, 6, 22, tzinfo=timezone.utc),
}


def test_index_empty_shows_coming_soon():
    htmlout = render_index([])
    assert "on the way" in htmlout
    assert "<title>" in htmlout and "Intro Connect" in htmlout


def test_index_lists_posts_with_links():
    htmlout = render_index([POST])
    assert "How to Network at Conferences" in htmlout
    assert '/blog/how-to-network-at-conferences' in htmlout
    assert "June 22, 2026" in htmlout


def test_post_renders_sections_and_cta_and_jsonld():
    htmlout = render_post(POST)
    assert "Before you go" in htmlout
    assert "Pick a few people" in htmlout
    assert "Do a little homework" in htmlout  # second paragraph from \n\n split
    assert "Intro Connect" in htmlout
    assert 'application/ld+json' in htmlout
    assert '"@type": "Article"' in htmlout


def test_post_escapes_html_in_content():
    evil = {**POST, "title": "<script>alert('x')</script>", "sections": [], "cta": ""}
    htmlout = render_post(evil)
    # the raw script must be escaped, not present as an executable tag
    assert "<script>alert('x')</script>" not in htmlout
    assert "&lt;script&gt;" in htmlout


def test_404_page():
    htmlout = render_404()
    assert "not found" in htmlout.lower()
    assert '/blog' in htmlout
