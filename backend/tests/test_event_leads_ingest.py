"""POST /api/admin/event-leads/ingest: the weekly sourcing job's door.

It is not behind the admin cookie, so the bearer check is the only thing
between the internet and the lead table. The auth tests come first for that
reason, and the missing-env case matters most: an unset key must lock the
route, not open it.

Run from backend/: python -m pytest tests/test_event_leads_ingest.py
"""
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import pytest
from fastapi.testclient import TestClient

import event_leads_store
import server
from routers import event_leads as route

client = TestClient(server.app)
URL = "/api/admin/event-leads/ingest"
KEY = "test-ingest-key"
AUTH = {"Authorization": f"Bearer {KEY}"}


def _event(event_id, start="2026-11-04T18:00:00-07:00"):
    return {
        "source": "revel",
        "source_event_id": event_id,
        "title": "Denver Tech Mixer",
        "start": start,
        "timezone": "America/Denver",
    }


def _lead(key="meetup:denver-devs", email="jane@host.org"):
    return {
        "organizer_key": key,
        "organizer_name": "Denver Devs",
        "organizer_url": "https://www.meetup.com/denver-devs",
        "city": "Denver",
        "events_listed": 1,
        "anchor": _event("e1"),
        "events": [_event("e1")],
        "score": {"tier": "A", "score": 94, "reason": "mixer"},
        "contact": {"name": "Jane", "email": email, "linkedin_url": ""},
    }


def _payload(*leads):
    return {
        "run": {"week": "2026-10-18", "ingested": len(leads), "errors": []},
        "leads": list(leads),
    }


class _Leads:
    def __init__(self):
        self.rows = {}
        self.writes = 0

    async def find_one(self, q):
        row = self.rows.get(q.get("organizer_key"))
        return dict(row) if row else None

    async def replace_one(self, q, doc, upsert=False):
        doc = dict(doc)
        doc.setdefault("_id", f"id-{len(self.rows) + 1}")
        self.rows[q["organizer_key"]] = doc
        self.writes += 1


class _Runs:
    def __init__(self):
        self.rows = []

    async def insert_one(self, doc):
        self.rows.append(doc)


class _Users:
    def __init__(self, by_email):
        self.by_email = by_email

    async def find_one(self, q):
        return self.by_email.get(q.get("email"))


class _Events:
    def __init__(self, hosts=()):
        self.hosts = set(hosts)

    async def count_documents(self, q):
        return 1 if q.get("created_by") in self.hosts else 0


class _NoFlags:
    """app_flags with no auto-approve threshold: auto-approve is off."""

    async def find_one(self, q):
        return None


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setenv("EVENT_LEADS_INGEST_KEY", KEY)
    leads, runs = _Leads(), _Runs()
    monkeypatch.setattr(event_leads_store, "event_leads", leads)
    monkeypatch.setattr(event_leads_store, "event_lead_runs", runs)
    monkeypatch.setattr(event_leads_store, "app_flags", _NoFlags())
    monkeypatch.setattr(route, "users", _Users({}))
    monkeypatch.setattr(route, "events", _Events())
    return leads, runs


def test_no_bearer_is_401(db):
    assert client.post(URL, json=_payload(_lead())).status_code == 401
    assert db[0].rows == {} and db[1].rows == []


def test_wrong_bearer_is_401(db):
    bad = {"Authorization": "Bearer nope"}
    assert client.post(URL, json=_payload(_lead()), headers=bad).status_code == 401
    assert db[0].rows == {}


def test_unset_key_fails_closed_even_for_an_empty_bearer(db, monkeypatch):
    monkeypatch.delenv("EVENT_LEADS_INGEST_KEY", raising=False)
    for header in ("Bearer ", "Bearer", ""):
        resp = client.post(
            URL, json=_payload(_lead()), headers={"Authorization": header}
        )
        assert resp.status_code == 401
    assert db[0].rows == {}


def test_counts_and_one_run_record(db):
    leads, runs = db
    body = _payload(_lead("a:one"), _lead("a:two", email="b@host.org"))

    resp = client.post(URL, json=body, headers=AUTH)

    assert resp.status_code == 200
    assert resp.json() == {
        "ok": True, "inserted": 2, "updated": 0, "unchanged": 0,
        "existing_customer": 0, "auto_approved": 0,
    }
    assert set(leads.rows) == {"a:one", "a:two"}
    assert len(runs.rows) == 1
    assert runs.rows[0]["week"] == "2026-10-18"
    assert "received_at" in runs.rows[0]


def test_resending_the_same_batch_is_unchanged_and_writes_nothing(db):
    leads, _ = db
    body = _payload(_lead())
    client.post(URL, json=body, headers=AUTH)
    writes = leads.writes

    resp = client.post(URL, json=body, headers=AUTH)

    assert resp.json()["unchanged"] == 1
    assert resp.json()["inserted"] == 0
    assert leads.writes == writes


def test_changed_lead_counts_as_updated(db):
    client.post(URL, json=_payload(_lead()), headers=AUTH)
    changed = _lead()
    changed["score"] = {"tier": "B", "score": 70, "reason": "rescored"}

    resp = client.post(URL, json=_payload(changed), headers=AUTH)

    assert resp.json()["updated"] == 1


def test_matching_host_becomes_existing_customer(db, monkeypatch):
    leads, _ = db
    monkeypatch.setattr(
        route, "users",
        _Users({"jane@host.org": {"_id": "uid1", "plan": "free"}}),
    )
    monkeypatch.setattr(route, "events", _Events(hosts={"uid1"}))

    resp = client.post(URL, json=_payload(_lead(email="Jane@Host.org")), headers=AUTH)

    assert resp.json()["inserted"] == 1
    assert resp.json()["existing_customer"] == 1
    row = leads.rows["meetup:denver-devs"]
    assert row["status"] == "existing_customer"
    assert row["existing_user_id"] == "uid1"


def test_paid_plan_user_without_events_is_a_customer(db, monkeypatch):
    monkeypatch.setattr(
        route, "users",
        _Users({"jane@host.org": {"_id": "uid1", "plan": "pro"}}),
    )

    resp = client.post(URL, json=_payload(_lead()), headers=AUTH)

    assert resp.json()["existing_customer"] == 1


def test_free_user_without_events_stays_new(db, monkeypatch):
    leads, _ = db
    monkeypatch.setattr(
        route, "users",
        _Users({"jane@host.org": {"_id": "uid1", "plan": "free"}}),
    )

    resp = client.post(URL, json=_payload(_lead()), headers=AUTH)

    assert resp.json()["existing_customer"] == 0
    assert leads.rows["meetup:denver-devs"]["status"] == "new"
    assert leads.rows["meetup:denver-devs"]["existing_user_id"] == "uid1"


def test_lead_without_organizer_key_is_rejected_after_auth(db):
    bad = _lead()
    bad["organizer_key"] = ""

    assert client.post(URL, json=_payload(bad), headers=AUTH).status_code == 422
    assert db[1].rows == []
