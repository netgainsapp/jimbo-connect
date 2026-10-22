"""Nightly Signal Scout status poll, funnel timestamps and the KPI strip.

Mongo and Signal Scout are faked. The poll must fill the funnel with the first
value it sees, roll an unclaimed pre-built event to a new anchor, stamp
`event_passed_at` and `converted_at` from our own data, and keep going when one
chunk of the status call fails.

Run from backend/: python -m pytest tests/test_event_leads_poll.py
"""
import asyncio
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

import attendee_import
import core
import event_leads_poll as poll
import event_leads_rules as rules
import event_leads_store
import outreach
import server

client = TestClient(server.app)
NOW = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
ANCHOR_START = "2026-11-04T18:00:00-07:00"
SECRET = "tick-secret"
EMAIL = "jane@host.org"


def _run(coro):
    return asyncio.run(coro)


# ---------- fakes ----------

def _get(doc, dotted):
    for part in dotted.split("."):
        doc = doc.get(part) if isinstance(doc, dict) else None
    return doc


def _matches(doc, q):
    for key, want in q.items():
        have = _get(doc, key)
        if isinstance(want, dict) and want and all(k.startswith("$") for k in want):
            for op, arg in want.items():
                if op == "$exists" and (have is not None) != arg:
                    return False
                if op == "$nin" and have in arg:
                    return False
                if op == "$ne" and have == arg:
                    return False
                if op == "$gte" and not (have is not None and have >= arg):
                    return False
        elif have != want:
            return False
    return True


def _set_dotted(row, fields):
    for key, value in fields.items():
        head, _, rest = key.partition(".")
        if rest:
            row[head] = {**(row.get(head) or {}), rest: value}
        else:
            row[key] = value


class _Cursor:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self, _length):
        return [dict(r) for r in self.rows]


class _Result:
    def __init__(self, matched):
        self.matched_count = matched


class _Table:
    """Rows keyed by `_id` with the few Mongo calls the code under test uses."""

    def __init__(self):
        self.rows = {}
        self.queries = []

    def add(self, **fields):
        doc = {"_id": ObjectId(), **fields}
        self.rows[doc["_id"]] = doc
        return doc["_id"]

    def find(self, q=None):
        self.queries.append(q or {})
        return _Cursor([r for r in self.rows.values() if _matches(r, q or {})])

    async def find_one(self, q):
        row = next((r for r in self.rows.values() if _matches(r, q)), None)
        return dict(row) if row else None

    async def count_documents(self, q):
        return sum(1 for r in self.rows.values() if _matches(r, q))

    async def update_one(self, q, update):
        row = next((r for r in self.rows.values() if _matches(r, q)), None)
        if row is None:
            return _Result(0)
        _set_dotted(row, update.get("$set", {}))
        return _Result(1)


@pytest.fixture
def db(monkeypatch):
    tables = type("DB", (), {})()
    tables.leads, tables.events, tables.users = _Table(), _Table(), _Table()
    tables.runs = _Table()
    monkeypatch.setattr(event_leads_store, "event_leads", tables.leads)
    monkeypatch.setattr(event_leads_store, "event_lead_runs", tables.runs)
    monkeypatch.setattr(poll, "events", tables.events)
    monkeypatch.setattr(poll, "users", tables.users)
    return tables


def _event(db, **extra):
    return db.events.add(
        name="Denver Tech Mixer", date=datetime(2026, 11, 5, 1, 0), created_by=None,
        provenance={"event_lead_id": "x", "pending_host": True}, **extra,
    )


def _lead(db, prospect="p1", event_oid=None, **extra):
    fields = {
        "organizer_key": f"k:{ObjectId()}",
        "status": "approved",
        "contact": {"email": EMAIL},
        "anchor": {"title": "Denver Tech Mixer", "start": ANCHOR_START},
        "signal_scout": {"prospect_id": prospect},
        "funnel": {"approved_at": NOW - timedelta(days=3)},
        "event_id": str(event_oid) if event_oid else None,
        **extra,
    }
    return db.leads.add(**fields)


