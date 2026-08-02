"""Persistence for generated posts. A post is only marked published when the
autopublish flag is ON and every guardrail passes; otherwise it is stored as a
draft with its guardrail_reasons for debugging.
"""
from datetime import datetime, timezone

from bson import ObjectId

from database import db
from . import cover, covers
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

    # Artwork last, and never fatally. The post is already stored, so a model
    # that is unconfigured, slow, or refuses simply leaves the post on the
    # stock pool in blog.images rather than losing the post.
    await attach_cover(doc)
    return doc


async def attach_cover(doc: dict) -> bool:
    """Generate and store a cover for a post, and point the post at it.

    Returns whether a cover was actually produced. Safe to call on a post that
    already has one: it does nothing and reports False.
    """
    slug = doc.get("slug")
    if not slug or doc.get("image_url") or await covers.has(slug):
        return False

    data = await cover.generate(doc.get("title") or "")
    if not data:
        return False

    await covers.save(slug, data)
    path = covers.cover_path(slug)
    await blog_post.update_one({"_id": doc["_id"]}, {"$set": {"image_url": path}})
    doc["image_url"] = path
    return True


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


async def update_post(post_id: str, post: GeneratedPost) -> dict:
    """Rewrite a draft or published post's content. Slug stays immutable, same
    reasoning as the news section: once published a post's URL may already be
    linked or indexed, so re-slugging on a content edit is never worth the
    risk of a broken link. This does not re-run the generation guardrails;
    an admin editing content by hand is trusted the same way an admin
    authoring a news article is."""
    oid = _oid(post_id)
    if oid is None:
        return None
    doc = await blog_post.find_one({"_id": oid})
    if not doc:
        return None
    patch = {
        "title": post.title,
        "summary": post.summary,
        "sections": [s.model_dump() for s in post.sections],
        "cta": post.cta,
        "updated_at": datetime.now(timezone.utc),
    }
    await blog_post.update_one({"_id": oid}, {"$set": patch})
    doc.update(patch)
    return doc


async def get_by_id(post_id: str) -> dict:
    """Any status, for the admin review view before publish/reject. Unlike
    get_by_slug (public, published-only), an admin must be able to read a
    draft's actual generated content to review it before it ever goes live."""
    oid = _oid(post_id)
    if oid is None:
        return None
    return await blog_post.find_one({"_id": oid})


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
