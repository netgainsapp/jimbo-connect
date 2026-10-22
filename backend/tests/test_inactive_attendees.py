"""Imported guests are the host's customers until they activate.

What this covers: an import seats someone as not yet active, signing in or
joining activates them everywhere, reminders stop once the event is a day
away, and the remove-me link takes a guest off one event's list for good
(a re-import skips them) without touching any other event.

Run from backend/: python -m pytest tests/test_inactive_attendees.py
"""
import asyncio
import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

from bson import ObjectId
from fastapi.testclient import TestClient

import attendee_import
import core
import directory
import invites
import server
from event_leads_rules import DENVER
from routers import auth as auth_router
from routers import events as events_router

client = TestClient(server.app)

E1, E2 = ObjectId(), ObjectId()
HOST = ObjectId()
REMOVE_PREFIX = "If you would rather not be on this list, remove yourself: "


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# A tiny in-memory collection: just the query shapes this feature uses.
# ---------------------------------------------------------------------------

def _matches(doc, query):
    for key, want in query.items():
        have = doc.get(key)
        if isinstance(want, dict):
            if "$exists" in want and (key in doc) != want["$exists"]:
                return False
            if "$gte" in want and not (have is not None and have >= want["$gte"]):
                return False
            if "$lt" in want and not (have is not None and have < want["$lt"]):
                return False
            if "$in" in want and have not in want["$in"]:
                return False
            if "$ne" in want and have == want["$ne"]:
                return False
        elif have != want:
            return False
    return True


class _Cursor:
    def __init__(self, rows):
        self._rows = list(rows)

    async def to_list(self, _n=None):
        return list(self._rows)

    def __aiter__(self):
        self._it = iter(self._rows)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


class _Coll:
    def __init__(self, rows=()):
        self.rows = [dict(r) for r in rows]

    async def find_one(self, query, *_proj):
        return next((r for r in self.rows if _matches(r, query)), None)

    def find(self, query=None, *_proj):
        return _Cursor(r for r in self.rows if _matches(r, query or {}))

    async def insert_one(self, doc):
        doc = dict(doc)
        doc.setdefault("_id", ObjectId())
        self.rows.append(doc)
        return type("R", (), {"inserted_id": doc["_id"]})()

    async def update_one(self, query, update, upsert=False):
        row = await self.find_one(query)
        if row is None:
            if not upsert:
                return type("R", (), {"matched_count": 0})()
            row = {k: v for k, v in query.items() if not isinstance(v, dict)}
            row.update(update.get("$setOnInsert", {}))
            self.rows.append(row)
        row.update(update.get("$set", {}))
        return type("R", (), {"matched_count": 1})()

    async def find_one_and_update(self, query, update):
        row = await self.find_one(query)
        if row is not None:
            row.update(update.get("$set", {}))
        return row

    async def delete_one(self, query):
        row = await self.find_one(query)
        if row is not None:
            self.rows.remove(row)
        return type("R", (), {"deleted_count": int(row is not None)})()

    async def count_documents(self, query):
        return sum(1 for r in self.rows if _matches(r, query))


class _Row:
    """Stands in for BulkImportRow; only the fields the import reads."""

    def __init__(self, email, name=""):
        self.email = email
        self.name = name
        self.role = self.company = self.industry = ""
        self.bio = self.looking_for = self.phone = self.linkedin = ""


EVENT = {
    "_id": E1,
    "name": "Dinner",
    "created_by": HOST,
    "date": datetime(2026, 12, 1, 18, tzinfo=timezone.utc),
    "location": "Denver",
    "join_code": "DIN123",
}


def _wire_import(monkeypatch, *, invite_rows=(), user_rows=(), link_rows=(),
                 email_on=False):
    users = _Coll([{"_id": HOST, "plan": "pro", "profile": {"name": "Scott"}},
                   *user_rows])
    links = _Coll(link_rows)
    invite_coll = _Coll(invite_rows)
    for module in (attendee_import, core):
        monkeypatch.setattr(module, "users", users)
        monkeypatch.setattr(module, "event_attendees", links)
    monkeypatch.setattr(invites, "event_invites", invite_coll)
    monkeypatch.setattr(attendee_import.email_send, "is_configured", lambda: email_on)
    monkeypatch.setattr(attendee_import, "hash_password", lambda p: "hashed:" + p)
    return users, links, invite_coll


def _import(rows):
    return _run(attendee_import.import_rows(
        actor={"_id": HOST, "profile": {"name": "Scott"}},
        rows=rows, event_doc=EVENT, event_oid=E1,
    ))


