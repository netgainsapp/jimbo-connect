"""The claim link: GET previews the pre-built event, POST signs the host in and
marks the lead claimed. Signal Scout hears about the first claim only.

Mongo is faked per collection with a generic fake that counts writes, so the
expired, unknown and second-completion tests can assert nothing changed.

Run from backend/: python -m pytest tests/test_claim.py
"""
import asyncio
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

import auth
import billing
import core
import event_leads_approve
import event_leads_claim
import event_leads_store
import outreach
import rate_limit
import server
from tests.test_event_leads_approve import _Resp, _UpdateResult, _matches, _set_dotted

client = TestClient(server.app)
TOKEN = "claim-token-abc"
HOST_EMAIL = "jane@host.org"
EVENT_DATE = datetime(2026, 11, 5, 1, 0)


class _Coll:
    """Enough of a Motor collection for the claim flow."""

    def __init__(self):
        self.rows = {}
        self.writes = 0
        self.inserts = 0

    def add(self, **fields):
        doc = {"_id": ObjectId(), **fields}
        self.rows[doc["_id"]] = doc
        return doc["_id"]

    async def find_one(self, q):
        row = next((r for r in self.rows.values() if _matches(r, q)), None)
        return dict(row) if row else None

    async def count_documents(self, q):
        return sum(1 for r in self.rows.values() if _matches(r, q))

    async def insert_one(self, doc):
        self.inserts += 1
        oid = ObjectId()
        self.rows[oid] = {**doc, "_id": oid}

        class _Result:
            inserted_id = oid
        return _Result()

    async def update_one(self, q, update):
        row = next((r for r in self.rows.values() if _matches(r, q)), None)
        if row is None:
            return _UpdateResult(0)
        self.writes += 1
        _set_dotted(row, update.get("$set", {}))
        return _UpdateResult(1)


class _Notify:
    def __init__(self):
        self.calls = []

    async def __call__(self, lead):
        self.calls.append(lead)
        return {"ok": True, "skipped": 0}


class Db:
    def __init__(self):
        self.leads, self.users, self.events = _Coll(), _Coll(), _Coll()
        self.notify = _Notify()

    def writes(self):
        return (self.leads.writes, self.users.writes, self.events.writes,
                self.users.inserts, self.events.inserts)


@pytest.fixture
def db(monkeypatch):
    d = Db()
    monkeypatch.setattr(event_leads_store, "event_leads", d.leads)
    for module in (auth, event_leads_claim, event_leads_approve):
        monkeypatch.setattr(module, "users", d.users)
    monkeypatch.setattr(event_leads_claim, "events", d.events)
    monkeypatch.setattr(outreach, "notify_claimed", d.notify)
    rate_limit._hits.clear()
    client.cookies.clear()
    yield d
    rate_limit._hits.clear()
    client.cookies.clear()


def _future():
    return datetime.now(timezone.utc) + timedelta(days=20)


def _host(d, **extra):
    return d.users.add(email=HOST_EMAIL, profile={"name": "Jane Doe"}, plan="free",
                       is_admin=False, host_origin="event_lead", **extra)


def _event(d, host_id, pending=False):
    return d.events.add(
        name="Denver Tech Mixer", date=EVENT_DATE, location="Galvanize, Denver",
        created_by=host_id,
        provenance={"source": "revel", "source_url": "https://revel.example/e1",
                    "event_lead_id": "lead", "pending_host": pending},
    )


def _lead(d, host_id, event_id, *, expires=None, status="approved", email=HOST_EMAIL):
    return d.leads.add(
        organizer_key="meetup:denver-devs", organizer_name="Denver Devs",
        contact={"name": "Jane Doe", "email": email,
                 "linkedin_url": "" if email else "https://linkedin.com/in/jane"},
        status=status, event_id=str(event_id),
        host_user_id=str(host_id) if host_id else None,
        claim_token_hash=core._hash_token(TOKEN),
        claim_expires_at=expires or _future(),
        claim_url=f"{core.APP_URL}/claim/{TOKEN}",
        signal_scout={"prospect_id": "p-1"} if email else {},
        funnel={"found_at": datetime(2026, 10, 1, tzinfo=timezone.utc)},
    )


