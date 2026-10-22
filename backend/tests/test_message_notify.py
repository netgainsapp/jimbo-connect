"""A message to an inactive attendee is their activation email (spec section 7).

What this covers: an active recipient gets nothing, an inactive one gets one
email in the host's name with the subject the spec names, the same sender is
held to one email a day and then waits for a reply, a second sender inside the
hour shares an email naming both, two senders inside the coalescing window
share one email, and nothing from the message itself ever reaches the mail.

Run from backend/: python -m pytest tests/test_message_notify.py
"""
import asyncio
import copy
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, parse_qs

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

import core
import email_send
import host_templates
import message_notify
import server
import rate_limit
from routers import auth as auth_routes
from routers import people

client = TestClient(server.app)

SECRET_TEXT = "Our merger closes Friday, keep it quiet"
# Noon in Denver. The microseconds matter: the route stamps datetime.now(),
# and Mongo keeps only milliseconds.
T0 = datetime(2026, 10, 22, 18, 0, 0, 123456, tzinfo=timezone.utc)
EVENT_ID, HOST_ID = ObjectId(), ObjectId()
MARCUS, PRIYA, GUEST = ObjectId(), ObjectId(), ObjectId()


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# A tiny in-memory collection: only the query shapes this feature uses.
# ---------------------------------------------------------------------------

