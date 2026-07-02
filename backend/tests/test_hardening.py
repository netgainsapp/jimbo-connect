"""Tests for the second-pass hardening batch: reset-token hashing, email
normalization, bulk-import size cap, and email-HTML escaping.

Run from backend/: python -m pytest tests/test_hardening.py
"""
import hashlib
import os

import pytest

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import invites
import nurture
import server
from models import (
    BulkImportRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
)


# ---- reset/magic token is stored hashed (M1) ----

def test_hash_token_is_sha256_and_not_the_raw_token():
    raw = "super-secret-token"
    assert server._hash_token(raw) == hashlib.sha256(raw.encode()).hexdigest()
    assert server._hash_token(raw) != raw


def test_hash_token_is_deterministic():
    assert server._hash_token("abc") == server._hash_token("abc")
    assert server._hash_token("abc") != server._hash_token("abd")


# ---- email normalization (M12) ----

def test_register_email_is_lowercased():
    assert RegisterRequest(email="Foo@Bar.COM", password="secret6").email == "foo@bar.com"


def test_login_email_is_lowercased():
    assert LoginRequest(email="ABC@Example.com", password="x").email == "abc@example.com"


def test_forgot_email_is_lowercased():
    assert ForgotPasswordRequest(email="Mixed@Case.io").email == "mixed@case.io"


# ---- bulk-import size cap (M5) ----

def test_bulk_import_accepts_up_to_cap():
    rows = [{"email": f"u{i}@x.com"} for i in range(500)]
    req = BulkImportRequest(rows=rows)
    assert len(req.rows) == 500


def test_bulk_import_rejects_over_cap():
    rows = [{"email": f"u{i}@x.com"} for i in range(501)]
    with pytest.raises(Exception):
        BulkImportRequest(rows=rows)


# ---- email HTML escaping (M3) ----

def test_invites_html_escapes_markup():
    out = invites._html("Join <script>alert(1)</script> now")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_nurture_html_escapes_markup():
    out = nurture._html("Hi <img src=x onerror=alert(1)> there")
    assert "<img" not in out
    assert "&lt;img" in out
