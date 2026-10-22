"""Admin list, detail, archive, contact and score-override routes.

Auth is the real cookie dependency against a faked users collection, so the
403 for a non-admin and the 401 for a stranger come from `get_current_admin`
itself, not from a stub.

Run from backend/: python -m pytest tests/test_event_leads_admin.py
"""
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

import auth
import event_leads_store
import server
from routers import event_leads as route

client = TestClient(server.app)
BASE = "/api/admin/event-leads"
ADMIN_ID, MEMBER_ID = ObjectId(), ObjectId()
EMPTY_CONTACT = {"name": "", "email": "", "linkedin_url": ""}


class _Cursor:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self, _length):
        return [dict(r) for r in self.rows]


class _Leads:
    def __init__(self):
        self.rows = {}
        self.updates = []

    def add(self, **fields):
        doc = {"_id": ObjectId(), "status": "new", "contact": {}, **fields}
        self.rows[doc["_id"]] = doc
        return doc["_id"]

    async def find_one(self, q):
        row = self.rows.get(q.get("_id"))
        return dict(row) if row else None

    def find(self, q):
        excluded = (q.get("score.tier") or {}).get("$ne")
        rows = [
            r for r in self.rows.values()
            if excluded is None or (r.get("score") or {}).get("tier") != excluded
        ]
        return _Cursor(rows)

    async def update_one(self, q, update):
        self.updates.append((q, update))
        row = self.rows[q["_id"]]
        row.update(update.get("$set", {}))
        for key in update.get("$unset", {}):
            row.pop(key, None)


class _Users:
    def __init__(self, rows):
        self.rows = rows

    async def find_one(self, q):
        if "_id" in q:
            return self.rows.get(q["_id"])
        return next(
            (u for u in self.rows.values() if u.get("email") == q.get("email")),
            None,
        )


class _Events:
    def __init__(self, hosts=()):
        self.hosts = set(hosts)

    async def count_documents(self, q):
        return 1 if q.get("created_by") in self.hosts else 0


class _NoFlags:
    async def find_one(self, q):
        return None


@pytest.fixture
def db(monkeypatch):
    leads = _Leads()
    people = _Users({
        ADMIN_ID: {"_id": ADMIN_ID, "is_admin": True},
        MEMBER_ID: {"_id": MEMBER_ID, "is_admin": False},
    })
    monkeypatch.setattr(event_leads_store, "event_leads", leads)
    monkeypatch.setattr(event_leads_store, "app_flags", _NoFlags())
    monkeypatch.setattr(auth, "users", people)
    monkeypatch.setattr(route, "users", people)
    monkeypatch.setattr(route, "events", _Events())
    client.cookies.clear()
    client.cookies.set(auth.COOKIE_NAME, auth.create_access_token(str(ADMIN_ID)))
    yield leads
    client.cookies.clear()


def _lead(leads, tier="A", start="2099-01-04T18:00:00-07:00", **extra):
    fields = {
        "organizer_key": f"k:{ObjectId()}",
        "organizer_name": "Denver Devs",
        "anchor": {"start": start, "title": "Mixer"},
        "score": {"tier": tier, "score": 90, "reason": "mixer"},
        **extra,
    }
    return leads.add(**fields)


def test_anonymous_is_401_and_non_admin_is_403(db):
    lead_id = _lead(db)
    client.cookies.clear()
    assert client.get(BASE).status_code == 401
    assert client.get(f"{BASE}/{lead_id}").status_code == 401

    client.cookies.set(auth.COOKIE_NAME, auth.create_access_token(str(MEMBER_ID)))
    calls = [
        client.get(BASE),
        client.get(f"{BASE}/{lead_id}"),
        client.post(f"{BASE}/{lead_id}/archive"),
        client.post(f"{BASE}/{lead_id}/unarchive"),
        client.put(f"{BASE}/{lead_id}/contact", json=EMPTY_CONTACT),
        client.put(f"{BASE}/{lead_id}/score-override", json={"score": 5}),
    ]
    assert [c.status_code for c in calls] == [403] * 6
    assert db.updates == []


def test_tier_c_is_hidden_by_default_and_shown_on_request(db):
    _lead(db, tier="A")
    _lead(db, tier="C")

    default = client.get(BASE).json()
    shown = client.get(BASE, params={"show_c": "true"}).json()

    assert [x["score"]["tier"] for x in default["leads"]] == ["A"]
    assert sorted(x["score"]["tier"] for x in shown["leads"]) == ["A", "C"]
    assert default["kpis"] == []