def _bson(value):
    """What a round trip through Mongo does to a value: datetimes come back
    naive UTC at millisecond precision. Without this, a datetime equality
    that real Mongo breaks would pass here."""
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value.replace(microsecond=value.microsecond // 1000 * 1000)
    if isinstance(value, dict):
        return {k: _bson(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_bson(v) for v in value]
    return value


def _get(doc, dotted):
    """Values at a dotted path; a list along the way fans out, as in Mongo."""
    values = [doc]
    for part in dotted.split("."):
        nxt = []
        for v in values:
            if isinstance(v, list):
                nxt.extend(x.get(part) for x in v if isinstance(x, dict))
            elif isinstance(v, dict):
                nxt.append(v.get(part))
        values = nxt
    return values or [None]


def _op_ok(have, op, want):
    if op == "$in":
        return have in want
    if op == "$gt":
        return have is not None and have > want
    if op == "$regex":
        return isinstance(have, str) and re.search(want, have) is not None
    if op == "$exists":
        return (have is not None) == want
    if op == "$elemMatch":
        return isinstance(have, list) and any(
            isinstance(x, dict) and _matches(x, want) for x in have)
    raise AssertionError(f"fake does not know {op}")


def _matches(doc, query):
    for key, want in _bson(query).items():
        candidates = _get(doc, key)
        if isinstance(want, dict) and all(k.startswith("$") for k in want):
            ok = any(all(_op_ok(have, op, arg) for op, arg in want.items())
                     for have in candidates)
        else:
            ok = any(have == want for have in candidates)
        if not ok:
            return False
    return True


class _Cursor:
    def __init__(self, rows):
        self._it = iter(list(rows))

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


def _result(**fields):
    return type("R", (), fields)()


class _Coll:
    """Rows are copied in and out, as a real driver does, so a caller holding
    a document never sees a later write change it underneath them, and every
    write goes through _bson."""

    def __init__(self, rows=(), unique=()):
        self.rows = [_bson(dict(r)) for r in rows]
        self.unique = tuple(unique)

    def _find(self, query):
        return next((r for r in self.rows if _matches(r, query)), None)

    async def find_one(self, query, *_a, **_k):
        row = self._find(query)
        return copy.deepcopy(row) if row is not None else None

    def find(self, query=None, *_a, **_k):
        return _Cursor(copy.deepcopy(r) for r in self.rows
                       if _matches(r, query or {}))

    async def insert_one(self, doc):
        doc = _bson(dict(doc))
        if self.unique and self._find({k: doc.get(k) for k in self.unique}):
            raise message_notify.DuplicateKeyError("duplicate key")
        doc.setdefault("_id", ObjectId())
        self.rows.append(doc)
        return _result(inserted_id=doc["_id"])

    async def update_one(self, query, update, upsert=False):
        row = self._find(query)
        if row is None:
            return _result(matched_count=0, modified_count=0)
        assert "_id" not in update.get("$set", {}), "never $set _id"
        row.update(_bson(update.get("$set", {})))
        for key in update.get("$unset", {}):
            row.pop(key, None)
        for key, spec in _bson(update.get("$push", {})).items():
            items = row.get(key, []) + list(spec["$each"])
            row[key] = items[spec["$slice"]:] if "$slice" in spec else items
        for key, cond in _bson(update.get("$pull", {})).items():
            row[key] = [x for x in row.get(key, []) if not _matches(x, cond)]
        return _result(matched_count=1, modified_count=1)


def _person(oid, name, company="", role="", photo="", **extra):
    return {"_id": oid, "email": f"{name.split()[0].lower()}@example.test",
            "profile": {"name": name, "company": company, "role": role,
                        "photo_url": photo}, **extra}


@pytest.fixture
def world(monkeypatch):
    """Marcus and Priya joined the Denver Tech Mixer; the guest was imported
    and has never signed in. Mail is captured at the provider boundary."""
    users = _Coll([
        _person(HOST_ID, "Jim Host", "Mixers Inc", "Organizer"),
        _person(MARCUS, "Marcus Lee", "Ramble Labs", "Founder",
                photo="https://cdn.example.test/marcus.jpg"),
        _person(PRIYA, "Priya Shah", "Northwind", "CTO",
                photo="data:image/png;base64,AAAA"),
        _person(GUEST, "Gina Guest"),
    ])
    links = _Coll([
        {"event_id": EVENT_ID, "user_id": MARCUS, "activated": True},
        {"event_id": EVENT_ID, "user_id": PRIYA, "activated": True},
        {"event_id": EVENT_ID, "user_id": GUEST, "activated": False},
    ])
    events = _Coll([{"_id": EVENT_ID, "name": "Denver Tech Mixer",
                     "date": datetime(2026, 11, 5, 18, 0),
                     "created_by": HOST_ID}])
    msgs = _Coll([
        {"from_user_id": MARCUS, "to_user_id": GUEST, "text": SECRET_TEXT,
         "sent_at": T0},
        {"from_user_id": PRIYA, "to_user_id": GUEST, "text": SECRET_TEXT,
         "sent_at": T0},
    ])
    state = _Coll(unique=("recipient_id", "event_id"))
    for name, coll in (("users", users), ("event_attendees", links),
                       ("events", events), ("messages", msgs),
                       ("message_notify_state", state)):
        monkeypatch.setattr(message_notify, name, coll)
    sent = []

    async def _send_email(to, subject, html, text=None, **kwargs):
        sent.append({"to": to, "subject": subject, "html": html,
                     "text": text or "", **kwargs})
        return {"sent": True}

    async def _no_wait(_seconds):
        return None

    monkeypatch.setattr(email_send, "send_email", _send_email)
    monkeypatch.setattr(message_notify, "_sleep", _no_wait)
    # Templates resolve from the seeds: no admin edits, no host overrides.
    overrides = _Coll()
    monkeypatch.setattr(core, "email_templates", _Coll())
    monkeypatch.setattr(host_templates, "host_email_templates", overrides)
    return {"users": users, "links": links, "events": events,
            "messages": msgs, "state": state, "sent": sent,
            "overrides": overrides}


def _user(world, oid):
    return next(r for r in world["users"].rows if r["_id"] == oid)


def _event(world):
    return world["events"].rows[0]


async def _drain():
    while message_notify._background:
        await asyncio.gather(*list(message_notify._background))


async def _notify(world, sender_id, now):
    result = await message_notify.maybe_notify(
        _user(world, sender_id), _user(world, GUEST), _event(world), now)
    await _drain()
    return result


def _button_url(mail):
    return next(w for w in mail["text"].split() if "/reset-password/" in w)


# ---------------------------------------------------------------------------
# The spec's rules, end to end through the plumbing
# ---------------------------------------------------------------------------

def test_an_active_recipient_gets_no_email(world):
    _user(world, GUEST)["activated_at"] = T0 - timedelta(days=3)
    result = _run(_notify(world, MARCUS, T0))
    assert result == {"sent": False, "reason": "recipient_active"}
    assert world["sent"] == []


def test_a_member_who_joined_on_their_own_is_active(world):
    world["links"].rows[2]["activated"] = True
    result = _run(_notify(world, MARCUS, T0))
    assert result["reason"] == "recipient_active"
    assert world["sent"] == []


def test_an_inactive_recipient_gets_one_email_with_the_spec_subject(world):
    result = _run(_notify(world, MARCUS, T0))
    assert result == {"sent": True}
    assert len(world["sent"]) == 1
    mail = world["sent"][0]
    assert mail["to"] == "gina@example.test"
    assert mail["subject"] == (
        "Denver Tech Mixer: Marcus from Ramble Labs sent you a message")
    for fact in ("Marcus", "Ramble Labs", "Founder", "Denver Tech Mixer",
                 "November 5, 2026", "Read the message"):
        assert fact in mail["html"]


def test_the_email_goes_out_in_the_hosts_name(world):
    _run(_notify(world, MARCUS, T0))
    mail = world["sent"][0]
    assert mail["from_header"].startswith("Jim Host")
    assert mail["reply_to"] == "jim@example.test"


def test_the_hosts_own_wording_is_used_when_they_customized_it(world):
    world["overrides"].rows.append({
        "host_id": HOST_ID, "template_id": "message-waiting",
        "subject": "{sender_first} wrote to you about {event_name}",
        "body": "Hi {attendee_name}, {sender_first} is waiting."})
    _run(_notify(world, MARCUS, T0))
    assert world["sent"][0]["subject"] == "Marcus wrote to you about Denver Tech Mixer"


def test_both_message_templates_are_host_editable_and_never_dashed():
    from template_seeds import DEFAULT_TEMPLATES

    seeds = {t["template_id"]: t for t in DEFAULT_TEMPLATES}
    one, many = seeds["message-waiting"], seeds["messages-waiting"]
    assert one["subject"] == (
        "{event_name}: {sender_first} from {sender_company} sent you a message")
    assert many["subject"] == (
        "{event_name}: {sender_first} and {sender2_first} sent you messages")
    for tid in ("message-waiting", "messages-waiting"):
        assert tid in host_templates.HOST_EDITABLE
        assert "Intro Connect" not in seeds[tid]["body"]


def test_the_button_signs_them_in_and_opens_the_thread(world):
    _run(_notify(world, MARCUS, T0))
    parts = urlsplit(_button_url(world["sent"][0]))
    token = parts.path.rsplit("/", 1)[1]
    assert parse_qs(parts.query)["next"] == [f"/messages/{MARCUS}"]
    sent_at = T0.replace(microsecond=123000, tzinfo=None) + timedelta(
        seconds=message_notify.COALESCE_SECONDS)
    assert _user(world, GUEST)["magic_tokens"] == [
        {"hash": core._hash_token(token), "expires_at": sent_at + timedelta(days=7)}]


# ---------------------------------------------------------------------------
# The button's magic sign in, through GET /api/auth/magic/{token}
# ---------------------------------------------------------------------------

@pytest.fixture
def signin(world, monkeypatch):
    """The real magic_login route over the same users collection."""
    monkeypatch.setattr(auth_routes, "users", world["users"])
    monkeypatch.setattr(core, "users", world["users"])
    monkeypatch.setattr(rate_limit, "guard", lambda *_a, **_k: None)

    def _open(token):
        try:
            return client.get(f"/api/auth/magic/{token}")
        finally:
            client.cookies.clear()

    return _open


def _token(mail):
    return urlsplit(_button_url(mail)).path.rsplit("/", 1)[1]


def test_two_message_emails_give_two_working_buttons(world, signin):
    now = datetime.now(timezone.utc)

    async def scenario():
        await _notify(world, MARCUS, now)
        await _notify(world, PRIYA, now + timedelta(hours=2))

    _run(scenario())
    assert len(world["sent"]) == 2
    first, second = (_token(m) for m in world["sent"])
    assert signin(first).status_code == 200
    assert signin(second).status_code == 200


def test_a_pending_password_reset_survives_a_message_email(world, signin):
    now = datetime.now(timezone.utc)
    guest = _user(world, GUEST)
    guest["reset_token"] = core._hash_token("reset-link-token")
    guest["reset_token_expires"] = (now + timedelta(hours=2)).replace(tzinfo=None)
    _run(_notify(world, MARCUS, now))
    assert len(world["sent"]) == 1
    assert _user(world, GUEST)["reset_token"] == core._hash_token("reset-link-token")
    assert signin("reset-link-token").status_code == 200


def test_a_used_magic_token_cannot_be_replayed(world, signin):
    _run(_notify(world, MARCUS, datetime.now(timezone.utc)))
    token = _token(world["sent"][0])
    assert signin(token).status_code == 200
    assert signin(token).status_code == 400
    assert _user(world, GUEST)["magic_tokens"] == []


def test_an_expired_magic_token_is_refused(world, signin):
    _run(_notify(world, MARCUS, datetime.now(timezone.utc) - timedelta(days=8)))
    assert signin(_token(world["sent"][0])).status_code == 400


def test_only_the_five_newest_magic_tokens_are_kept(world):
    async def scenario():
        for day in range(7):
            world["messages"].rows.append({
                "from_user_id": GUEST, "to_user_id": MARCUS, "text": "hi",
                "sent_at": _bson(T0 + timedelta(days=day, hours=1))})
            await _notify(world, MARCUS, T0 + timedelta(days=day))

    _run(scenario())
    assert len(world["sent"]) == 7
    kept = [t["hash"] for t in _user(world, GUEST)["magic_tokens"]]
    assert kept == [core._hash_token(_token(m)) for m in world["sent"][2:]]


def test_the_sender_headshot_shows_only_for_an_https_photo(world):
    _run(_notify(world, MARCUS, T0))
    html = world["sent"][0]["html"]
    assert 'src="https://cdn.example.test/marcus.jpg" width="48"' in html


def test_an_uploaded_data_photo_is_left_out(world):
    _run(_notify(world, PRIYA, T0))
    html = world["sent"][0]["html"]
    assert "data:image" not in html
    assert 'width="48"' not in html


def test_the_body_never_contains_the_message_text(world):
    async def scenario():
        await _notify(world, MARCUS, T0)
        await _notify(world, PRIYA, T0 + timedelta(minutes=10))

    _run(scenario())
    assert len(world["sent"]) == 2
    for mail in world["sent"]:
        for part in (mail["subject"], mail["html"], mail["text"]):
            assert SECRET_TEXT not in part
            assert "merger" not in part


def test_no_real_message_means_no_email(world):
    world["messages"].rows = [r for r in world["messages"].rows
                              if r["from_user_id"] != MARCUS]
    result = _run(_notify(world, MARCUS, T0))
    assert result == {"sent": False, "reason": "no_message"}
    assert world["sent"] == []


def test_a_blank_message_is_not_a_real_message(world):
    world["messages"].rows[0]["text"] = "   "
    result = _run(_notify(world, MARCUS, T0))
    assert result["reason"] == "no_message"


def test_a_second_message_from_the_same_sender_the_same_day_sends_nothing(world):
    async def scenario():
        await _notify(world, MARCUS, T0)
        return await _notify(world, MARCUS, T0 + timedelta(hours=3))

    assert _run(scenario()) == {"sent": False, "reason": "daily_cap"}
    assert len(world["sent"]) == 1


def test_the_next_day_the_same_sender_still_waits_for_a_reply(world):
    async def scenario():
        await _notify(world, MARCUS, T0)
        return await _notify(world, MARCUS, T0 + timedelta(days=1))

    assert _run(scenario()) == {"sent": False, "reason": "awaiting_reply"}
    assert len(world["sent"]) == 1


def test_a_reply_releases_the_same_sender(world):
    async def scenario():
        await _notify(world, MARCUS, T0)
        world["messages"].rows.append({
            "from_user_id": GUEST, "to_user_id": MARCUS, "text": "hi",
            "sent_at": _bson(T0 + timedelta(hours=2))})
        return await _notify(world, MARCUS, T0 + timedelta(days=1))

    assert _run(scenario()) == {"sent": True}
    assert len(world["sent"]) == 2


def test_a_second_sender_inside_the_hour_gets_one_email_naming_both(world):
    async def scenario():
        await _notify(world, MARCUS, T0)
        return await _notify(world, PRIYA, T0 + timedelta(minutes=20))

    assert _run(scenario()) == {"sent": True}
    assert len(world["sent"]) == 2
    both = world["sent"][1]
    assert both["subject"] == "Denver Tech Mixer: Marcus and Priya sent you messages"
    for fact in ("Marcus", "Ramble Labs", "Priya", "Northwind", "CTO",
                 "Read your messages"):
        assert fact in both["html"]
    assert parse_qs(urlsplit(_button_url(both)).query)["next"] == ["/messages"]


def test_a_second_sender_after_the_hour_gets_an_email_of_their_own(world):
    async def scenario():
        await _notify(world, MARCUS, T0)
        await _notify(world, PRIYA, T0 + timedelta(hours=2))

    _run(scenario())
    assert world["sent"][1]["subject"] == (
        "Denver Tech Mixer: Priya from Northwind sent you a message")


def test_two_senders_inside_the_window_share_one_email(world, monkeypatch):
    async def scenario():
        gate = asyncio.Event()

        async def _held(_seconds):
            await gate.wait()

        monkeypatch.setattr(message_notify, "_sleep", _held)
        first = await message_notify.maybe_notify(
            _user(world, MARCUS), _user(world, GUEST), _event(world), T0)
        second = await message_notify.maybe_notify(
            _user(world, PRIYA), _user(world, GUEST), _event(world),
            T0 + timedelta(seconds=30))
        gate.set()
        await _drain()
        return first, second

    first, second = _run(scenario())
    assert first == {"sent": True}
    assert second == {"sent": False, "reason": "coalesced"}
    assert len(world["sent"]) == 1
    assert world["sent"][0]["subject"] == (
        "Denver Tech Mixer: Marcus and Priya sent you messages")


def test_a_recipient_who_activates_during_the_window_gets_nothing(world, monkeypatch):
    async def _activates(_seconds):
        _user(world, GUEST)["activated_at"] = T0

    monkeypatch.setattr(message_notify, "_sleep", _activates)
    _run(_notify(world, MARCUS, T0))
    assert world["sent"] == []


def test_a_failure_is_reported_never_raised_and_logs_no_address(world, monkeypatch, caplog):
    async def _boom(*_a, **_k):
        raise RuntimeError("gina@example.test bounced")

    monkeypatch.setattr(world["links"], "find_one", _boom)
    with caplog.at_level(logging.DEBUG):
        result = _run(_notify(world, MARCUS, T0))
    assert result == {"sent": False, "reason": "error"}
    assert "@" not in caplog.text


def test_a_failed_send_logs_no_address(world, monkeypatch, caplog):
    async def _boom(*_a, **_k):
        raise RuntimeError("gina@example.test rejected")

    monkeypatch.setattr(email_send, "send_email", _boom)
    with caplog.at_level(logging.DEBUG):
        _run(_notify(world, MARCUS, T0))
    assert caplog.text  # the failure is logged
    assert "@" not in caplog.text


# ---------------------------------------------------------------------------
# Pure rules
# ---------------------------------------------------------------------------

def _card(sid, first):
    return {"sender_id": sid, "first_name": first, "company": "", "role": "",
            "photo_url": ""}


def test_the_first_sender_opens_a_window():
    state, action = message_notify.next_state(None, _card("a", "Ann"), T0)
    assert action == "open"
    assert [s["sender_id"] for s in state["senders"]] == ["a"]
    assert state["window_opened_at"] == T0
    assert state["sent_at"] is None
    assert state["last_notified"] == {"a": T0}


def test_a_sender_inside_an_open_window_is_coalesced():
    state, _ = message_notify.next_state(None, _card("a", "Ann"), T0)
    later = T0 + timedelta(seconds=message_notify.COALESCE_SECONDS - 1)
    state, action = message_notify.next_state(state, _card("b", "Bo"), later)
    assert action == "coalesced"
    assert [s["sender_id"] for s in state["senders"]] == ["a", "b"]
    assert state["window_opened_at"] == T0


def test_a_sender_inside_the_hour_after_a_sent_email_opens_a_window_naming_both():
    state, _ = message_notify.next_state(None, _card("a", "Ann"), T0)
    state = {**state, "sent_at": T0 + timedelta(minutes=1)}
    later = T0 + timedelta(minutes=50)
    state, action = message_notify.next_state(state, _card("b", "Bo"), later)
    assert action == "open"
    assert [s["sender_id"] for s in state["senders"]] == ["a", "b"]
    assert state["window_opened_at"] == later and state["sent_at"] is None


def test_a_sender_after_the_hour_starts_fresh():
    state, _ = message_notify.next_state(None, _card("a", "Ann"), T0)
    state = {**state, "sent_at": T0 + timedelta(minutes=1)}
    later = T0 + timedelta(hours=2)
    state, _ = message_notify.next_state(state, _card("b", "Bo"), later)
    assert [s["sender_id"] for s in state["senders"]] == ["b"]
    assert set(state["last_notified"]) == {"a", "b"}


def test_a_window_whose_send_was_lost_reopens_and_keeps_its_senders():
    state, _ = message_notify.next_state(None, _card("a", "Ann"), T0)
    later = T0 + timedelta(minutes=5)
    state, action = message_notify.next_state(state, _card("b", "Bo"), later)
    assert action == "open"
    assert [s["sender_id"] for s in state["senders"]] == ["a", "b"]
    assert state["window_opened_at"] == later


def test_the_same_sender_is_named_once():
    state, _ = message_notify.next_state(None, _card("a", "Ann"), T0)
    state, _ = message_notify.next_state(state, _card("a", "Ann"), T0)
    assert [s["sender_id"] for s in state["senders"]] == ["a"]


def test_the_daily_cap_follows_the_denver_calendar():
    late_evening = datetime(2026, 10, 22, 4, 0, tzinfo=timezone.utc)  # Oct 21, 10pm Denver
    after_midnight = datetime(2026, 10, 22, 7, 0, tzinfo=timezone.utc)  # Oct 22, 1am Denver
    state = {"last_notified": {"a": late_evening}}
    assert message_notify.gate(state, "a", late_evening + timedelta(hours=1), False) == "daily_cap"
    assert message_notify.gate(state, "a", after_midnight, False) == "awaiting_reply"
    assert message_notify.gate(state, "a", after_midnight, True) is None
    assert message_notify.gate(state, "b", after_midnight, False) is None


def test_naive_stored_times_read_as_utc():
    naive = T0.replace(tzinfo=None)
    state = {"last_notified": {"a": naive}, "window_opened_at": naive,
             "sent_at": None, "senders": [_card("a", "Ann")]}
    assert message_notify.gate(state, "a", T0, False) == "daily_cap"
    _, action = message_notify.next_state(state, _card("b", "Bo"), T0 + timedelta(seconds=5))
    assert action == "coalesced"


def test_three_senders_read_as_one_name_and_others():
    ctx = message_notify.email_context(
        [_card("a", "Ann"), _card("b", "Bo"), _card("c", "Cy")],
        {"name": "Mixer", "date": datetime(2026, 11, 5)}, {"profile": {}}, "Jim")
    assert ctx["sender2_first"] == "2 others"


def test_a_sender_without_a_company_still_reads_cleanly():
    ctx = message_notify.email_context(
        [_card("a", "Ann")], {"name": "Mixer", "date": datetime(2026, 11, 5)},
        {"profile": {}}, "Jim")
    assert ctx["sender_company"] == "the guest list"
    assert ctx["sender_line"] == "Ann"


def test_the_event_is_the_soonest_upcoming_then_the_most_recent():
    past = {"_id": 1, "date": T0 - timedelta(days=30)}
    recent = {"_id": 2, "date": T0 - timedelta(days=2)}
    soon = {"_id": 3, "date": T0 + timedelta(days=3)}
    later = {"_id": 4, "date": T0 + timedelta(days=40)}
    assert message_notify.pick_event([past, later, soon, recent], T0)["_id"] == 3
    assert message_notify.pick_event([past, recent], T0)["_id"] == 2
    assert message_notify.pick_event([], T0) is None


# ---------------------------------------------------------------------------
# Which event, and the route
# ---------------------------------------------------------------------------

def test_the_shared_event_is_where_the_recipient_is_inactive(world):
    other = ObjectId()
    world["events"].rows.append({"_id": other, "name": "Other", "date": T0,
                                 "created_by": ObjectId()})
    world["links"].rows.append({"event_id": other, "user_id": GUEST,
                                "activated": False})
    found = _run(message_notify.resolve_event(MARCUS, GUEST, T0))
    assert found["_id"] == EVENT_ID


def test_the_host_messaging_their_own_guest_counts_as_shared(world):
    found = _run(message_notify.resolve_event(HOST_ID, GUEST, T0))
    assert found["_id"] == EVENT_ID


def test_no_shared_inactive_event_means_no_email(world):
    result = _run(message_notify.notify_for_message(
        _user(world, MARCUS), _user(world, PRIYA), T0))
    assert result == {"sent": False, "reason": "no_shared_event"}
    assert world["sent"] == []


def test_the_message_route_notifies_after_the_insert_and_survives_a_failure(monkeypatch):
    import auth

    sender = _person(MARCUS, "Marcus Lee")
    target = _person(GUEST, "Gina Guest")
    users = _Coll([sender, target])
    inserted = _Coll()
    calls = []

    async def _connected(*_a):
        return True

    async def _maybe_spy(s, r, event, now):
        calls.append((s["_id"], r["_id"], len(inserted.rows)))
        raise RuntimeError("notify blew up")

    async def _shared(*_a):
        return {"_id": EVENT_ID}

    monkeypatch.setattr(auth, "users", users)
    monkeypatch.setattr(people, "users", users)
    monkeypatch.setattr(people, "messages", inserted)
    monkeypatch.setattr(people, "_users_connected", _connected)
    monkeypatch.setattr(message_notify, "resolve_event", _shared)
    monkeypatch.setattr(message_notify, "_maybe_notify", _maybe_spy)
    client.cookies.set(auth.COOKIE_NAME, auth.create_access_token(str(MARCUS)))
    try:
        res = client.post("/api/messages",
                          json={"to_user_id": str(GUEST), "text": SECRET_TEXT})
    finally:
        client.cookies.clear()
    assert res.status_code == 200
    assert res.json()["text"] == SECRET_TEXT
    assert calls == [(MARCUS, GUEST, 1)]
