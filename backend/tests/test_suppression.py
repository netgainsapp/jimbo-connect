"""Tests for the CAN-SPAM layer: signed unsubscribe tokens, the suppression
list (unsubscribe / bounce / complaint), Resend webhook signature verification
(svix scheme), and the marketing-send wrapper that enforces all of it.

Uses in-memory fakes for the motor collections and asyncio.run, so no live
MongoDB and no extra async-test dependency is needed.

Run from backend/: python -m pytest tests/test_suppression.py
"""
import asyncio
import base64
import hashlib
import hmac as hmac_mod
import os
import time

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import email_send
import suppression


# ---------- fakes ----------

class _FakeSuppressed:
    """In-memory stand-in for the suppressed_emails collection."""

    def __init__(self):
        self.docs = {}  # email -> doc

    async def find_one(self, query):
        return self.docs.get(query.get("email"))

    async def update_one(self, query, update, upsert=False):
        email = query.get("email")
        doc = self.docs.get(email)
        if doc is None and upsert:
            doc = dict(update.get("$setOnInsert", {}))
            doc["email"] = email
            self.docs[email] = doc
        elif doc is not None and "$set" in update:
            doc.update(update["$set"])


class _FakeUsers:
    def __init__(self):
        self.updates = []

    async def update_one(self, query, update):
        self.updates.append((query, update))


def _wire(monkeypatch):
    fake = _FakeSuppressed()
    fake_users = _FakeUsers()
    monkeypatch.setattr(suppression, "suppressed_emails", fake)
    monkeypatch.setattr(suppression, "users", fake_users)
    return fake, fake_users


# ---------- unsubscribe token ----------

def test_token_roundtrip():
    tok = suppression.make_unsub_token("Person@Example.com")
    assert suppression.verify_unsub_token(tok) == "person@example.com"


def test_token_rejects_tampered_signature():
    tok = suppression.make_unsub_token("a@b.com")
    body, sig = tok.rsplit(".", 1)
    flipped = ("0" if sig[0] != "0" else "1") + sig[1:]
    assert suppression.verify_unsub_token(f"{body}.{flipped}") is None


def test_token_rejects_swapped_email():
    tok_a = suppression.make_unsub_token("a@b.com")
    tok_b = suppression.make_unsub_token("c@d.com")
    _, sig_b = tok_b.rsplit(".", 1)
    body_a, _ = tok_a.rsplit(".", 1)
    assert suppression.verify_unsub_token(f"{body_a}.{sig_b}") is None


def test_token_rejects_garbage():
    assert suppression.verify_unsub_token("") is None
    assert suppression.verify_unsub_token("no-dot-here") is None
    assert suppression.verify_unsub_token("!!!.abc") is None
    assert suppression.verify_unsub_token(None) is None


def test_token_rejects_correctly_signed_non_email_payload():
    # Even with a valid signature, a payload that is not email-shaped is
    # rejected before anything downstream trusts it.
    payload = "not an email at all"
    body = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    tok = f"{body}.{suppression._sign_email(payload)}"
    assert suppression.verify_unsub_token(tok) is None


def test_unsubscribe_url_contains_endpoint_and_token():
    url = suppression.unsubscribe_url("a@b.com")
    assert "/api/unsubscribe?token=" in url
    token = url.split("token=", 1)[1]
    assert suppression.verify_unsub_token(token) == "a@b.com"


# ---------- suppression list ----------

def test_not_suppressed_by_default(monkeypatch):
    _wire(monkeypatch)
    assert asyncio.run(suppression.is_suppressed("a@b.com")) is False
    assert asyncio.run(suppression.is_suppressed("a@b.com", marketing=False)) is False


def test_unsubscribe_blocks_marketing_not_transactional(monkeypatch):
    _wire(monkeypatch)
    asyncio.run(suppression.suppress("a@b.com", "unsubscribe"))
    assert asyncio.run(suppression.is_suppressed("a@b.com")) is True
    assert asyncio.run(suppression.is_suppressed("a@b.com", marketing=False)) is False


def test_bounce_blocks_everything(monkeypatch):
    _wire(monkeypatch)
    asyncio.run(suppression.suppress("a@b.com", "bounce"))
    assert asyncio.run(suppression.is_suppressed("a@b.com")) is True
    assert asyncio.run(suppression.is_suppressed("a@b.com", marketing=False)) is True


