"""Tests for JWT create/decode after the python-jose -> PyJWT migration
(python-jose 3.3.0 carries CVE-2024-33663 / CVE-2024-33664).

Run from backend/: python -m pytest tests/test_auth_tokens.py
"""
import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import jwt as pyjwt

import auth


def test_token_roundtrip():
    token = auth.create_access_token("user123")
    assert isinstance(token, str)
    assert auth.decode_token(token) == "user123"


def test_expired_token_rejected():
    expired = pyjwt.encode(
        {"sub": "user123", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        auth.JWT_SECRET,
        algorithm=auth.JWT_ALGORITHM,
    )
    assert auth.decode_token(expired) is None


def test_wrong_secret_rejected():
    forged = pyjwt.encode(
        {"sub": "user123", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "not-the-real-secret",
        algorithm=auth.JWT_ALGORITHM,
    )
    assert auth.decode_token(forged) is None


def test_garbage_token_rejected():
    assert auth.decode_token("") is None
    assert auth.decode_token("not.a.jwt") is None
    assert auth.decode_token("a" * 200) is None


def test_none_algorithm_rejected():
    # An alg=none token must never validate, even with a matching payload.
    unsigned = pyjwt.encode(
        {"sub": "user123", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        None,
        algorithm="none",
    )
    assert auth.decode_token(unsigned) is None
