"""Task 6: attendee mail goes out as the host.

Covers the From display name and reply-to, the host header (name, optional
round headshot), the single Intro Connect mention in the footer, and that mail
sent without a host context renders exactly as it did before.
Run from backend/: python -m pytest tests/test_host_sender.py
"""
import asyncio
import base64
import hashlib
import os
from datetime import datetime, timezone

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_host_sender")
os.environ.setdefault("JWT_SECRET", "test-secret")

import core
import email_layout as el
import email_send
import invites
import suppression

FROM = "Intro Connect <hello@intro-connect.com>"
HOST = {"name": "Jane Doe", "email": "jane@acme.co", "photo_url": "https://cdn.test/jane.jpg"}
NO_PHOTO = {**HOST, "photo_url": ""}


def _sha(html: str) -> str:
    return hashlib.sha256(html.encode()).hexdigest()


# ---------- snapshot: no host means no change ----------
# Hashes captured from email_layout.render BEFORE the host layout existed.

_BASELINE = {
    "full": "6ee04072afd316d86ce79ff56b43621436932146afcc2393931e62dab921151a",
    "pro_brand": "f6402d1c4b83f2f0653d7ab136c7b30eb379d852f7e0a177ab83842b7c7ef46e",
    "plain": "bb17a361e638edcb030404bb18c4de4a9bcfbef5013b4f6c584c670836255949",
}


def test_render_without_host_is_byte_identical_to_before():
    full = el.render(
        heading="Welcome back",
        paragraphs=["Hi there.", "Second line."],
        button={"label": "Open your directory", "url": "https://x.test/go"},
        unsubscribe_url="https://x.test/u?t=1",
    )
    pro = el.render(
        heading="Welcome back",
        paragraphs=["Hi there."],
        button={"label": "Go", "url": "https://x.test/go"},
        brand={"logo_url": "https://x.test/l.png", "accent_dark": "#123456"},
    )
    plain = el.render(heading="Plain", paragraphs=["Only."])
    assert _sha(full) == _BASELINE["full"]
    assert _sha(pro) == _BASELINE["pro_brand"]
    assert _sha(plain) == _BASELINE["plain"]


# ---------- host_block ----------

def test_host_block_reads_name_email_and_photo():
    user = {"email": "jane@acme.co", "profile": {"name": " Jane Doe ", "photo_url": "https://p/x.jpg"}}
    assert core.host_block(user) == {
        "name": "Jane Doe", "email": "jane@acme.co", "photo_url": "https://p/x.jpg",
    }


def test_host_block_never_falls_back_to_the_email_for_the_name():
    block = core.host_block({"email": "jane@acme.co", "profile": {"name": "  "}})
    assert block["name"] == "Your host"
    assert "jane" not in block["name"]
    assert block["photo_url"] == ""


def test_host_block_is_none_for_a_missing_user():
    assert core.host_block(None) is None
    assert core.host_block({}) is None


# ---------- host header ----------

def _host_html(host=HOST, **kw):
    base = dict(heading="You are invited", paragraphs=["Hello."], host=host)
    base.update(kw)
    return el.render(**base)


def test_headshot_renders_only_with_a_photo():
    with_photo = _host_html(HOST)
    assert '<img src="https://cdn.test/jane.jpg"' in with_photo
    assert 'width="56" height="56"' in with_photo
    assert "border-radius:50%" in with_photo
    without = _host_html(NO_PHOTO)
    assert "border-radius:50%" not in without
    assert 'width="56"' not in without


def test_host_name_is_in_the_header_and_escaped():
    html = _host_html({**HOST, "name": "<b>Jane</b>"})
    assert "&lt;b&gt;Jane&lt;/b&gt;" in html
    assert "<b>Jane</b>" not in html


def test_host_header_replaces_the_platform_lockup_at_the_top():
    html = _host_html()
    assert html.index("Jane Doe") < html.index("Intro Connect")
    assert el.LOGO_URL not in html.split("Jane Doe")[0]


def test_pro_logo_still_renders_beside_the_host():
    brand = {"logo_url": "https://x.test/l.png", "accent_dark": "#0a5c36"}
    html = _host_html(brand=brand, button={"label": "Go", "url": "https://x.test"})
    assert "https://x.test/l.png" in html
    assert 'bgcolor="#0a5c36"' in html
    assert html.count("Intro Connect") == 1  # no "via Intro Connect" credit


# ---------- footer ----------

