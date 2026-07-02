"""Lightweight in-memory rate limiting for sensitive endpoints.

The API runs as a single uvicorn worker on Render's free tier, so an in-process
sliding-window counter is sufficient to blunt brute force, credential stuffing,
and email-bomb abuse. State resets on restart, which is acceptable here. If the
service is ever scaled to multiple instances, move this to a shared store
(e.g. Redis) so limits are enforced across workers.
"""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

_lock = threading.Lock()
_hits: dict[str, list[float]] = defaultdict(list)

# Bound memory: if the key space grows large (many distinct IPs/emails), sweep
# buckets whose entries have all expired.
_MAX_KEYS = 20_000

# Number of trusted reverse proxies in front of the app (Render is one). Only
# the rightmost N entries of X-Forwarded-For are appended by proxies we
# control; anything to the left is client-supplied and forgeable.
_TRUSTED_PROXY_HOPS = max(1, int(os.getenv("TRUSTED_PROXY_HOPS", "1")))


def _client_ip(request: Request) -> str:
    """Real client IP behind a trusted reverse proxy.

    X-Forwarded-For is a comma-separated list where each proxy appends the
    address it received the request from. The leftmost entries are
    client-supplied and trivially spoofable, so keying rate limits on them
    lets a client rotate to a fresh bucket per request. We instead take the
    entry appended by the outermost trusted proxy (the Nth from the right,
    N = TRUSTED_PROXY_HOPS), which a client cannot forge."""
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            idx = -_TRUSTED_PROXY_HOPS if _TRUSTED_PROXY_HOPS <= len(parts) else 0
            return parts[idx]
    return request.client.host if request.client else "unknown"


def _record(key: str, limit: int, window_seconds: int, now: float) -> bool:
    """Return True if this hit is within the limit, False if it exceeds it."""
    cutoff = now - window_seconds
    bucket = _hits[key]
    # Drop timestamps outside the window (bucket is time-ordered).
    drop = 0
    for ts in bucket:
        if ts >= cutoff:
            break
        drop += 1
    if drop:
        del bucket[:drop]
    if len(bucket) >= limit:
        return False
    bucket.append(now)
    return True


def _sweep(now: float) -> None:
    if len(_hits) <= _MAX_KEYS:
        return
    for key in [k for k, v in _hits.items() if not v or v[-1] < now - 3600]:
        _hits.pop(key, None)


def guard(
    request: Request,
    scope: str,
    *,
    limit: int,
    window_seconds: int,
    identifier: str | None = None,
) -> None:
    """Enforce a per-IP limit for `scope`, plus an optional per-identifier
    (e.g. email) limit using the same budget. Raises HTTP 429 if exceeded.

    Both checks are evaluated so each gets recorded; if either is over budget
    the request is rejected.
    """
    now = time.time()
    with _lock:
        within = _record(f"{scope}:ip:{_client_ip(request)}", limit, window_seconds, now)
        if identifier:
            ident = identifier.lower().strip()
            if ident:
                ident_ok = _record(f"{scope}:id:{ident}", limit, window_seconds, now)
                within = within and ident_ok
        _sweep(now)
    if not within:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please wait a bit and try again.",
        )