def test_list_sorts_by_tier_then_date_and_archived_last(db):
    _lead(db, tier="B", start="2099-01-01T18:00:00-07:00", organizer_name="b-soon")
    _lead(db, tier="A", start="2099-03-01T18:00:00-07:00", organizer_name="a-late")
    _lead(db, tier="A", start="2099-02-01T18:00:00-07:00", organizer_name="a-soon")
    _lead(db, tier="A", start="2099-01-01T18:00:00-07:00",
          organizer_name="a-archived", status="archived")

    names = [x["organizer_name"] for x in client.get(BASE).json()["leads"]]

    assert names == ["a-soon", "a-late", "b-soon", "a-archived"]


def test_payload_adds_days_until_and_hides_internals(db):
    _lead(db, claim_token_hash="secret-hash", score_override=40,
          existing_user_id="u1")
    _lead(db, start="")

    rows = client.get(BASE).json()["leads"]

    dated = next(r for r in rows if r["anchor"]["start"])
    assert isinstance(dated["days_until"], int) and dated["days_until"] > 0
    assert "_id" not in dated and "claim_token_hash" not in dated
    assert dated["id"] and dated["score_override"] == 40
    assert dated["existing_user_id"] == "u1"
    undated = next(r for r in rows if not r["anchor"]["start"])
    assert undated["days_until"] is None


class _Templates:
    def __init__(self, rows=()):
        self.rows = {r["seed_key"]: r for r in rows}

    async def find_one(self, q):
        return self.rows.get(q.get("seed_key"))


def test_detail_returns_email_and_linkedin_previews_from_the_seeds(db, monkeypatch):
    monkeypatch.setattr(route.sales_templates, "sales_templates", _Templates())
    lead_id = _lead(db, claim_url="https://app.example.com/claim/t0k")

    body = client.get(f"{BASE}/{lead_id}").json()

    assert body["id"] == str(lead_id)
    assert body["email_preview"]["subject"].startswith("Mixer on ")
    assert "https://app.example.com/claim/t0k" in body["email_preview"]["body"]
    assert set(body["linkedin_preview"]) == {"note", "followup"}
    assert len(body["linkedin_preview"]["note"]) <= 300


def test_detail_previews_honour_an_admin_edited_template(db, monkeypatch):
    edited = {"seed_key": "ic-linkedin-note", "body": "Edited note for {first_name}"}
    monkeypatch.setattr(route.sales_templates, "sales_templates", _Templates([edited]))
    lead_id = _lead(db, contact={"name": "Jane Doe"})

    body = client.get(f"{BASE}/{lead_id}").json()

    assert body["linkedin_preview"]["note"] == "Edited note for Jane"
    assert body["linkedin_preview"]["followup"].startswith("Thanks for connecting, Jane")


@pytest.mark.parametrize("bad", ["not-an-id", str(ObjectId())])
def test_unknown_or_malformed_id_is_404_on_every_route(db, bad):
    calls = [
        client.get(f"{BASE}/{bad}"),
        client.post(f"{BASE}/{bad}/archive"),
        client.post(f"{BASE}/{bad}/unarchive"),
        client.put(f"{BASE}/{bad}/contact", json=EMPTY_CONTACT),
        client.put(f"{BASE}/{bad}/score-override", json={"score": 5}),
    ]
    assert [c.status_code for c in calls] == [404] * 5


def test_archive_sets_status_and_timestamp_and_remembers_prior_status(db):
    lead_id = _lead(db, status="approved")

    body = client.post(f"{BASE}/{lead_id}/archive").json()

    row = db.rows[lead_id]
    assert body["status"] == "archived" and row["status"] == "archived"
    assert row["archived_at"] is not None
    assert row["status_before_archive"] == "approved"
    assert row["updated_at"] is not None


def test_archiving_twice_changes_nothing(db):
    lead_id = _lead(db, status="approved")
    client.post(f"{BASE}/{lead_id}/archive")
    writes = len(db.updates)

    body = client.post(f"{BASE}/{lead_id}/archive").json()

    assert body["status"] == "archived"
    assert len(db.updates) == writes
    assert db.rows[lead_id]["status_before_archive"] == "approved"


def test_unarchive_restores_prior_status_and_clears_archived_at(db):
    lead_id = _lead(db, status="approved")
    client.post(f"{BASE}/{lead_id}/archive")

    body = client.post(f"{BASE}/{lead_id}/unarchive").json()

    assert body["status"] == "approved"
    assert "archived_at" not in db.rows[lead_id]
    assert "status_before_archive" not in db.rows[lead_id]


def test_unarchive_without_a_remembered_status_goes_to_new(db):
    lead_id = _lead(db, status="archived")

    assert client.post(f"{BASE}/{lead_id}/unarchive").json()["status"] == "new"


