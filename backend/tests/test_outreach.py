"""Tests for the outreach cockpit helpers (CSV export + config gate). The live
push needs signal-scout + httpx and is not exercised here.
Run from backend/: python -m pytest tests/test_outreach.py
"""
import asyncio
import os

import outreach
from outreach import to_csv, lead_to_row, CSV_FIELDS


def test_server_imports_outreach_leads_collection():
    # Regression: the /admin/outreach routes reference `outreach_leads` directly,
    # so it must be importable into server.py's namespace (a missing import only
    # surfaces at request time, not at module import).
    os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
    os.environ.setdefault("DB_NAME", "t")
    os.environ.setdefault("JWT_SECRET", "x")
    import server

    assert server.outreach_leads is not None


def test_lead_to_row_splits_name_and_tags_source():
    row = lead_to_row(
        {
            "name": "Eric Marcoullier",
            "company": "Thunderview",
            "email": "e@x.com",
            "role": "Director",
            "source": "https://thunderview.com",
        }
    )
    assert row["first_name"] == "Eric"
    assert row["last_name"] == "Marcoullier"
    assert row["company"] == "Thunderview"
    assert row["email"] == "e@x.com"
    assert row["title"] == "Director"
    assert row["source"] == "intro_connect"


def test_to_csv_header_and_rows():
    csv_text = to_csv([{"name": "A B", "email": "a@b.com"}])
    lines = csv_text.strip().splitlines()
    assert lines[0] == ",".join(CSV_FIELDS)
    assert "a@b.com" in lines[1]


def test_is_configured_gate(monkeypatch):
    monkeypatch.setattr(outreach, "SIGNAL_SCOUT_URL", "")
    monkeypatch.setattr(outreach, "SIGNAL_SCOUT_API_KEY", "")
    assert outreach.is_configured() is False
    monkeypatch.setattr(outreach, "SIGNAL_SCOUT_URL", "https://signal-scout.example")
    monkeypatch.setattr(outreach, "SIGNAL_SCOUT_API_KEY", "secret")
    assert outreach.is_configured() is True


# ---- push result reflects signal-scout's BODY, not just the HTTP status ----
# Regression: a 200 with imported:0 used to report ok/pushed=len(leads), so the
# cockpit showed success for an import that landed nothing (found live 2026-07-11).

class _FakeResp:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class _FakeClient:
    def __init__(self, resp):
        self._resp = resp

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, *a, **k):
        return self._resp


def _wire_push(monkeypatch, resp):
    import httpx
    monkeypatch.setattr(outreach, "SIGNAL_SCOUT_URL", "https://ss.test")
    monkeypatch.setattr(outreach, "SIGNAL_SCOUT_API_KEY", "k")
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: _FakeClient(resp))


LEAD = [{"email": "a@b.com", "name": "A", "company": "C", "role": "r"}]


def test_push_success_reports_signal_scout_counts(monkeypatch):
    _wire_push(monkeypatch, _FakeResp(200, {"imported": 1, "sequences_scheduled": 5, "already_scheduled": 0, "errors": []}))
    out = asyncio.run(outreach.push_to_signal_scout(LEAD))
    assert out["ok"] is True
    assert out["pushed"] == 1
    assert out["sequences_scheduled"] == 5


def test_push_200_with_zero_imported_is_not_success(monkeypatch):
    # The exact shape that fooled us: HTTP 200, nothing actually imported.
    _wire_push(monkeypatch, _FakeResp(200, {"imported": 0, "sequences_scheduled": 0, "already_scheduled": 0, "errors": []}))
    out = asyncio.run(outreach.push_to_signal_scout(LEAD))
    assert out["ok"] is False
    assert out["pushed"] == 0


def test_push_200_with_errors_is_not_success(monkeypatch):
    _wire_push(monkeypatch, _FakeResp(200, {"imported": 0, "errors": [{"email": "a@b.com", "reason": "upsert: boom"}]}))
    out = asyncio.run(outreach.push_to_signal_scout(LEAD))
    assert out["ok"] is False
    assert out["error_count"] == 1


def test_push_200_with_unparseable_body_is_not_success(monkeypatch):
    _wire_push(monkeypatch, _FakeResp(200, None, text="<html>gateway</html>"))
    out = asyncio.run(outreach.push_to_signal_scout(LEAD))
    assert out["ok"] is False
    assert out["pushed"] == 0


def test_push_non_2xx_is_not_success(monkeypatch):
    _wire_push(monkeypatch, _FakeResp(500, None, text="boom"))
    out = asyncio.run(outreach.push_to_signal_scout(LEAD))
    assert out["ok"] is False
    assert out["pushed"] == 0