def _status(prospect_id, **fields):
    return {"prospect_id": prospect_id, **fields}


@pytest.fixture
def scout(monkeypatch):
    """Replaces outreach.fetch_status; `calls` records each chunk's ids."""
    state = type("Scout", (), {})()
    state.calls, state.prospects, state.fail_on = [], {}, set()

    async def fake(prospect_ids):
        state.calls.append(list(prospect_ids))
        if len(state.calls) in state.fail_on:
            return {"ok": False, "error": "Signal Scout returned HTTP 503"}
        found = [state.prospects[i] for i in prospect_ids if i in state.prospects]
        return {"ok": True, "prospects": found}

    monkeypatch.setattr(outreach, "fetch_status", fake)
    return state


# ---------- funnel_updates, pure ----------

def test_funnel_updates_maps_every_signal_scout_field():
    lead = {"funnel": {}, "signal_scout": {"prospect_id": "p1"}}
    prospect = _status(
        "p1", sent_at="2026-10-19T15:00:00Z", opened_at="2026-10-19T16:00:00Z",
        clicked_at="2026-10-20T10:00:00Z", replied_at="2026-10-20T11:00:00Z",
        bounced_at="2026-10-20T12:00:00Z", unsubscribed_at="2026-10-20T13:00:00Z",
        next_step_at="2026-10-25T15:00:00Z",
    )

    got = poll.funnel_updates(lead, prospect)

    assert got == {
        "funnel.emailed_at": datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc),
        "funnel.opened_at": datetime(2026, 10, 19, 16, 0, tzinfo=timezone.utc),
        "funnel.clicked_at": datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc),
        "funnel.replied_at": datetime(2026, 10, 20, 11, 0, tzinfo=timezone.utc),
        "funnel.bounced_at": datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc),
        "funnel.unsubscribed_at": datetime(2026, 10, 20, 13, 0, tzinfo=timezone.utc),
        "signal_scout.next_step_at": datetime(2026, 10, 25, 15, 0, tzinfo=timezone.utc),
    }


def test_funnel_updates_first_occurrence_wins_and_nulls_are_skipped():
    first = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)
    lead = {"funnel": {"emailed_at": first}, "signal_scout": {"next_step_at": first}}
    prospect = _status(
        "p1", sent_at="2026-10-19T15:00:00Z", opened_at=None, clicked_at="",
        next_step_at="2026-10-25T15:00:00Z",
    )

    assert poll.funnel_updates(lead, prospect) == {}


def test_funnel_updates_skips_an_unreadable_timestamp():
    prospect = _status("p1", sent_at="not a date", opened_at="2026-10-19T16:00:00Z")

    got = poll.funnel_updates({"funnel": {}}, prospect)

    assert list(got) == ["funnel.opened_at"]


# ---------- poll_status: funnel, chunking, errors ----------

def test_poll_fills_funnel_from_status_and_stamps_polled_at(db, scout):
    oid = _lead(db, "p1")
    scout.prospects["p1"] = _status(
        "p1", sent_at="2026-10-19T15:00:00Z", opened_at="2026-10-19T16:00:00Z"
    )

    result = _run(poll.poll_status(NOW))

    row = db.leads.rows[oid]
    assert row["funnel"]["emailed_at"] == datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)
    assert row["funnel"]["opened_at"] == datetime(2026, 10, 19, 16, 0, tzinfo=timezone.utc)
    assert row["funnel"]["approved_at"] == NOW - timedelta(days=3)
    assert row["signal_scout"]["polled_at"] == NOW
    assert row["signal_scout"]["prospect_id"] == "p1"
    assert (result["polled"], result["updated"], result["errors"]) == (1, 1, [])


def test_poll_does_not_overwrite_an_earlier_value(db, scout):
    first = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)
    oid = _lead(db, "p1", funnel={"emailed_at": first})
    scout.prospects["p1"] = _status("p1", sent_at="2026-10-19T15:00:00Z")

    result = _run(poll.poll_status(NOW))

    assert db.leads.rows[oid]["funnel"]["emailed_at"] == first
    assert result["updated"] == 0


