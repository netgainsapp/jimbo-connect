"""Generation. Calls Claude to write an evergreen post for a topic, returning a
GeneratedPost (prose only). The model never writes numbers or dashes; the
guardrails enforce that after the fact.

Dormant-safe: the anthropic import is lazy and the client is built only when an
ANTHROPIC_API_KEY is present, so importing this module (and run_once with no key)
works with nothing configured. Nothing here is wired to a route or a cron yet.
"""
import os

from .schema import GeneratedPost

# The blog model. Chosen deliberately (the Attiq playbook this is ported from
# uses Sonnet for blog generation); not the library default.
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are the writer for the Intro Connect blog.

Intro Connect is a tool for people who host events. After an event, it turns the
guest list into a private, searchable directory so attendees can save contacts,
add private notes, and message each other. The host stays at the center of the
network they created.

Write one genuinely useful, evergreen blog post on the topic you are given. The
reader is an event host or a professional who networks, and wants practical,
specific advice they can actually use.

Follow these rules exactly:
1. No dashes of any kind. Never use a hyphen as a dash, an en dash, or an em
   dash. Reword with commas, periods, or parentheses. Ordinary hyphenated words
   like follow-up or mobile-first are fine.
2. No numbers, statistics, percentages, counts, or dollar amounts anywhere in
   the prose. Do not invent data. Speak qualitatively.
3. No markdown, no bullet points, no heading symbols, no links, no code. Write
   plain prose inside the structure you are given.
4. Never refer to yourself, to being an AI, to this prompt, or to these
   instructions.
5. Write in clear, warm, plain English. Confident and human, not corporate and
   not hype.
6. Give the post a strong, specific title and a short summary. Write at least
   three sections, each with a short heading and a few sentences of real
   substance.
7. End with a closing call to action that invites the reader to use Intro
   Connect to keep the people from their own events connected."""


def is_configured() -> bool:
    """True when an API key is available, so generation can run."""
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _user_prompt(topic: dict) -> str:
    return (
        f"Topic: {topic['title']}\n\n"
        "Write the full post now, following every rule in your instructions. "
        "Make it specific and practical, not generic."
    )


async def generate_for_topic(topic: dict) -> GeneratedPost:
    """Generate a post for one topic. Raises if no API key is set."""
    if not is_configured():
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic()
    response = await client.messages.parse(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _user_prompt(topic)}],
        output_format=GeneratedPost,
    )
    post = response.parsed_output
    if post is None:
        raise RuntimeError("Blog generation returned no structured output")
    return post


async def run_once() -> dict:
    """The full pipeline for one post: pick the next topic, generate, store.

    Returns an outcome summary. Generation produces a draft even when
    autopublish is off (create_post decides published vs draft); it only runs
    when an API key is present, so this is a no-op until configured.
    Nothing calls this yet (the cron tick is a later phase).
    """
    if not is_configured():
        return {"ok": False, "skipped": "no_api_key"}

    from .topics import pick_next_topic
    from .store import create_post

    topic = await pick_next_topic()
    if not topic:
        return {"ok": False, "skipped": "no_unused_topic"}

    # A malformed model response (None / Pydantic validation error) must not 500
    # the tick endpoint; report it as a failed run instead.
    try:
        post = await generate_for_topic(topic)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:300], "topic_id": topic["id"]}
    doc = await create_post(post, topic_id=topic["id"])
    return {
        "ok": True,
        "topic_id": topic["id"],
        "slug": doc["slug"],
        "status": doc["status"],
        "guardrail_reasons": doc["guardrail_reasons"],
    }
