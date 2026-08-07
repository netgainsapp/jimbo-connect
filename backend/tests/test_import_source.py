"""Where a guest list came from, recorded on the event membership.

Attribution exists so we can later ask whether an imported list actually
became a network: invited, joined, connected. That question is only answerable
if the source is written at import time, because nothing downstream can infer
it afterwards.

The tests that matter here are the ones about restraint. Attribution must never
cost a host their import (a bad label is not a reason to refuse real guests),
and it must never widen what a host can do or see.

Run from backend/: python -m pytest tests/test_import_source.py
"""
import asyncio
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import attendee_import
import core


def _run(coro):
    return asyncio.run(coro)


class _Row:
    def __init__(self, email, name=""):
        self.email = email
        self.name = name
        self.role = self.company = self.industry = ""
        self.bio = self.looking_for = self.phone = self.linkedin = ""


def _patch(monkeypatch, *, existing_emails=()):
    seated = []

    class _Users:
        async def find_one(self, q):
            if "email" in q:
                e = q["email"]
                return {"_id": f"uid-{e}"} if e in existing_emails else None
            return {"plan": "free"}

        async def insert_one(self, doc):
            class R:
                inserted_id = f"new-{doc['email']}"

            return R()

    class _Attendees:
        async def find_one(self, _q):
            return None

        async def insert_one(self, doc):
            seated.append(doc)

        async def count_documents(self, _q):
            return 0

    monkeypatch.setattr(attendee_import, "users", _Users())
    monkeypatch.setattr(attendee_import, "event_attendees", _Attendees())
    monkeypatch.setattr(core, "users", _Users())
    monkeypatch.setattr(core, "event_attendees", _Attendees())
    monkeypatch.setattr(attendee_import.email_send, "is_configured", lambda: False)
    monkeypatch.setattr(attendee_import, "hash_password", lambda p: "hashed:" + p)
    return seated


ACTOR = {"_id": "host-1", "profile": {"name": "Scott"}}
EVENT = {"_id": "evt", "name": "Dinner", "created_by": "host-1"}


def test_source_is_written_on_the_membership(monkeypatch):
    seated = _patch(monkeypatch)
    _run(
        attendee_import.import_rows(
            actor=ACTOR,
            rows=[_Row("ava@example.com", "Ava Reynolds")],
            event_doc=EVENT,
            event_oid="evt",
            source="audience_republic",
        )
    )
    assert len(seated) == 1
    assert seated[0]["source"] == "audience_republic"
    assert "imported_at" in seated[0]


def test_source_defaults_to_manual_when_a_caller_says_nothing(monkeypatch):
    """The admin path does not pass a source, and must keep working."""
    seated = _patch(monkeypatch)
    _run(
        attendee_import.import_rows(
            actor=ACTOR,
            rows=[_Row("ben@example.com")],
            event_doc=EVENT,
            event_oid="evt",
        )
    )
    assert seated[0]["source"] == "manual"


def test_an_existing_person_still_gets_the_membership_labelled(monkeypatch):
    """Someone who already has an account is `skipped` as a user but is still
    newly on this event, so the membership this import creates carries the
    source like any other."""
    seated = _patch(monkeypatch, existing_emails=("cara@example.com",))
    out = _run(
        attendee_import.import_rows(
            actor=ACTOR,
            rows=[_Row("cara@example.com")],
            event_doc=EVENT,
            event_oid="evt",
            source="audience_republic",
        )
    )
    assert out["skipped"] == 1
    assert out["added_to_event"] == 1
    assert seated[0]["source"] == "audience_republic"


def test_import_without_an_event_writes_no_membership(monkeypatch):
    """Attribution lives on the membership, so an admin import with no event
    simply has nowhere to put it and must not invent one."""
    seated = _patch(monkeypatch)
    _run(
        attendee_import.import_rows(
            actor=ACTOR,
            rows=[_Row("solo@example.com")],
            event_doc=None,
            event_oid=None,
            source="audience_republic",
        )
    )
    assert seated == []


# ---------------------------------------------------------------------------
# The request model
# ---------------------------------------------------------------------------