def test_poll_only_selects_approved_unclaimed_unarchived_leads_with_a_prospect(db, scout):
    wanted = _lead(db, "p-ok")
    _lead(db, "p-new", status="new")
    _lead(db, "p-claimed", funnel={"claimed_at": NOW})
    _lead(db, "p-archived", archived_at=NOW)
    _lead(db, None, signal_scout={})
    _lead(db, "", signal_scout={"prospect_id": ""})
    scout.prospects["p-ok"] = _status("p-ok")

    _run(poll.poll_status(NOW))

    assert scout.calls == [["p-ok"]]
    assert db.leads.rows[wanted]["signal_scout"]["polled_at"] == NOW


def test_poll_asks_in_chunks_of_200(db, scout):
    for n in range(450):
        _lead(db, f"p{n}")

    _run(poll.poll_status(NOW))

    assert [len(c) for c in scout.calls] == [200, 200, 50]
    assert sorted(i for c in scout.calls for i in c) == sorted(f"p{n}" for n in range(450))


def test_a_failed_chunk_is_recorded_and_the_loop_continues(db, scout):
    for n in range(250):
        _lead(db, f"p{n}", organizer_name=f"o{n}")
    scout.fail_on = {1}
    for n in range(250):
        scout.prospects[f"p{n}"] = _status(f"p{n}", sent_at="2026-10-19T15:00:00Z")

    result = _run(poll.poll_status(NOW))

    assert len(scout.calls) == 2
    assert len(result["errors"]) == 1
    assert "503" in result["errors"][0] and "@" not in result["errors"][0]
    assert result["polled"] == len(scout.calls[1])
    stamped = [r for r in db.leads.rows.values() if (r.get("funnel") or {}).get("emailed_at")]
    assert len(stamped) == len(scout.calls[1])


def test_poll_survives_a_crashing_fetch(db, monkeypatch):
    _lead(db, "p1")

    async def boom(_ids):
        raise RuntimeError(f"upstream said {EMAIL}")

    monkeypatch.setattr(outreach, "fetch_status", boom)

    result = _run(poll.poll_status(NOW))

    assert len(result["errors"]) == 1
    assert EMAIL not in result["errors"][0]


# ---------- anchor roll ----------

ROLLED = {
    "anchor_rolled_since_last_send": True,
    "anchor": {"name": "Denver Tech Mixer, December", "date": "2026-12-02T18:00:00-07:00"},
}


def test_anchor_roll_renames_and_redates_the_unclaimed_event(db, scout):
    event_oid = _event(db)
    oid = _lead(db, "p1", event_oid)
    scout.prospects["p1"] = _status("p1", **ROLLED)

    result = _run(poll.poll_status(NOW))

    event = db.events.rows[event_oid]
    assert event["name"] == "Denver Tech Mixer, December"
    assert event["date"] == datetime(2026, 12, 3, 1, 0, tzinfo=timezone.utc)
    lead = db.leads.rows[oid]
    assert lead["anchor"]["title"] == "Denver Tech Mixer, December"
    assert lead["anchor"]["start"] == "2026-12-02T18:00:00-07:00"
    assert lead["anchor"]["rolled_at"] == NOW
    assert lead["claim_expires_at"] == datetime(2027, 1, 2, 1, 0, tzinfo=timezone.utc)
    assert result["rolled"] == 1


def test_anchor_roll_leaves_a_claimed_event_alone(db, scout):
    event_oid = db.events.add(
        name="Mine now", date=datetime(2026, 11, 5, 1, 0), created_by=ObjectId(),
        provenance={"event_lead_id": "x", "claimed_at": NOW},
    )
    oid = _lead(db, "p1", event_oid)
    scout.prospects["p1"] = _status("p1", **ROLLED)

    result = _run(poll.poll_status(NOW))

    assert db.events.rows[event_oid]["name"] == "Mine now"
    assert db.events.rows[event_oid]["date"] == datetime(2026, 11, 5, 1, 0)
    assert db.leads.rows[oid]["anchor"]["start"] == ANCHOR_START
    assert "rolled_at" not in db.leads.rows[oid]["anchor"]
    assert result["rolled"] == 0