def test_complaint_blocks_marketing_not_transactional(monkeypatch):
    _wire(monkeypatch)
    asyncio.run(suppression.suppress("a@b.com", "complaint"))
    assert asyncio.run(suppression.is_suppressed("a@b.com")) is True
    assert asyncio.run(suppression.is_suppressed("a@b.com", marketing=False)) is False


def test_suppress_lowercases_and_bounce_upgrades(monkeypatch):
    fake, _ = _wire(monkeypatch)
    asyncio.run(suppression.suppress("Mixed@Case.IO", "unsubscribe"))
    assert "mixed@case.io" in fake.docs
    assert fake.docs["mixed@case.io"]["reason"] == "unsubscribe"
    # A later bounce upgrades the reason (bounce blocks transactional too)...
    asyncio.run(suppression.suppress("mixed@case.io", "bounce"))
    assert fake.docs["mixed@case.io"]["reason"] == "bounce"
    # ...but a later unsubscribe does not downgrade it.
    asyncio.run(suppression.suppress("mixed@case.io", "unsubscribe"))
    assert fake.docs["mixed@case.io"]["reason"] == "bounce"


def test_apply_unsubscribe_suppresses_and_disables_nurture(monkeypatch):
    fake, fake_users = _wire(monkeypatch)
    asyncio.run(suppression.apply_unsubscribe("Person@Example.com"))
    assert fake.docs["person@example.com"]["reason"] == "unsubscribe"
    assert fake_users.updates == [
        ({"email": "person@example.com"}, {"$set": {"nurture_enabled": False}})
    ]


# ---------- Resend (svix) webhook signature ----------

_WH_SECRET_BYTES = b"0123456789abcdef0123456789abcdef"
_WH_SECRET = "whsec_" + base64.b64encode(_WH_SECRET_BYTES).decode()


def _sign(msg_id, ts, body: bytes) -> str:
    signed = f"{msg_id}.{ts}.{body.decode()}".encode()
    mac = hmac_mod.new(_WH_SECRET_BYTES, signed, hashlib.sha256).digest()
    return "v1," + base64.b64encode(mac).decode()


def test_webhook_signature_valid():
    body = b'{"type":"email.bounced"}'
    ts = str(int(time.time()))
    sig = _sign("msg_1", ts, body)
    assert suppression.verify_resend_signature(_WH_SECRET, "msg_1", ts, sig, body) is True


def test_webhook_signature_multiple_space_delimited():
    body = b"{}"
    ts = str(int(time.time()))
    sig = "v1,bm90aGluZw== " + _sign("m", ts, body)
    assert suppression.verify_resend_signature(_WH_SECRET, "m", ts, sig, body) is True


def test_webhook_signature_wrong_sig_fails():
    body = b"{}"
    ts = str(int(time.time()))
    assert (
        suppression.verify_resend_signature(_WH_SECRET, "m", ts, "v1,AAAA", body)
        is False
    )


def test_webhook_signature_stale_timestamp_fails():
    body = b"{}"
    ts = str(int(time.time()) - 3600)
    sig = _sign("m", ts, body)
    assert suppression.verify_resend_signature(_WH_SECRET, "m", ts, sig, body) is False


def test_webhook_signature_malformed_inputs_fail():
    body = b"{}"
    ts = str(int(time.time()))
    sig = _sign("m", ts, body)
    assert suppression.verify_resend_signature("", "m", ts, sig, body) is False
    assert suppression.verify_resend_signature(_WH_SECRET, None, ts, sig, body) is False
    assert suppression.verify_resend_signature(_WH_SECRET, "m", "not-a-number", sig, body) is False
    assert suppression.verify_resend_signature(_WH_SECRET, "m", ts, "", body) is False


# ---------- webhook event handling ----------

def test_bounced_event_suppresses_as_bounce(monkeypatch):
    fake, _ = _wire(monkeypatch)
    out = asyncio.run(
        suppression.handle_resend_event(
            {"type": "email.bounced", "data": {"to": ["X@Y.com"]}}
        )
    )
    assert out["suppressed"] == 1
    assert fake.docs["x@y.com"]["reason"] == "bounce"


