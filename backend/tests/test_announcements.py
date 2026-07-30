"""Host announcements: read state and input handling.

Run from backend/: python -m pytest tests/test_announcements.py
"""
import asyncio
import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import pytest
from bson import ObjectId

import announcements


class _Col:
    def __init__(self):
        self.docs = {}

    async def insert_one(self, doc):
        oid = ObjectId()
        self.docs[oid] = {**doc, "_id": oid}
        return type("R", (), {"inserted_id": oid})()

    def _match(self, doc, query):
        for k, v in query.items():
            if isinstance(v, dict) and ("$gt" in v or "$gte" in v):
                if not (doc.get(k) and doc[k] >= v.get("$gte", v.get("$gt"))):
                    return False
            elif doc.get(k) != v:
                return False
        return True

    async def find_one(self, query):
        for doc in self.docs.values():
            if self._match(doc, query):
                return doc
        return None

    async def count_documents(self, query):
        return sum(1 for d in self.docs.values() if self._match(d, query))

    def find(self, query):
        rows = [d for d in self.docs.values() if self._match(d, query)]
        col = self

        class _C:
            def sort(self, key, direction=1):
                # Mirrors motor: either sort("field", dir) or a list of
                # (field, dir) pairs. Applied last-key-first so the earlier
                # keys win, which is what a compound sort means.
                keys = key if isinstance(key, list) else [(key, direction)]
                for field, dir_ in reversed(keys):
                    rows.sort(key=lambda d: d.get(field), reverse=dir_ < 0)
                return self

            async def to_list(self, _limit):
                return rows

        return _C()

    async def update_one(self, query, update, upsert=False):
        doc = await self.find_one(query)
        if doc:
            doc.update(update["$set"])
        elif upsert:
            oid = ObjectId()
            self.docs[oid] = {**query, **update["$set"], "_id": oid}

    async def delete_one(self, query):
        for oid, doc in list(self.docs.items()):
            if self._match(doc, query):
                del self.docs[oid]
                return type("R", (), {"deleted_count": 1})()
        return type("R", (), {"deleted_count": 0})()


def _run(coro):
    return asyncio.run(coro)


class _Clock:
    """A clock that advances a second per call.

    These tests are about ordering and read state, and the real clock cannot
    express either reliably: create and mark_read land in the same tick often
    enough to fail intermittently, especially on Windows where the timer
    resolution is around 15ms. Note the production code is deliberately built
    to survive that collision, which is what the ambiguous-tie test below
    covers; this fixture just stops every OTHER test from depending on it.
    """

    def __init__(self):
        self.t = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def now(self, _tz=None):
        self.t += timedelta(seconds=1)
        return self.t


@pytest.fixture(autouse=True)
def _stub(monkeypatch):
    monkeypatch.setattr(announcements, "event_announcements", _Col())
    monkeypatch.setattr(announcements, "announcement_reads", _Col())
    clock = _Clock()
    monkeypatch.setattr(announcements, "datetime", clock)
    return clock


HOST = {"_id": "host-1", "profile": {"name": "Scott Weiss"}}
EVENT = ObjectId()


def test_posting_records_the_author_name():
    out = _run(announcements.create(EVENT, HOST, "Parking", "Use the west lot."))
    assert out["author_name"] == "Scott Weiss"
    assert out["body"] == "Use the west lot."


def test_a_host_with_no_profile_name_still_gets_attribution():
    out = _run(announcements.create(EVENT, {"_id": "h"}, "", "Doors at six."))
    assert out["author_name"] == "The host"


def test_an_empty_announcement_is_refused():
    with pytest.raises(announcements.AnnouncementError):
        _run(announcements.create(EVENT, HOST, "Title only", "   "))


def test_over_long_input_is_trimmed_not_rejected():
    out = _run(announcements.create(EVENT, HOST, "t" * 500, "b" * 9000))
    assert len(out["title"]) <= announcements.MAX_TITLE
    assert len(out["body"]) <= announcements.MAX_BODY


def test_everything_is_unread_until_you_have_looked():
    _run(announcements.create(EVENT, HOST, "", "One"))
    _run(announcements.create(EVENT, HOST, "", "Two"))
    rows = _run(announcements.list_for_event(EVENT, "reader-1"))
    assert len(rows) == 2
    assert all(r["unread"] for r in rows)
    assert _run(announcements.unread_count(EVENT, "reader-1")) == 2


def test_marking_read_clears_the_unread_flag():
    _run(announcements.create(EVENT, HOST, "", "One"))
    _run(announcements.mark_read(EVENT, "reader-1"))
    rows = _run(announcements.list_for_event(EVENT, "reader-1"))
    assert not any(r["unread"] for r in rows)
    assert _run(announcements.unread_count(EVENT, "reader-1")) == 0


def test_something_posted_after_you_looked_is_unread_again():
    _run(announcements.create(EVENT, HOST, "", "Old"))
    _run(announcements.mark_read(EVENT, "reader-1"))
    _run(announcements.create(EVENT, HOST, "", "New"))
    rows = _run(announcements.list_for_event(EVENT, "reader-1"))
    unread = [r for r in rows if r["unread"]]
    assert [r["body"] for r in unread] == ["New"]
    assert _run(announcements.unread_count(EVENT, "reader-1")) == 1


def test_read_state_is_per_reader():
    _run(announcements.create(EVENT, HOST, "", "One"))
    _run(announcements.mark_read(EVENT, "reader-1"))
    assert _run(announcements.unread_count(EVENT, "reader-1")) == 0
    assert _run(announcements.unread_count(EVENT, "reader-2")) == 1


def test_newest_first():
    _run(announcements.create(EVENT, HOST, "", "First"))
    _run(announcements.create(EVENT, HOST, "", "Second"))
    rows = _run(announcements.list_for_event(EVENT, "reader-1"))
    assert rows[0]["body"] == "Second"


def test_announcements_are_scoped_to_their_event():
    other = ObjectId()
    _run(announcements.create(EVENT, HOST, "", "Mine"))
    assert _run(announcements.list_for_event(other, "reader-1")) == []


def test_delete_removes_only_the_named_one():
    a = _run(announcements.create(EVENT, HOST, "", "Keep"))
    b = _run(announcements.create(EVENT, HOST, "", "Remove"))
    assert _run(announcements.delete(EVENT, b["id"])) is True
    remaining = _run(announcements.list_for_event(EVENT, "reader-1"))
    assert [r["body"] for r in remaining] == ["Keep"]


def test_deleting_a_missing_or_malformed_id_is_false_not_an_error():
    assert _run(announcements.delete(EVENT, str(ObjectId()))) is False
    assert _run(announcements.delete(EVENT, "not-an-id")) is False


def test_a_post_in_the_same_instant_as_a_read_counts_as_unread(monkeypatch):
    """The ambiguous tie, pinned deliberately.

    A host posting at the exact moment a reader marks the page read is an
    ordinary collision, not a theoretical one. The two failure directions are
    not equal: counting it as read HIDES the announcement from that reader
    permanently, counting it as unread merely shows a badge for something they
    might already have seen. It must resolve to unread.
    """
    frozen = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)

    class _Frozen:
        @staticmethod
        def now(_tz=None):
            return frozen

    monkeypatch.setattr(announcements, "datetime", _Frozen)
    _run(announcements.mark_read(EVENT, "reader-1"))
    _run(announcements.create(EVENT, HOST, "", "Posted in the same tick"))

    rows = _run(announcements.list_for_event(EVENT, "reader-1"))
    assert rows[0]["unread"] is True
    assert _run(announcements.unread_count(EVENT, "reader-1")) == 1