def test_no_roll_when_the_flag_is_off_or_the_date_is_unchanged(db, scout):
    event_oid = _event(db)
    _lead(db, "p1", event_oid)
    _lead(db, "p2", event_oid)
    scout.prospects["p1"] = _status(
        "p1", anchor_rolled_since_last_send=False, anchor=ROLLED["anchor"]
    )
    scout.prospects["p2"] = _status(
        "p2", anchor_rolled_since_last_send=True,
        anchor={"name": "x", "date": ANCHOR_START},
    )

    result = _run(poll.poll_status(NOW))

    assert db.events.rows[event_oid]["name"] == "Denver Tech Mixer"
    assert result["rolled"] == 0


# ---------- event_passed_at ----------

def test_event_passed_at_is_set_for_a_past_anchor_even_without_a_status(db, scout):
    past = _lead(db, "p-past", anchor={"title": "Old", "start": "2026-10-01T18:00:00-06:00"})
    future = _lead(db, "p-future")
    done = datetime(2026, 10, 2, 0, 0, tzinfo=timezone.utc)
    kept = _lead(db, "p-kept", anchor={"title": "Old", "start": "2026-10-01T18:00:00-06:00"},
                 funnel={"event_passed_at": done})

    result = _run(poll.poll_status(NOW))

    assert db.leads.rows[past]["funnel"]["event_passed_at"] == NOW
    assert "event_passed_at" not in db.leads.rows[future]["funnel"]
    assert db.leads.rows[kept]["funnel"]["event_passed_at"] == done
    assert result["passed"] == 1


def test_event_passed_at_uses_the_rolled_anchor(db, scout):
    event_oid = _event(db)
    oid = _lead(db, "p1", event_oid, anchor={"title": "Old", "start": "2026-10-01T18:00:00-06:00"})
    scout.prospects["p1"] = _status("p1", **ROLLED)

    _run(poll.poll_status(NOW))

    assert "event_passed_at" not in db.leads.rows[oid]["funnel"]


# ---------- converted_at ----------

def _host(db, plan="free"):
    return db.users.add(email="host@x.org", plan=plan)


def _claimed(db, host_oid, **extra):
    return db.leads.add(
        organizer_key=f"k:{ObjectId()}", status="claimed", host_user_id=str(host_oid),
        contact={"email": EMAIL}, anchor={"start": ANCHOR_START},
        funnel={"claimed_at": NOW - timedelta(days=1)}, **extra,
    )


def test_converted_when_the_host_has_a_second_event(db, scout):
    host = _host(db)
    db.events.add(created_by=host, name="first")
    db.events.add(created_by=host, name="second")
    oid = _claimed(db, host)

    result = _run(poll.poll_status(NOW))

    assert db.leads.rows[oid]["funnel"]["converted_at"] == NOW
    assert result["converted"] == 1


def test_converted_when_the_host_is_on_a_paid_plan(db, scout):
    host = _host(db, plan="pro")
    db.events.add(created_by=host, name="only")
    oid = _claimed(db, host)

    _run(poll.poll_status(NOW))

    assert db.leads.rows[oid]["funnel"]["converted_at"] == NOW


def test_not_converted_with_one_event_on_the_free_plan(db, scout):
    host = _host(db)
    db.events.add(created_by=host, name="only")
    oid = _claimed(db, host)

    result = _run(poll.poll_status(NOW))

    assert "converted_at" not in db.leads.rows[oid]["funnel"]
    assert result["converted"] == 0


def test_converted_at_keeps_its_first_value(db, scout):
    host = _host(db, plan="pro")
    stamped_at = datetime(2026, 10, 5, tzinfo=timezone.utc)
    oid = db.leads.add(
        organizer_key="k:s", status="claimed", host_user_id=str(host),
        funnel={"claimed_at": NOW, "converted_at": stamped_at},
    )

    _run(poll.poll_status(NOW))

    assert db.leads.rows[oid]["funnel"]["converted_at"] == stamped_at


