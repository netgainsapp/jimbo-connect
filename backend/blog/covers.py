"""Storage for generated cover images, keyed by post slug.

Its own collection rather than a field on the post, because a post document is
read on every index render and every guardrail similarity check, and dragging
~180kb of JPEG through all of that would be wasteful. Covers are fetched only
by the route that serves them.

The slug is the key, not the post id, because that is what the URL carries and
it keeps the lookup a single indexed query.
"""
from datetime import datetime, timezone

from database import db

blog_cover = db["blog_cover"]

CONTENT_TYPE = "image/jpeg"

#: Covers never change for a given slug, so they can be cached hard. A new post
#: is a new slug and therefore a new URL.
CACHE_CONTROL = "public, max-age=31536000, immutable"


def cover_path(slug: str) -> str:
    return f"/blog/cover/{slug}.jpg"


async def save(slug: str, data: bytes) -> None:
    await blog_cover.update_one(
        {"_id": slug},
        {
            "$set": {
                "data": data,
                "content_type": CONTENT_TYPE,
                "bytes": len(data),
                "created_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )


async def load(slug: str):
    """The stored bytes for a slug, or None."""
    doc = await blog_cover.find_one({"_id": slug})
    return doc.get("data") if doc else None


async def has(slug: str) -> bool:
    return (await blog_cover.find_one({"_id": slug}, {"_id": 1})) is not None


async def slugs_with_covers() -> set:
    return {doc["_id"] async for doc in blog_cover.find({}, {"_id": 1})}
