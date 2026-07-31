"""Per-host email template overrides: resolution order, the allowlist, and
what a host can never touch.

Run from backend/: python -m pytest tests/test_host_templates.py
"""
import asyncio
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import pytest
from bson import ObjectId

import core
import host_templates


class _Col:
    def __init__(self):
        self.docs = {}

    def _match(self, doc, query):
        return all(doc.get(k) == v for k, v in query.items())

    async def find_one(self, query):
        for d in self.docs.values():
            if self._match(d, query):
                return d
        return None

    async def update_one(self, query, update, upsert=False):
        doc = await self.find_one(query)
        if doc:
            doc.update(update["$set"])
        elif upsert:
            oid = ObjectId()
            self.docs[oid] = {**query, **update["$set"], "_id": oid}

    async def delete_one(self, query):
        for oid, d in list(self.docs.items()):
            if self._match(d, query):
                del self.docs[oid]
                return type("R", (), {"deleted_count": 1})()
        return type("R", (), {"deleted_count": 0})()

    async def delete_many(self, query):
        n = 0
        for oid, d in list(self.docs.items()):
            if self._match(d, query):
                del self.docs[oid]
                n += 1
        return type("R", (), {"deleted_count": n})()


HOST = ObjectId()
OTHER = ObjectId()


@pytest.fixture(autouse=True)
def _stub(monkeypatch):
    overrides = _Col()
    admin_globals = _Col()
    monkeypatch.setattr(host_templates, "host_email_templates", overrides)
    # get_email_template reads core's email_templates (admin-edited globals),
    # falling through to the DEFAULT_TEMPLATES seeds.
    monkeypatch.setattr(core, "email_templates", admin_globals)
    return overrides, admin_globals


def _run(c):
    return asyncio.run(c)


# --------------------------------------------------------------------------
# The allowlist is the security boundary
# --------------------------------------------------------------------------

def test_password_reset_is_never_editable():
    with pytest.raises(host_templates.TemplateError):
        _run(host_templates.upsert(HOST, "password-reset", "s", "b"))


def test_outreach_templates_are_not_editable():
    for tid in ("what-is-jimbo", "sponsor-pitch", "host-intro"):
        with pytest.raises(host_templates.TemplateError):
            _run(host_templates.upsert(HOST, tid, "s", "b"))


def test_unknown_template_is_not_editable():
    with pytest.raises(host_templates.TemplateError):
        _run(host_templates.upsert(HOST, "made-up", "s", "b"))


def test_a_smuggled_row_for_an_uneditable_template_is_ignored(_stub):
    """Even if a row somehow exists for password-reset, resolution must never
    read it. The allowlist gates reads too, not just writes."""
    overrides, _ = _stub
    oid = ObjectId()
    overrides.docs[oid] = {
        "_id": oid, "host_id": HOST, "template_id": "password-reset",
        "subject": "EVIL", "body": "EVIL",
    }
    t = _run(host_templates.resolve("password-reset", HOST))
    assert t["subject"] != "EVIL"
    assert "Reset your Intro Connect password" in t["subject"]


def test_list_never_includes_system_or_outreach_templates():
    ids = [t["id"] for t in _run(host_templates.list_for(HOST))]
    assert "password-reset" not in ids
    assert "sponsor-pitch" not in ids
    assert set(ids) == set(host_templates.HOST_EDITABLE)


# --------------------------------------------------------------------------
# Resolution order: host override > admin-edited global > seed default
# --------------------------------------------------------------------------

def test_seed_default_when_nothing_is_stored():
    t = _run(host_templates.resolve("invitation", HOST))
    assert "You're invited to {event_name}" == t["subject"]


def test_admin_global_beats_seed(_stub):
    _, admin_globals = _stub
    oid = ObjectId()
    admin_globals.docs[oid] = {
        "_id": oid, "template_id": "invitation",
        "subject": "ADMIN SUBJECT", "body": "ADMIN BODY",
    }
    t = _run(host_templates.resolve("invitation", HOST))
    assert t["subject"] == "ADMIN SUBJECT"


