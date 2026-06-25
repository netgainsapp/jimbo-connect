"""Tests for the nurture sequence content + structure. The actual send and the
DB-driven tick need Resend + Mongo and are not exercised here.
Run from backend/: python -m pytest tests/test_nurture.py
"""
from nurture import STEPS, WELCOME_SUBJECT, welcome_body, _html, _name


def test_welcome_includes_name_and_setup_link():
    body = welcome_body("Sarah")
    assert "Sarah" in body
    assert "/events" in body  # the set-up-your-first-event link
    assert WELCOME_SUBJECT


def test_steps_are_ordered_and_gated():
    assert len(STEPS) == 3
    days = [s["after_days"] for s in STEPS]
    assert days == sorted(days)  # 2, 5, 10 ascending
    gates = {s["gate"] for s in STEPS}
    assert gates <= {"no_event", "has_event", "always"}
    # each step body renders with a name and is non-trivial
    for s in STEPS:
        body = s["body"]("Alex")
        assert "Alex" in body
        assert len(body) > 80


def test_no_dashes_in_copy():
    # brand voice: no em or en dashes anywhere in the sequence
    blobs = [welcome_body("X")] + [s["body"]("X") for s in STEPS]
    for body in blobs:
        assert "—" not in body  # em dash
        assert "–" not in body  # en dash


def test_html_wraps_paragraphs():
    out = _html("One.\n\nTwo.")
    assert out.count("<p>") == 2


def test_name_fallback():
    assert _name({"profile": {"name": "Jo"}}) == "Jo"
    assert _name({}) == "there"
