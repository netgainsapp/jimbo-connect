"""Cross-event directory: per-event opt in, no emails, both-sides messaging.

The directory is the one feature that introduces people who were never in a
room together, so most of these tests are about what it refuses to do.

Run from backend/: python -m pytest tests/test_directory.py
"""
import asyncio
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import pytest
from bson import ObjectId

import core
import directory

E1, E2 = ObjectId(), ObjectId()
ANN, BOB, CHRIS, ADMIN = ObjectId(), ObjectId(), ObjectId(), ObjectId()


class _Links:
    """Stands in for the event_attendees collection."""

    def __init__(self, rows=()):
        self.rows = [dict(r) for r in rows]

    def _match(self, doc, query):
        return all(doc.get(k) == v for k, v in query.items())

    async def find_one(self, query):
        for r in self.rows:
            if self._match(r, query):
                return r
        return None

    def find(self, query, *_projection):
        """Both shapes the real code uses: directory awaits .to_list(), while
        core._attended_event_ids iterates the cursor and passes a projection."""
        rows = [r for r in self.rows if self._match(r, query)]

        class _C:
            async def to_list(self, _limit=None):
                return rows

            def __aiter__(self):
                self._it = iter(rows)
                return self

            async def __anext__(self):
                try:
                    return next(self._it)
                except StopIteration:
                    raise StopAsyncIteration

        return _C()

    async def update_one(self, query, update):
        n = 0
        for r in self.rows:
            if self._match(r, query):
                r.update(update["$set"])
                n = 1
                break
        return type("R", (), {"matched_count": n})()


class _Users:
    def __init__(self, docs=()):
        self.docs = list(docs)

    def find(self, query):
        wanted = set(query["_id"]["$in"])
        docs = [d for d in self.docs if d["_id"] in wanted]

        class _C:
            async def to_list(self, _limit=None):
                return docs

        return _C()


def _person(oid, name, **profile):
    return {
        "_id": oid,
        "email": f"{name.lower()}@example.com",
        "profile": {"name": name, **profile},
    }


def _wire(monkeypatch, rows, users=()):
    monkeypatch.setattr(directory, "event_attendees", _Links(rows))
    monkeypatch.setattr(directory, "users", _Users(users))


def _run(c):
    return asyncio.run(c)


# --------------------------------------------------------------------------
# Opt in is per event and off by default
# --------------------------------------------------------------------------

def test_a_new_attendee_is_not_listed(monkeypatch):
    """Rows that predate this feature have no flag at all, and must read as
    opted out rather than being published by default."""
    _wire(monkeypatch, [{"event_id": E1, "user_id": ANN}])
    assert _run(directory.get_discoverable(E1, ANN)) is False
    assert _run(directory.is_discoverable(ANN)) is False


def test_opting_in_applies_to_one_event_only(monkeypatch):
    _wire(monkeypatch, [
        {"event_id": E1, "user_id": ANN},
        {"event_id": E2, "user_id": ANN},
    ])
    assert _run(directory.set_discoverable(E1, ANN, True)) is True

    assert _run(directory.get_discoverable(E1, ANN)) is True
    assert _run(directory.get_discoverable(E2, ANN)) is False
    # Listed through one event is listed, which is what makes the switch useful.
    assert _run(directory.is_discoverable(ANN)) is True


def test_opting_out_again_removes_the_listing(monkeypatch):
    _wire(monkeypatch, [{"event_id": E1, "user_id": ANN, "discoverable": True}])
    _run(directory.set_discoverable(E1, ANN, False))
    assert _run(directory.is_discoverable(ANN)) is False


def test_cannot_opt_in_without_being_on_the_guest_list(monkeypatch):
    """A host who never joined their own event has no link row. Creating one
    here would add them to the guest list and the attendee count as a side
    effect of flipping a privacy switch."""
    _wire(monkeypatch, [])
    assert _run(directory.set_discoverable(E1, ANN, True)) is False


# --------------------------------------------------------------------------
# Messaging needs both sides
# --------------------------------------------------------------------------

def test_both_discoverable_requires_both_sides(monkeypatch):
    _wire(monkeypatch, [
        {"event_id": E1, "user_id": ANN, "discoverable": True},
        {"event_id": E2, "user_id": BOB},
    ])
    assert _run(directory.both_discoverable(ANN, BOB)) is False

    _run(directory.set_discoverable(E2, BOB, True))
    assert _run(directory.both_discoverable(ANN, BOB)) is True


def test_nobody_is_connected_to_themselves_via_the_directory(monkeypatch):
    _wire(monkeypatch, [{"event_id": E1, "user_id": ANN, "discoverable": True}])
    assert _run(directory.both_discoverable(ANN, ANN)) is False


