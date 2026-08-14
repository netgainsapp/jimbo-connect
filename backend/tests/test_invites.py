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


# ---------- send_event_invites: honest reporting + retry safety ----------
#
# A send that fails must not leave the invite state claiming it succeeded. The
# 24h anti-abuse window is keyed on invited_at, so writing that stamp before the
# send lands means one failed attempt locks the address out of any retry.

import asyncio
from datetime import datetime, timedelta, timezone

import invites as invites_mod


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    async def to_list(self, _n):
        return list(self._rows)


class _FakeInvites:
    """In-memory stand-in for the event_invites collection."""

    def __init__(self):
        self.docs = []

    def find(self, query, _projection=None):
        wanted = set(query.get("email", {}).get("$in", []))
        gte = (query.get("invited_at") or {}).get("$gte")
        return _FakeCursor([
            d
            for d in self.docs
            if d["email"] in wanted
            and d.get("invited_at") is not None
            and (gte is None or d["invited_at"] >= gte)
        ])

    async def update_one(self, query, update, upsert=False):
        doc = next(
            (
                d
                for d in self.docs
                if d.get("event_id") == query.get("event_id")
                and d.get("email") == query.get("email")
            ),
            None,
        )
        if doc is None:
            if not upsert:
                return
            doc = dict(update.get("$setOnInsert", {}))
            self.docs.append(doc)
        doc.update(update.get("$set", {}))


class _StubEmail:
    """Stands in for the email_send module. Results are consumed one per send."""

    def __init__(self, results):
        self._results = list(results)
        self.sent_to = []

    def is_configured(self):
        return True

    async def send_branded(self, *, to, **_kw):
        self.sent_to.append(to)
        return self._results.pop(0) if self._results else {"sent": True}


_EVENT = {"_id": "evt1", "join_code": "ABC123", "name": "Denver Founders Dinner"}


def _wire(monkeypatch, results):
    fake = _FakeInvites()
    stub = _StubEmail(results)
    monkeypatch.setattr(invites_mod, "event_invites", fake)
    monkeypatch.setattr(invites_mod, "email_send", stub)
    return fake, stub


def _invite(emails):
    return asyncio.run(invites_mod.send_event_invites(_EVENT, emails, "Eric"))


def test_failed_send_writes_no_invite_record(monkeypatch):
    fake, _ = _wire(monkeypatch, [{"sent": False, "reason": "domain not verified"}])
    res = _invite(["a@x.com"])
    assert res["sent"] == 0
    assert res["failed"] == 1
    assert fake.docs == []


def test_failed_send_does_not_block_a_retry(monkeypatch):
    _, stub = _wire(monkeypatch, [{"sent": False, "reason": "boom"}, {"sent": True}])
    _invite(["a@x.com"])
    res = _invite(["a@x.com"])
    assert res["sent"] == 1
    assert res["skipped_recent"] == 0
    assert stub.sent_to == ["a@x.com", "a@x.com"]


def test_successful_send_blocks_a_resend_within_24h(monkeypatch):
    _, stub = _wire(monkeypatch, [{"sent": True}, {"sent": True}])
    _invite(["a@x.com"])
    res = _invite(["a@x.com"])
    assert res["skipped_recent"] == 1
    assert res["invited"] == 0
    assert stub.sent_to == ["a@x.com"]  # the second call mailed nobody


def test_resend_after_the_window_moves_it_forward(monkeypatch):
    # Without this the stamp only ever gets written on insert, so an address
    # invited once is never protected again.
    fake, _ = _wire(monkeypatch, [{"sent": True}])
    stale = datetime.now(timezone.utc) - timedelta(hours=48)
    fake.docs.append({
        "event_id": "evt1",
        "email": "a@x.com",
        "invited_at": stale,
        "joined_at": None,
        "reminder_step": 0,
    })
    _invite(["a@x.com"])
    assert fake.docs[0]["invited_at"] > stale


def test_successful_send_keeps_the_reminder_state_it_creates(monkeypatch):
    fake, _ = _wire(monkeypatch, [{"sent": True}])
    _invite(["a@x.com"])
    doc = fake.docs[0]
    assert doc["joined_at"] is None
    assert doc["reminder_step"] == 0
    assert doc["email"] == "a@x.com"


def test_failures_are_aggregated_by_reason(monkeypatch):
    _wire(monkeypatch, [
        {"sent": False, "reason": "suppressed"},
        {"sent": False, "reason": "suppressed"},
        {"sent": False, "reason": "domain not verified"},
        {"sent": True},
    ])
    res = _invite(["a@x.com", "b@x.com", "c@x.com", "d@x.com"])
    assert res["sent"] == 1
    assert res["failed"] == 3
    assert res["failures"] == {"suppressed": 2, "domain not verified": 1}


def test_failure_reasons_stay_bounded(monkeypatch):
    # Resend echoes the request back in some errors, so the reason is not a
    # closed set. The summary must not grow with the size of the send.
    _wire(monkeypatch, [{"sent": False, "reason": f"reason {i}"} for i in range(12)])
    res = _invite([f"u{i}@x.com" for i in range(12)])
    assert res["failed"] == 12
    assert len(res["failures"]) <= 6
    assert sum(res["failures"].values()) == 12


def test_missing_reason_still_counts(monkeypatch):
    _wire(monkeypatch, [{"sent": False}])
    res = _invite(["a@x.com"])
    assert res["failed"] == 1
    assert sum(res["failures"].values()) == 1