def _hosted(d, **extra):
    host_id = _host(d, **extra)
    event_id = _event(d, host_id)
    return host_id, event_id, _lead(d, host_id, event_id)


def _pending(d):
    event_id = _event(d, None, pending=True)
    return event_id, _lead(d, None, event_id, email="")


def _set_cookie(resp):
    return resp.headers.get("set-cookie") or ""


# ---------- GET: preview only ----------

def test_a_valid_link_previews_the_event_and_host_without_signing_in(db):
    _, event_id, _ = _hosted(db)

    resp = client.get(f"/api/claim/{TOKEN}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "ok"
    assert body["event"]["id"] == str(event_id)
    assert body["event"]["name"] == "Denver Tech Mixer"
    assert body["event"]["location"] == "Galvanize, Denver"
    assert body["event"]["date"].startswith("2026-11-05")
    assert body["host"] == {"name": "Jane Doe"}
    assert "@" not in resp.text
    assert auth.COOKIE_NAME not in _set_cookie(resp)
    assert db.writes() == (0, 0, 0, 0, 0)


def test_a_pending_host_link_asks_for_an_email(db):
    _pending(db)

    resp = client.get(f"/api/claim/{TOKEN}")

    body = resp.json()
    assert body["state"] == "needs_email"
    assert body["host"] == {"name": "Jane Doe"}
    assert body["event"]["name"] == "Denver Tech Mixer"
    assert db.writes() == (0, 0, 0, 0, 0)


def test_an_unknown_link_says_unknown(db):
    _hosted(db)

    assert client.get("/api/claim/not-a-real-token").json() == {"state": "unknown"}
    resp = client.post("/api/claim/not-a-real-token", json={})
    assert resp.status_code == 404 and resp.json() == {"state": "unknown"}
    assert auth.COOKIE_NAME not in _set_cookie(resp)
    assert db.writes() == (0, 0, 0, 0, 0) and db.notify.calls == []


def test_an_archived_lead_behaves_as_unknown(db):
    host_id = _host(db)
    _lead(db, host_id, _event(db, host_id), status="archived")

    assert client.get(f"/api/claim/{TOKEN}").json() == {"state": "unknown"}
    assert client.post(f"/api/claim/{TOKEN}", json={}).status_code == 404


def test_an_expired_link_says_expired_and_writes_nothing(db):
    host_id = _host(db)
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    _lead(db, host_id, _event(db, host_id), expires=past)

    assert client.get(f"/api/claim/{TOKEN}").json() == {"state": "expired"}
    resp = client.post(f"/api/claim/{TOKEN}", json={})

    assert resp.status_code == 410 and resp.json() == {"state": "expired"}
    assert auth.COOKIE_NAME not in _set_cookie(resp)
    assert db.writes() == (0, 0, 0, 0, 0) and db.notify.calls == []


def test_a_naive_stored_expiry_is_read_as_utc(db):
    host_id = _host(db)
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).replace(tzinfo=None)
    _lead(db, host_id, _event(db, host_id), expires=past)

    assert client.get(f"/api/claim/{TOKEN}").json() == {"state": "expired"}


def test_the_claim_routes_are_rate_limited_after_ten_calls(db):
    _hosted(db)

    codes = [client.get(f"/api/claim/{TOKEN}").status_code for _ in range(10)]

    assert codes == [200] * 10
    assert client.get(f"/api/claim/{TOKEN}").status_code == 429
    assert client.post(f"/api/claim/{TOKEN}", json={}).status_code == 429


# ---------- POST: completion ----------