def test_conversion_is_stamped_when_signal_scout_is_down(db, monkeypatch):
    host = _host(db, plan="pro")
    oid = _claimed(db, host)
    _lead(db, "p1")

    async def down(_ids):
        return {"ok": False, "error": "Signal Scout unreachable (ConnectError)"}

    monkeypatch.setattr(outreach, "fetch_status", down)

    result = _run(poll.poll_status(NOW))

    assert db.leads.rows[oid]["funnel"]["converted_at"] == NOW
    assert len(result["errors"]) == 1


# ---------- attendee import stamps the funnel ----------

class _Row:
    def __init__(self, email):
        self.email, self.name = email, ""
        self.role = self.company = self.industry = ""
        self.bio = self.looking_for = self.phone = self.linkedin = ""


@pytest.fixture
def import_env(monkeypatch):
    class _Users:
        async def find_one(self, q):
            return {"_id": "uid"} if "email" in q else {"plan": "free"}

    class _Attendees:
        async def find_one(self, _q):
            return None

        async def insert_one(self, _doc):
            return None

        async def count_documents(self, _q):
            return 0

    async def none_removed(*_args):
        return set()

    monkeypatch.setattr(attendee_import, "users", _Users())
    monkeypatch.setattr(attendee_import, "event_attendees", _Attendees())
    monkeypatch.setattr(core, "users", _Users())
    monkeypatch.setattr(core, "event_attendees", _Attendees())
    monkeypatch.setattr(attendee_import.invites, "removed_emails", none_removed)
    monkeypatch.setattr(attendee_import.email_send, "is_configured", lambda: False)


def _import(event_doc):
    return _run(attendee_import.import_rows(
        actor={"_id": "host-1", "profile": {}}, rows=[_Row("ava@example.com")],
        event_doc=event_doc, event_oid="evt",
    ))


def test_attendee_import_stamps_the_lead_funnel(db, import_env):
    oid = _lead(db, "p1")
    event = {"_id": "evt", "name": "Dinner", "created_by": "host-1",
             "provenance": {"event_lead_id": str(oid)}}

    result = _import(event)

    assert result["added_to_event"] == 1
    stamp = db.leads.rows[oid]["funnel"]["attendees_uploaded_at"]
    assert isinstance(stamp, datetime)


def test_attendee_import_keeps_the_first_stamp(db, import_env):
    first = datetime(2026, 10, 5, tzinfo=timezone.utc)
    oid = _lead(db, "p1", funnel={"attendees_uploaded_at": first})
    event = {"_id": "evt", "name": "Dinner", "created_by": "host-1",
             "provenance": {"event_lead_id": str(oid)}}

    _import(event)

    assert db.leads.rows[oid]["funnel"]["attendees_uploaded_at"] == first


def test_attendee_import_ignores_events_without_provenance(db, import_env):
    oid = _lead(db, "p1")

    result = _import({"_id": "evt", "name": "Dinner", "created_by": "host-1"})

    assert result["added_to_event"] == 1
    assert "attendees_uploaded_at" not in db.leads.rows[oid]["funnel"]


def test_a_failed_stamp_never_breaks_the_import(db, import_env, monkeypatch):
    async def boom(*_a, **_k):
        raise RuntimeError("mongo down")

    monkeypatch.setattr(event_leads_store, "update_lead_if", boom)
    event = {"_id": "evt", "name": "Dinner", "created_by": "host-1",
             "provenance": {"event_lead_id": str(ObjectId())}}

    result = _import(event)

    assert result["added_to_event"] == 1 and result["errors"] == []


def test_attendee_import_does_not_stamp_when_nobody_was_added(db, import_env):
    oid = _lead(db, "p1")
    event = {"_id": "evt", "name": "Dinner", "created_by": "host-1",
             "provenance": {"event_lead_id": str(oid)}}

    _run(attendee_import.import_rows(
        actor={"_id": "host-1", "profile": {}}, rows=[], event_doc=event, event_oid="evt",
    ))

    assert "attendees_uploaded_at" not in db.leads.rows[oid]["funnel"]


