"""Tests for the sales/outreach template library store + schema. In-memory fake
collection + asyncio.run, no live DB.
Run from backend/: python -m pytest tests/test_sales_templates.py
"""
import asyncio
import os

import pytest
from bson import ObjectId

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import sales_templates as st
from sales_templates import SalesTemplateInput


class _Fake:
    def __init__(self):
        self.docs = []

    def find(self, query=None):
        docs = list(self.docs)

        class _Cur:
            def sort(self, *a, **k):
                return self

            def __aiter__(self):
                self._it = iter(docs)
                return self

            async def __anext__(self):
                try:
                    return next(self._it)
                except StopIteration:
                    raise StopAsyncIteration

        return _Cur()

    async def find_one(self, query):
        for d in self.docs:
            if all(d.get(k) == v for k, v in query.items()):
                return d
        return None

    async def insert_one(self, doc):
        oid = ObjectId()
        doc = {**doc, "_id": oid}
        self.docs.append(doc)

        class R:
            inserted_id = oid

        return R()

    async def update_one(self, query, update):
        for d in self.docs:
            if all(d.get(k) == v for k, v in query.items()):
                d.update(update.get("$set", {}))

    async def delete_one(self, query):
        before = len(self.docs)
        self.docs = [d for d in self.docs if not all(d.get(k) == v for k, v in query.items())]

        class R:
            deleted_count = before - len(self.docs)

        return R()


def _wire(monkeypatch):
    fake = _Fake()
    monkeypatch.setattr(st, "sales_templates", fake)
    return fake


def _input(**kw):
    base = dict(title="Cold intro", category="cold", subject="hi {first_name}", body="Hi {first_name}, ...")
    base.update(kw)
    return SalesTemplateInput(**base)


def test_seed_is_idempotent(monkeypatch):
    fake = _wire(monkeypatch)
    asyncio.run(st.seed_starters())
    n = len(fake.docs)
    assert n == len(st.STARTERS) and n > 0
    asyncio.run(st.seed_starters())  # again
    assert len(fake.docs) == n  # no duplicates


def test_create_and_list(monkeypatch):
    fake = _wire(monkeypatch)
    out = asyncio.run(st.create(_input(title="My cold email")))
    assert out["title"] == "My cold email"
    assert out["category_label"] == "Cold outreach"
    listed = asyncio.run(st.list_all())
    assert any(t["title"] == "My cold email" for t in listed)


def test_unknown_category_falls_back_to_cold(monkeypatch):
    _wire(monkeypatch)
    out = asyncio.run(st.create(_input(category="bogus")))
    assert out["category"] == "cold"


def test_update_changes_content(monkeypatch):
    _wire(monkeypatch)
    created = asyncio.run(st.create(_input()))
    edited = asyncio.run(st.update(created["id"], _input(title="Edited", subject="new subj")))
    assert edited["title"] == "Edited"
    assert edited["subject"] == "new subj"


def test_update_unknown_returns_none(monkeypatch):
    _wire(monkeypatch)
    assert asyncio.run(st.update("not-an-oid", _input())) is None
    assert asyncio.run(st.update(str(ObjectId()), _input())) is None


def test_duplicate_makes_a_copy(monkeypatch):
    fake = _wire(monkeypatch)
    created = asyncio.run(st.create(_input(title="Original")))
    dup = asyncio.run(st.duplicate(created["id"]))
    assert dup["title"] == "Original (copy)"
    assert len(fake.docs) == 2


def test_delete(monkeypatch):
    fake = _wire(monkeypatch)
    created = asyncio.run(st.create(_input()))
    assert asyncio.run(st.delete(created["id"])) is True
    assert fake.docs == []
    assert asyncio.run(st.delete("not-an-oid")) is False


def test_schema_requires_nonempty_fields():
    with pytest.raises(Exception):
        SalesTemplateInput(title="", category="cold", subject="s", body="b")
