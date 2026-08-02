"""A generated photograph for each post.

Posts are written by a model that cannot draw, and the stock pool in
`blog.images` is ten photographs shared across a growing number of posts, so
repeats are guaranteed. This asks an image model for artwork specific to the
post's subject.

Three decisions worth knowing:

**Stored as bytes in Mongo, served from a URL, NOT inlined as a data URI.**
The app already keeps profile photos and host logos as base64 data URLs, so a
data URI would have matched the house pattern, but the blog index shows every
post at once: fifteen posts at ~180kb each would be a three megabyte HTML
document that no browser can cache a piece of. A URL per cover keeps the page
small and lets the browser cache each image normally.

**Downscaled and re-encoded before storage.** The model returns a large PNG.
Stored raw that is megabytes per post, on a page that shows a grid of them.
Pillow re-encodes to a width-capped JPEG, which is the difference between a
~180kb thumbnail and a ~2mb one.

**Dormant-safe and failure-safe.** No API key, a refusal, a timeout or a bad
response all return None, and the caller falls back to the stock pool. A post
must never fail to publish because a picture could not be drawn.
"""
from __future__ import annotations

import base64
import io
import os

import httpx

API_URL = "https://api.openai.com/v1/images/generations"
MODEL = "gpt-image-1"

#: 3:2, the closest landscape this model offers to the 16:10 tile and 16:9 hero.
#: Both crop with object-fit, so the exact ratio only has to be close.
SIZE = "1536x1024"

#: "high" roughly doubles the cost for artwork that is displayed at 338px wide
#: in a tile. Not worth it.
QUALITY = "medium"

#: Generation is slow. The blog tick allows 150s for the whole request, so this
#: has to leave room for the text generation that precedes it.
TIMEOUT = 90.0

#: What gets stored. Wide enough for the 712px hero on a retina screen without
#: paying for pixels nobody sees.
STORED_WIDTH = 1200
JPEG_QUALITY = 82

STYLE = (
    "Editorial photograph for a business article. Natural light, shallow depth "
    "of field, candid and unposed, muted realistic colour. Real people in a real "
    "space, shot at a slight distance. No text, no words, no lettering, no "
    "logos, no watermarks, no charts, no user interface, no illustration, no "
    "3D render, no collage."
)


#: Why the last generation failed, for whoever is looking. Swallowing every
#: error is right for the publishing path and useless for diagnosis: the first
#: real run reported "no image returned" three times when the actual answer was
#: "Billing hard limit has been reached", which is a two minute fix nobody could
#: see. Read by scripts/backfill_blog_covers.py.
LAST_FAILURE = ""


def is_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def _fail(reason: str) -> None:
    global LAST_FAILURE
    LAST_FAILURE = reason


def prompt_for(title: str) -> str:
    """The image brief for one post.

    The title carries the subject, so it is quoted rather than paraphrased, but
    it is framed as "an article about" so the model illustrates the topic rather
    than trying to render the sentence as text in the picture.
    """
    return (
        f"A photograph to accompany an article about: {title.strip()}. "
        "The setting is professional networking: a conference, a meetup, a "
        "coworking space, or people talking after an event. "
        f"{STYLE}"
    )


def _compress(raw: bytes) -> bytes | None:
    """Downscale and re-encode to JPEG. Returns None if the bytes are not an
    image we can read, which is treated as a generation failure."""
    try:
        from PIL import Image

        image = Image.open(io.BytesIO(raw))
        image = image.convert("RGB")
        if image.width > STORED_WIDTH:
            height = round(image.height * (STORED_WIDTH / image.width))
            image = image.resize((STORED_WIDTH, height), Image.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        return buffer.getvalue()
    except Exception:
        return None


async def generate(title: str) -> bytes | None:
    """JPEG bytes for a post, or None when anything at all goes wrong.

    Never raises. A missing picture is a cosmetic problem with a fallback; an
    exception here would take down the whole publishing run.
    """
    _fail("")
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        _fail("OPENAI_API_KEY is not set")
        return None

    payload = {
        "model": MODEL,
        "prompt": prompt_for(title),
        "size": SIZE,
        "quality": QUALITY,
        "n": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                API_URL,
                headers={"Authorization": f"Bearer {key}"},
                json=payload,
            )
        if response.status_code != 200:
            # The API's own words. Its errors are specific and actionable
            # ("Billing hard limit has been reached"); paraphrasing loses that.
            try:
                detail = response.json().get("error", {}).get("message", "")
            except Exception:
                detail = response.text[:200]
            _fail(f"HTTP {response.status_code}: {detail}")
            return None
        data = (response.json().get("data") or [{}])[0]
        encoded = data.get("b64_json")
        if not encoded:
            _fail("the response carried no image (a refusal, usually)")
            return None
        out = _compress(base64.b64decode(encoded))
        if out is None:
            _fail("the returned bytes could not be read as an image")
        return out
    except Exception as exc:
        _fail(f"{type(exc).__name__}: {str(exc)[:150]}")
        return None