# ---------- kpis, pure ----------

DENVER = rules.DENVER
# Wednesday 2026-10-21; its Denver week starts Monday 2026-10-19.
WEEKS = ["2026-10-19", "2026-10-12", "2026-10-05", "2026-09-28", "2026-09-21"]


def _at(day, hour=12):
    return datetime(2026, 10, day, hour, 0, tzinfo=DENVER)


def _run_row(received_at, ingested, a, b, c=0):
    return {"ingested": ingested, "by_tier": {"A": a, "B": b, "C": c},
            "received_at": received_at}


def test_kpis_returns_five_weekly_rows_newest_first():
    rows = rules.kpis([], [], NOW)

    assert [r["week"] for r in rows] == WEEKS
    assert all(r["ingested"] == 0 and r["qualification_rate"] == 0.0 for r in rows)


def test_kpis_qualification_rate_is_a_plus_b_over_ingested():
    runs = [
        _run_row(_at(20), 100, 10, 20, 70),
        _run_row(_at(21), 100, 5, 5, 90),
        _run_row(_at(14), 212, 31, 58, 123),
    ]

    rows = rules.kpis([], runs, NOW)

    assert rows[0]["ingested"] == 200
    assert rows[0]["qualification_rate"] == round(40 / 200, 3)
    assert rows[1]["ingested"] == 212
    assert rows[1]["qualification_rate"] == round(89 / 212, 3)
    assert rows[2]["qualification_rate"] == 0.0


def test_kpis_counts_each_funnel_timestamp_in_its_denver_week():
    leads = [
        {"funnel": {"approved_at": _at(19, 0), "emailed_at": _at(20), "opened_at": _at(21),
                    "clicked_at": _at(21), "claimed_at": _at(21),
                    "attendees_uploaded_at": _at(21), "converted_at": _at(21)}},
        {"funnel": {"approved_at": _at(18, 23), "emailed_at": _at(13)}},
        {"funnel": {"approved_at": _at(26)}, "status": "archived"},
        {"funnel": {}},
        {},
    ]

    rows = rules.kpis(leads, [], NOW)
    this_week, last_week = rows[0], rows[1]

    assert this_week["approved"] == 1  # Mon 00:00 Denver counts; Sun 23:00 does not
    assert last_week["approved"] == 1
    assert (this_week["emailed"], last_week["emailed"]) == (1, 1)
    for field in ("opened", "clicked", "claimed", "attendees_uploaded", "converted"):
        assert this_week[field] == 1 and last_week[field] == 0


def test_kpis_reads_stored_utc_datetimes_and_ignores_older_weeks():
    old = datetime(2026, 8, 1, tzinfo=timezone.utc)
    naive_utc = datetime(2026, 10, 21, 18, 0)  # how Mongo hands datetimes back
    leads = [{"funnel": {"approved_at": naive_utc, "emailed_at": old}}]

    rows = rules.kpis(leads, [], NOW)

    assert rows[0]["approved"] == 1
    assert sum(r["emailed"] for r in rows) == 0


def test_kpis_ignores_a_run_with_missing_numbers():
    runs = [{"received_at": _at(20)}, {"ingested": None, "by_tier": None, "received_at": _at(20)}]

    assert rules.kpis([], runs, NOW)[0]["qualification_rate"] == 0.0


def test_the_list_route_returns_kpis(db, monkeypatch):
    import auth
    from routers import event_leads as route

    admin = ObjectId()
    people = _Table()
    people.rows[admin] = {"_id": admin, "is_admin": True}
    monkeypatch.setattr(auth, "users", people)
    monkeypatch.setattr(route, "users", people)

    class _NoFlags:
        async def find_one(self, q):
            return None

    monkeypatch.setattr(event_leads_store, "app_flags", _NoFlags())
    db.leads.add(organizer_key="k", status="approved", score={"tier": "C"},
                 anchor={}, funnel={"approved_at": datetime.now(timezone.utc)})
    db.runs.add(received_at=datetime.now(timezone.utc), ingested=10,
                by_tier={"A": 1, "B": 1, "C": 8})
    client.cookies.clear()
    client.cookies.set(auth.COOKIE_NAME, auth.create_access_token(str(admin)))
    try:
        body = client.get("/api/admin/event-leads").json()
    finally:
        client.cookies.clear()

    assert len(body["kpis"]) == 5
    # The only lead is tier C and hidden from the list, yet it still counts.
    assert body["leads"] == []
    assert body["kpis"][0]["approved"] == 1
    assert body["kpis"][0]["ingested"] == 10
    assert body["kpis"][0]["qualification_rate"] == 0.2