# ---------------------------------------------------------------------------
# Imported guests start inactive
# ---------------------------------------------------------------------------

def test_an_imported_guest_is_seated_as_not_yet_active(monkeypatch):
    users, links, _ = _wire_import(monkeypatch)
    out = _import([_Row("new@acme.co", "Ann")])
    assert out["added_to_event"] == 1
    membership = links.rows[0]
    assert membership["activated"] is False
    created = next(u for u in users.rows if u.get("email") == "new@acme.co")
    assert "activated_at" not in created


def test_importing_someone_who_joined_an_event_themselves_seats_them_active(monkeypatch):
    """An account from before activation existed has no activated_at, but a
    membership no import made shows they came in on their own."""
    veteran = ObjectId()
    _, links, _ = _wire_import(
        monkeypatch,
        user_rows=[{"_id": veteran, "email": "veteran@acme.co", "profile": {}}],
        link_rows=[{"event_id": E2, "user_id": veteran, "joined_at": 1}],
    )
    _import([_Row("veteran@acme.co")])
    seat = next(r for r in links.rows if r["event_id"] == E1)
    assert seat["activated"] is True


def test_importing_someone_only_ever_imported_seats_them_inactive(monkeypatch):
    stranger = ObjectId()
    _, links, _ = _wire_import(
        monkeypatch,
        user_rows=[{"_id": stranger, "email": "stranger@acme.co", "profile": {}}],
        link_rows=[{"event_id": E2, "user_id": stranger, "imported_at": 1,
                    "activated": False}],
    )
    _import([_Row("stranger@acme.co")])
    seat = next(r for r in links.rows if r["event_id"] == E1)
    assert seat["activated"] is False


def test_a_join_by_code_seats_an_active_member_and_activates_the_person(monkeypatch):
    person = {"_id": ObjectId(), "email": "walkin@acme.co"}
    users = _Coll([person])
    links = _Coll()
    monkeypatch.setattr(core, "users", users)
    monkeypatch.setattr(events_router, "event_attendees", links)

    async def _room(*_a, **_k):
        return None

    async def _joined(*_a):
        return None

    monkeypatch.setattr(events_router, "assert_event_has_room", _room)
    monkeypatch.setattr(events_router.invites, "mark_joined", _joined)
    _run(events_router._join_user_to_event(EVENT, person))
    assert links.rows[0]["activated"] is True
    assert isinstance(users.rows[0].get("activated_at"), datetime)


# ---------------------------------------------------------------------------
# Signing in activates, once
# ---------------------------------------------------------------------------

def _wire_login(monkeypatch, user):
    users = _Coll([user])
    monkeypatch.setattr(auth_router, "users", users)
    monkeypatch.setattr(core, "users", users)
    monkeypatch.setattr(auth_router, "verify_password", lambda _p, _h: True)
    return users


def test_password_login_sets_activated_at(monkeypatch):
    users = _wire_login(monkeypatch, {
        "_id": ObjectId(), "email": "login@acme.co", "password_hash": "h",
        "profile": {}, "is_admin": False,
    })
    res = client.post("/api/auth/login",
                      json={"email": "login@acme.co", "password": "whatever1"})
    assert res.status_code == 200
    assert isinstance(users.rows[0].get("activated_at"), datetime)


def test_a_second_login_keeps_the_first_activation_time(monkeypatch):
    first = datetime(2026, 1, 1, tzinfo=timezone.utc)
    users = _wire_login(monkeypatch, {
        "_id": ObjectId(), "email": "again@acme.co", "password_hash": "h",
        "profile": {}, "is_admin": False, "activated_at": first,
    })
    client.post("/api/auth/login",
                json={"email": "again@acme.co", "password": "whatever1"})
    assert users.rows[0]["activated_at"] == first


def test_magic_link_sign_in_sets_activated_at(monkeypatch):
    token = "magic-token-value"
    users = _wire_login(monkeypatch, {
        "_id": ObjectId(), "email": "magic@acme.co", "profile": {},
        "is_admin": False, "reset_token": core._hash_token(token),
        "reset_token_expires": datetime.now(timezone.utc) + timedelta(hours=1),
    })
    res = client.get(f"/api/auth/magic/{token}")
    assert res.status_code == 200
    assert isinstance(users.rows[0].get("activated_at"), datetime)


def _wire_session(monkeypatch, user):
    import auth

    users = _Coll([user])
    monkeypatch.setattr(auth, "users", users)
    monkeypatch.setattr(core, "users", users)
    client.cookies.set(auth.COOKIE_NAME, auth.create_access_token(str(user["_id"])))
    return users


