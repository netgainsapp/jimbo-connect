"""Generate cover images for posts that do not have one yet.

New posts get a cover as they are written. Anything that already existed, and
anything the seed script wrote, has to be filled in once.

    cd <repo root>
    $env:OPENAI_API_KEY="sk-..."
    $env:MONGO_URL="<connection string>"
    backend\\.venv\\Scripts\\python.exe scripts\\backfill_blog_covers.py          # dry run
    backend\\.venv\\Scripts\\python.exe scripts\\backfill_blog_covers.py --apply  # writes

Costs roughly two to four cents per post. The dry run tells you the count and
therefore the bill before anything is spent.

Safe to re-run: a post that already has a cover is skipped, so an interrupted
run resumes where it stopped.
"""
import asyncio
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

# Explicit path, because this script is run from the repo root while the .env
# lives in backend/. A bare load_dotenv() reads the current directory and would
# silently find nothing, leaving the run looking unconfigured.
try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND / ".env")
except ImportError:
    pass


def _require_env() -> None:
    mongo = os.getenv("MONGO_URL", "").strip()
    placeholder = (not mongo) or mongo.startswith("<") or "connection string" in mongo.lower()
    if placeholder:
        print(
            "MONGO_URL is not a real connection string.\n"
            "  dashboard.render.com -> jimbo-connect-api -> Environment -> MONGO_URL\n"
            'Then:  $env:MONGO_URL="<the value you copied>"',
            file=sys.stderr,
        )
        raise SystemExit(2)
    if not os.getenv("OPENAI_API_KEY"):
        print(
            "OPENAI_API_KEY is not set, so no image can be generated.\n"
            'Set it with:  $env:OPENAI_API_KEY="sk-..."',
            file=sys.stderr,
        )
        raise SystemExit(2)


async def main(apply: bool) -> int:
    # Imported after the env check: database builds its client at import time.
    from blog import covers, images, store

    posts = await store.list_all(limit=500)
    have = await covers.slugs_with_covers()
    # A stock path is a placeholder, not artwork, so it still counts as missing.
    # Matching attach_cover, which replaces stock but leaves anything set by
    # hand alone. Without this the script reported "nothing to do" for fifteen
    # posts that had just been given stock images.
    missing = [
        p
        for p in posts
        if p.get("slug") not in have
        and (not p.get("image_url") or images.is_stock(p.get("image_url")))
    ]

    print(f"{len(posts)} posts, {len(have)} with covers, {len(missing)} missing\n")
    for p in missing:
        print(f"  {p.get('status','?'):<9} {p.get('title','')[:66]}")

    if not missing:
        print("\nNothing to do.")
        return 0

    if not apply:
        low, high = len(missing) * 0.02, len(missing) * 0.04
        print(f"\nDry run. {len(missing)} would be generated, roughly ${low:.2f} to ${high:.2f}.")
        print("Re run with --apply.")
        return 0

    made = 0
    for i, p in enumerate(missing, 1):
        title = p.get("title", "")
        print(f"[{i}/{len(missing)}] {title[:60]} ... ", end="", flush=True)
        try:
            ok = await store.attach_cover(p)
        except Exception as exc:  # a bad post must not end the run
            print(f"failed ({str(exc)[:60]})")
            continue
        if ok:
            made += 1
            print("done")
        else:
            from blog import cover

            print(f"skipped: {cover.LAST_FAILURE or 'already had a cover'}")
            # A billing cap or a bad key fails identically for every post, so
            # stop rather than making the same doomed call fourteen more times.
            if "HTTP 4" in cover.LAST_FAILURE or "not set" in cover.LAST_FAILURE:
                print("\nThis will fail the same way for every post. Stopping.")
                break

    print(f"\n{made} of {len(missing)} covers generated.")
    return 0


if __name__ == "__main__":
    _require_env()
    sys.exit(asyncio.run(main("--apply" in sys.argv)))
