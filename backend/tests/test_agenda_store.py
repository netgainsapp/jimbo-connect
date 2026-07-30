"""Saved agenda persistence: ownership, logo sanitising, and the autosave
logo rule.

The suite has no DB fixtures, so the motor collection is stubbed with a small
in-memory stand-in. That is enough, because what matters here is the ownership
comparison and the update semantics, not Mongo itself.

Run from backend/: python -m pytest tests/test_agenda_store.py
"""
import asyncio
import base64
import io
import os
from datetime import date

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import pytest
from bson import ObjectId
from PIL import Image

from agenda import store
from agenda.schema import AgendaExportRequest


class _Agendas:
    """Minimal stand-in for the motor collection."""

    def __init__(self):
        self.docs = {}

    async def insert_one(self, doc):
        oid = ObjectId()
        self.docs[oid] = {**doc, "_id": oid}
        return type("R", (), {"inserted_id": oid})()

    async def find_one(self, query):
        return self.docs.get(query.get("_id"))

    async def update_one(self, query, update):
        doc = self.docs.get(query["_id"])
        if doc:
            doc.update(update["$set"])

    async def delete_one(self, query):
        self.docs.pop(query["_id"], None)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _stub(monkeypatch):
    col = _Agendas()
    monkeypatch.setattr(store, "agendas", col)
    return col


def _payload(**over):
    base = {
        "event_name": "Denver Founders Dinner",
        "start_date": date(2026, 8, 1),
        "items": [
            {"date": date(2026, 8, 1), "start_time": "18:00", "end_time": "19:00",
             "title": "Welcome"}
        ],
    }
    base.update(over)
    return AgendaExportRequest(**base)


def _png_data_url(color=(37, 99, 235)):
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), color).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------

def test_owner_can_read_back_their_agenda():
    created = _run(store.create("user-1", _payload()))
    got = _run(store.get(created["id"], "user-1"))
    assert got["event_name"] == "Denver Founders Dinner"
    assert len(got["items"]) == 1


def test_another_user_cannot_read_it():
    created = _run(store.create("user-1", _payload()))
    with pytest.raises(store.AgendaNotFound):
        _run(store.get(created["id"], "user-2"))


def test_another_user_cannot_update_or_delete_it():
    created = _run(store.create("user-1", _payload()))
    with pytest.raises(store.AgendaNotFound):
        _run(store.update(created["id"], "user-2", _payload(), logo_provided=False))
    with pytest.raises(store.AgendaNotFound):
        _run(store.delete(created["id"], "user-2"))
    # and it is still there for its real owner
    assert _run(store.get(created["id"], "user-1"))["id"] == created["id"]


def test_ownership_compares_as_strings():
    """An ObjectId stored against a string user id must still match."""
    uid = ObjectId()
    created = _run(store.create(uid, _payload()))
    assert _run(store.get(created["id"], str(uid)))["id"] == created["id"]


def test_missing_and_malformed_ids_are_both_not_found():
    """Same exception for both: distinguishing them would confirm that an id
    exists."""
    with pytest.raises(store.AgendaNotFound):
        _run(store.get(str(ObjectId()), "user-1"))
    with pytest.raises(store.AgendaNotFound):
        _run(store.get("not-an-object-id", "user-1"))


# ---------------------------------------------------------------------------
# Autosave semantics
# ---------------------------------------------------------------------------

def test_update_replaces_the_fields_the_client_sent():
    created = _run(store.create("user-1", _payload()))
    _run(store.update(created["id"], "user-1",
                      _payload(event_name="Renamed"), logo_provided=False))
    assert _run(store.get(created["id"], "user-1"))["event_name"] == "Renamed"


def test_autosave_without_a_logo_field_leaves_the_logo_alone():
    """The important one: autosave omits the logo, and must not wipe it."""
    created = _run(store.create("user-1", _payload(logo=_png_data_url())))
    assert created["logo"]
    _run(store.update(created["id"], "user-1",
                      _payload(event_name="Renamed"), logo_provided=False))
    assert _run(store.get(created["id"], "user-1"))["logo"]


def test_explicit_null_logo_removes_it():
    created = _run(store.create("user-1", _payload(logo=_png_data_url())))
    _run(store.update(created["id"], "user-1",
                      _payload(logo=None), logo_provided=True))
    assert _run(store.get(created["id"], "user-1"))["logo"] is None


