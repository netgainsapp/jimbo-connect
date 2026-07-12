"""Tests for the Signal Scout error-hub reporter (error_hub.py).

Run from backend/: python -m pytest tests/test_error_hub.py
"""
import asyncio
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import error_hub


def _reset_window():
    error_hub._sent = 0
    error_hub._window_start = 0.0


def test_noop_without_key(monkeypatch):
    _reset_window()
    monkeypatch.delenv("ERROR_HUB_KEY", raising=False)
    posted = []
    monkeypatch.setattr(error_hub, "_post", lambda p, k: posted.append(p))
    error_hub.report_error("server", ValueError("boom"))
    assert posted == []
    assert error_hub._sent == 0


def test_payload_shape():
    try:
        raise ValueError("boom")
    except ValueError as exc:
        payload = error_hub.build_payload("server", exc, False, "https://x/api/y")
    assert payload["kind"] == "server"
    assert payload["message"] == "boom"
    assert "ValueError: boom" in payload["stack"]
    assert payload["fatal"] is False
    assert payload["platform"] == "server"
    assert payload["url"] == "https://x/api/y"


def test_message_falls_back_to_type_name():
    payload = error_hub.build_payload("server", ValueError(), True, None)
    assert payload["message"] == "ValueError"
    assert payload["fatal"] is True


def test_rate_cap_per_window(monkeypatch):
    _reset_window()
    monkeypatch.setenv("ERROR_HUB_KEY", "ssk_test")
    posted = []

    async def fake_post(payload, key):
        posted.append(payload)

    monkeypatch.setattr(error_hub, "_post", fake_post)

    async def fire_many():
        for _ in range(error_hub.MAX_REPORTS_PER_WINDOW + 10):
            error_hub.report_error("server", ValueError("boom"))
        await asyncio.sleep(0)

    asyncio.run(fire_many())
    assert len(posted) == error_hub.MAX_REPORTS_PER_WINDOW


def test_never_raises_without_loop(monkeypatch):
    _reset_window()
    monkeypatch.setenv("ERROR_HUB_KEY", "ssk_test")
    # No running event loop: must silently skip, not raise.
    error_hub.report_error("server", ValueError("boom"))