# ---------- the tick route ----------

def test_tick_without_the_secret_is_401(monkeypatch):
    monkeypatch.setenv("BLOG_TICK_SECRET", SECRET)

    assert client.post("/api/event-leads/tick").status_code == 401
    wrong = client.post("/api/event-leads/tick", headers={"X-Tick-Secret": "nope"})
    assert wrong.status_code == 401


def test_tick_with_the_secret_runs_the_poll(monkeypatch):
    monkeypatch.setenv("BLOG_TICK_SECRET", SECRET)
    seen = []

    async def fake_poll(now):
        seen.append(now)
        return {"polled": 3, "updated": 2, "rolled": 1, "passed": 0, "errors": []}

    monkeypatch.setattr(poll, "poll_status", fake_poll)

    resp = client.post("/api/event-leads/tick", headers={"X-Tick-Secret": SECRET})

    assert resp.status_code == 200
    assert resp.json()["polled"] == 3
    assert seen and seen[0].tzinfo is not None


# ---------- outreach.fetch_status ----------

class _Resp:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code, self._payload, self.text = status_code, payload, text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class _Client:
    sent = []
    result = None

    def __init__(self, *a, **k):
        _Client.sent.append({"timeout": k.get("timeout")})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, headers=None, params=None):
        _Client.sent[-1].update(url=url, headers=headers, params=params)
        if isinstance(_Client.result, Exception):
            raise _Client.result
        return _Client.result


@pytest.fixture
def wire(monkeypatch):
    _Client.sent, _Client.result = [], None
    monkeypatch.setattr(outreach, "SIGNAL_SCOUT_URL", "https://ss.test")
    monkeypatch.setattr(outreach, "SIGNAL_SCOUT_API_KEY", "key-123")
    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    return _Client


def test_fetch_status_sends_bearer_and_ids_and_returns_prospects(wire):
    wire.result = _Resp(200, {"prospects": [{"prospect_id": "a"}, {"prospect_id": "b"}]})

    got = _run(outreach.fetch_status(["a", "b"]))

    assert got == {"ok": True, "prospects": [{"prospect_id": "a"}, {"prospect_id": "b"}]}
    sent = wire.sent[0]
    assert sent["url"] == "https://ss.test/api/intro-connect/status"
    assert sent["params"] == {"prospect_ids": "a,b"}
    assert sent["headers"] == {"Authorization": "Bearer key-123"}
    assert sent["timeout"] == 30


def test_fetch_status_never_raises(wire, monkeypatch, capsys):
    wire.result = httpx.ConnectError(f"cannot reach {EMAIL}")
    assert _run(outreach.fetch_status(["a"]))["ok"] is False

    wire.result = _Resp(500, text=f"boom for {EMAIL}")
    bad_status = _run(outreach.fetch_status(["a"]))
    assert bad_status["ok"] is False and "500" in bad_status["error"]

    wire.result = _Resp(200, None)
    assert _run(outreach.fetch_status(["a"]))["ok"] is False

    wire.result = _Resp(200, {"prospects": "nope"})
    assert _run(outreach.fetch_status(["a"]))["ok"] is False

    assert EMAIL not in capsys.readouterr().err

    monkeypatch.setattr(outreach, "SIGNAL_SCOUT_API_KEY", "")
    assert _run(outreach.fetch_status(["a"])) == {
        "ok": False, "error": "Signal Scout is not configured",
    }
