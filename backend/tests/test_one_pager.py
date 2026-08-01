"""The marketing site's one pager lead form, exercised through the real app.

Like tests/test_route_auth.py, the TestClient is used WITHOUT its context
manager so the app lifespan (Mongo index creation) never runs. The collection
and both email sends are monkeypatched, so no live MongoDB or Resend is needed.

Run from backend/: python -m pytest tests/test_one_pager.py
"""
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import pytest
from fastapi.testclient import TestClient

import database
import email_send
import rate_limit
import server

client = TestClient(server.app)

ENDPOINT = "/api/one-pager"


@pytest.fixture(autouse=True)
def _clear_rate_limit():
    """The limiter is process global, so a test that exhausts the budget would
    otherwise 429 every later test in the session."""
    rate_limit._hits.clear()
    yield
    rate_limit._hits.clear()


class FakeLeads:
    def __init__(self):
        self.upserts = []

    async def update_one(self, match, update, upsert=False):
        self.upserts.append({"match": match, "update": update, "upsert": upsert})


@pytest.fixture()
def capture(monkeypatch):
    """Fake collection + both email paths, all recording their calls."""
    leads = FakeLeads()
    branded = []
    plain = []

    async def fake_branded(to, subject, **kwargs):
        branded.append({"to": to, "subject": subject, **kwargs})
        return {"sent": True, "id": "em_1"}

    async def fake_email(to, subject, html, **kwargs):
        plain.append({"to": to, "subject": subject, "html": html})
        return {"sent": True, "id": "em_2"}

    monkeypatch.setattr(database, "one_pager_leads", leads)
    monkeypatch.setattr(email_send, "send_branded", fake_branded)
    monkeypatch.setattr(email_send, "send_email", fake_email)
    return {"leads": leads, "branded": branded, "plain": plain}


def test_valid_request_stores_lead_and_sends_both_emails(capture):
    r = client.post(ENDPOINT, json={"email": " Host@Example.com ", "name": "Jordan"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["url"].endswith(".pdf")

    # Lead upserted under the normalized address.
    assert len(capture["leads"].upserts) == 1
    up = capture["leads"].upserts[0]
    assert up["match"] == {"email": "host@example.com"}
    assert up["upsert"] is True
    assert up["update"]["$set"]["name"] == "Jordan"

    # The one pager email went to the requester, with the founding offer.
    assert len(capture["branded"]) == 1
    sent = capture["branded"][0]
    assert sent["to"] == "host@example.com"
    assert sent["button"]["url"].endswith(".pdf")
    assert any("$199" in p for p in sent["paragraphs"])

    # The admin got the heads-up.
    assert len(capture["plain"]) == 1
    assert "host@example.com" in capture["plain"][0]["subject"]


def test_invalid_email_is_rejected(capture):
    r = client.post(ENDPOINT, json={"email": "not-an-email"})
    assert r.status_code == 400
    assert capture["leads"].upserts == []
    assert capture["branded"] == []


def test_honeypot_pretends_success_but_does_nothing(capture):
    r = client.post(
        ENDPOINT,
        json={"email": "bot@example.com", "website": "https://spam.example"},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert capture["leads"].upserts == []
    assert capture["branded"] == []
    assert capture["plain"] == []


def test_rate_limited_after_five_requests(capture):
    for _ in range(5):
        assert client.post(ENDPOINT, json={"email": "same@example.com"}).status_code == 200
    r = client.post(ENDPOINT, json={"email": "same@example.com"})
    assert r.status_code == 429