def test_a_session_load_activates_an_account_from_before_activation(monkeypatch):
    """Long lived accounts come back on a cookie, never a fresh login."""
    users = _wire_session(monkeypatch, {"_id": ObjectId(), "email": "old@acme.co",
                                        "profile": {}, "is_admin": False})
    try:
        assert client.get("/api/auth/me").status_code == 200
        stamped = users.rows[0]["activated_at"]
        assert isinstance(stamped, datetime)
        client.get("/api/auth/me")
        assert users.rows[0]["activated_at"] == stamped
    finally:
        client.cookies.clear()


def test_a_session_refresh_activates_too(monkeypatch):
    users = _wire_session(monkeypatch, {"_id": ObjectId(), "email": "r@acme.co",
                                        "profile": {}, "is_admin": False})
    try:
        assert client.post("/api/auth/refresh").status_code == 200
        assert isinstance(users.rows[0].get("activated_at"), datetime)
    finally:
        client.cookies.clear()


def test_a_self_registered_user_is_active_from_the_start(monkeypatch):
    users = _Coll()
    monkeypatch.setattr(auth_router, "users", users)

    async def _quiet(*_a, **_k):
        return None

    monkeypatch.setattr(auth_router.nurture, "send_welcome", _quiet)
    monkeypatch.setattr(auth_router, "issue_email_verification", _quiet)
    res = client.post("/api/auth/register", json={
        "email": "self@acme.co", "password": "longenough1", "name": "Self",
    })
    assert res.status_code == 200
    assert isinstance(users.rows[0].get("activated_at"), datetime)


# ---------------------------------------------------------------------------
# What other attendees see
# ---------------------------------------------------------------------------

def test_serialize_attendee_reports_an_imported_unactivated_member_inactive():
    user = {"_id": ObjectId(), "profile": {"name": "Ann"}}
    assert core.serialize_attendee(user, membership={"activated": False})["active"] is False


def test_an_activated_person_is_active_in_every_event():
    user = {"_id": ObjectId(), "profile": {}, "activated_at": datetime.now(timezone.utc)}
    assert core.serialize_attendee(user, membership={"activated": False})["active"] is True


def test_memberships_without_the_flag_read_as_active():
    """Every membership that predates this feature joined on its own."""
    user = {"_id": ObjectId(), "profile": {}}
    assert core.serialize_attendee(user, membership={"joined_at": 1})["active"] is True
    assert core.serialize_attendee(user)["active"] is True


def test_the_event_guest_list_marks_inactive_members(monkeypatch):
    ann, bob = ObjectId(), ObjectId()
    monkeypatch.setattr(events_router, "events", _Coll([EVENT]))
    monkeypatch.setattr(events_router, "event_attendees", _Coll([
        {"event_id": E1, "user_id": ann, "activated": False},
        {"event_id": E1, "user_id": bob, "activated": True},
    ]))
    monkeypatch.setattr(events_router, "users", _Coll([
        {"_id": ann, "profile": {"name": "Ann"}},
        {"_id": bob, "profile": {"name": "Bob"}},
    ]))
    out = _run(events_router.get_event_attendees(str(E1), user={"_id": HOST}))
    by_name = {a["profile"]["name"]: a["active"] for a in out}
    assert by_name == {"Ann": False, "Bob": True}


def test_the_all_events_view_marks_inactive_members_too(monkeypatch):
    me, ann = ObjectId(), ObjectId()
    monkeypatch.setattr(events_router, "event_attendees", _Coll([
        {"event_id": E1, "user_id": me, "activated": True},
        {"event_id": E1, "user_id": ann, "activated": False},
    ]))
    monkeypatch.setattr(events_router, "users", _Coll([
        {"_id": ann, "profile": {"name": "Ann"}},
    ]))
    out = _run(events_router.my_attendees(user={"_id": me}))
    assert [a["active"] for a in out] == [False]


def test_an_imported_inactive_member_is_never_in_the_directory(monkeypatch):
    ann = ObjectId()
    monkeypatch.setattr(directory, "event_attendees", _Coll([
        {"event_id": E1, "user_id": ann, "activated": False},
    ]))
    monkeypatch.setattr(directory, "users", _Coll([
        {"_id": ann, "profile": {"name": "Ann"}},
    ]))
    assert _run(directory.list_people(ObjectId())) == []


# ---------------------------------------------------------------------------
# Reminders stop once the event is a day away
# ---------------------------------------------------------------------------

class _Mail:
    def __init__(self):
        self.sent = []

    def is_configured(self):
        return True

    async def send_branded(self, **kw):
        self.sent.append(kw)
        return {"sent": True}


