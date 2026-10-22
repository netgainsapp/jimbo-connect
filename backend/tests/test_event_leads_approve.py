"""One-button Approve: host account, event, claim token, Signal Scout push,
LinkedIn queue, and the auto-approve hook on ingest.

Mongo is faked per collection. The fakes count inserts and writes so the
idempotency tests can assert that a second Approve touches nothing.

Run from backend/: python -m pytest tests/test_event_leads_approve.py
"""
import asyncio
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from fastapi import HTTPException
from fastapi.testclient import TestClient

import auth
import billing
import core
import event_leads_approve as approve_mod
import event_leads_store
import outreach
import server
from routers import event_leads as route
from routers import events as events_route

client = TestClient(server.app)
BASE = "/api/admin/event-leads"
INGEST_KEY = "test-ingest-key"
NOW = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
ADMIN_ID = ObjectId()
ANCHOR_START = "2026-11-04T18:00:00-07:00"
# The real push, kept before the fixture swaps the module attribute for a fake.
REAL_PUSH = outreach.push_event_lead


def _set_dotted(row, fields):
    for key, value in fields.items():
        head, _, rest = key.partition(".")
        if rest:
            row[head] = {**(row.get(head) or {}), rest: value}
        else:
            row[key] = value


def _get(doc, dotted):
    for part in dotted.split("."):
        doc = doc.get(part) if isinstance(doc, dict) else None
    return doc


def _matches(doc, q):
    """Enough of Mongo's filter language for these tests: equality on dotted
    keys, $ne, $exists, $lt and a top level $or."""
    for key, want in q.items():
        if key == "$or":
            if not any(_matches(doc, sub) for sub in want):
                return False
            continue
        have = _get(doc, key)
        if isinstance(want, dict) and want and all(k.startswith("$") for k in want):
            for op, arg in want.items():
                if op == "$ne" and have == arg:
                    return False
                if op == "$exists" and (have is not None) != arg:
                    return False
                if op == "$lt" and not (have is not None and have < arg):
                    return False
        elif have != want:
            return False
    return True


class _UpdateResult:
    def __init__(self, matched):
        self.matched_count = matched


class _Cursor:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self, _length):
        return [dict(r) for r in self.rows]


class _Leads:
    def __init__(self):
        self.rows = {}
        self.writes = 0
        self.updates = []  # every applied update document, in order
        # A predicate on the update document: that one write raises instead.
        self.fail_when = None

    def add(self, **fields):
        doc = {"_id": ObjectId(), **fields}
        self.rows[doc["_id"]] = doc
        return doc["_id"]

    async def find_one(self, q):
        if "_id" in q:
            row = self.rows.get(q["_id"])
        else:
            row = next((r for r in self.rows.values()
                        if r.get("organizer_key") == q.get("organizer_key")), None)
        return dict(row) if row else None

    def find(self, q):
        return _Cursor(list(self.rows.values()))

    async def replace_one(self, q, doc, upsert=False):
        current = await self.find_one(q)
        doc = {**doc, "_id": current["_id"] if current else ObjectId()}
        self.rows[doc["_id"]] = doc
        self.writes += 1

    async def update_one(self, q, update):
        row = self.rows.get(q["_id"])
        if row is None or not _matches(row, q):
            return _UpdateResult(0)
        if self.fail_when and self.fail_when(update):
            self.fail_when = None
            raise RuntimeError("injected crash")
        self.writes += 1
        self.updates.append(update)
        _set_dotted(row, update.get("$set", {}))
        for key in update.get("$unset", {}):
            row.pop(key, None)
        return _UpdateResult(1)


class _Runs:
    async def insert_one(self, doc):
        return None

    def find(self, q):
        return _Cursor([])


class _Users:
    def __init__(self, *rows):
        self.rows = {r["_id"]: r for r in rows}
        self.inserts = 0

    async def find_one(self, q):
        if "_id" in q:
            return self.rows.get(q["_id"])
        return next((u for u in self.rows.values()
                     if u.get("email") and u.get("email") == q.get("email")), None)

    async def insert_one(self, doc):
        self.inserts += 1
        oid = ObjectId()
        self.rows[oid] = {**doc, "_id": oid}

        class _Result:
            inserted_id = oid
        return _Result()


