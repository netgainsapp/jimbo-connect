"""iCalendar generation.

The two things that actually break .ics files in the wild are escaping and line
folding, so most of this file is about those rather than about happy-path
output.

Run from backend/: python -m pytest tests/test_calendar_ics.py
"""
import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import pytest

import calendar_ics as ics


def _event(**over):
    base = {
        "id": "abc123",
        "name": "Denver Founders Dinner",
        "date": datetime(2026, 8, 1, 18, 30, tzinfo=timezone.utc),
        "location": "The Loft",
    }
    base.update(over)
    return base


def _lines(text):
    return text.split("\r\n")


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

def test_produces_a_well_formed_single_event_calendar():
    out = ics.build_event_ics(_event())
    lines = _lines(out)
    assert lines[0] == "BEGIN:VCALENDAR"
    assert "END:VCALENDAR" in lines
    assert lines.count("BEGIN:VEVENT") == 1
    assert "VERSION:2.0" in lines
    assert out.endswith("\r\n")


def test_uses_crlf_not_bare_newlines():
    """Some clients accept bare LF; others reject the file outright."""
    out = ics.build_event_ics(_event())
    assert "\r\n" in out
    assert "\n" not in out.replace("\r\n", "")


def test_uid_is_stable_and_namespaced():
    a = ics.build_event_ics(_event())
    b = ics.build_event_ics(_event())
    assert "UID:abc123@intro-connect.com" in a
    assert a.replace(_dtstamp(a), "") == b.replace(_dtstamp(b), "")


def _dtstamp(text):
    for line in _lines(text):
        if line.startswith("DTSTAMP:"):
            return line
    return ""


# ---------------------------------------------------------------------------
# Escaping: the reason a comma in a title corrupts the import
# ---------------------------------------------------------------------------

def test_commas_and_semicolons_are_escaped():
    out = ics.build_event_ics(_event(name="Dinner, drinks; and intros"))
    assert "SUMMARY:Dinner\\, drinks\\; and intros" in out


def test_newlines_become_literal_backslash_n():
    out = ics.build_event_ics(_event(description="Line one\nLine two"))
    assert "DESCRIPTION:Line one\\nLine two" in out
    # and the real newline is gone, so it cannot end the property early
    assert "DESCRIPTION:Line one\r\nLine two" not in out


def test_backslashes_are_escaped_first():
    """Escape order matters: doing backslashes last would double-escape the
    escapes inserted for commas and semicolons."""
    assert ics.escape_text("a\\b,c") == "a\\\\b\\,c"


def test_escaping_handles_empty_and_none():
    assert ics.escape_text(None) == ""
    assert ics.escape_text("") == ""


# ---------------------------------------------------------------------------
# Folding: the reason a long title works in one client and not another
# ---------------------------------------------------------------------------

def test_long_lines_are_folded_at_75_octets():
    out = ics.build_event_ics(_event(name="D" * 200))
    for line in _lines(out):
        assert len(line.encode("utf-8")) <= 75, f"unfolded line: {line[:90]}"


def test_folded_continuations_start_with_a_single_space():
    folded = ics.fold("SUMMARY:" + "x" * 200)
    parts = folded.split("\r\n")
    assert len(parts) > 1
    for part in parts[1:]:
        assert part.startswith(" ")
        assert not part.startswith("  ")


def test_folding_never_splits_a_multibyte_character():
    """Counting characters instead of octets corrupts the file at the boundary."""
    folded = ics.fold("SUMMARY:" + "é" * 100)
    for part in folded.split("\r\n"):
        part.encode("utf-8").decode("utf-8")  # must not raise
        assert len(part.encode("utf-8")) <= 75


def test_short_lines_are_left_alone():
    assert ics.fold("VERSION:2.0") == "VERSION:2.0"


# ---------------------------------------------------------------------------
# Times and dates
# ---------------------------------------------------------------------------

def test_a_timed_event_gets_a_two_hour_default_end():
    out = ics.build_event_ics(_event())
    assert "DTSTART:20260801T183000Z" in out
    assert "DTEND:20260801T203000Z" in out


def test_an_explicit_end_date_wins_over_the_default():
    out = ics.build_event_ics(
        _event(end_date=datetime(2026, 8, 1, 23, 0, tzinfo=timezone.utc))
    )
    assert "DTEND:20260801T230000Z" in out


def test_an_end_before_the_start_falls_back_to_the_default():
    out = ics.build_event_ics(
        _event(end_date=datetime(2026, 7, 1, tzinfo=timezone.utc))
    )
    assert "DTEND:20260801T203000Z" in out


def test_midnight_is_treated_as_an_all_day_event():
    """The product stores one date per event, so midnight nearly always means
    no time was given rather than a party starting at 00:00."""
    out = ics.build_event_ics(_event(date=datetime(2026, 8, 1)))
    assert "DTSTART;VALUE=DATE:20260801" in out
    # DTEND is exclusive for all-day entries: without the +1 day the event
    # vanishes from some calendar views.
    assert "DTEND;VALUE=DATE:20260802" in out


def test_a_naive_datetime_is_treated_as_utc():
    out = ics.build_event_ics(_event(date=datetime(2026, 8, 1, 18, 30)))
    assert "DTSTART:20260801T183000Z" in out


def test_an_event_with_no_date_is_refused():
    with pytest.raises(ValueError):
        ics.build_event_ics(_event(date=None))


# ---------------------------------------------------------------------------
# Optional fields
# ---------------------------------------------------------------------------

def test_optional_fields_are_omitted_rather_than_left_empty():
    out = ics.build_event_ics({"id": "x", "name": "Bare", "date": datetime(2026, 8, 1, 9, 0)})
    assert "LOCATION:" not in out
    assert "DESCRIPTION:" not in out
    assert "URL:" not in out


def test_url_is_included_when_given():
    out = ics.build_event_ics(_event(), url="https://app.intro-connect.com/events/abc123")
    assert "URL:https://app.intro-connect.com/events/abc123" in out


def test_filename_is_slugged_from_the_event_name():
    assert ics.filename_for({"name": "Denver Founders Dinner!"}) == "denver-founders-dinner.ics"
    assert ics.filename_for({}) == "event.ics"