def _denver(y, m, d, hour):
    return datetime(y, m, d, hour, tzinfo=DENVER)


def _wire_tick(monkeypatch, event_date, **invite_extra):
    invite = {
        "_id": ObjectId(), "event_id": E1, "email": "g@acme.co",
        "joined_at": None, "reminder_step": 0, "host_name": "Scott",
        "invited_at": _denver(2026, 11, 1, 9), **invite_extra,
    }
    invite_coll = _Coll([invite])
    mail = _Mail()
    monkeypatch.setattr(invites, "event_invites", invite_coll)
    monkeypatch.setattr(invites, "events", _Coll([{**EVENT, "date": event_date}]))
    monkeypatch.setattr(invites, "users", _Coll())
    monkeypatch.setattr(invites, "email_send", mail)
    return invite_coll, mail


NOW = _denver(2026, 11, 20, 10)


def test_a_reminder_still_goes_out_the_day_before_the_event(monkeypatch):
    invite_coll, mail = _wire_tick(monkeypatch, _denver(2026, 11, 21, 18))
    _run(invites.run_invite_reminder_tick(now=NOW))
    assert len(mail.sent) == 1
    assert invite_coll.rows[0]["reminder_step"] == 1


def test_no_reminder_on_the_day_of_the_event(monkeypatch):
    invite_coll, mail = _wire_tick(monkeypatch, _denver(2026, 11, 20, 23))
    _run(invites.run_invite_reminder_tick(now=NOW))
    assert mail.sent == []
    assert invite_coll.rows[0]["reminder_step"] == 0


def test_no_reminder_the_day_after_the_event(monkeypatch):
    invite_coll, mail = _wire_tick(monkeypatch, _denver(2026, 11, 19, 18))
    _run(invites.run_invite_reminder_tick(now=NOW))
    assert mail.sent == []
    assert invite_coll.rows[0]["reminder_step"] == 0


def test_the_cap_uses_denver_days_for_a_naive_stored_date(monkeypatch):
    """Mongo hands dates back naive and in UTC. 03:00 UTC on the 21st is still
    the evening of the 20th in Denver, so this event is today, not tomorrow."""
    invite_coll, mail = _wire_tick(monkeypatch, datetime(2026, 11, 21, 3))
    _run(invites.run_invite_reminder_tick(now=NOW))
    assert mail.sent == []


def test_a_guest_who_removed_themselves_gets_no_reminder(monkeypatch):
    _, mail = _wire_tick(monkeypatch, _denver(2026, 12, 20, 18),
                         removed_at=NOW)
    _run(invites.run_invite_reminder_tick(now=NOW))
    assert mail.sent == []


def test_the_reminder_ends_with_the_remove_link(monkeypatch):
    _, mail = _wire_tick(monkeypatch, _denver(2026, 12, 20, 18))
    _run(invites.run_invite_reminder_tick(now=NOW))
    last = mail.sent[0]["paragraphs"][-1]
    assert last.startswith(REMOVE_PREFIX)
    assert "/api/invites/remove/" in last


# ---------------------------------------------------------------------------
# The remove-me link
# ---------------------------------------------------------------------------

def test_the_remove_token_round_trips_and_names_one_event():
    token = invites.make_remove_token(E1, "Guest@Acme.co")
    assert invites.verify_remove_token(token) == (E1, "guest@acme.co")


def test_a_remove_token_cannot_be_pointed_at_another_event():
    import base64

    token = invites.make_remove_token(E1, "guest@acme.co")
    _, sig = token.rsplit(".", 1)
    forged_body = base64.urlsafe_b64encode(
        f"{E2}:guest@acme.co".encode()).decode().rstrip("=")
    assert invites.verify_remove_token(f"{forged_body}.{sig}") is None


def test_an_unsubscribe_token_is_not_a_remove_token():
    import suppression

    assert invites.verify_remove_token(
        suppression.make_unsub_token(f"{E1}:guest@acme.co")) is None


def test_garbage_remove_tokens_are_rejected():
    for bad in ("", "nodot", "a.b", "!!!.00"):
        assert invites.verify_remove_token(bad) is None


def _wire_remove(monkeypatch):
    guest = {"_id": ObjectId(), "email": "guest@acme.co"}
    links = _Coll([
        {"event_id": E1, "user_id": guest["_id"], "activated": False},
        {"event_id": E2, "user_id": guest["_id"], "activated": True},
    ])
    invite_coll = _Coll()
    monkeypatch.setattr(invites, "event_attendees", links)
    monkeypatch.setattr(invites, "event_invites", invite_coll)
    monkeypatch.setattr(invites, "users", _Coll([guest]))
    monkeypatch.setattr(invites, "events", _Coll([EVENT]))
    return links, invite_coll


