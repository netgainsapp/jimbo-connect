"""Take the news section down. Owner decision 2026-08-02.

Unpublishes every news article. The documents are NOT deleted: status goes back
to draft, so everything is still in the admin and republishing is one click per
item if the section ever comes back.

    cd <repo root>
    backend\\.venv\\Scripts\\python.exe scripts\\unpublish_news.py          # dry run
    backend\\.venv\\Scripts\\python.exe scripts\\unpublish_news.py --apply

⚠️ Published article URLs start returning 404 after this. That is the accepted
cost of the decision; anything already indexed or linked externally breaks.
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
    from news.store import list_all, unpublish_article

    articles = await list_all(limit=500)
    published = [a for a in articles if a.get("status") == "published"]

    print(f"{len(articles)} news articles, {len(published)} published\n")
    for a in published:
        print(f"  /news/{a.get('slug')}")

    if not published:
        print("Nothing to unpublish.")
        return 0

    if not apply:
        print(f"\nDry run. {len(published)} would be unpublished and their URLs would 404.")
        print("The documents stay in the database as drafts. Re run with --apply.")
        return 0

    for a in published:
        await unpublish_article(str(a["_id"]))
    print(f"\nUnpublished {len(published)}. They remain in /admin/news as drafts.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main("--apply" in sys.argv)))
