"""Pure rules for the event lead engine: merge, first status, sort.

No Mongo, no FastAPI. The merge test that matters most is the second one: a
lead the admin already approved must not have its anchor, score or contact
rewritten by a later weekly run, or the email Scott approved is not the email
that goes out.

Run from backend/: python -m pytest tests/test_event_leads_rules.py
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import event_leads_rules as rules

DENVER = ZoneInfo("America/Denver")
NOW = datetime(2026, 10, 22, 10, 0, tzinfo=DENVER)


def _event(event_id, start="2026-11-04T18:00:00-07:00", title="Denver Tech Mixer"):
    return {
        "source": "revel",
        "source_event_id": event_id,
        "title": title,
        "start": start,
        "timezone": "America/Denver",
    }


def _incoming(**over):
    base = {
        "organizer_key": "meetup:denver-devs",
        "organizer_name": "Denver Devs",
        "organizer_url": "https://www.meetup.com/denver-devs",
        "city": "Denver",
        "events_listed": 2,
        "anchor": _event("e1"),
        "events": [_event("e1"), _event("e2", "2026-11-18T18:00:00-07:00")],
        "score": {"tier": "A", "score": 94, "reason": "mixer"},
        "contact": {
            "name": "Jane Doe",
            "email": "Jane@Host.org",
            "linkedin_url": "",
            "website": "https://host.org",
            "email_status": "verified",
        },
    }
    base.update(over)
    return base


def test_new_doc_is_built_from_incoming():
    doc = rules.merge_ingest(None, _incoming(), NOW)

    assert doc["organizer_key"] == "meetup:denver-devs"
    assert doc["status"] == "new"
    assert doc["events_listed"] == 2
    assert doc["anchor"]["source_event_id"] == "e1"
    assert doc["score"]["tier"] == "A"
    assert doc["contact"]["email"] == "jane@host.org"
    assert doc["linkedin"] == {"status": "none"}
    assert doc["signal_scout"] == {}
    assert doc["funnel"]["found_at"] == NOW
    assert doc["funnel"]["scored_at"] == NOW
    assert doc["created_at"] == NOW and doc["updated_at"] == NOW


def test_new_doc_takes_status_and_user_from_the_matched_user():
    user = {"_id": "u1", "plan": "pro", "hosts_events": False}
    doc = rules.merge_ingest(None, _incoming(), NOW, existing_user=user)

    assert doc["status"] == "existing_customer"
    assert doc["existing_user_id"] == "u1"


def test_approved_doc_keeps_anchor_score_and_contact_but_gains_an_event():
    existing = rules.merge_ingest(None, _incoming(), NOW)
    existing["status"] = "approved"
    later = datetime(2026, 10, 29, 10, 0, tzinfo=DENVER)
    rerun = _incoming(
        anchor=_event("e9", "2026-12-01T18:00:00-07:00", "A different anchor"),
        events=[_event("e1"), _event("e9", "2026-12-01T18:00:00-07:00")],
        score={"tier": "C", "score": 10, "reason": "rescored"},
        contact={"name": "Someone Else", "email": "x@y.org"},
    )

    merged = rules.merge_ingest(existing, rerun, later)

    assert merged["status"] == "approved"
    assert merged["anchor"] == existing["anchor"]
    assert merged["score"] == existing["score"]
    assert merged["contact"] == existing["contact"]
    assert [e["source_event_id"] for e in merged["events"]] == ["e1", "e2", "e9"]
    assert merged["updated_at"] == later
    assert existing["status"] == "approved" and len(existing["events"]) == 2


def test_new_doc_is_replaced_by_a_rerun():
    existing = rules.merge_ingest(None, _incoming(), NOW)
    rerun = _incoming(
        anchor=_event("e9", "2026-12-01T18:00:00-07:00"),
        events=[_event("e9", "2026-12-01T18:00:00-07:00")],
        events_listed=1,
        score={"tier": "B", "score": 70, "reason": "fresh"},
    )

    merged = rules.merge_ingest(existing, rerun, NOW)

    assert merged["anchor"]["source_event_id"] == "e9"
    assert merged["score"]["tier"] == "B"
    assert merged["events_listed"] == 1
    assert merged["created_at"] == existing["created_at"]
    assert merged["funnel"]["found_at"] == existing["funnel"]["found_at"]


def test_identical_rerun_changes_nothing_including_updated_at():
    existing = rules.merge_ingest(None, _incoming(), NOW)
    later = datetime(2026, 10, 29, 10, 0, tzinfo=DENVER)

    merged = rules.merge_ingest(existing, _incoming(), later)

    assert merged == existing


def test_unreachable_lead_becomes_new_once_a_contact_appears():
    bare = _incoming(contact={"name": "", "email": "", "linkedin_url": ""})
    existing = rules.merge_ingest(None, bare, NOW)
    assert existing["status"] == "unreachable"

    merged = rules.merge_ingest(existing, _incoming(), NOW)

    assert merged["status"] == "new"


def test_initial_status_three_cases():
    assert rules.initial_status(_incoming(), None) == "new"
    nobody = _incoming(contact={"email": "", "linkedin_url": ""})
    assert rules.initial_status(nobody, None) == "unreachable"
    host = {"_id": "u", "plan": "free", "hosts_events": True}
    assert rules.initial_status(_incoming(), host) == "existing_customer"


def test_initial_status_paid_plan_is_a_customer_even_with_no_events():
    paid = {"_id": "u", "plan": "pro", "hosts_events": False}
    assert rules.initial_status(_incoming(), paid) == "existing_customer"
    free_no_events = {"_id": "u", "plan": "free", "hosts_events": False}
    assert rules.initial_status(_incoming(), free_no_events) == "new"


def test_user_with_null_plan_counts_as_free():
    user = {"_id": "u", "plan": None, "hosts_events": False}
    assert rules.initial_status(_incoming(), user) == "new"


def test_linkedin_alone_is_reachable():
    li = _incoming(contact={"email": "", "linkedin_url": "https://linkedin.com/in/j"})
    assert rules.initial_status(li, None) == "new"


def test_days_until_counts_denver_calendar_days():
    assert rules.days_until("2026-11-04T18:00:00-07:00", NOW) == 13
    # Same Denver calendar day, late evening UTC of the next day.
    assert rules.days_until("2026-10-22T20:00:00-06:00", NOW) == 0
    # 23:30 Denver on Oct 22 is already Oct 23 in UTC; still day 0 in Denver.
    assert rules.days_until("2026-10-23T05:30:00+00:00", NOW) == 0


def test_sort_puts_a_in_twenty_days_before_b_in_three():
    a_far = {"score": {"tier": "A"}, "anchor": {"start": "2026-11-11T18:00:00-07:00"}}
    b_near = {"score": {"tier": "B"}, "anchor": {"start": "2026-10-25T18:00:00-06:00"}}
    a_near = {"score": {"tier": "A"}, "anchor": {"start": "2026-10-30T18:00:00-06:00"}}

    ordered = sorted(
        [b_near, a_far, a_near], key=lambda d: rules.tier_sort_key(d, NOW)
    )

    assert ordered == [a_near, a_far, b_near]
    assert rules.tier_sort_key(a_far, NOW) == (0, 20)
    assert rules.tier_sort_key(b_near, NOW) == (1, 3)
