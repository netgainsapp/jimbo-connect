"""Spread the stock photographs evenly across posts that have no artwork yet.

Hashing the slug is uniform but not even. Across the real fifteen posts it used
seven of the ten images and repeated one of them four times, which is visible on
a page that shows every post at once. Ranking by publish date and walking the
pool uses all ten and repeats none more than twice.

The assignment is written to each post's image_url so the tile and the article
page always agree, and so it survives new posts being added.

    cd <repo root>
    backend\\.venv\\Scripts\\python.exe scripts\\assign_stock_images.py          # dry run
    backend\\.venv\\Scripts\\python.exe scripts\\assign_stock_images.py --apply

Costs nothing and calls no API. This is the placeholder that makes the blog look
right until generated covers exist; those overwrite it, because a stock path is
treated as "no artwork yet".
"""
import asyncio
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND / ".env")
except ImportError:
    pass

if not os.getenv("MONGO_URL", "").strip():
    sys.exit("MONGO_URL is not set. Put it in backend/.env")


async def main(apply: bool) -> int:
    from blog import images
    from blog.store import blog_post, list_all

    posts = await list_all(limit=500)
    # A generated cover is finished work and is never overwritten here.
    targets = [
        p for p in posts
        if not p.get("image_url") or images.is_stock(p.get("image_url"))
    ]
    assignment = images.assign_round_robin(targets)

    changed = [p for p in targets if p.get("image_url") != assignment.get(p.get("slug"))]

    print(f"{len(posts)} posts, {len(targets)} on stock artwork, {len(changed)} would change\n")
    for p in sorted(targets, key=lambda d: (d.get("published_at") is None, d.get("published_at") or 0)):
        name = assignment[p["slug"]].rsplit("/", 1)[1]
        mark = " " if p.get("image_url") == assignment[p["slug"]] else "*"
        print(f"  {mark} {p.get('title','')[:52]:<54} {name}")

    distinct = len(set(assignment.values()))
    print(f"\n{distinct} distinct images across {len(targets)} posts (pool has {len(images.POOL)})")

    if not apply:
        print("\nDry run. Re run with --apply.")
        return 0

    for p in changed:
        await blog_post.update_one(
            {"_id": p["_id"]}, {"$set": {"image_url": assignment[p["slug"]]}}
        )
    print(f"\nUpdated {len(changed)} posts.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main("--apply" in sys.argv)))