def test_opening_the_remove_link_only_asks_and_writes_nothing(monkeypatch):
    """Mail scanners open every link, so the GET must not remove anyone."""
    links, invite_coll = _wire_remove(monkeypatch)
    token = invites.make_remove_token(E1, "guest@acme.co")
    res = client.get(f"/api/invites/remove/{token}")
    assert res.status_code == 200
    assert "Remove yourself from Dinner's guest list?" in res.text
    assert 'method="post"' in res.text
    assert f'action="/api/invites/remove/{token}"' in res.text
    assert "guest@acme.co" not in res.text
    assert len(links.rows) == 2 and invite_coll.rows == []


def test_confirming_takes_the_guest_off_that_event_only(monkeypatch):
    links, invite_coll = _wire_remove(monkeypatch)
    token = invites.make_remove_token(E1, "guest@acme.co")
    res = client.post(f"/api/invites/remove/{token}")
    assert res.status_code == 200
    assert "You have been removed from Dinner's guest list." in res.text
    assert "guest@acme.co" not in res.text
    assert [r["event_id"] for r in links.rows] == [E2]
    marker = invite_coll.rows[0]
    assert marker["event_id"] == E1 and marker["email"] == "guest@acme.co"
    assert isinstance(marker["removed_at"], datetime)


def test_a_bad_remove_link_is_a_plain_400(monkeypatch):
    links, invite_coll = _wire_remove(monkeypatch)
    for send in (client.get, client.post):
        res = send("/api/invites/remove/not-a-token")
        assert res.status_code == 400
        assert "not valid" in res.text
    assert len(links.rows) == 2 and invite_coll.rows == []


def test_a_reimport_skips_a_guest_who_removed_themselves(monkeypatch):
    users, links, _ = _wire_import(
        monkeypatch,
        invite_rows=[{"event_id": E1, "email": "gone@acme.co",
                      "removed_at": datetime.now(timezone.utc)}],
    )
    out = _import([_Row("gone@acme.co"), _Row("stay@acme.co")])
    assert out["removed"] == 1
    assert out["added_to_event"] == 1
    assert [u.get("email") for u in users.rows if u.get("email")] == ["stay@acme.co"]
    assert len(links.rows) == 1


def test_removal_from_another_event_does_not_block_this_import(monkeypatch):
    _, links, _ = _wire_import(
        monkeypatch,
        invite_rows=[{"event_id": E2, "email": "other@acme.co",
                      "removed_at": datetime.now(timezone.utc)}],
    )
    out = _import([_Row("other@acme.co")])
    assert out["removed"] == 0
    assert len(links.rows) == 1


def test_the_import_invitation_ends_with_the_remove_link(monkeypatch):
    _wire_import(monkeypatch, email_on=True)
    sent = []

    async def _render(_tid, _ctx, host_id=None):
        return {"subject": "s", "body": "Hello.\n\nSee you there."}

    async def _send(**kw):
        sent.append(kw)
        return {"sent": True}

    monkeypatch.setattr(attendee_import.host_templates, "render_for_host", _render)
    monkeypatch.setattr(attendee_import.email_send, "send_template_branded", _send)
    _import([_Row("new@acme.co")])
    last = sent[0]["rendered"]["body"].split("\n\n")[-1]
    assert last.startswith(REMOVE_PREFIX)
    token = last[len(REMOVE_PREFIX):].rsplit("/", 1)[-1]
    assert invites.verify_remove_token(token) == (E1, "new@acme.co")


def test_the_invite_ends_with_the_remove_link_and_skips_removed_guests(monkeypatch):
    mail = _Mail()
    invite_coll = _Coll([{"event_id": E1, "email": "gone@acme.co",
                          "removed_at": datetime.now(timezone.utc)}])
    monkeypatch.setattr(invites, "event_invites", invite_coll)
    monkeypatch.setattr(invites, "email_send", mail)
    out = _run(invites.send_event_invites(EVENT, ["new@acme.co", "gone@acme.co"], "Scott"))
    assert [m["to"] for m in mail.sent] == ["new@acme.co"]
    assert out["removed"] == 1
    last = mail.sent[0]["paragraphs"][-1]
    assert last.startswith(REMOVE_PREFIX)


def test_the_remove_copy_is_dash_free():
    para = invites.remove_paragraph("https://x/api/invites/remove/t")
    assert "—" not in para and "–" not in para