def test_complained_event_suppresses_as_complaint(monkeypatch):
    fake, _ = _wire(monkeypatch)
    asyncio.run(
        suppression.handle_resend_event(
            {"type": "email.complained", "data": {"to": ["a@b.com", "c@d.com"]}}
        )
    )
    assert fake.docs["a@b.com"]["reason"] == "complaint"
    assert fake.docs["c@d.com"]["reason"] == "complaint"


def test_to_as_plain_string_is_handled(monkeypatch):
    fake, _ = _wire(monkeypatch)
    asyncio.run(
        suppression.handle_resend_event(
            {"type": "email.bounced", "data": {"to": "solo@x.com"}}
        )
    )
    assert "solo@x.com" in fake.docs


def test_other_event_types_ignored(monkeypatch):
    fake, _ = _wire(monkeypatch)
    out = asyncio.run(
        suppression.handle_resend_event(
            {"type": "email.delivered", "data": {"to": ["a@b.com"]}}
        )
    )
    assert out.get("ignored") == "email.delivered"
    assert fake.docs == {}


# ---------- marketing send wrapper ----------

def _capture_send(monkeypatch, result=None):
    calls = []

    async def fake_send(to, subject, html, text=None, reply_to=None, headers=None):
        calls.append(
            {"to": to, "subject": subject, "html": html, "text": text, "headers": headers}
        )
        return result or {"sent": True, "id": "fake"}

    monkeypatch.setattr(email_send, "send_email", fake_send)
    return calls


def test_marketing_send_skips_suppressed(monkeypatch):
    _wire(monkeypatch)
    calls = _capture_send(monkeypatch)
    monkeypatch.setattr(email_send, "RESEND_API_KEY", "k")
    asyncio.run(suppression.suppress("a@b.com", "unsubscribe"))
    out = asyncio.run(
        email_send.send_marketing_email("a@b.com", "s", "<p>hi</p>", text="hi")
    )
    assert out == {"sent": False, "reason": "suppressed"}
    assert calls == []


def test_marketing_send_dormant_without_key(monkeypatch):
    _wire(monkeypatch)
    calls = _capture_send(monkeypatch)
    monkeypatch.setattr(email_send, "RESEND_API_KEY", "")
    out = asyncio.run(email_send.send_marketing_email("a@b.com", "s", "<p>hi</p>"))
    assert out["sent"] is False
    assert calls == []


def test_transactional_send_blocked_on_hard_bounce(monkeypatch):
    # send_email itself refuses hard-bounced addresses (central enforcement,
    # covering password resets and imported-account credentials too)...
    _wire(monkeypatch)
    monkeypatch.setattr(email_send, "RESEND_API_KEY", "k")
    asyncio.run(suppression.suppress("dead@x.com", "bounce"))
    out = asyncio.run(email_send.send_email("dead@x.com", "s", "<p>hi</p>"))
    assert out == {"sent": False, "reason": "suppressed"}


def test_transactional_send_not_blocked_by_unsubscribe(monkeypatch):
    # ...but an unsubscribe only blocks marketing mail: the transactional path
    # gets past the suppression gate (send captured before any network call).
    _wire(monkeypatch)
    calls = _capture_send(monkeypatch)
    monkeypatch.setattr(email_send, "RESEND_API_KEY", "k")
    asyncio.run(suppression.suppress("a@b.com", "unsubscribe"))
    assert asyncio.run(suppression.is_suppressed("a@b.com", marketing=False)) is False
    out = asyncio.run(
        email_send.send_marketing_email("a@b.com", "s", "<p>hi</p>")
    )
    assert out == {"sent": False, "reason": "suppressed"}
    assert calls == []


def test_marketing_send_adds_footer_and_list_unsubscribe(monkeypatch):
    _wire(monkeypatch)
    calls = _capture_send(monkeypatch)
    monkeypatch.setattr(email_send, "RESEND_API_KEY", "k")
    out = asyncio.run(
        email_send.send_marketing_email("a@b.com", "s", "<p>hi</p>", text="hi")
    )
    assert out["sent"] is True
    assert len(calls) == 1
    call = calls[0]
    url = suppression.unsubscribe_url("a@b.com")
    assert url in call["html"]
    assert "Unsubscribe" in call["html"]
    assert url in call["text"]
    assert call["headers"]["List-Unsubscribe"] == f"<{url}>"
    assert call["headers"]["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
