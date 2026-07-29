"""Tests for the nurture sequence content + structure. The actual send and the
DB-driven tick need Resend + Mongo and are not exercised here.
Run from backend/: python -m pytest tests/test_nurture.py
"""
from nurture import (
    STEPS,
    WELCOME_SUBJECT,
    WELCOME_HEADING,
    gate_matches,
    welcome_paragraphs,
    _html,
    _name,
)


def test_welcome_includes_name_and_heading():
    paras = welcome_paragraphs("Sarah")
    joined = " ".join(paras)
    assert "Sarah" in joined
    assert WELCOME_SUBJECT and WELCOME_HEADING


def test_steps_are_ordered_and_gated():
    assert len(STEPS) == 4
    days = [s["after_days"] for s in STEPS]
    assert days == sorted(days)  # 2, 3, 5, 10 ascending
    gates = {s["gate"] for s in STEPS}
    assert gates <= {"cold_host", "attendee", "has_event", "always"}
    # each step renders paragraphs with the name, a heading, and a button URL
    for s in STEPS:
        paras = s["paragraphs"]("Alex")
        assert any("Alex" in p for p in paras)
        assert len(" ".join(paras)) > 80
        assert s["heading"]
        assert s["button"]["label"] and s["button"]["url"].startswith("http")


def test_no_dashes_in_copy():
    # brand voice: no em or en dashes anywhere in the sequence
    blobs = [" ".join(welcome_paragraphs("X"))]
    blobs += [" ".join(s["paragraphs"]("X")) + " " + s["heading"] for s in STEPS]
    for body in blobs:
        assert "—" not in body  # em dash
        assert "–" not in body  # en dash


# ---------- attendee to host routing ----------

def test_cold_signup_gets_the_setup_pitch_only():
    """Signed up on spec: hosts nothing, has been nobody's guest."""
    assert gate_matches("cold_host", has_event=False, joined_others=False)
    assert not gate_matches("attendee", has_event=False, joined_others=False)
    assert not gate_matches("has_event", has_event=False, joined_others=False)


def test_attendee_gets_the_attendee_pitch_only():
    """Joined someone else's room, hosts nothing. The loop's target."""
    assert gate_matches("attendee", has_event=False, joined_others=True)
    assert not gate_matches("cold_host", has_event=False, joined_others=True)


def test_host_gets_neither_starter_pitch():
    for joined in (True, False):
        assert not gate_matches("cold_host", has_event=True, joined_others=joined)
        assert not gate_matches("attendee", has_event=True, joined_others=joined)
        assert gate_matches("has_event", has_event=True, joined_others=joined)


def test_always_gate_matches_everyone():
    for has_event in (True, False):
        for joined in (True, False):
            assert gate_matches("always", has_event, joined)


def test_unknown_gate_fails_closed():
    assert not gate_matches("no_event", has_event=False, joined_others=False)
    assert not gate_matches("", True, True)


def test_attendee_step_links_into_the_create_flow():
    step = next(s for s in STEPS if s["gate"] == "attendee")
    assert step["button"]["url"].endswith("/events?host=1")


def test_html_wraps_paragraphs():
    out = _html("One.\n\nTwo.")
    assert out.count("<p>") == 2


def test_name_fallback():
    assert _name({"profile": {"name": "Jo"}}) == "Jo"
    assert _name({}) == "there"
