"""Tests for the soft email-verification flow (M6) and the photo validators.
In-memory fakes + asyncio.run, no live DB, repo convention.

Run from backend/: python -m pytest tests/test_email_verify.py
"""
import asyncio
import os
from datetime import datetime, timedelta, timezone

import pytest

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import core
import server
from models import PhotoUploadRequest, ProfileUpdateRequest


class _FakeUsers:
    def __init__(self, docs=None):
        self.docs = docs or []
        self.updates = []

    async def find_one(self, query):
        key, val = next(iter(query.items()))
        for d in self.docs:
            if d.get(key) == val:
                return d
        return None

    async def update_one(self, query, update):
        self.updates.append((query, update))
        for d in self.docs:
            if all(d.get(k) == v for k, v in query.items()):
                for k, v in update.get("$set", {}).items():
                    d[k] = v
                for k in update.get("$unset", {}):
                    d.pop(k, None)


def _token_pair():
    raw = "raw-verification-token"
    return raw, server._hash_token(raw)


# ---- apply_email_verification ----

def test_valid_token_verifies_and_burns(monkeypatch):
    raw, hashed = _token_pair()
    fake = _FakeUsers(
        [
            {
                "_id": "u1",
                "verify_token": hashed,
                "verify_token_expires": datetime.now(timezone.utc) + timedelta(days=1),
            }
        ]
    )
    monkeypatch.setattr(core, "users", fake)
    assert asyncio.run(server.apply_email_verification(raw)) is True
    doc = fake.docs[0]
    assert doc["email_verified"] is True
    assert "verify_token" not in doc
    assert "verify_token_expires" not in doc


def test_expired_token_rejected(monkeypatch):
    raw, hashed = _token_pair()
    fake = _FakeUsers(
        [
            {
                "_id": "u1",
                "verify_token": hashed,
                "verify_token_expires": datetime.now(timezone.utc) - timedelta(minutes=1),
            }
        ]
    )
    monkeypatch.setattr(core, "users", fake)
    assert asyncio.run(server.apply_email_verification(raw)) is False
    assert "email_verified" not in fake.docs[0]


def test_unknown_and_empty_tokens_rejected(monkeypatch):
    monkeypatch.setattr(core, "users", _FakeUsers())
    assert asyncio.run(server.apply_email_verification("nope")) is False
    assert asyncio.run(server.apply_email_verification("")) is False


def test_naive_expiry_datetime_handled(monkeypatch):
    # Mongo round-trips datetimes as naive UTC; the check must not crash.
    raw, hashed = _token_pair()
    fake = _FakeUsers(
        [
            {
                "_id": "u1",
                "verify_token": hashed,
                "verify_token_expires": datetime.utcnow() + timedelta(days=1),
            }
        ]
    )
    monkeypatch.setattr(core, "users", fake)
    assert asyncio.run(server.apply_email_verification(raw)) is True


# ---- copy + serialization ----

def test_verify_body_has_url_and_no_dashes():
    paras = server.verify_email_paragraphs("Sam")
    joined = " ".join(paras)
    assert "Sam" in joined
    assert "seven days" in joined
    assert "—" not in joined and "–" not in joined


def test_serialize_user_includes_email_verified():
    doc = {"_id": "u1", "email": "a@b.com", "profile": {}}
    assert server.serialize_user(doc)["email_verified"] is False
    doc["email_verified"] = True
    assert server.serialize_user(doc)["email_verified"] is True


# ---- photo validators ----

def test_photo_url_accepts_https_and_empty():
    assert ProfileUpdateRequest(photo_url="https://x.test/a.png").photo_url
    assert ProfileUpdateRequest(photo_url="").photo_url == ""
    assert ProfileUpdateRequest().photo_url is None


def test_photo_url_accepts_image_data_url():
    v = "data:image/png;base64,iVBORw0KGgo="
    assert ProfileUpdateRequest(photo_url=v).photo_url == v


@pytest.mark.parametrize(
    "bad",
    [
        "javascript:alert(1)",
        "http://insecure.test/a.png",
        "file:///etc/passwd",
        "data:text/html;base64,PHNjcmlwdD4=",
        "not-a-url",
    ],
)
def test_photo_url_rejects_non_image_schemes(bad):
    with pytest.raises(Exception):
        ProfileUpdateRequest(photo_url=bad)


def test_photo_data_must_be_image_data_url():
    ok = "data:image/jpeg;base64,/9j/4AAQ"
    assert PhotoUploadRequest(photo_data=ok).photo_data == ok
    with pytest.raises(Exception):
        PhotoUploadRequest(photo_data="https://x.test/a.jpg")
    with pytest.raises(Exception):
        PhotoUploadRequest(photo_data="data:text/plain;base64,aGk=")
