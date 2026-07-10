"""Route-level auth sweep (M15): every API route must reject unauthenticated
requests with 401 unless it is explicitly allowlisted as public or shared-
secret gated. A new route added without auth (or a route that silently loses
its auth dependency in a refactor) fails this test.

Also snapshots the route inventory (route_inventory.json) so the M13 router
split can prove it did not add, drop, or rename any route.

The TestClient is used WITHOUT its context manager so the app lifespan (Mongo
index creation) never runs; protected routes 401 in the auth dependency before
any DB access, so no live MongoDB is needed.

Run from backend/: python -m pytest tests/test_route_auth.py
"""
import json
import os
import re
from pathlib import Path

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import server

client = TestClient(server.app)

# Routes that are legitimately reachable without a session. These are NOT
# called here (several would touch the DB); the test only asserts the
# classification stays explicit and complete.
PUBLIC = {
    ("GET", "/api/health"),
    ("POST", "/api/auth/register"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/logout"),
    ("POST", "/api/auth/forgot-password"),
    ("POST", "/api/auth/reset-password"),
    ("GET", "/api/auth/magic/{token}"),
    ("GET", "/api/auth/verify-email"),
    ("GET", "/blog"),
    ("GET", "/blog/{slug}"),
    ("GET", "/api/unsubscribe"),
    ("POST", "/api/unsubscribe"),
}

# Shared-secret gated (cron ticks, webhook): callable without a session but
# must 401 when the secret header is missing. These ARE called.
SECRET_GATED = {
    ("POST", "/api/blog/tick"),
    ("POST", "/api/nurture/tick"),
    ("POST", "/api/invites/tick"),
    ("POST", "/api/webhooks/resend"),
}

_PARAM_RE = re.compile(r"\{[^}]+\}")


def _fill(path: str) -> str:
    return _PARAM_RE.sub("x", path)


def _api_routes():
    for route in server.app.routes:
        if isinstance(route, APIRoute):
            for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
                yield method, route.path


def test_all_routes_are_classified():
    inventory = set(_api_routes())
    unknown_public = (PUBLIC | SECRET_GATED) - inventory
    assert not unknown_public, f"allowlisted routes no longer exist: {unknown_public}"


def test_protected_routes_reject_unauthenticated(monkeypatch):
    monkeypatch.delenv("BLOG_TICK_SECRET", raising=False)
    monkeypatch.delenv("RESEND_WEBHOOK_SECRET", raising=False)
    failures = []
    for method, path in _api_routes():
        if (method, path) in PUBLIC:
            continue
        resp = client.request(method, _fill(path))
        if resp.status_code != 401:
            failures.append(f"{method} {path} -> {resp.status_code}")
    assert not failures, "routes reachable without auth:\n" + "\n".join(failures)


def test_route_inventory_matches_snapshot():
    """The M13 router split (and any future refactor) must not add, drop, or
    rename routes silently. Regenerate deliberately with:
    python -m tests.test_route_auth  (writes route_inventory.json)"""
    snapshot_path = Path(__file__).parent / "route_inventory.json"
    current = sorted(f"{m} {p}" for m, p in _api_routes())
    snapshot = json.loads(snapshot_path.read_text())
    assert current == snapshot, (
        "route inventory changed; if intentional, regenerate the snapshot"
    )


if __name__ == "__main__":
    out = Path(__file__).parent / "route_inventory.json"
    out.write_text(json.dumps(sorted(f"{m} {p}" for m, p in _api_routes()), indent=1))
    print(f"wrote {out}")
