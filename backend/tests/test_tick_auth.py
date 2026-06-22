"""Tests for the blog tick's shared-secret auth. Run from backend/:
    python -m pytest tests/test_tick_auth.py
"""
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import server


def test_tick_disabled_when_no_secret(monkeypatch):
    monkeypatch.delenv("BLOG_TICK_SECRET", raising=False)
    assert server._tick_authorized("anything") is False
    assert server._tick_authorized(None) is False


def test_tick_requires_matching_secret(monkeypatch):
    monkeypatch.setenv("BLOG_TICK_SECRET", "s3cret-value")
    assert server._tick_authorized("s3cret-value") is True
    assert server._tick_authorized("wrong") is False
    assert server._tick_authorized("") is False
    assert server._tick_authorized(None) is False