def test_users_connected_opens_up_for_two_opted_in_strangers(monkeypatch):
    """The point of the whole feature: two people who never shared an event can
    reach each other, but only because both chose to be listed."""
    monkeypatch.setattr(core, "event_attendees", _Links([]))
    monkeypatch.setattr(core, "events", type("E", (), {
        "find_one": staticmethod(lambda *_a, **_k: _none()),
    })())
    monkeypatch.setattr(core, "saved_contacts", type("S", (), {
        "find_one": staticmethod(lambda *_a, **_k: _none()),
    })())
    monkeypatch.setattr(core, "messages", type("M", (), {
        "find_one": staticmethod(lambda *_a, **_k: _none()),
    })())

    rows = [
        {"event_id": E1, "user_id": ANN, "discoverable": True},
        {"event_id": E2, "user_id": BOB, "discoverable": True},
        {"event_id": E2, "user_id": CHRIS},
    ]
    monkeypatch.setattr(directory, "event_attendees", _Links(rows))

    requester = {"_id": ANN}
    assert _run(core._users_connected(requester, BOB)) is True
    # Chris attended something but never opted in, so he stays unreachable.
    assert _run(core._users_connected(requester, CHRIS)) is False


async def _none():
    return None


# --------------------------------------------------------------------------
# What the listing exposes
# --------------------------------------------------------------------------

def test_a_directory_entry_carries_no_email(monkeypatch):
    """The serializer is separate from serialize_attendee precisely so an email
    field cannot arrive here by inheritance."""
    person = directory.serialize_person(_person(ANN, "Ann", role="VP"))
    assert "email" not in person
    assert "email" not in person["profile"]
    assert str(ANN) not in repr(person.get("email", ""))
    assert person["profile"]["name"] == "Ann"


def test_listing_excludes_the_viewer_admins_and_anyone_not_opted_in(monkeypatch):
    rows = [
        {"event_id": E1, "user_id": ANN, "discoverable": True},
        {"event_id": E1, "user_id": BOB, "discoverable": True},
        {"event_id": E1, "user_id": CHRIS},                       # not opted in
        {"event_id": E1, "user_id": ADMIN, "discoverable": True},  # admin
    ]
    people = [
        _person(ANN, "Ann"), _person(BOB, "Bob"),
        _person(CHRIS, "Chris"), {**_person(ADMIN, "Root"), "is_admin": True},
    ]
    _wire(monkeypatch, rows, people)

    names = [p["profile"]["name"] for p in _run(directory.list_people(ANN))]
    assert names == ["Bob"]


def test_listing_never_leaks_an_email(monkeypatch):
    rows = [{"event_id": E1, "user_id": BOB, "discoverable": True}]
    _wire(monkeypatch, rows, [_person(BOB, "Bob")])
    assert "bob@example.com" not in repr(_run(directory.list_people(ANN)))


def test_someone_listed_through_two_events_appears_once(monkeypatch):
    rows = [
        {"event_id": E1, "user_id": BOB, "discoverable": True},
        {"event_id": E2, "user_id": BOB, "discoverable": True},
    ]
    _wire(monkeypatch, rows, [_person(BOB, "Bob")])
    assert len(_run(directory.list_people(ANN))) == 1


def test_search_matches_across_profile_fields(monkeypatch):
    rows = [
        {"event_id": E1, "user_id": BOB, "discoverable": True},
        {"event_id": E1, "user_id": CHRIS, "discoverable": True},
    ]
    _wire(monkeypatch, rows, [
        _person(BOB, "Bob", company="Northwind", industry="Software"),
        _person(CHRIS, "Chris", company="Globex", industry="Retail"),
    ])

    assert [p["profile"]["name"] for p in _run(directory.list_people(ANN, query="northwind"))] == ["Bob"]
    assert [p["profile"]["name"] for p in _run(directory.list_people(ANN, industry="Retail"))] == ["Chris"]
    assert len(_run(directory.list_people(ANN, industry="all"))) == 2
    assert _run(directory.list_people(ANN, query="nobody here")) == []


def test_results_are_capped(monkeypatch):
    many = [ObjectId() for _ in range(directory.MAX_RESULTS + 25)]
    rows = [{"event_id": E1, "user_id": oid, "discoverable": True} for oid in many]
    _wire(monkeypatch, rows, [_person(oid, f"P{i:04}") for i, oid in enumerate(many)])
    assert len(_run(directory.list_people(ANN))) == directory.MAX_RESULTS


def test_browsing_requires_having_attended_something(monkeypatch):
    _wire(monkeypatch, [{"event_id": E1, "user_id": ANN}])
    assert _run(directory.has_any_attendance(ANN)) is True
    assert _run(directory.has_any_attendance(BOB)) is False