def test_an_unknown_source_becomes_other_rather_than_a_422():
    """A mislabelled import is not a reason to refuse a real guest list."""
    from models import EventAttendeeImportRequest

    req = EventAttendeeImportRequest(rows=[], source="salesforce")
    assert req.source == "other"


def test_known_sources_are_kept_verbatim():
    from models import EventAttendeeImportRequest, IMPORT_SOURCES

    for s in IMPORT_SOURCES:
        assert EventAttendeeImportRequest(rows=[], source=s).source == s


def test_source_does_not_reopen_the_host_restrictions():
    """Adding a field must not have widened what the host model can carry."""
    from models import EventAttendeeImportRequest

    assert "default_password" not in EventAttendeeImportRequest.model_fields
    assert "event_id" not in EventAttendeeImportRequest.model_fields


def test_a_missing_source_defaults_to_csv_on_the_request():
    from models import EventAttendeeImportRequest

    assert EventAttendeeImportRequest(rows=[]).source == "csv"


# ---------------------------------------------------------------------------
# Reading the attribution back out
# ---------------------------------------------------------------------------

class _Cursor:
    """Async iterable standing in for a Motor cursor."""

    def __init__(self, docs):
        self._docs = list(docs)

    def __aiter__(self):
        async def gen():
            for d in self._docs:
                yield d

        return gen()


def test_insights_split_the_same_numbers_by_source(monkeypatch):
    """The point of storing a source is being able to ask whether an imported
    list became a network. Totals and per source counts are built in one pass,
    so they cannot disagree."""
    from bson import ObjectId
    import asyncio as _asyncio

    from routers import admin as admin_router

    oid = ObjectId()
    ar_user, self_user = ObjectId(), ObjectId()

    class _Events:
        async def find_one(self, _q):
            return {"_id": oid}

    class _Attendees:
        def find(self, _q, _proj=None):
            return _Cursor([
                {"user_id": ar_user, "source": "audience_republic"},
                {"user_id": self_user},  # joined before attribution existed
            ])

    class _Saved:
        def find(self, _q, _proj=None):
            # The imported attendee saved the other one.
            return _Cursor([{"owner_id": ar_user, "contact_id": self_user}])

    class _Messages:
        def find(self, _q, _proj=None):
            return _Cursor([{"from_user_id": ar_user, "to_user_id": self_user}])

    class _Invites:
        async def count_documents(self, q):
            return 1 if "joined_at" not in q else 1

    class _Users:
        def find(self, _q, _proj=None):
            return _Cursor([
                {"_id": ar_user, "profile": {"role": "Founder"}},
                {"_id": self_user, "profile": {}},
            ])

        async def find_one(self, _q, _proj=None):
            return {"_id": self_user, "profile": {"name": "Ben"}}

    monkeypatch.setattr(admin_router, "events", _Events())
    monkeypatch.setattr(admin_router, "event_attendees", _Attendees())
    monkeypatch.setattr(admin_router, "saved_contacts", _Saved())
    monkeypatch.setattr(admin_router, "users", _Users())
    import database

    monkeypatch.setattr(database, "messages", _Messages())
    monkeypatch.setattr(database, "event_invites", _Invites())

    out = _asyncio.run(admin_router.admin_event_insights(str(oid), _={}))

    assert out["attendees"] == 2
    assert out["connections"] == 1
    assert out["messages"] == 1

    ar = out["by_source"]["audience_republic"]
    assert ar["attendees"] == 1
    assert ar["connections"] == 1
    assert ar["messages"] == 1
    assert ar["profile_completed"] == 1, "role filled in after import"

    # A membership written before attribution existed is unknown, not "manual".
    assert out["by_source"]["unattributed"]["attendees"] == 1
    assert out["by_source"]["unattributed"]["profile_completed"] == 0

    # The split must account for everyone, with nothing double counted.
    assert sum(v["attendees"] for v in out["by_source"].values()) == out["attendees"]
    assert sum(v["connections"] for v in out["by_source"].values()) == out["connections"]
