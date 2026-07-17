"""Canonical public app URL for links in emails and redirects.

FRONTEND_URL may be a comma list (CORS origins) and may lead with the bare
Render URL; user-facing links must always prefer the custom domain (or
localhost in dev), never *.onrender.com. Dependency-free so core, invites,
nurture, and routers can all import it without cycles.
"""
import os


def _canonical_app_url(raw: str) -> str:
    entries = [e.strip().rstrip("/") for e in raw.split(",") if e.strip()]
    for e in entries:
        if ".onrender.com" not in e:
            return e
    return "https://app.intro-connect.com" if entries else "http://localhost:3000"


APP_URL = _canonical_app_url(os.getenv("FRONTEND_URL", "http://localhost:3000"))
