"""Feature flags, single source of truth. Stored as one doc in Mongo so they can
be flipped without a deploy.

The blog autopublishes as of 2026-08-02, by owner decision. News is paused the
same day, also by owner decision: the engine is built and tested but the section
is not wanted for now, so its flag is off and its cron is commented out.

⚠️ A DEFAULT ONLY APPLIES WHEN THE FLAG HAS NEVER BEEN SET. `get_flags` reads
the stored document first, so if `blog_autopublish` was ever toggled off in the
admin, that stored False wins and changing the default here does nothing. The
reliable way to turn one on is the toggle at /admin/blog, which writes the
document. Check the tick's response: it reports the status the post was saved
with, which is the only proof that the flag actually took effect.

Note that "autopublish" still means "publish once the guardrails pass" for both
sections; an item that fails them is kept as a draft rather than published
broken.
"""
from database import db

app_flags = db["app_flags"]

DEFAULTS = {
    "blog_autopublish": True,   # owner decision 2026-08-02: publish generated posts
    "blog_data_posts": False,   # flip ON once there is enough real data to ground posts
    # OFF from 2026-08-02, owner decision: the news section is paused. Belt and
    # braces with the commented-out cron, so a manual tick cannot publish either.
    "news_autopublish": False,
}

_FLAGS_ID = "flags"


async def get_flags() -> dict:
    doc = await app_flags.find_one({"_id": _FLAGS_ID}) or {}
    return {key: bool(doc.get(key, default)) for key, default in DEFAULTS.items()}


async def get_flag(name: str) -> bool:
    return (await get_flags()).get(name, False)


async def set_flag(name: str, value: bool) -> None:
    if name not in DEFAULTS:
        raise ValueError(f"unknown flag: {name}")
    await app_flags.update_one(
        {"_id": _FLAGS_ID}, {"$set": {name: bool(value)}}, upsert=True
    )