def test_completing_signs_the_host_in_and_marks_the_lead_claimed(db):
    host_id, event_id, lead_id = _hosted(db)

    resp = client.post(f"/api/claim/{TOKEN}", json={})

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True and body["state"] == "ok"
    assert body["redirect"] == f"/events/{event_id}?claimed=1"
    assert body["event"] == {"id": str(event_id), "name": "Denver Tech Mixer"}
    assert auth.decode_token(body["token"]) == str(host_id)
    assert auth.COOKIE_NAME in _set_cookie(resp)
    assert "@" not in resp.text

    lead = db.leads.rows[lead_id]
    assert lead["status"] == "claimed"
    assert lead["funnel"]["claimed_at"] is not None
    assert lead["funnel"]["found_at"] is not None
    assert db.events.rows[event_id]["provenance"]["claimed_at"] is not None
    assert db.users.rows[host_id]["activated_at"] is not None
    assert [call["_id"] for call in db.notify.calls] == [lead_id]


def test_the_claim_token_still_works_after_a_completion(db):
    _hosted(db)

    client.post(f"/api/claim/{TOKEN}", json={})
    client.cookies.clear()

    assert client.get(f"/api/claim/{TOKEN}").json()["state"] == "ok"


def test_a_second_completion_from_another_device_signs_in_without_notifying_again(db):
    host_id, event_id, lead_id = _hosted(db)
    client.post(f"/api/claim/{TOKEN}", json={})
    client.cookies.clear()  # the second device has no session
    before = db.writes()
    first_claimed_at = db.leads.rows[lead_id]["funnel"]["claimed_at"]

    resp = client.post(f"/api/claim/{TOKEN}", json={})

    assert resp.status_code == 200
    assert auth.COOKIE_NAME in _set_cookie(resp)
    assert auth.decode_token(resp.json()["token"]) == str(host_id)
    assert len(db.notify.calls) == 1
    assert db.writes() == before
    assert db.leads.rows[lead_id]["funnel"]["claimed_at"] == first_claimed_at


def test_two_racing_completions_notify_once(db):
    _, _, lead_id = _hosted(db)
    lead = asyncio.run(event_leads_store.get_lead(str(lead_id)))
    now = datetime.now(timezone.utc)

    first = asyncio.run(event_leads_claim._mark_first_claim(lead, now))
    second = asyncio.run(event_leads_claim._mark_first_claim(lead, now))

    assert (first, second) == (True, False)


# ---------- POST: pending host ----------

def test_a_pending_host_completion_creates_the_user_and_attaches_the_event(db):
    event_id, lead_id = _pending(db)

    resp = client.post(f"/api/claim/{TOKEN}", json={"email": "  Jane@Host.ORG ", "name": "Jane D"})

    assert resp.status_code == 200
    host = next(u for u in db.users.rows.values() if u.get("email") == HOST_EMAIL)
    assert host["profile"]["name"] == "Jane D"
    assert host["plan"] == "free" and host["host_origin"] == "event_lead"
    assert host["is_admin"] is False and host["password_hash"]
    assert host["email_verified"] is False  # typed on the page, never confirmed
    assert host["activated_at"] is not None
    event = db.events.rows[event_id]
    assert event["created_by"] == host["_id"]
    assert event["provenance"]["pending_host"] is False
    assert event["provenance"]["claimed_at"] is not None
    lead = db.leads.rows[lead_id]
    assert lead["host_user_id"] == str(host["_id"])
    assert lead["status"] == "claimed"
    assert auth.decode_token(resp.json()["token"]) == str(host["_id"])
    assert "@" not in resp.text
    # Later visits see a hosted lead and sign straight in.
    client.cookies.clear()
    assert client.get(f"/api/claim/{TOKEN}").json()["state"] == "ok"


def test_a_pending_host_without_a_name_is_named_after_the_contact(db):
    _pending(db)

    client.post(f"/api/claim/{TOKEN}", json={"email": HOST_EMAIL})

    host = next(u for u in db.users.rows.values() if u.get("email") == HOST_EMAIL)
    assert host["profile"]["name"] == "Jane Doe"


@pytest.mark.parametrize("body", [{}, {"email": ""}, {"email": "not-an-email"}])
def test_a_pending_host_must_give_a_real_email(db, body):
    _pending(db)

    resp = client.post(f"/api/claim/{TOKEN}", json=body)

    assert resp.status_code == 422
    assert auth.COOKIE_NAME not in _set_cookie(resp)
    assert db.writes() == (0, 0, 0, 0, 0)


