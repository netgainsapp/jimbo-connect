"""Tests for the cross-user authorization gate (users_share_event /
_users_connected) that fixes the IDOR/BOLA on profile view, contact save, and
messaging: any authenticated user could previously read any user's PII or DM
anyone by walking ObjectIds.

Uses in-memory fakes for the motor collections and asyncio.run, so no live
MongoDB and no extra async-test dependency is needed.

Run from backend/: python -m pytest tests/test_authz.py
"""
import asyncio
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import server


class _AsyncCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def __aiter__(self):
        self._it = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


class _FakeAttendees:
    """links: list of (event_id, user_id) tuples."""

    def __init__(self, links):
        self.links = links

    def find(self, query, projection=None):
        uid = query.get("user_id")
        return _AsyncCursor(
            [{"event_id": e} for (e, u) in self.links if u == uid]
        )


class _FakeEvents:
    """events: dict of event_id -> created_by (host user id)."""

    def __init__(self, events):
        self.events = events

    def find(self, query, projection=None):
        ids = query.get("_id", {}).get("$in", [])
        return _AsyncCursor(
            [{"created_by": self.events[i]} for i in ids if i in self.events]
        )


class _FakeFindOne:
    def __init__(self, result=None):
        self.result = result

    async def find_one(self, query):
        return self.result


def _wire(monkeypatch, *, links=None, events=None, saved=None, thread=None):
    monkeypatch.setattr(server, "event_attendees", _FakeAttendees(links or []))
    monkeypatch.setattr(server, "events", _FakeEvents(events or {}))
    monkeypatch.setattr(server, "saved_contacts", _FakeFindOne(saved))
    monkeypatch.setattr(server, "messages", _FakeFindOne(thread))


def test_share_event_true_when_both_attend_same_event(monkeypatch):
    _wire(monkeypatch, links=[("E1", "A"), ("E1", "B")])
    assert asyncio.run(server.users_share_event("A", "B")) is True


def test_share_event_true_when_target_hosts_event_requester_attends(monkeypatch):
    # A attends E1, B is the host (created_by) of E1 and not an attendee.
    _wire(monkeypatch, links=[("E1", "A")], events={"E1": "B"})
    assert asyncio.run(server.users_share_event("A", "B")) is True


def test_share_event_true_when_requester_hosts_event_target_attends(monkeypatch):
    _wire(monkeypatch, links=[("E1", "B")], events={"E1": "A"})
    assert asyncio.run(server.users_share_event("A", "B")) is True


def test_share_event_false_for_unrelated_users(monkeypatch):
    _wire(monkeypatch, links=[("E1", "A"), ("E2", "B")], events={"E1": "A", "E2": "B"})
    assert asyncio.run(server.users_share_event("A", "B")) is False


def test_share_event_false_when_requester_has_no_events(monkeypatch):
    _wire(monkeypatch, links=[("E1", "B")])
    assert asyncio.run(server.users_share_event("A", "B")) is False


def test_connected_allows_admin(monkeypatch):
    _wire(monkeypatch)  # no shared events at all
    admin = {"_id": "A", "is_admin": True}
    assert asyncio.run(server._users_connected(admin, "B")) is True


def test_connected_allows_self(monkeypatch):
    _wire(monkeypatch)
    me = {"_id": "A", "is_admin": False}
    assert asyncio.run(server._users_connected(me, "A")) is True


def test_connected_false_for_stranger(monkeypatch):
    _wire(monkeypatch, links=[("E1", "A"), ("E2", "B")])
    me = {"_id": "A", "is_admin": False}
    assert asyncio.run(server._users_connected(me, "B")) is False


def test_connected_true_via_shared_event(monkeypatch):
    _wire(monkeypatch, links=[("E1", "A"), ("E1", "B")])
    me = {"_id": "A", "is_admin": False}
    assert asyncio.run(server._users_connected(me, "B")) is True


def test_connected_true_when_already_saved_contact(monkeypatch):
    _wire(monkeypatch, saved={"_id": "sc1"})
    me = {"_id": "A", "is_admin": False}
    assert asyncio.run(server._users_connected(me, "B")) is True


def test_connected_true_when_existing_thread(monkeypatch):
    _wire(monkeypatch, thread={"_id": "m1"})
    me = {"_id": "A", "is_admin": False}
    assert asyncio.run(server._users_connected(me, "B")) is True