def test_unarchive_on_a_live_lead_changes_nothing(db):
    lead_id = _lead(db, status="approved")

    body = client.post(f"{BASE}/{lead_id}/unarchive").json()

    assert body["status"] == "approved" and db.updates == []


def test_contact_edit_on_unreachable_lead_with_an_email_makes_it_new(db):
    lead_id = _lead(db, status="unreachable",
                    contact={"name": "", "email": "", "linkedin_url": "",
                             "website": "https://host.org", "email_status": ""})

    resp = client.put(f"{BASE}/{lead_id}/contact", json={
        "name": " Jane ", "email": "  Jane@Host.ORG ", "linkedin_url": "",
    })

    assert resp.status_code == 200
    row = db.rows[lead_id]
    assert row["status"] == "new"
    assert row["contact"]["email"] == "jane@host.org"
    assert row["contact"]["name"] == "Jane"
    assert row["contact"]["website"] == "https://host.org"


def test_clearing_the_contact_on_a_new_lead_makes_it_unreachable(db):
    lead_id = _lead(db, status="new", contact={"email": "jane@host.org"})

    client.put(f"{BASE}/{lead_id}/contact", json=EMPTY_CONTACT)

    assert db.rows[lead_id]["status"] == "unreachable"


def test_contact_edit_matching_a_hosting_user_becomes_existing_customer(
    db, monkeypatch
):
    uid = ObjectId()
    monkeypatch.setattr(route, "users", _Users(
        {uid: {"_id": uid, "email": "jane@host.org", "plan": "free"}}))
    monkeypatch.setattr(route, "events", _Events(hosts={uid}))
    lead_id = _lead(db, status="new")

    client.put(f"{BASE}/{lead_id}/contact",
               json={"name": "J", "email": "Jane@host.org", "linkedin_url": ""})

    row = db.rows[lead_id]
    assert row["status"] == "existing_customer"
    assert row["existing_user_id"] == str(uid)


def test_contact_edit_to_an_unmatched_email_clears_existing_user_id(db):
    lead_id = _lead(db, status="new", existing_user_id="old",
                    contact={"email": "old@host.org"})

    client.put(f"{BASE}/{lead_id}/contact",
               json={"name": "", "email": "new@host.org", "linkedin_url": ""})

    assert "existing_user_id" not in db.rows[lead_id]


def test_contact_edit_on_an_approved_lead_keeps_its_status(db):
    lead_id = _lead(db, status="approved", contact={"email": "a@host.org"})

    client.put(f"{BASE}/{lead_id}/contact", json=EMPTY_CONTACT)

    row = db.rows[lead_id]
    assert row["status"] == "approved"
    assert row["contact"]["email"] == ""


def test_changing_the_email_resets_its_verification_status(db):
    lead_id = _lead(db, status="new",
                    contact={"email": "a@host.org", "email_status": "verified"})

    client.put(f"{BASE}/{lead_id}/contact",
               json={"name": "", "email": "b@host.org", "linkedin_url": ""})

    assert db.rows[lead_id]["contact"]["email_status"] == ""


def test_score_override_is_stored_beside_the_score_never_over_it(db):
    lead_id = _lead(db)

    resp = client.put(f"{BASE}/{lead_id}/score-override", json={"score": 55})

    assert resp.status_code == 200
    row = db.rows[lead_id]
    assert row["score_override"] == 55
    assert row["score"]["score"] == 90
    assert resp.json()["score_override"] == 55


@pytest.mark.parametrize("bad", [-1, 101, "high", 5.5, True])
def test_score_override_outside_0_to_100_is_422(db, bad):
    lead_id = _lead(db)

    resp = client.put(f"{BASE}/{lead_id}/score-override", json={"score": bad})

    assert resp.status_code == 422
    assert "score_override" not in db.rows[lead_id]


@pytest.mark.parametrize("edge", [0, 100])
def test_score_override_accepts_the_edges(db, edge):
    lead_id = _lead(db)

    resp = client.put(f"{BASE}/{lead_id}/score-override", json={"score": edge})

    assert resp.status_code == 200


def test_every_write_keys_on_id_and_bumps_updated_at(db):
    lead_id = _lead(db)
    client.put(f"{BASE}/{lead_id}/score-override", json={"score": 10})
    client.put(f"{BASE}/{lead_id}/contact", json=EMPTY_CONTACT)
    client.post(f"{BASE}/{lead_id}/archive")

    assert len(db.updates) == 3
    for query, update in db.updates:
        assert query == {"_id": lead_id}
        assert "updated_at" in update["$set"]