def test_an_existing_account_email_needs_that_account_signed_in(db):
    """Typing someone else's email must never sign the typist in as them."""
    _host(db)
    _pending(db)

    resp = client.post(f"/api/claim/{TOKEN}", json={"email": HOST_EMAIL})

    assert resp.status_code == 409
    assert auth.COOKIE_NAME not in _set_cookie(resp)
    assert db.writes() == (0, 0, 0, 0, 0) and db.notify.calls == []


def test_a_signed_in_existing_account_can_claim_a_pending_event(db):
    host_id = _host(db)
    event_id, lead_id = _pending(db)
    client.cookies.set(auth.COOKIE_NAME, auth.create_access_token(str(host_id)))

    resp = client.post(f"/api/claim/{TOKEN}", json={"email": HOST_EMAIL})

    assert resp.status_code == 200
    assert db.events.rows[event_id]["created_by"] == host_id
    assert db.leads.rows[lead_id]["host_user_id"] == str(host_id)
    assert db.users.inserts == 0


def test_an_existing_account_at_its_plan_limit_is_refused(db, monkeypatch):
    monkeypatch.setenv("BILLING_ENFORCED", "true")
    host_id = _host(db)
    for _ in range(billing.event_limit_for(db.users.rows[host_id])):
        db.events.add(name="Theirs", created_by=host_id)
    _pending(db)
    client.cookies.set(auth.COOKIE_NAME, auth.create_access_token(str(host_id)))

    resp = client.post(f"/api/claim/{TOKEN}", json={"email": HOST_EMAIL})

    assert resp.status_code == 409
    assert "Upgrade to host more" in resp.json()["detail"]
    assert db.writes() == (0, 0, 0, 0, 0) and db.notify.calls == []


# ---------- outreach.notify_claimed ----------

def _wire(monkeypatch, resp=None, exc=None):
    import httpx

    calls = []

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            calls.append((url, headers, json))
            if exc:
                raise exc
            return resp

    monkeypatch.setattr(outreach, "SIGNAL_SCOUT_URL", "https://ss.test")
    monkeypatch.setattr(outreach, "SIGNAL_SCOUT_API_KEY", "k")
    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    return calls


NOTIFY = outreach.notify_claimed
CLAIMED_LEAD = {"_id": ObjectId(), "contact": {"email": HOST_EMAIL},
                "signal_scout": {"prospect_id": "p-1"}}


def test_notify_claimed_posts_the_claimed_contract(monkeypatch):
    calls = _wire(monkeypatch, _Resp(200, {"ok": True, "skipped": 0}))

    out = asyncio.run(NOTIFY(CLAIMED_LEAD))

    assert out["ok"] is True
    url, headers, payload = calls[0]
    assert url == "https://ss.test/api/intro-connect/claimed"
    assert headers == {"Authorization": "Bearer k"}
    assert payload == {"prospect_id": "p-1", "lead_id": str(CLAIMED_LEAD["_id"]),
                       "email": HOST_EMAIL}


def test_notify_claimed_skips_without_config_or_prospect(monkeypatch):
    calls = _wire(monkeypatch, _Resp(200, {"ok": True}))
    no_prospect = {**CLAIMED_LEAD, "signal_scout": {}}

    assert asyncio.run(NOTIFY(no_prospect))["skipped"]
    monkeypatch.setattr(outreach, "SIGNAL_SCOUT_API_KEY", "")
    assert asyncio.run(NOTIFY(CLAIMED_LEAD))["skipped"]
    assert calls == []


def test_notify_claimed_never_raises_and_never_logs_the_email(monkeypatch, capsys):
    _wire(monkeypatch, exc=RuntimeError(f"boom for {HOST_EMAIL}"))
    assert asyncio.run(NOTIFY(CLAIMED_LEAD))["ok"] is False

    _wire(monkeypatch, _Resp(500, text=f"bad {HOST_EMAIL}"))
    assert asyncio.run(NOTIFY(CLAIMED_LEAD))["ok"] is False

    captured = capsys.readouterr()
    assert HOST_EMAIL not in captured.err and HOST_EMAIL not in captured.out
