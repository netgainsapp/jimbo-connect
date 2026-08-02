"""Persistence for admin-authored news articles.

A news item is created as a draft and explicitly published by an admin (no
autopublish, no AI guardrails: news is human-authored and source-attributed).
Mirrors backend/blog/store.py so the admin flow feels the same.
"""
from datetime import datetime, timezone

from bson import ObjectId

from database import db
from .schema import NewsArticleInput, article_slug

news_article = db["news_article"]


async def _unique_slug(base: str) -> str:
    """news items are dated, so same-headline collisions are possible; append a
    numeric suffix instead of overwriting an existing slug."""
    slug = base or "news"
    n = 1
    while await news_article.find_one({"slug": slug}):
        n += 1
        slug = f"{base}-{n}"
    return slug


async def create_article(item: NewsArticleInput, *, guardrail_reasons=None) -> dict:
    """Store a news item as a draft.

    guardrail_reasons is why the generated item was not fit to publish, kept on
    the document the way the blog keeps it. Without it a held-back draft sits in
    the admin with no explanation, and the only record of the reason is a line
    in a cron log nobody keeps. Empty for anything an admin wrote by hand.
    """
    now = datetime.now(timezone.utc)
    slug = await _unique_slug(article_slug(item.headline))
    doc = {
        "slug": slug,
        "headline": item.headline,
        "summary": item.summary,
        "sections": [s.model_dump() for s in item.sections],
        "source_url": item.source_url,
        "sources": item.sources,
        "event_date": item.event_date,
        "image_url": item.image_url,
        "status": "draft",
        "guardrail_reasons": list(guardrail_reasons or []),
        "created_at": now,
        "published_at": None,
        "modified_at": None,
    }
    result = await news_article.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def list_published(limit: int = 50) -> list:
    cursor = (
        news_article.find({"status": "published"})
        .sort("published_at", -1)
        .limit(limit)
    )
    return [doc async for doc in cursor]


async def get_by_slug(slug: str) -> dict:
    return await news_article.find_one({"slug": slug, "status": "published"})


# ---------- Admin ----------

async def list_all(limit: int = 100) -> list:
    cursor = news_article.find({}).sort("created_at", -1).limit(limit)
    return [doc async for doc in cursor]


def _oid(article_id: str):
    try:
        return ObjectId(article_id)
    except Exception:
        return None


async def update_article(article_id: str, item: NewsArticleInput):
    """Rewrite an article's content. The slug is deliberately immutable: a
    published article's URL is already indexed and linked, so re-slugging on a
    headline edit would break it. Sets modified_at (surfaced as dateModified
    in the NewsArticle JSON-LD)."""
    oid = _oid(article_id)
    if oid is None:
        return None
    doc = await news_article.find_one({"_id": oid})
    if not doc:
        return None
    patch = {
        "headline": item.headline,
        "summary": item.summary,
        "sections": [s.model_dump() for s in item.sections],
        "source_url": item.source_url,
        "sources": item.sources,
        "event_date": item.event_date,
        "image_url": item.image_url,
        "modified_at": datetime.now(timezone.utc),
    }
    await news_article.update_one({"_id": oid}, {"$set": patch})
    doc.update(patch)
    return doc


async def delete_article(article_id: str) -> bool:
    oid = _oid(article_id)
    if oid is None:
        return False
    res = await news_article.delete_one({"_id": oid})
    return res.deleted_count > 0


async def publish_article(article_id: str):
    oid = _oid(article_id)
    if oid is None:
        return None
    doc = await news_article.find_one({"_id": oid})
    if not doc:
        return None
    now = datetime.now(timezone.utc)
    await news_article.update_one(
        {"_id": oid}, {"$set": {"status": "published", "published_at": now}}
    )
    doc["status"] = "published"
    doc["published_at"] = now
    return doc


async def unpublish_article(article_id: str):
    oid = _oid(article_id)
    if oid is None:
        return None
    doc = await news_article.find_one({"_id": oid})
    if not doc:
        return None
    await news_article.update_one(
        {"_id": oid}, {"$set": {"status": "draft", "published_at": None}}
    )
    doc["status"] = "draft"
    doc["published_at"] = None
    return doc
