"""Tests for guest-invite content + helpers. The send and DB-driven tick need
Resend + Mongo and are not exercised here.
Run from backend/: python -m pytest tests/test_invites.py
"""
from invites import (
    normalize_emails,
    invite_heading,
    invite_paragraphs,
    reminder_paragraphs,
    invite_subject,
    REMINDER_DAYS,
    MAX_REMINDERS,
    _join_url,
)


def test_normalize_emails_from_blob():
    out = normalize_emails("a@x.com, b@y.com\nB@Y.com  c@z.com; not-an-email")
    assert out == ["a@x.com", "b@y.com", "c@z.com"]  # lowercased, deduped, filtered


def test_normalize_emails_from_list():
    out = normalize_emails(["  Foo@Bar.com ", "foo@bar.com", "bad"])
    assert out == ["foo@bar.com"]


def test_invite_content_has_event_host_and_heading():
    joined = " ".join(invite_paragraphs("Denver Founders Dinner", "Eric"))
    assert "Denver Founders Dinner" in joined
    assert "Eric" in joined
    assert "Denver Founders Dinner" in invite_heading("Denver Founders Dinner")


def test_reminder_content_mentions_not_joined():
    joined = " ".join(reminder_paragraphs("Pitch Night", "Ian"))
    assert "Pitch Night" in joined
    assert "Ian" in joined
    assert "not joined" in joined


def test_copy_is_dash_free():
    blobs = (
        invite_paragraphs("E", "H")
        + reminder_paragraphs("E", "H")
        + [invite_subject("E"), invite_heading("E")]
    )
    for b in blobs:
        assert "—" not in b and "–" not in b


def test_reminder_cadence():
    assert REMINDER_DAYS == [2, 5]
    assert MAX_REMINDERS == 2


def test_join_url_shape():
    assert _join_url("ABC123").endswith("/join/ABC123")
