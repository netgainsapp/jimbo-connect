"""Signal Scout error-hub reporter (https://signal-scout.email/api/errors/report).

Fire-and-forget: never raises, never blocks the event loop, and rate-caps
itself so a crash loop cannot flood the hub. Reporting is a no-op unless
ERROR_HUB_KEY is set (report-only per-project key minted by the hub).
"""
import asyncio
import os
import time
import traceback

import httpx

ERROR_HUB_URL = "https://signal-scout.email/api/errors/report"

# At most this many reports per rolling window, per process. The hub digests
# every 30 minutes, so a capped sample is plenty to surface an incident.
MAX_REPORTS_PER_WINDOW = 25
WINDOW_SECONDS = 3600.0

_sent = 0
_window_start = 0.0


def _allow() -> bool:
    global _sent, _window_start
    now = time.monotonic()
    if now - _window_start > WINDOW_SECONDS:
        _window_start = now
        _sent = 0
    if _sent >= MAX_REPORTS_PER_WINDOW:
        return False
    _sent += 1
    return True


async def _post(payload: dict, key: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                ERROR_HUB_URL,
                json=payload,
                headers={"Authorization": f"Bearer {key}"},
            )
    except Exception:
        pass  # reporting must never break the app


def build_payload(kind: str, exc: BaseException, fatal: bool, url: str | None) -> dict:
    stack = "".join(
        traceback.format_exception(type(exc), exc, exc.__traceback__)
    )
    return {
        "kind": kind,
        "message": str(exc)[:1000] or type(exc).__name__,
        "stack": stack[:8000],
        "fatal": fatal,
        "platform": "server",
        "url": url,
    }


def report_error(kind: str, exc: BaseException, fatal: bool = False, url: str | None = None) -> None:
    """Schedule an error report; safe to call from async request handlers."""
    try:
        key = os.environ.get("ERROR_HUB_KEY", "")
        if not key or not _allow():
            return
        payload = build_payload(kind, exc, fatal, url)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # no loop (sync/test context): skip rather than block
        loop.create_task(_post(payload, key))
    except Exception:
        pass  # reporting must never break the app
