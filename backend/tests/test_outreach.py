"""Tests for the outreach cockpit helpers (CSV export + config gate). The live
push needs signal-scout + httpx and is not exercised here.
Run from backend/: python -m pytest tests/test_outreach.py
"""
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