class _Events:
    def __init__(self):
        self.rows = {}
        self.inserts = 0

    async def find_one(self, q):
        return next((e for e in self.rows.values() if _matches(e, q)), None)

    async def count_documents(self, q):
        return sum(1 for e in self.rows.values() if _matches(e, q))

    async def insert_one(self, doc):
        self.inserts += 1
        oid = ObjectId()
        self.rows[oid] = {**doc, "_id": oid}

        class _Result:
            inserted_id = oid
        return _Result()


class _Flags:
    def __init__(self):
        self.rows = {}

    async def find_one(self, q):
        return self.rows.get(q["_id"])

    async def update_one(self, q, update, upsert=False):
        self.rows[q["_id"]] = {"_id": q["_id"], **update["$set"]}

    async def delete_one(self, q):
        self.rows.pop(q["_id"], None)


class _Push:
    """Stands in for outreach.push_event_lead and records each call."""

    def __init__(self, result=None):
        self.calls = []
        self.result = result or {"ok": True, "prospect_id": "p-1", "outcome": "imported"}

    async def __call__(self, lead, claim_url, now=None):
        self.calls.append((lead, claim_url))
        return dict(self.result)


class Db:
    def __init__(self):
        self.leads, self.users, self.events = _Leads(), _Users(), _Events()
        self.flags, self.push = _Flags(), _Push()


@pytest.fixture
def db(monkeypatch):
    d = Db()
    d.users.rows[ADMIN_ID] = {"_id": ADMIN_ID, "is_admin": True}
    monkeypatch.setenv("EVENT_LEADS_INGEST_KEY", INGEST_KEY)
    monkeypatch.setattr(event_leads_store, "event_leads", d.leads)
    monkeypatch.setattr(event_leads_store, "event_lead_runs", _Runs())
    monkeypatch.setattr(event_leads_store, "app_flags", d.flags)
    for module in (auth, route, approve_mod):
        monkeypatch.setattr(module, "users", d.users)
    for module in (route, approve_mod, events_route):
        monkeypatch.setattr(module, "events", d.events)
    monkeypatch.setattr(approve_mod.outreach, "push_event_lead", d.push)
    client.cookies.clear()
    client.cookies.set(auth.COOKIE_NAME, auth.create_access_token(str(ADMIN_ID)))
    yield d
    client.cookies.clear()


def _anchor(**extra):
    return {
        "source": "revel", "source_event_id": "e1", "title": "Denver Tech Mixer",
        "description": "Talks and drinks.", "start": ANCHOR_START,
        "timezone": "America/Denver", "venue": "Galvanize", "city": "Denver",
        "source_url": "https://revel.example/e1", **extra,
    }


def _contact(email="jane@host.org", linkedin_url=""):
    return {"name": "Jane Doe", "email": email, "linkedin_url": linkedin_url,
            "website": "", "email_status": "verified"}


def _lead_doc(key="meetup:denver-devs", score=94, contact=None, status="new", **extra):
    return {
        "organizer_key": key, "organizer_name": "Denver Devs", "city": "Denver",
        "anchor": _anchor(), "events": [_anchor()],
        "score": {"tier": "A", "score": score, "vertical": "tech"},
        "contact": contact if contact is not None else _contact(),
        "status": status, "signal_scout": {}, "linkedin": {"status": "none"},
        "funnel": {"found_at": NOW}, **extra,
    }


def _approve(lead_id, actor="ingest"):
    return asyncio.run(approve_mod.approve(str(lead_id), actor, NOW))


def _snapshot(d):
    """Everything Approve could change. The lead rows are compared whole, so
    a lease that is taken and released again leaves no trace."""
    rows = {k: dict(v) for k, v in d.leads.rows.items()}
    return (d.users.inserts, d.events.inserts, rows, len(d.push.calls))


# ---------- happy path ----------

