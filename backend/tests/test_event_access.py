"""Tests for self-serve host event ownership. Run from backend/:
    python -m pytest tests/test_event_access.py
"""
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import server


def test_admin_can_manage_any_event():
    assert server._can_manage_event({"is_admin": True, "_id": 1}, {"created_by": 2}) is True


def test_creator_can_manage_own_event():
    assert server._can_manage_event({"is_admin": False, "_id": 7}, {"created_by": 7}) is True


def test_non_creator_cannot_manage():
    assert server._can_manage_event({"is_admin": False, "_id": 7}, {"created_by": 8}) is False
    assert server._can_manage_event({"is_admin": False, "_id": 7}, {}) is False
