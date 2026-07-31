"""Host-facing guest list import.

The interesting tests here are not "does it import" but "what can a host NOT
do". A host imports email addresses they do not own, so any path that lets them
learn or set the password of an account created for someone else is an account
takeover, not a feature.

Run from backend/: python -m pytest tests/test_attendee_import.py
"""
import asyncio
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")
os.environ.setdefault("BILLING_ENFORCED", "true")

import pytest

import attendee_import
import core


def _run(coro):
    return asyncio.run(coro)


class _Row:
    """Stands in for BulkImportRow; only the fields the loop reads."""

    def __init__(self, email, name=""):
        self.email = email
        self.name = name
        self.role = self.company = self.industry = ""
        self.bio = self.looking_for = self.phone = self.linkedin = ""


def _patch(monkeypatch, *, existing_emails=(), attendee_count=0, host=None,
           email_configured=False):
    inserted_users = []
    seated = []

    class _Users:
        async def find_one(self, q):
            if "email" in q:
                e = q["email"]
                return {"_id": f"uid-{e}"} if e in existing_emails else None
            return host if host is not None else {"plan": "free"}

        async def insert_one(self, doc):
            inserted_users.append(doc)

            class R:
                inserted_id = f"new-{doc['email']}"

            return R()

    class _Attendees:
        async def find_one(self, _q):
            return None

        async def insert_one(self, doc):
            seated.append(doc)

        async def count_documents(self, _q):
            return attendee_count

    monkeypatch.setattr(attendee_import, "users", _Users())
    monkeypatch.setattr(attendee_import, "event_attendees", _Attendees())
    monkeypatch.setattr(core, "users", _Users())
    monkeypatch.setattr(core, "event_attendees", _Attendees())
    monkeypatch.setattr(
        attendee_import.email_send, "is_configured", lambda: email_configured
    )
    monkeypatch.setattr(
        attendee_import, "hash_password", lambda p: "hashed:" + p
    )
    return inserted_users, seated


ACTOR = {"_id": "host-1", "profile": {"name": "Scott"}}
EVENT = {"_id": "evt", "name": "Dinner", "created_by": "host-1"}


# ---------------------------------------------------------------------------
# What a host must not be able to do
# ---------------------------------------------------------------------------

def test_host_import_never_returns_a_plaintext_password(monkeypatch):
    """Even with email unconfigured, where the ADMIN path falls back to
    returning credentials, the host path must return none. Otherwise importing
    a stranger's address hands the host a login for that person."""
    _patch(monkeypatch, email_configured=False)
    out = _run(
        attendee_import.import_rows(
            actor=ACTOR,
            rows=[_Row("stranger@acme.co")],
            event_doc=EVENT,
            event_oid="evt",
        )
    )
    assert out["created"] == 1
    assert out["accounts"] == []


def test_host_created_passwords_are_random_and_not_shared(monkeypatch):
    """Two imported accounts must not end up with the same password, which is
    what a caller-supplied default would produce."""
    inserted, _ = _patch(monkeypatch)
    _run(
        attendee_import.import_rows(
            actor=ACTOR,
            rows=[_Row("a@acme.co"), _Row("b@acme.co")],
            event_doc=EVENT,
            event_oid="evt",
        )
    )
    assert len(inserted) == 2
    assert inserted[0]["password_hash"] != inserted[1]["password_hash"]


def test_the_host_request_model_has_no_password_field():
    """The restriction is structural, not a runtime check that a later edit
    could drop: the host model simply cannot carry a password."""
    from models import EventAttendeeImportRequest

    assert "default_password" not in EventAttendeeImportRequest.model_fields
    assert "event_id" not in EventAttendeeImportRequest.model_fields


# ---------------------------------------------------------------------------
# The admin path keeps the powers it already had
# ---------------------------------------------------------------------------

def test_admin_path_still_returns_credentials_when_email_is_off(monkeypatch):
    _patch(monkeypatch, email_configured=False)
    out = _run(
        attendee_import.import_rows(
            actor=ACTOR,
            rows=[_Row("a@acme.co")],
            event_doc=None,
            event_oid=None,
            disclose_credentials=True,
        )
    )
    assert out["accounts"] and out["accounts"][0]["email"] == "a@acme.co"


def test_credentials_are_never_returned_when_email_is_configured(monkeypatch):
    """One channel only: if the invitation email can carry the password, the
    response must not also contain it."""
    _patch(monkeypatch, email_configured=True)
    monkeypatch.setattr(
        attendee_import, "render_email_template", lambda *a, **k: _none()
    )
    out = _run(
        attendee_import.import_rows(
            actor=ACTOR,
            rows=[_Row("a@acme.co")],
            event_doc=None,
            event_oid=None,
            disclose_credentials=True,
        )
    )
    assert out["accounts"] == []


async def _none():
    return None


# ---------------------------------------------------------------------------
# Capacity, shared with every other add path
# ---------------------------------------------------------------------------

def test_import_fills_to_the_cap_and_reports_the_rest(monkeypatch):
    """A spreadsheet bigger than the plan should seat everyone it can, not
    fail wholesale. Free cap is 50; start at 49 so exactly one seat is left."""
    _, seated = _patch(monkeypatch, attendee_count=49, host={"plan": "free"})
    out = _run(
        attendee_import.import_rows(
            actor=ACTOR,
            rows=[_Row("a@acme.co"), _Row("b@acme.co"), _Row("c@acme.co")],
            event_doc=EVENT,
            event_oid="evt",
        )
    )
    assert out["added_to_event"] == 1
    assert len(seated) == 1
    # The two who missed out are named, not silently dropped.
    assert len(out["errors"]) == 2
    assert {e["email"] for e in out["errors"]} == {"b@acme.co", "c@acme.co"}
    # Their accounts still exist; they are simply not on this event.
    assert out["created"] == 3


def test_existing_users_are_seated_but_not_recreated(monkeypatch):
    _, seated = _patch(monkeypatch, existing_emails={"known@acme.co"})
    out = _run(
        attendee_import.import_rows(
            actor=ACTOR,
            rows=[_Row("known@acme.co")],
            event_doc=EVENT,
            event_oid="evt",
        )
    )
    assert out["created"] == 0 and out["skipped"] == 1
    assert out["added_to_event"] == 1


def test_no_event_means_nobody_is_seated(monkeypatch):
    _, seated = _patch(monkeypatch)
    out = _run(
        attendee_import.import_rows(
            actor=ACTOR, rows=[_Row("a@acme.co")], event_doc=None, event_oid=None
        )
    )
    assert out["added_to_event"] == 0 and seated == []