def test_approve_creates_host_event_and_claim_then_pushes_once(db):
    lead_id = db.leads.add(**_lead_doc())

    resp = client.post(f"{BASE}/{lead_id}/approve")

    assert resp.status_code == 200
    body = resp.json()
    host = next(u for u in db.users.rows.values() if u.get("email") == "jane@host.org")
    assert host["plan"] == "free" and host["host_origin"] == "event_lead"
    assert host["nurture_enabled"] is False and host["email_verified"] is True
    assert host["is_admin"] is False and host["profile"]["name"] == "Jane Doe"
    assert host["password_hash"]

    event = db.events.rows[ObjectId(body["event_id"])]
    assert event["created_by"] == host["_id"]
    assert event["name"] == "Denver Tech Mixer"
    assert event["location"] == "Galvanize, Denver"
    assert event["industry_tags"] == ["tech"]
    assert event["provenance"] == {
        "source": "revel", "source_url": "https://revel.example/e1",
        "event_lead_id": str(lead_id), "pending_host": False,
    }

    row = db.leads.rows[lead_id]
    token = body["claim_url"].rsplit("/claim/", 1)[1]
    assert body["claim_url"] == f"{core.APP_URL}/claim/{token}"
    assert row["claim_token_hash"] == core._hash_token(token)
    assert token not in str(row.get("claim_token_hash"))
    start = datetime.fromisoformat(ANCHOR_START)
    assert row["claim_expires_at"] == (start + timedelta(days=30)).astimezone(timezone.utc)
    assert row["claim_url"] == body["claim_url"]

    assert len(db.push.calls) == 1
    pushed_lead, pushed_url = db.push.calls[0]
    assert pushed_url == body["claim_url"] and pushed_lead["_id"] == lead_id

    assert row["status"] == "approved" and row["funnel"]["approved_at"] is not None
    assert row["funnel"]["found_at"] == NOW
    assert row["event_id"] == body["event_id"]
    assert row["host_user_id"] == str(host["_id"]) == body["host_user_id"]
    assert row["signal_scout"]["prospect_id"] == "p-1"
    assert row["signal_scout"]["outcome"] == "imported"
    assert body == {
        "status": "approved", "event_id": row["event_id"],
        "host_user_id": row["host_user_id"], "claim_url": row["claim_url"],
        "signal_scout": {"prospect_id": "p-1", "outcome": "imported", "error": None},
    }


def test_an_empty_contact_name_names_the_host_after_the_organizer(db):
    lead_id = db.leads.add(**_lead_doc(contact={**_contact(), "name": ""}))

    body = _approve(lead_id)

    host = db.users.rows[ObjectId(body["host_user_id"])]
    assert host["profile"]["name"] == "Denver Devs"


def test_a_naive_anchor_start_uses_the_anchor_timezone(db):
    doc = _lead_doc()
    doc["anchor"] = {**doc["anchor"], "start": "2026-11-04T18:00:00",
                     "timezone": "America/New_York"}
    lead_id = db.leads.add(**doc)

    _approve(lead_id)

    expires = db.leads.rows[lead_id]["claim_expires_at"]
    assert expires == datetime(2026, 12, 4, 23, 0, tzinfo=timezone.utc)


def test_free_user_without_events_is_reused_as_the_host(db):
    uid = ObjectId()
    db.users.rows[uid] = {"_id": uid, "email": "jane@host.org", "plan": "free"}
    lead_id = db.leads.add(**_lead_doc())

    body = _approve(lead_id)

    assert db.users.inserts == 0
    assert body["host_user_id"] == str(uid)
    assert db.leads.rows[lead_id]["host_user_preexisting"] is True


def test_a_host_approve_created_is_not_marked_preexisting(db):
    lead_id = db.leads.add(**_lead_doc())

    _approve(lead_id)

    assert "host_user_preexisting" not in db.leads.rows[lead_id]


def test_a_resumed_approve_does_not_mark_its_own_new_host_preexisting(db):
    """A crash after the host insert but before the event: the next run finds
    the account this Approve made, which is still not a pre-existing one."""
    lead_id = db.leads.add(**_lead_doc())
    asyncio.run(approve_mod.create_lead_host("jane@host.org", "Jane Doe", NOW))

    _approve(lead_id)

    assert "host_user_preexisting" not in db.leads.rows[lead_id]


