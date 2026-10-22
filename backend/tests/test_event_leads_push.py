"""outreach.push_event_lead: the Signal Scout import contract with `event`.

It must never raise: every failure becomes `ok: False` with a short error, so
Approve can record it and move on. The lead's email must never reach the log.

Run from backend/: python -m pytest tests/test_event_leads_push.py
"""
import asyncio
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

from datetime import datetime, timezone

import httpx
import pytest
from bson import ObjectId

import outreach

NOW = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
CLAIM = "https://app.example.com/claim/t0k"
EMAIL = "jane@host.org"


def _event(title, start, event_id):
    return {"title": title, "start": start, "venue": "Galvanize", "city": "Denver",
            "source_url": f"https://revel.example/{event_id}",
            "source_event_id": event_id, "description": "not sent"}


LEAD = {
    "_id": ObjectId(),
    "organizer_name": "Denver Devs",
    "anchor": _event("Mixer", "2026-11-04T18:00:00-07:00", "e1"),
    "events": [
        _event("Old one", "2026-09-01T18:00:00-06:00", "e0"),
        _event("Mixer", "2026-11-04T18:00:00-07:00", "e1"),
        _event("Next one", "2026-12-02T18:00:00-07:00", "e2"),
    ],
    "contact": {"name": "Jane Doe", "email": EMAIL},
}


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

    async def post(self, url, headers=None, json=None):
        _Client.sent[-1].update(url=url, headers=headers, json=json)
        if isinstance(_Client.result, Exception):
            raise _Client.result
        return _Client.result


@pytest.fixture
def wire(monkeypatch):
    _Client.sent, _Client.result = [], None
    monkeypatch.setattr(outreach, "SIGNAL_SCOUT_URL", "https://ss.test")
    monkeypatch.setattr(outreach, "SIGNAL_SCOUT_API_KEY", "k")
    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    return _Client


def _push():
    return asyncio.run(outreach.push_event_lead(LEAD, CLAIM, now=NOW))


def test_posts_the_import_contract_and_returns_the_prospect(wire):
    wire.result = _Resp(200, {"results": [
        {"email": EMAIL, "prospect_id": "p-1", "outcome": "imported"}]})

    out = _push()

    assert out == {"ok": True, "prospect_id": "p-1", "outcome": "imported"}
    sent = wire.sent[0]
    assert sent["url"] == "https://ss.test/api/intro-connect/import"
    assert sent["headers"] == {"Authorization": "Bearer k"}
    assert sent["timeout"] == 30
    lead = sent["json"]["leads"][0]
    assert {k: lead[k] for k in ("email", "name", "company", "role")} == {
        "email": EMAIL, "name": "Jane Doe", "company": "Denver Devs", "role": ""}
    event = lead["event"]
    assert event["anchor"] == {
        "name": "Mixer", "date": "2026-11-04T18:00:00-07:00", "venue": "Galvanize",
        "city": "Denver", "source_url": "https://revel.example/e1"}
    assert [e["name"] for e in event["upcoming"]] == ["Mixer", "Next one"]
    assert event["claim_url"] == CLAIM and event["lead_id"] == str(LEAD["_id"])


def test_already_scheduled_counts_as_success(wire):
    wire.result = _Resp(200, {"results": [
        {"prospect_id": "p-1", "outcome": "already_scheduled"}]})

    assert _push()["ok"] is True


@pytest.mark.parametrize("resp", [
    _Resp(500, text=f"boom for {EMAIL}"),
    _Resp(200, text=f"<html>{EMAIL}</html>"),
    _Resp(200, {"results": []}),
    _Resp(200, {"results": [{"outcome": "imported"}]}),
    _Resp(200, {"results": [{"email": EMAIL, "outcome": "error", "reason": f"bad {EMAIL}"}]}),
])
def test_every_failure_is_ok_false_with_a_short_error_and_no_email_logged(
    wire, resp, capsys
):
    wire.result = resp

    out = _push()

    assert out["ok"] is False and out["error"] and len(out["error"]) <= 120
    assert EMAIL not in out["error"]
    assert EMAIL not in capsys.readouterr().err


def test_network_error_is_ok_false(wire):
    wire.result = httpx.ConnectError(f"no route to {EMAIL}")

    out = _push()

    assert out["ok"] is False and EMAIL not in out["error"]


def test_unconfigured_never_calls_out(wire, monkeypatch):
    monkeypatch.setattr(outreach, "SIGNAL_SCOUT_API_KEY", "")

    out = _push()

    assert out["ok"] is False and out["error"]
    assert wire.sent == []