def test_footer_names_intro_connect_exactly_once():
    for host in (HOST, NO_PHOTO):
        html = _host_html(host, unsubscribe_url="https://x.test/u")
        assert html.count("Intro Connect") == 1
        assert "You are receiving this because" not in html
        assert "&copy;" not in html


def test_footer_carries_the_sign_in_link_and_host_name():
    html = _host_html(sign_in_url="https://app.test/login")
    footer = html[html.rindex("Sent for") :]
    assert "Jane Doe" in footer
    assert 'href="https://app.test/login"' in footer


def test_sign_in_link_defaults_to_the_app_login():
    from app_url import APP_URL

    assert f'href="{APP_URL}/login"' in _host_html()


def test_unsubscribe_link_survives_in_the_host_footer():
    html = _host_html(unsubscribe_url="https://x.test/u?t=9")
    assert 'href="https://x.test/u?t=9"' in html


# ---------- sender: From header and reply-to ----------

class _FakeResp:
    status_code = 200
    text = ""

    def json(self):
        return {"id": "m1"}


def _capture(monkeypatch):
    """Stand in for Resend: record every JSON payload posted."""
    posted = []

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            posted.append(json)
            return _FakeResp()

    async def _not_suppressed(*a, **k):
        return False

    monkeypatch.setattr(email_send, "RESEND_API_KEY", "re_test")
    monkeypatch.setattr(email_send, "EMAIL_FROM", FROM)
    monkeypatch.setattr(email_send.httpx, "AsyncClient", _Client)
    monkeypatch.setattr(suppression, "is_suppressed", _not_suppressed)
    return posted


def _branded(**kw):
    base = dict(heading="H", paragraphs=["p"], marketing=False)
    base.update(kw)
    return asyncio.run(email_send.send_branded("guest@x.test", "Subject", **base))


def test_host_send_uses_the_hosts_name_on_our_address(monkeypatch):
    posted = _capture(monkeypatch)
    _branded(host=HOST)
    assert posted[0]["from"] == "Jane Doe via Intro Connect <hello@intro-connect.com>"
    assert posted[0]["reply_to"] == "jane@acme.co"


def test_explicit_reply_to_wins_over_the_host(monkeypatch):
    posted = _capture(monkeypatch)
    _branded(host=HOST, reply_to="other@acme.co")
    assert posted[0]["reply_to"] == "other@acme.co"


def test_marketing_host_send_keeps_unsubscribe_and_host_sender(monkeypatch):
    posted = _capture(monkeypatch)
    _branded(host=HOST, marketing=True)
    assert posted[0]["from"].startswith("Jane Doe via Intro Connect <")
    assert "List-Unsubscribe" in posted[0]["headers"]
    assert "Unsubscribe" in posted[0]["html"]


def test_send_without_host_is_unchanged(monkeypatch):
    posted = _capture(monkeypatch)
    _branded()
    assert posted[0]["from"] == FROM
    assert "reply_to" not in posted[0]
    assert "You are receiving this because" in posted[0]["html"]


def test_template_send_goes_out_as_the_host(monkeypatch):
    posted = _capture(monkeypatch)
    asyncio.run(
        email_send.send_template_branded(
            "guest@x.test",
            {"subject": "S", "body": "One.\n\nTwo."},
            button_label="Open",
            button_url="https://x.test/o",
            host=HOST,
        )
    )
    assert posted[0]["from"] == "Jane Doe via Intro Connect <hello@intro-connect.com>"
    assert posted[0]["reply_to"] == "jane@acme.co"
    assert posted[0]["html"].count("Intro Connect") == 1
    assert 'width="56" height="56"' in posted[0]["html"]


def test_a_hostile_host_name_cannot_break_the_from_header(monkeypatch):
    posted = _capture(monkeypatch)
    _branded(host={**HOST, "name": 'Jane"\r\nBcc: spy@evil.test <x'})
    sender = posted[0]["from"]
    assert "\r" not in sender and "\n" not in sender
    assert sender.endswith(' via Intro Connect" <hello@intro-connect.com>')
    assert sender.count("<") == 1 and sender.count('"') == 2


# ---------- invites and reminders ----------

def test_invite_and_reminder_copy_does_not_name_intro_connect():
    for paras in (invites.invite_paragraphs("Dinner", "Jane"), invites.reminder_paragraphs("Dinner", "Jane")):
        assert "Intro Connect" not in " ".join(paras)