def test_an_adopted_event_of_a_reused_host_is_marked_preexisting(db):
    uid = ObjectId()
    db.users.rows[uid] = {"_id": uid, "email": "jane@host.org", "plan": "free"}
    lead_id = db.leads.add(**_lead_doc())
    _crash_on_event_write(db)
    with pytest.raises(RuntimeError):
        _approve(lead_id)

    _approve(lead_id)

    assert db.leads.rows[lead_id]["host_user_preexisting"] is True


def test_contact_with_linkedin_and_email_is_also_queued_for_linkedin(db):
    lead_id = db.leads.add(**_lead_doc(
        contact=_contact(linkedin_url="https://linkedin.com/in/jane")))

    _approve(lead_id)

    row = db.leads.rows[lead_id]
    assert row["linkedin"]["status"] == "queued"
    assert row["linkedin"]["updated_at"] is not None
    assert len(db.push.calls) == 1


# ---------- LinkedIn only ----------

def test_linkedin_only_lead_gets_a_pending_event_and_no_push(db):
    lead_id = db.leads.add(**_lead_doc(
        contact=_contact(email="", linkedin_url="https://linkedin.com/in/jane")))

    body = _approve(lead_id)

    assert db.users.inserts == 0 and db.push.calls == []
    event = db.events.rows[ObjectId(body["event_id"])]
    assert event["created_by"] is None
    assert event["provenance"]["pending_host"] is True
    row = db.leads.rows[lead_id]
    assert row["claim_token_hash"] and body["claim_url"]
    assert row["linkedin"]["status"] == "queued"
    assert row["status"] == "approved" and row["host_user_id"] is None
    assert body["signal_scout"] == {"prospect_id": None, "outcome": None, "error": None}


# ---------- refusals ----------

@pytest.mark.parametrize("user", [
    {"plan": "free", "hosts": True},
    {"plan": "pro", "hosts": False},
])
def test_existing_host_is_409_and_only_marks_the_lead_existing_customer(db, user):
    """Plan Review Focus 2: the lead becomes existing_customer, so the badge
    shows and Approve disables. That one status write is all that happens."""
    uid = ObjectId()
    db.users.rows[uid] = {"_id": uid, "email": "jane@host.org", "plan": user["plan"]}
    if user["hosts"]:
        db.events.rows[ObjectId()] = {"created_by": uid, "join_code": "X"}
    lead_id = db.leads.add(**_lead_doc())
    before = dict(db.leads.rows[lead_id])

    resp = client.post(f"{BASE}/{lead_id}/approve")

    assert resp.status_code == 409
    assert "already" in resp.json()["detail"]
    assert db.users.inserts == 0 and db.events.inserts == 0
    assert db.push.calls == []
    row = db.leads.rows[lead_id]
    # The Approve lease is taken and released around it; nothing else is set.
    lead_writes = [u for u in db.leads.updates
                   if set(u.get("$set", {})) - {"approving_at"}]
    assert [set(u["$set"]) for u in lead_writes] == [
        {"status", "existing_user_id", "updated_at"}]
    assert "approving_at" not in row
    assert row["status"] == "existing_customer"
    assert row["existing_user_id"] == str(uid)
    assert row["updated_at"] is not None
    changed = {k for k in set(row) | set(before) if row.get(k) != before.get(k)}
    assert changed == {"status", "existing_user_id", "updated_at"}
    assert "claim_token_hash" not in row and "event_id" not in row


def test_an_existing_host_lead_is_then_refused_before_any_write(db):
    uid = ObjectId()
    db.users.rows[uid] = {"_id": uid, "email": "jane@host.org", "plan": "pro"}
    lead_id = db.leads.add(**_lead_doc())
    client.post(f"{BASE}/{lead_id}/approve")
    writes = db.leads.writes

    resp = client.post(f"{BASE}/{lead_id}/approve")

    assert resp.status_code == 409
    assert db.leads.writes == writes


@pytest.mark.parametrize("status", ["existing_customer", "archived"])
def test_customer_or_archived_lead_is_409_before_any_write(db, status):
    lead_id = db.leads.add(**_lead_doc(status=status))
    before = _snapshot(db)

    with pytest.raises(HTTPException) as err:
        _approve(lead_id)

    assert err.value.status_code == 409
    assert _snapshot(db) == before


