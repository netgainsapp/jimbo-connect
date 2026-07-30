"""Attendee caps: Free 50, Starter 250, Pro 2000, keyed off the host's plan.

Run from backend/: python -m pytest tests/test_attendee_limits.py
"""
import asyncio
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")
os.environ.setdefault("BILLING_ENFORCED", "true")

import pytest
from fastapi import HTTPException

import billing
import core


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# The limits themselves
# ---------------------------------------------------------------------------

def test_limits_match_what_the_pricing_page_advertises():
    assert billing.attendee_limit_for({"plan": "free"}) == 50
    assert billing.attendee_limit_for({"plan": "starter"}) == 250
    assert billing.attendee_limit_for({"plan": "pro"}) == 2000


def test_no_plan_is_treated_as_free():
    assert billing.attendee_limit_for({}) == billing.FREE_ATTENDEE_LIMIT


def test_admins_are_uncapped():
    assert billing.attendee_limit_for({"is_admin": True, "plan": "free"}) is None


def test_nobody_is_capped_when_billing_enforcement_is_off(monkeypatch):
    monkeypatch.setenv("BILLING_ENFORCED", "false")
    assert billing.attendee_limit_for({"plan": "free"}) is None


# ---------------------------------------------------------------------------
# The shared gate, which every add path goes through
# ---------------------------------------------------------------------------

def _patch(monkeypatch, host, count):
    class _Users:
        async def find_one(self, _q):
            return host

    class _Attendees:
        async def count_documents(self, _q):
            return count

    monkeypatch.setattr(core, "users", _Users())
    monkeypatch.setattr(core, "event_attendees", _Attendees())
    return {"_id": "evt", "created_by": "host-1"}


def test_room_below_the_cap_is_allowed(monkeypatch):
    event = _patch(monkeypatch, {"plan": "free"}, count=49)
    _run(core.assert_event_has_room(event))  # must not raise


def test_the_seat_that_exactly_fills_the_cap_is_allowed(monkeypatch):
    """Off-by-one guard: at 49 of 50, the 50th person still gets in."""
    event = _patch(monkeypatch, {"plan": "free"}, count=49)
    _run(core.assert_event_has_room(event, adding=1))


def test_one_past_the_cap_is_refused(monkeypatch):
    event = _patch(monkeypatch, {"plan": "free"}, count=50)
    with pytest.raises(HTTPException) as exc:
        _run(core.assert_event_has_room(event))
    assert exc.value.status_code == 403


def test_a_batch_that_would_overflow_is_refused(monkeypatch):
    event = _patch(monkeypatch, {"plan": "free"}, count=45)
    _run(core.assert_event_has_room(event, adding=5))
    with pytest.raises(HTTPException):
        _run(core.assert_event_has_room(event, adding=6))


def test_the_cap_follows_the_host_plan_not_the_joiner(monkeypatch):
    """A Pro host's event holds 2000 no matter who is joining."""
    event = _patch(monkeypatch, {"plan": "pro"}, count=500)
    _run(core.assert_event_has_room(event))
    event = _patch(monkeypatch, {"plan": "free"}, count=500)
    with pytest.raises(HTTPException):
        _run(core.assert_event_has_room(event))


def test_an_admin_hosted_event_is_never_full(monkeypatch):
    event = _patch(monkeypatch, {"is_admin": True}, count=100_000)
    _run(core.assert_event_has_room(event))


def test_a_missing_host_does_not_lock_guests_out(monkeypatch):
    """An event with no resolvable host is a data problem, not the guest's."""
    event = _patch(monkeypatch, None, count=10_000)
    _run(core.assert_event_has_room(event))
    assert _run(core.attendee_room(event)) == (None, 0)


def test_a_guest_facing_message_can_be_supplied(monkeypatch):
    """The person hitting the join cap cannot upgrade anything; it is the
    host's plan, so the wording must not tell them to."""
    event = _patch(monkeypatch, {"plan": "free"}, count=50)
    with pytest.raises(HTTPException) as exc:
        _run(core.assert_event_has_room(event, message="This event is full."))
    assert exc.value.detail == "This event is full."
    assert "upgrade" not in exc.value.detail.lower()


# ---------------------------------------------------------------------------
# A cap enforced on only some paths is not a cap
# ---------------------------------------------------------------------------

def test_every_attendee_insert_path_is_guarded():
    """Fails if someone adds a new way to insert an attendee without going
    through the cap. Seed data is exempt: it is not a user-facing path."""
    import re
    from pathlib import Path

    backend = Path(__file__).parent.parent
    offenders = []
    for path in list((backend / "routers").glob("*.py")) + [backend / "core.py"]:
        source = path.read_text(encoding="utf-8")
        for match in re.finditer(r"event_attendees\.insert_one", source):
            window = source[max(0, match.start() - 1600):match.start()]
            guarded = (
                "assert_event_has_room" in window
                or "attendee_limit" in window
                or "seed" in window.lower()
            )
            if not guarded:
                line = source[: match.start()].count("\n") + 1
                offenders.append(f"{path.name}:{line}")
    assert not offenders, (
        "attendee inserts with no capacity check nearby: " + ", ".join(offenders)
    )
