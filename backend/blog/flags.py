"""Feature flags, single source of truth. Stored as one doc in Mongo so they can
be flipped without a deploy. Both default OFF: the engine ships dormant and
publishes nothing until an operator turns autopublish on.
"""
from database import db

app_flags = db["app_flags"]

DEFAULTS = {
    "blog_autopublish": False,  # flip ON to start publishing generated posts
    "blog_data_posts": False,   # flip ON once there is enough real data to ground posts
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