def test_unknown_lead_is_404(db):
    assert client.post(f"{BASE}/{ObjectId()}/approve").status_code == 404
    assert client.post(f"{BASE}/not-an-id/approve").status_code == 404


def test_plan_limit_from_create_event_for_is_409_and_the_lead_is_unchanged(
    db, monkeypatch
):
    monkeypatch.setenv("BILLING_ENFORCED", "true")
    monkeypatch.setattr(billing, "FREE_EVENT_LIMIT", 0)
    lead_id = db.leads.add(**_lead_doc())
    before = dict(db.leads.rows[lead_id])

    resp = client.post(f"{BASE}/{lead_id}/approve")

    assert resp.status_code == 409
    assert resp.json()["detail"].startswith("Your free plan includes 0 events")
    assert db.leads.rows[lead_id] == before
    assert db.events.inserts == 0 and db.push.calls == []


# ---------- Signal Scout failure and retry ----------

class _Resp:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code, self._payload, self.text = status_code, payload, text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def _wire_http(monkeypatch, db, resp):
    import httpx

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            db.push.calls.append((json, url))
            return resp

    monkeypatch.setattr(outreach, "push_event_lead", REAL_PUSH)
    monkeypatch.setattr(outreach, "SIGNAL_SCOUT_URL", "https://ss.test")
    monkeypatch.setattr(outreach, "SIGNAL_SCOUT_API_KEY", "k")
    monkeypatch.setattr(httpx, "AsyncClient", _Client)


def test_signal_scout_500_still_approves_and_records_the_error(db, monkeypatch):
    _wire_http(monkeypatch, db, _Resp(500, text="boom"))
    lead_id = db.leads.add(**_lead_doc())

    body = _approve(lead_id)

    row = db.leads.rows[lead_id]
    assert row["status"] == "approved"
    assert row["signal_scout"]["error"] and "prospect_id" not in row["signal_scout"]
    assert row["signal_scout"]["pushed_at"] is not None
    assert "outcome" in row["signal_scout"]
    assert body["signal_scout"]["error"] == row["signal_scout"]["error"]
    assert ObjectId(row["event_id"]) in db.events.rows


def test_a_rejected_import_keeps_signal_scouts_outcome(db):
    db.push.result = {"ok": False, "outcome": "error", "error": "not imported"}
    lead_id = db.leads.add(**_lead_doc())

    body = _approve(lead_id)

    assert db.leads.rows[lead_id]["signal_scout"]["outcome"] == "error"
    assert body["signal_scout"]["outcome"] == "error"


def test_retry_outreach_pushes_again_only_for_a_failed_push(db):
    db.push.result = {"ok": False, "error": "HTTP 500"}
    lead_id = db.leads.add(**_lead_doc())
    _approve(lead_id)
    db.push.result = {"ok": True, "prospect_id": "p-9", "outcome": "imported"}

    resp = client.post(f"{BASE}/{lead_id}/retry-outreach")

    assert resp.status_code == 200
    assert resp.json()["signal_scout"]["prospect_id"] == "p-9"
    assert db.leads.rows[lead_id]["signal_scout"]["prospect_id"] == "p-9"
    assert "error" not in db.leads.rows[lead_id]["signal_scout"]
    assert db.events.inserts == 1 and len(db.push.calls) == 2
    assert client.post(f"{BASE}/{lead_id}/retry-outreach").status_code == 409


def test_retry_outreach_while_another_run_holds_the_lease_is_409(db):
    db.push.result = {"ok": False, "error": "HTTP 500"}
    lead_id = db.leads.add(**_lead_doc())
    _approve(lead_id)
    db.leads.rows[lead_id]["approving_at"] = datetime.now(timezone.utc)

    assert client.post(f"{BASE}/{lead_id}/retry-outreach").status_code == 409
    assert len(db.push.calls) == 1


def test_retry_outreach_on_a_lead_not_yet_approved_is_409(db):
    lead_id = db.leads.add(**_lead_doc())

    assert client.post(f"{BASE}/{lead_id}/retry-outreach").status_code == 409
    assert db.push.calls == []


# ---------- idempotency ----------

