"""Sponsor write authorization.

Sponsor writes used to be platform-admin only, so a paying host could not add a
sponsor to their own event. They are now host-manageable, which makes these
the tests that matter: the gate must admit the event's creator and an admin,
and nobody else, in particular not an attendee who merely joined the event.

Run from backend/: python -m pytest tests/test_sponsor_access.py
"""
import asyncio
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import pytest
from bson import ObjectId
from fastapi import HTTPException

from routers import sponsors


class _Events:
    """Stand-in for the motor collection: only find_one is used by the gate."""

    def __init__(self, doc):
        self._doc = doc

    async def find_one(self, _query):
        return self._doc


def _run(coro):
    return asyncio.run(coro)


def _with_event(monkeypatch, doc):
    monkeypatch.setattr(sponsors, "events", _Events(doc))


def test_creator_may_manage_sponsors_on_their_own_event(monkeypatch):
    oid = ObjectId()
    _with_event(monkeypatch, {"_id": oid, "created_by": 7})
    got, event = _run(
        sponsors._require_event_manage(str(oid), {"_id": 7, "is_admin": False})
    )
    assert got == oid
    assert event["created_by"] == 7


def test_admin_may_manage_sponsors_on_any_event(monkeypatch):
    oid = ObjectId()
    _with_event(monkeypatch, {"_id": oid, "created_by": 999})
    got, _ = _run(
        sponsors._require_event_manage(str(oid), {"_id": 7, "is_admin": True})
    )
    assert got == oid


def test_attendee_who_merely_joined_may_not_write_sponsors(monkeypatch):
    """The looser _require_event_access admits joined attendees because it
    backs a read. Writing must not."""
    oid = ObjectId()
    _with_event(monkeypatch, {"_id": oid, "created_by": 999})
    with pytest.raises(HTTPException) as exc:
        _run(sponsors._require_event_manage(str(oid), {"_id": 7, "is_admin": False}))
    assert exc.value.status_code == 403


def test_ownership_compares_as_strings(monkeypatch):
    """ObjectId stored vs string user id must still match; the reverse mismatch
    is the bug _can_manage_event was hardened against."""
    oid = ObjectId()
    creator = ObjectId()
    _with_event(monkeypatch, {"_id": oid, "created_by": creator})
    got, _ = _run(
        sponsors._require_event_manage(str(oid), {"_id": str(creator), "is_admin": False})
    )
    assert got == oid


def test_missing_event_is_404(monkeypatch):
    _with_event(monkeypatch, None)
    with pytest.raises(HTTPException) as exc:
        _run(sponsors._require_event_manage(str(ObjectId()), {"_id": 7}))
    assert exc.value.status_code == 404


def test_malformed_event_id_is_400(monkeypatch):
    _with_event(monkeypatch, {"_id": 1})
    with pytest.raises(HTTPException) as exc:
        _run(sponsors._require_event_manage("not-an-object-id", {"_id": 7}))
    assert exc.value.status_code == 400


def test_sponsor_writes_are_no_longer_admin_only():
    """Guard against a refactor quietly restoring the admin gate."""
    import inspect

    source = inspect.getsource(sponsors)
    assert "get_current_admin" not in source
    for name in (
        "create_event_sponsor",
        "update_event_sponsor",
        "refresh_event_sponsor",
        "delete_event_sponsor",
    ):
        fn_src = inspect.getsource(getattr(sponsors, name))
        assert "_require_event_manage" in fn_src, f"{name} lost its manage check"