class _Invites:
    def __init__(self, docs=None):
        self.docs = docs or []
        self.updates = []

    def find(self, q, proj=None):
        outer = self

        class _Cur:
            async def to_list(self, _n):
                return []

            def __aiter__(self):
                self._it = iter(outer.docs)
                return self

            async def __anext__(self):
                try:
                    return next(self._it)
                except StopIteration:
                    raise StopAsyncIteration

        return _Cur()

    async def update_one(self, q, u, upsert=False):
        self.updates.append((q, u))

    async def find_one_and_update(self, q, u):
        return {"_id": q["_id"]}


class _Sender:
    def __init__(self):
        self.calls = []

    def is_configured(self):
        return True

    async def send_branded(self, *, to, **kw):
        self.calls.append(kw)
        return {"sent": True}


_EVENT = {"_id": "evt1", "join_code": "ABC123", "name": "Dinner"}


def test_send_event_invites_passes_the_host_through(monkeypatch):
    sender = _Sender()
    monkeypatch.setattr(invites, "event_invites", _Invites())
    monkeypatch.setattr(invites, "email_send", sender)
    asyncio.run(invites.send_event_invites(_EVENT, ["a@x.test"], "Jane Doe", host=HOST))
    assert sender.calls[0]["host"] == HOST


def _reminder_world(monkeypatch, host_user):
    from datetime import datetime, timedelta, timezone

    inv = {
        "_id": "i1", "event_id": "evt1", "email": "a@x.test", "host_name": "Jane Doe",
        "reminder_step": 0, "joined_at": None,
        "invited_at": datetime.now(timezone.utc) - timedelta(days=3),
    }

    class _One:
        def __init__(self, doc):
            self.doc = doc

        async def find_one(self, q):
            return self.doc

    sender = _Sender()
    monkeypatch.setattr(invites, "event_invites", _Invites([inv]))
    monkeypatch.setattr(invites, "events", _One({**_EVENT, "created_by": "u1"}))
    monkeypatch.setattr(invites, "users", _One(host_user))
    monkeypatch.setattr(invites, "email_send", sender)
    return sender


def test_reminder_tick_sends_as_the_host(monkeypatch):
    user = {"_id": "u1", "email": "jane@acme.co", "profile": {"name": "Jane Doe", "photo_url": ""}}
    sender = _reminder_world(monkeypatch, user)
    asyncio.run(invites.run_invite_reminder_tick())
    assert sender.calls[0]["host"] == {"name": "Jane Doe", "email": "jane@acme.co", "photo_url": ""}


def test_reminder_for_a_deleted_host_falls_back_to_the_platform_layout(monkeypatch):
    sender = _reminder_world(monkeypatch, None)
    asyncio.run(invites.run_invite_reminder_tick())
    assert sender.calls[0]["host"] is None


# ---------- headshots must be loadable by an email client ----------

_PNG = b"fake-png-bytes"
_DATA_URL = "data:image/png;base64," + base64.b64encode(_PNG).decode()


def test_an_uploaded_photo_becomes_a_public_url():
    user = {"_id": "64b000000000000000000001", "email": "j@x.co",
            "profile": {"name": "Jane", "photo_url": _DATA_URL}}
    url = core.host_block(user)["photo_url"]
    assert url == f"{suppression.API_PUBLIC_URL}/api/public/host-photo/64b000000000000000000001"
    assert "data:" not in url


def test_an_https_photo_passes_through_unchanged():
    user = {"_id": "u1", "email": "j@x.co",
            "profile": {"name": "Jane", "photo_url": "https://cdn.test/jane.jpg"}}
    assert core.host_block(user)["photo_url"] == "https://cdn.test/jane.jpg"


def test_a_data_photo_without_an_id_is_dropped_rather_than_sent_inline():
    user = {"email": "j@x.co", "profile": {"name": "Jane", "photo_url": _DATA_URL}}
    assert core.host_block(user)["photo_url"] == ""


def _photo_client(monkeypatch, photo):
    from bson import ObjectId
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from routers import branding as branding_router

    oid = ObjectId()

    class _Users:
        async def find_one(self, q):
            return {"_id": oid, "profile": {"photo_url": photo}} if q["_id"] == oid else None

    monkeypatch.setattr(branding_router, "users", _Users())
    app = FastAPI()
    app.include_router(branding_router.router)
    return TestClient(app), oid