def test_second_approve_returns_the_same_response_and_writes_nothing(db):
    lead_id = db.leads.add(**_lead_doc(
        contact=_contact(linkedin_url="https://linkedin.com/in/jane")))
    first = _approve(lead_id)
    before, writes = _snapshot(db), db.leads.writes

    second = _approve(lead_id)

    assert second == first
    assert _snapshot(db) == before and db.leads.writes == writes
    assert "approving_at" not in db.leads.rows[lead_id]


def _crash_on_event_write(db):
    db.leads.fail_when = lambda update: "event_id" in update.get("$set", {})


def test_a_crash_after_the_event_insert_resumes_with_the_same_event(db):
    lead_id = db.leads.add(**_lead_doc())
    _crash_on_event_write(db)

    with pytest.raises(RuntimeError):
        _approve(lead_id)
    assert db.events.inserts == 1 and "event_id" not in db.leads.rows[lead_id]
    assert "approving_at" not in db.leads.rows[lead_id]

    body = _approve(lead_id)

    assert db.events.inserts == 1 and db.users.inserts == 1
    (event_id,) = db.events.rows
    assert body["event_id"] == str(event_id) and body["status"] == "approved"
    assert body["host_user_id"] == str(db.events.rows[event_id]["created_by"])


def test_a_crashed_linkedin_only_approve_does_not_make_a_second_event(db):
    lead_id = db.leads.add(**_lead_doc(
        contact=_contact(email="", linkedin_url="https://linkedin.com/in/jane")))
    _crash_on_event_write(db)
    with pytest.raises(RuntimeError):
        _approve(lead_id)

    body = _approve(lead_id)

    assert db.events.inserts == 1 and body["host_user_id"] is None


def test_approve_while_another_approve_holds_the_lease_is_409(db):
    lead_id = db.leads.add(**_lead_doc(approving_at=NOW - timedelta(minutes=1)))
    before, writes = _snapshot(db), db.leads.writes

    with pytest.raises(HTTPException) as err:
        _approve(lead_id)

    assert err.value.status_code == 409
    assert err.value.detail == "Approve is already running for this lead"
    assert _snapshot(db) == before and db.leads.writes == writes


def test_a_lease_older_than_five_minutes_is_taken_over(db):
    lead_id = db.leads.add(**_lead_doc(approving_at=NOW - timedelta(minutes=6)))

    assert _approve(lead_id)["status"] == "approved"
    assert "approving_at" not in db.leads.rows[lead_id]


def test_the_claim_write_never_replaces_a_stored_hash(db):
    lead_id = db.leads.add(**_lead_doc(
        claim_token_hash="stored-hash", claim_url="https://app.test/claim/stored"))
    stale = {k: v for k, v in db.leads.rows[lead_id].items()
             if k not in ("claim_token_hash", "claim_url")}

    out = asyncio.run(approve_mod._mint_claim(stale))

    assert db.leads.rows[lead_id]["claim_token_hash"] == "stored-hash"
    assert out["claim_url"] == "https://app.test/claim/stored"


def test_only_events_from_other_leads_make_a_user_an_existing_host(db):
    uid = ObjectId()
    user = {"_id": uid, "email": "jane@host.org", "plan": "free"}
    own = {"created_by": uid, "provenance": {"event_lead_id": "lead-1"}}
    db.events.rows[ObjectId()] = own

    assert asyncio.run(approve_mod._is_existing_host(user, "lead-1")) is False
    assert asyncio.run(approve_mod._is_existing_host(user, "lead-2")) is True


def test_second_approve_after_a_failed_push_does_not_push_again(db):
    db.push.result = {"ok": False, "error": "HTTP 500"}
    lead_id = db.leads.add(**_lead_doc())
    first = _approve(lead_id)
    before = _snapshot(db)

    assert _approve(lead_id) == first
    assert _snapshot(db) == before


# ---------- auto-approve on ingest ----------

def _ingest(*leads):
    payload = {"run": {"week": "2026-10-18"}, "leads": list(leads)}
    headers = {"Authorization": f"Bearer {INGEST_KEY}"}
    return client.post(f"{BASE}/ingest", json=payload, headers=headers)


def _incoming(key, score, email):
    doc = _lead_doc(key=key, score=score, contact=_contact(
        email=email, linkedin_url="" if email else "https://linkedin.com/in/x"))
    return {k: doc[k] for k in
            ("organizer_key", "organizer_name", "city", "anchor", "events", "score", "contact")}


