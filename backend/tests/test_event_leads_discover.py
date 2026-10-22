"""An approved event lead's event is not public until its host claims it.

Approve builds the event for a prospect who has not signed up. Until the claim
(Task 5 sets provenance.claimed_at) it must stay out of every signed-in
user's discover feed, and the host's email must never stand in for a name.

Run from backend/: python -m pytest tests/test_event_leads_discover.py
"""
import asyncio
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from routers import events as route

SOON = datetime.now(timezone.utc) + timedelta(days=7)
VIEWER = {"_id": ObjectId()}


class _Cursor:
    def __init__(self, rows):
        self.rows = list(rows)

    def sort(self, *a):
        return self

    async def to_list(self, _length):
        return list(self.rows)

    def __aiter__(self):
        self._it = iter(self.rows)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


class _Events:
    def __init__(self, rows):
        self.rows = rows

    def find(self, q):
        return _Cursor(self.rows)


class _Attendees:
    def find(self, q):
        return _Cursor([])

    def aggregate(self, pipeline):
        return _Cursor([])


class _Users:
    def __init__(self, rows):
        self.rows = rows

    def find(self, q):
        wanted = set(q["_id"]["$in"])
        return _Cursor(u for u in self.rows if u["_id"] in wanted)


def _event(host_id, **extra):
    return {"_id": ObjectId(), "name": "Mixer", "date": SOON, "join_code": "J",
            "created_by": host_id, **extra}


@pytest.fixture
def wire(monkeypatch):
    def _wire(event_rows, user_rows=()):
        monkeypatch.setattr(route, "events", _Events(event_rows))
        monkeypatch.setattr(route, "event_attendees", _Attendees())
        monkeypatch.setattr(route, "users", _Users(list(user_rows)))
        return asyncio.run(route.discoverable_events(VIEWER))
    return _wire


def test_an_unclaimed_lead_event_is_hidden_and_a_claimed_one_is_shown(wire):
    host = {"_id": ObjectId(), "profile": {"name": "Jane"}}
    unclaimed = _event(host["_id"], provenance={"event_lead_id": "lead-1"})
    pending = _event(None, provenance={"event_lead_id": "lead-2", "pending_host": True})
    claimed = _event(host["_id"], provenance={
        "event_lead_id": "lead-3", "claimed_at": SOON - timedelta(days=1)})
    ordinary = _event(host["_id"])

    ids = [e["id"] for e in wire([unclaimed, pending, claimed, ordinary], [host])]

    assert ids == [str(claimed["_id"]), str(ordinary["_id"])]


def test_an_event_lead_host_without_a_name_never_shows_their_email(wire):
    lead_host = {"_id": ObjectId(), "email": "jane@host.org", "profile": {"name": ""},
                 "host_origin": "event_lead"}
    normal = {"_id": ObjectId(), "email": "bob@host.org", "profile": {"name": ""}}
    claimed = {"event_lead_id": "lead-1", "claimed_at": SOON}

    rows = wire([_event(lead_host["_id"], provenance=claimed), _event(normal["_id"])],
                [lead_host, normal])

    assert [r["host_name"] for r in rows] == ["", "bob@host.org"]


def test_the_helper_reads_only_provenance():
    assert route.is_unclaimed_lead_event({"provenance": {"event_lead_id": "x"}})
    assert not route.is_unclaimed_lead_event({})
    assert not route.is_unclaimed_lead_event(
        {"provenance": {"event_lead_id": "x", "claimed_at": SOON}})