def test_the_photo_route_serves_the_decoded_bytes(monkeypatch):
    client, oid = _photo_client(monkeypatch, _DATA_URL)
    r = client.get(f"/api/public/host-photo/{oid}")
    assert r.status_code == 200
    assert r.content == _PNG
    assert r.headers["content-type"] == "image/png"
    assert "max-age" in r.headers["cache-control"]


def test_the_photo_route_404s_without_a_data_photo(monkeypatch):
    for photo in ("", "https://cdn.test/jane.jpg", "data:image/png;base64,@@not-base64@@"):
        client, oid = _photo_client(monkeypatch, photo)
        assert client.get(f"/api/public/host-photo/{oid}").status_code == 404
    assert client.get("/api/public/host-photo/not-an-id").status_code == 404


# ---------- From header quoting ----------

def test_a_comma_in_the_host_name_is_quoted_in_the_from_header(monkeypatch):
    posted = _capture(monkeypatch)
    _branded(host={**HOST, "name": "Smith, Jane"})
    assert posted[0]["from"] == (
        '"Smith, Jane via Intro Connect" <hello@intro-connect.com>'
    )


# ---------- subjects lead with the event name ----------

def test_invite_and_reminder_subjects_lead_with_the_event_name():
    assert invites.invite_subject("Denver Dinner") == "Denver Dinner: you are invited"
    assert invites.reminder_subject("Denver Dinner").startswith("Denver Dinner: ")
    for subject in (invites.invite_subject("E"), invites.reminder_subject("E")):
        assert "—" not in subject and "–" not in subject and "-" not in subject


def test_reminder_tick_uses_the_reminder_subject(monkeypatch):
    sender = _reminder_world(monkeypatch, None)
    asyncio.run(invites.run_invite_reminder_tick())
    assert sender.calls[0]["subject"] == invites.reminder_subject("Dinner")


def test_seeded_attendee_invitations_lead_with_the_event_name():
    from template_seeds import DEFAULT_TEMPLATES

    by_id = {t["template_id"]: t for t in DEFAULT_TEMPLATES}
    for template_id in ("invitation", "save-the-date"):
        assert by_id[template_id]["subject"].startswith("{event_name}:")


# ---------- an admin import sends as the event's host ----------

def test_an_admin_import_into_a_hosts_event_sends_as_that_host(monkeypatch):
    import attendee_import

    admin = {"_id": "admin-1", "email": "jim@ic.co", "profile": {"name": "Jim"}}
    owner = {"_id": "host-9", "email": "jane@acme.co", "profile": {"name": "Jane Doe"}}
    event = {"_id": "evt", "name": "Dinner", "created_by": "host-9",
             "date": datetime(2026, 9, 1, tzinfo=timezone.utc), "location": "Denver"}
    sent, rendered_for = [], []

    class _Users:
        async def find_one(self, q):
            if "email" in q:
                return None
            return owner if q["_id"] == "host-9" else None

        async def insert_one(self, doc):
            class R:
                inserted_id = "new"
            return R()

    class _Attendees:
        async def find_one(self, _q):
            return None

        async def insert_one(self, doc):
            pass

        async def count_documents(self, _q):
            return 0

    async def _render(_name, _ctx, host_id=None):
        rendered_for.append((host_id, _ctx["host_name"]))
        return {"subject": "s", "body": "b"}

    async def _send(*, to, **kw):
        sent.append(kw)
        return {"sent": True}

    monkeypatch.setattr(attendee_import, "users", _Users())
    monkeypatch.setattr(attendee_import, "event_attendees", _Attendees())
    monkeypatch.setattr(core, "users", _Users())
    monkeypatch.setattr(core, "event_attendees", _Attendees())
    monkeypatch.setattr(attendee_import.email_send, "is_configured", lambda: True)
    monkeypatch.setattr(attendee_import, "hash_password", lambda p: "h")
    monkeypatch.setattr(attendee_import.host_templates, "render_for_host", _render)
    monkeypatch.setattr(attendee_import.email_send, "send_template_branded", _send)

    class _Row:
        email, name = "a@x.co", "A"
        role = company = industry = bio = looking_for = phone = linkedin = ""

    asyncio.run(
        attendee_import.import_rows(actor=admin, rows=[_Row()], event_doc=event, event_oid="evt")
    )
    assert sent[0]["host"]["name"] == "Jane Doe"
    assert sent[0]["host"]["email"] == "jane@acme.co"
    assert rendered_for == [("host-9", "Jane Doe")]
