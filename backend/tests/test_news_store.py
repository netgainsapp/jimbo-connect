"""Tests for the news store (slug uniqueness, draft-then-publish lifecycle) and
the input schema (source URLs required + http/https). In-memory fake collection
+ asyncio.run, no live DB.

Run from backend/: python -m pytest tests/test_news_store.py
"""
import asyncio
import os

import pytest
from bson import ObjectId

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

from news import store as news_store
from news.schema import NewsArticleInput


class _FakeNews:
    def __init__(self):
        self.docs = []

    async def find_one(self, query):
        for d in self.docs:
            if all(d.get(k) == v for k, v in query.items()):
                return d
        return None

    async def insert_one(self, doc):
        # Real ObjectId so the store's ObjectId(str(id)) round-trip works.
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


def _valid_input(headline="A Real Newsworthy Headline Here"):
    return NewsArticleInput(
        headline=headline,
        summary="A short valid summary of the item.",
        sections=[{"heading": "What happened", "body": "It happened today."}],
        source_url="https://example.com/source",
        sources=["https://example.org/more"],
        event_date="July 10, 2026",
    )


def test_create_makes_a_draft(monkeypatch):
    fake = _FakeNews()
    monkeypatch.setattr(news_store, "news_article", fake)
    doc = asyncio.run(news_store.create_article(_valid_input()))
    assert doc["status"] == "draft"
    assert doc["published_at"] is None
    assert doc["slug"] == "a-real-newsworthy-headline-here"
    assert doc["source_url"] == "https://example.com/source"


def test_duplicate_headline_gets_unique_slug(monkeypatch):
    fake = _FakeNews()
    monkeypatch.setattr(news_store, "news_article", fake)
    a = asyncio.run(news_store.create_article(_valid_input()))
    b = asyncio.run(news_store.create_article(_valid_input()))
    assert a["slug"] != b["slug"]
    assert b["slug"].endswith("-2")


def test_publish_then_unpublish(monkeypatch):
    fake = _FakeNews()
    monkeypatch.setattr(news_store, "news_article", fake)
    doc = asyncio.run(news_store.create_article(_valid_input()))
    pub = asyncio.run(news_store.publish_article(str(doc["_id"])))
    assert pub["status"] == "published" and pub["published_at"] is not None
    un = asyncio.run(news_store.unpublish_article(str(doc["_id"])))
    assert un["status"] == "draft" and un["published_at"] is None


def test_publish_bad_id_returns_none(monkeypatch):
    monkeypatch.setattr(news_store, "news_article", _FakeNews())
    assert asyncio.run(news_store.publish_article("not-an-oid")) is None


# ---- schema validation ----

def test_source_url_must_be_http():
    with pytest.raises(Exception):
        _valid_input().model_copy(update={"source_url": "ftp://x"})
        NewsArticleInput(
            headline="Another Valid Headline For Test",
            summary="Summary here.",
            sections=[{"heading": "h", "body": "b"}],
            source_url="javascript:alert(1)",
        )


def test_extra_sources_must_be_http():
    with pytest.raises(Exception):
        NewsArticleInput(
            headline="Another Valid Headline For Test",
            summary="Summary here.",
            sections=[{"heading": "h", "body": "b"}],
            source_url="https://ok.com",
            sources=["not-a-url"],
        )


def test_headline_and_sections_required():
    with pytest.raises(Exception):
        NewsArticleInput(
            headline="short",  # under min_length
            summary="Summary here.",
            sections=[{"heading": "h", "body": "b"}],
            source_url="https://ok.com",
        )
    with pytest.raises(Exception):
        NewsArticleInput(
            headline="A Valid Long Enough Headline",
            summary="Summary here.",
            sections=[],  # empty
            source_url="https://ok.com",
        )