# ---------------------------------------------------------------------------
# Logo handling
# ---------------------------------------------------------------------------

def test_logo_is_re_encoded_to_png_not_stored_as_sent():
    """Never store the bytes the client sent: they go through Pillow first."""
    jpeg = io.BytesIO()
    Image.new("RGB", (40, 40), (200, 30, 30)).save(jpeg, format="JPEG")
    sent = "data:image/jpeg;base64," + base64.b64encode(jpeg.getvalue()).decode()
    created = _run(store.create("user-1", _payload(logo=sent)))
    assert created["logo"].startswith("data:image/png;base64,")
    assert created["logo"] != sent


def test_a_non_image_logo_is_rejected():
    bad = "data:image/png;base64," + base64.b64encode(b"not an image").decode()
    with pytest.raises(ValueError):
        _run(store.create("user-1", _payload(logo=bad)))


def test_a_malformed_data_url_is_rejected():
    with pytest.raises(ValueError):
        store.sanitize_logo("https://example.com/logo.png")
    with pytest.raises(ValueError):
        store.sanitize_logo("data:image/png;base64,!!!not-base64!!!")


def test_no_logo_is_fine():
    assert store.sanitize_logo(None) is None
    assert store.sanitize_logo("") is None


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------

def test_list_omits_items_and_logo():
    """A list of ten agendas must not ship ten logos."""
    _run(store.create("user-1", _payload(logo=_png_data_url())))

    class _Cursor:
        def __init__(self, docs):
            self._docs = docs

        def sort(self, *_a, **_k):
            return self

        async def to_list(self, _limit):
            return self._docs

    col = store.agendas
    col.find = lambda q: _Cursor([d for d in col.docs.values()
                                  if str(d["user_id"]) == str(q["user_id"])])
    rows = _run(store.list_for_user("user-1"))
    assert len(rows) == 1
    assert rows[0]["item_count"] == 1
    assert "items" not in rows[0]
    assert "logo" not in rows[0]


# ---------------------------------------------------------------------------
# Conversion to an event
# ---------------------------------------------------------------------------

def test_attach_event_links_and_marks_converted():
    created = _run(store.create("user-1", _payload()))
    event_id = ObjectId()
    out = _run(store.attach_event(created["id"], "user-1", event_id))
    assert out["event_id"] == str(event_id)
    assert out["status"] == "converted"


def test_attach_event_respects_ownership():
    created = _run(store.create("user-1", _payload()))
    with pytest.raises(store.AgendaNotFound):
        _run(store.attach_event(created["id"], "user-2", ObjectId()))


def test_event_datetime_combines_start_date_and_time():
    from routers.agenda import _event_datetime

    got = _event_datetime({"start_date": "2026-08-01", "start_time": "18:30", "items": []})
    assert (got.year, got.month, got.day, got.hour, got.minute) == (2026, 8, 1, 18, 30)


def test_event_datetime_falls_back_to_the_earliest_session():
    """An agenda where only the rows carry dates must still convert."""
    from routers.agenda import _event_datetime

    got = _event_datetime(
        {"start_date": "", "start_time": "",
         "items": [{"date": "2026-09-04"}, {"date": "2026-09-02"}]}
    )
    assert (got.year, got.month, got.day) == (2026, 9, 2)


def test_event_datetime_is_none_when_nothing_is_dated():
    from routers.agenda import _event_datetime

    assert _event_datetime({"start_date": "", "start_time": "", "items": []}) is None


def test_event_datetime_survives_a_nonsense_time():
    from routers.agenda import _event_datetime

    got = _event_datetime({"start_date": "2026-08-01", "start_time": "99:99", "items": []})
    assert got is not None and got.hour == 0


def test_list_only_returns_your_own():
    _run(store.create("user-1", _payload()))
    _run(store.create("user-2", _payload()))

    class _Cursor:
        def __init__(self, docs):
            self._docs = docs

        def sort(self, *_a, **_k):
            return self

        async def to_list(self, _limit):
            return self._docs

    col = store.agendas
    col.find = lambda q: _Cursor([d for d in col.docs.values()
                                  if str(d["user_id"]) == str(q["user_id"])])
    assert len(_run(store.list_for_user("user-1"))) == 1
