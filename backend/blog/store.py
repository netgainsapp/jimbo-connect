"""Persistence for generated posts. A post is only marked published when the
autopublish flag is ON and every guardrail passes; otherwise it is stored as a
draft with its guardrail_reasons for debugging.
"""
from datetime import datetime, timezone

from bson import ObjectId

from database import db
from .flags import get_flag
from .guardrails import check_guardrails
from .schema import GeneratedPost, slugify

blog_post = db["blog_post"]
blog_topic = db["blog_topic"]


async def _existing_for_guardrails() -> list:
    """Minimal projection of existing posts for dedupe/similarity checks."""
    cursor = blog_post.find(
        {}, {"slug": 1, "topic_id": 1, "title": 1, "summary": 1, "sections": 1, "cta": 1}
    )
    return [doc async for doc in cursor]


async def create_post(
    post: GeneratedPost,
    *,
    topic_id=None,
    is_data_post: bool = False,
    comp_count: int = 0,
) -> dict:
    """Validate and store a generated post. Returns the stored document.

    Published only when blog_autopublish is ON and guardrails pass. Otherwise a
    draft carrying its guardrail_reasons.
    """
    slug = slugify(post.title)
    existing = await _existing_for_guardrails()
    reasons = check_guardrails(
        post,
        existing,
        slug=slug,
        topic_id=topic_id,
        is_data_post=is_data_post,
        comp_count=comp_count,
    )
    autopublish = await get_flag("blog_autopublish")
    publish = autopublish and not reasons
    now = datetime.now(timezone.utc)

    doc = {
        "slug": slug,
        "title": post.title,
        "summary": post.summary,
        "sections": [s.model_dump() for s in post.sections],
        "cta": post.cta,
        "topic_id": topic_id,
        "is_data_post": is_data_post,
        "status": "published" if publish else "draft",
        "guardrail_reasons": reasons,
        "created_at": now,
        "published_at": now if publish else None,
    }
    result = await blog_post.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def list_published(limit: int = 50) -> list:
    cursor = blog_post.find({"status": "published"}).sort("published_at", -1).limit(limit)
    return [doc async for doc in cursor]


async def get_by_slug(slug: str) -> dict:
    return await blog_post.find_one({"slug": slug, "status": "published"})


# ---------- Admin ----------

async def list_all(limit: int = 100) -> list:
    """All posts (drafts and published), newest first, for the admin view."""
    cursor = blog_post.find({}).sort("created_at", -1).limit(limit)
    return [doc async for doc in cursor]


def _oid(post_id: str):
    try:
        return ObjectId(post_id)
    except Exception:
        return None


async def publish_post(post_id: str):
    """Publish a draft. Returns the doc, or {"error": "guardrails_failed",
    "reasons": [...]} if it has unresolved guardrail failures, or None if not
    found / bad id."""
    oid = _oid(post_id)
    if oid is None:
        return None
    doc = await blog_post.find_one({"_id": oid})
    if not doc:
        return None
    if doc.get("guardrail_reasons"):
        return {"error": "guardrails_failed", "reasons": doc["guardrail_reasons"]}
    now = datetime.now(timezone.utc)
    await blog_post.update_one(
        {"_id": oid}, {"$set": {"status": "published", "published_at": now}}
    )
    doc["status"] = "published"
    doc["published_at"] = now
    return doc


async def unpublish_post(post_id: str):
    """Revert a post to draft. Returns the doc, or None if not found / bad id."""
    oid = _oid(post_id)
    if oid is None:
        return None
    doc = await blog_post.find_one({"_id": oid})
    if not doc:
        return None
    await blog_post.update_one(
        {"_id": oid}, {"$set": {"status": "draft", "published_at": None}}
    )
    doc["status"] = "draft"
    doc["published_at"] = None
    return doc
