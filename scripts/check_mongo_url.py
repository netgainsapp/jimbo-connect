"""Does MONGO_URL actually work? Reports without ever printing the credential.

Run after changing the connection string and BEFORE deleting the old database
user, so a bad paste is caught while the old credential still exists.

    cd <repo root>
    backend\\.venv\\Scripts\\python.exe scripts\\check_mongo_url.py

Reads backend/.env. Prints the host, the user, and what the server said. Never
prints the password, so the output is safe to paste anywhere.
"""
import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND / ".env")
except ImportError:
    pass


def _describe(url: str) -> str:
    """Host and username only. The password is never returned."""
    parts = urlsplit(url)
    user = (parts.username or "(none)")
    host = parts.hostname or "(no host)"
    return f"user {user} @ {host}"


async def main() -> int:
    url = os.getenv("MONGO_URL", "").strip()
    if not url:
        print("MONGO_URL is empty. Fill it in at backend/.env", file=sys.stderr)
        return 2
    if url.startswith("<") or "db_password" in url:
        print(
            "MONGO_URL still has the Atlas placeholder in it.\n"
            "Replace <db_password> with the real password.",
            file=sys.stderr,
        )
        return 2

    print(f"connecting as {_describe(url)} ...")

    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=15000)
    try:
        await client.admin.command("ping")
    except Exception as exc:
        message = str(exc)
        # Say which failure it is: the two look identical to most people and
        # have completely different fixes.
        if "auth" in message.lower() or "credential" in message.lower():
            hint = "Authentication failed: wrong user or password, or the user was deleted."
        elif "timed out" in message.lower() or "ServerSelection" in type(exc).__name__:
            hint = (
                "Could not reach the cluster: usually Network Access in Atlas not "
                "allowing this address, not a bad password."
            )
        else:
            hint = "Unrecognised failure."
        print(f"\nFAILED. {hint}\n\n{message[:400]}", file=sys.stderr)
        return 1

    db_name = os.getenv("DB_NAME", "jimbo_connect")
    db = client[db_name]
    names = await db.list_collection_names()
    posts = await db["blog_post"].count_documents({})
    users = await db["users"].count_documents({})

    print(f"OK. Connected, and the credential can read.")
    print(f"   database    : {db_name}")
    print(f"   collections : {len(names)}")
    print(f"   blog posts  : {posts}")
    print(f"   users       : {users}")
    print("\nSafe to update Render and then delete the old database user.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