def _status_of(db, key):
    return next(r for r in db.leads.rows.values() if r["organizer_key"] == key)["status"]


def test_auto_approve_absent_means_ingest_approves_nothing(db):
    resp = _ingest(_incoming("a:hi", 99, "a@host.org"))

    assert resp.json()["auto_approved"] == 0
    assert _status_of(db, "a:hi") == "new"
    assert db.events.inserts == 0 and db.push.calls == []


def test_auto_approve_at_90_takes_the_94_with_an_email_only(db):
    db.flags.rows["event_leads_auto_approve_min_score"] = {
        "_id": "event_leads_auto_approve_min_score", "value": 90}

    resp = _ingest(
        _incoming("a:mail", 94, "a@host.org"),
        _incoming("a:linkedin", 94, ""),
        _incoming("a:low", 80, "b@host.org"),
    )

    assert resp.status_code == 200
    assert resp.json()["auto_approved"] == 1 and resp.json()["inserted"] == 3
    assert _status_of(db, "a:mail") == "approved"
    assert _status_of(db, "a:linkedin") == "new"
    assert _status_of(db, "a:low") == "new"
    assert db.events.inserts == 1 and len(db.push.calls) == 1


def test_auto_approve_failure_is_recorded_on_the_lead_and_never_raised(db):
    db.flags.rows["event_leads_auto_approve_min_score"] = {
        "_id": "event_leads_auto_approve_min_score", "value": 90}
    bad = _incoming("a:bad", 94, "a@host.org")
    bad["anchor"] = {**bad["anchor"], "start": "not a date"}

    resp = _ingest(bad)

    assert resp.status_code == 200 and resp.json()["auto_approved"] == 0
    row = next(r for r in db.leads.rows.values() if r["organizer_key"] == "a:bad")
    assert row["status"] == "new" and row["auto_approve_error"]


# ---------- settings ----------

def test_settings_round_trip_and_ride_along_with_the_list(db):
    assert client.get(f"{BASE}/settings").json() == {"auto_approve_min_score": None}

    put = client.put(f"{BASE}/settings", json={"auto_approve_min_score": 85})

    assert put.status_code == 200 and put.json() == {"auto_approve_min_score": 85}
    assert client.get(BASE).json()["settings"] == {"auto_approve_min_score": 85}
    client.put(f"{BASE}/settings", json={"auto_approve_min_score": None})
    assert db.flags.rows == {}


@pytest.mark.parametrize("bad", [-1, 101, "90", 9.5, True])
def test_settings_outside_0_to_100_is_422(db, bad):
    resp = client.put(f"{BASE}/settings", json={"auto_approve_min_score": bad})

    assert resp.status_code == 422 and db.flags.rows == {}


def test_new_routes_require_an_admin(db):
    lead_id = db.leads.add(**_lead_doc())
    client.cookies.clear()

    calls = [
        client.post(f"{BASE}/{lead_id}/approve"),
        client.post(f"{BASE}/{lead_id}/retry-outreach"),
        client.get(f"{BASE}/settings"),
        client.put(f"{BASE}/settings", json={"auto_approve_min_score": 1}),
    ]

    assert [c.status_code for c in calls] == [401] * 4
    assert db.events.inserts == 0 and db.flags.rows == {}


# ---------- create_event_for provenance ----------

def _payload():
    from models import EventCreateRequest
    return EventCreateRequest(name="Mixer", date=ANCHOR_START)


def test_create_event_for_without_a_user_needs_a_pending_host(db):
    with pytest.raises(ValueError):
        asyncio.run(events_route.create_event_for(None, _payload()))
    with pytest.raises(ValueError):
        asyncio.run(events_route.create_event_for(
            None, _payload(), provenance={"pending_host": False}))
    assert db.events.inserts == 0


def test_create_event_for_keeps_its_old_shape_without_provenance(db):
    user = {"_id": ObjectId(), "plan": "pro"}

    out = asyncio.run(events_route.create_event_for(user, _payload()))

    assert "provenance" not in db.events.rows[ObjectId(out["id"])]
    assert out["created_by"] == str(user["_id"])