def test_host_override_beats_admin_global(_stub):
    _, admin_globals = _stub
    oid = ObjectId()
    admin_globals.docs[oid] = {
        "_id": oid, "template_id": "invitation",
        "subject": "ADMIN SUBJECT", "body": "ADMIN BODY",
    }
    _run(host_templates.upsert(HOST, "invitation", "HOST SUBJECT", "HOST BODY"))
    t = _run(host_templates.resolve("invitation", HOST))
    assert t["subject"] == "HOST SUBJECT"
    assert t["body"] == "HOST BODY"


def test_overrides_are_per_host():
    _run(host_templates.upsert(HOST, "invitation", "MINE", "MINE B"))
    theirs = _run(host_templates.resolve("invitation", OTHER))
    assert theirs["subject"] != "MINE"


def test_no_host_id_resolves_to_the_default():
    _run(host_templates.upsert(HOST, "invitation", "MINE", "MINE B"))
    t = _run(host_templates.resolve("invitation", None))
    assert t["subject"] != "MINE"


def test_override_keeps_the_base_title_and_category():
    """The host edits words, not identity: title/blurb/category still come from
    the base template so the editor UI stays labelled correctly."""
    _run(host_templates.upsert(HOST, "day-of", "s", "b"))
    listed = {t["id"]: t for t in _run(host_templates.list_for(HOST))}
    assert listed["day-of"]["title"]  # non-empty, from the seed
    assert listed["day-of"]["subject"] == "s"
    assert listed["day-of"]["customized"] is True


# --------------------------------------------------------------------------
# Upsert and reset
# --------------------------------------------------------------------------

def test_blank_subject_or_body_is_refused():
    with pytest.raises(host_templates.TemplateError):
        _run(host_templates.upsert(HOST, "invitation", "   ", "body"))
    with pytest.raises(host_templates.TemplateError):
        _run(host_templates.upsert(HOST, "invitation", "subject", ""))


def test_over_cap_input_is_truncated_not_stored_whole():
    _run(host_templates.upsert(
        HOST, "invitation",
        "s" * (host_templates.MAX_SUBJECT + 50),
        "b" * (host_templates.MAX_BODY + 50),
    ))
    t = _run(host_templates.resolve("invitation", HOST))
    assert len(t["subject"]) == host_templates.MAX_SUBJECT
    assert len(t["body"]) == host_templates.MAX_BODY


def test_reset_returns_to_the_default():
    _run(host_templates.upsert(HOST, "invitation", "MINE", "MINE B"))
    _run(host_templates.reset(HOST, "invitation"))
    t = _run(host_templates.resolve("invitation", HOST))
    assert t["subject"] == "You're invited to {event_name}"
    listed = {t["id"]: t for t in _run(host_templates.list_for(HOST))}
    assert listed["invitation"]["customized"] is False


def test_reset_of_an_uneditable_template_is_refused():
    with pytest.raises(host_templates.TemplateError):
        _run(host_templates.reset(HOST, "password-reset"))


def test_reset_when_nothing_customized_is_a_quiet_no_op():
    # Not an error: the state the host asked for is the state they get.
    _run(host_templates.reset(HOST, "invitation"))


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def test_render_for_host_uses_the_override_and_merges_vars():
    _run(host_templates.upsert(
        HOST, "invitation", "Come to {event_name}!", "See you there, {attendee_name}."
    ))
    out = _run(host_templates.render_for_host(
        "invitation", {"event_name": "Dinner", "attendee_name": "Ann"}, HOST
    ))
    assert out == {"subject": "Come to Dinner!", "body": "See you there, Ann."}


def test_render_for_host_falls_back_to_default_without_an_override():
    out = _run(host_templates.render_for_host(
        "invitation", {"event_name": "Dinner"}, HOST
    ))
    assert out["subject"] == "You're invited to Dinner"


def test_render_for_host_unknown_template_returns_none():
    assert _run(host_templates.render_for_host("nope", {}, HOST)) is None
