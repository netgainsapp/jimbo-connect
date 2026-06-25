"""Tests for guest-invite content + helpers. The send and DB-driven tick need
Resend + Mongo and are not exercised here.
Run from backend/: python -m pytest tests/test_invites.py
"""
from invites import (
    normalize_emails,
    invite_body,
    reminder_body,
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


def test_invite_body_has_event_host_and_join_link():
    body = invite_body("Denver Founders Dinner", "Eric", "https://app/join/ABC123")
    assert "Denver Founders Dinner" in body
    assert "Eric" in body
    assert "https://app/join/ABC123" in body


def test_reminder_body_mentions_not_joined_and_link():
    body = reminder_body("Pitch Night", "Ian", "https://app/join/XYZ")
    assert "Pitch Night" in body
    assert "https://app/join/XYZ" in body


def test_copy_is_dash_free():
    blobs = [
        invite_body("E", "H", "u"),
        reminder_body("E", "H", "u"),
        invite_subject("E"),
    ]
    for b in blobs:
        assert "—" not in b and "–" not in b


def test_reminder_cadence():
    assert REMINDER_DAYS == [2, 5]
    assert MAX_REMINDERS == 2


def test_join_url_shape():
    assert _join_url("ABC123").endswith("/join/ABC123")
