"""Persistence for generated posts. A post is only marked published when the
autopublish flag is ON and every guardrail passes; otherwise it is stored as a
draft with its guardrail_reasons for debugging.
"""
from datetime import datetime, timezone

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
