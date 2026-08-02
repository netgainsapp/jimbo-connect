"""Generated cover images: the prompt, the compression, and the failure paths.

The behaviour that matters most is that nothing here can stop a post being
published. A missing picture has a fallback (the stock pool in blog.images); a
raised exception in the middle of the publishing run does not.

Run from backend/: python -m pytest tests/test_blog_cover.py
"""
import asyncio
import io

from blog import cover, covers


def _png(width=1536, height=1024, colour=(40, 90, 200)) -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(buffer, format="PNG")
    return buffer.getvalue()


class _Response:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class _Client:
    """Stands in for httpx.AsyncClient, which is used as an async context
    manager, so both protocol methods have to exist."""

    def __init__(self, response=None, raises=None):
        self._response = response
        self._raises = raises
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self._raises:
            raise self._raises
        return self._response


def _patch(monkeypatch, client):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(cover.httpx, "AsyncClient", lambda **kw: client)
    return client


# --- the prompt -------------------------------------------------------------


def test_prompt_carries_the_title_as_subject():
    assert "Following Up After an Event" in cover.prompt_for("Following Up After an Event")


def test_prompt_forbids_text_in_the_picture():
    """Image models will happily render a garbled version of the headline into
    the artwork if not told otherwise."""
    low = cover.prompt_for("Anything").lower()
    for banned in ("no text", "no words", "no lettering", "no logos"):
        assert banned in low


# --- compression ------------------------------------------------------------


def test_large_png_becomes_a_width_capped_jpeg():
    from PIL import Image

    out = cover._compress(_png())
    assert out is not None
    image = Image.open(io.BytesIO(out))
    assert image.format == "JPEG"
    assert image.width == cover.STORED_WIDTH


def test_compression_actually_shrinks_it():
    """The point of this step: a raw model PNG on a grid of tiles is megabytes."""
    raw = _png()
    out = cover._compress(raw)
    assert len(out) < len(raw)


def test_a_narrow_image_is_not_upscaled():
    from PIL import Image

    out = cover._compress(_png(width=600, height=400))
    assert Image.open(io.BytesIO(out)).width == 600


def test_junk_bytes_are_not_an_image():
    assert cover._compress(b"this is not a png") is None


# --- generation, and every way it can fail ----------------------------------


def test_returns_jpeg_bytes_on_success(monkeypatch):
    import base64

    payload = {"data": [{"b64_json": base64.b64encode(_png()).decode()}]}
    client = _patch(monkeypatch, _Client(_Response(200, payload)))
    out = asyncio.run(cover.generate("How to Introduce Yourself"))
    assert out and out[:2] == b"\xff\xd8"  # JPEG magic
    url, kwargs = client.calls[0]
    assert url == cover.API_URL
    assert kwargs["json"]["model"] == cover.MODEL
    assert "How to Introduce Yourself" in kwargs["json"]["prompt"]


def test_no_api_key_is_a_quiet_none(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert asyncio.run(cover.generate("Anything")) is None


def test_no_request_is_made_without_a_key(monkeypatch):
    """Not just the return value: an unconfigured deploy must not call out."""
    client = _Client(_Response(200, {}))
    monkeypatch.setattr(cover.httpx, "AsyncClient", lambda **kw: client)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    asyncio.run(cover.generate("Anything"))
    assert client.calls == []


def test_http_error_is_a_quiet_none(monkeypatch):
    _patch(monkeypatch, _Client(_Response(429, {})))
    assert asyncio.run(cover.generate("Anything")) is None


def test_the_api_error_message_is_kept_for_diagnosis(monkeypatch):
    """The first real run reported "no image returned" three times when the
    actual answer was a billing cap. Quiet in production, legible to whoever
    is looking."""
    payload = {"error": {"message": "Billing hard limit has been reached."}}
    _patch(monkeypatch, _Client(_Response(400, payload)))
    assert asyncio.run(cover.generate("Anything")) is None
    assert "Billing hard limit" in cover.LAST_FAILURE
    assert "400" in cover.LAST_FAILURE


def test_a_missing_key_says_so(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    asyncio.run(cover.generate("Anything"))
    assert "OPENAI_API_KEY" in cover.LAST_FAILURE


def test_failure_is_cleared_by_a_successful_run(monkeypatch):
    """A stale reason from an earlier post would be read as this post's."""
    import base64

    cover.LAST_FAILURE = "something old"
    payload = {"data": [{"b64_json": base64.b64encode(_png()).decode()}]}
    _patch(monkeypatch, _Client(_Response(200, payload)))
    assert asyncio.run(cover.generate("Anything")) is not None
    assert cover.LAST_FAILURE == ""


def test_refusal_with_no_image_is_a_quiet_none(monkeypatch):
    _patch(monkeypatch, _Client(_Response(200, {"data": [{}]})))
    assert asyncio.run(cover.generate("Anything")) is None


def test_a_timeout_never_escapes(monkeypatch):
    """A raised exception here would abort the publishing run mid flight."""
    _patch(monkeypatch, _Client(raises=TimeoutError("too slow")))
    assert asyncio.run(cover.generate("Anything")) is None


# --- the served URL ---------------------------------------------------------


def test_cover_path_is_derived_from_the_slug():
    assert covers.cover_path("how-to-network") == "/blog/cover/how-to-network.jpg"


def test_covers_are_cached_immutably():
    """A slug's artwork never changes, and a new post is a new slug."""
    assert "immutable" in covers.CACHE_CONTROL
