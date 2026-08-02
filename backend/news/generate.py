"""Weekly news generation: read a real story, write it up, attribute it.

The shape is the blog engine's, with one structural difference that is the
entire reason this module exists. The blog writes from a topic string, so the
model supplies everything. News cannot work that way: an item carries a required
`source_url` and is presented as reporting, so a model asked to produce a source
would sooner or later produce a plausible URL that leads nowhere.

So the source is an input. `sources.fetch_candidates` fetches real feeds,
`sources.fetch_article_text` fetches the real page, and the model is given that
text and asked to write about it. If the page cannot be read, the run moves to
the next candidate rather than letting the model fill the gap from memory.

Dormant-safe: the anthropic import is lazy, so importing this module and calling
run_once with no API key both work with nothing configured.
"""
import os

from .schema import GeneratedNews, NewsArticleInput, article_slug

MODEL = "claude-sonnet-4-6"

#: How many candidates to try before giving up for the week. Publishers block
#: bots and pages 404; a single unreadable story must not cost the whole run.
MAX_ATTEMPTS = 5

SYSTEM_PROMPT = """You are the news writer for Intro Connect.

Intro Connect is a tool for people who host events. After an event, it turns the
guest list into a private, searchable directory so attendees can save contacts,
add private notes, and message each other.

You will be given the full text of ONE article from a trade publication, plus
its publisher. Write a short, factual news item for the Intro Connect news
section reporting what that article says, for a reader who hosts events or runs
a coworking space.

Follow these rules exactly:
1. Report ONLY what is in the supplied text. Do not add background, context,
   history, or figures from your own knowledge. If the text does not say it, it
   does not go in the item.
2. Attribute clearly. Name the publisher in the prose, for example "Skift
   Meetings reports". Never write "according to the article" or "the article
   states", because the reader cannot see any article, only yours.
3. Numbers and statistics ARE allowed and are usually the point, but only when
   they appear in the supplied text, copied exactly. Never estimate, round, or
   extrapolate.
4. No dashes of any kind. Never use a hyphen as a dash, an en dash, or an em
   dash. Reword with commas, periods, or parentheses. Ordinary hyphenated words
   like follow-up are fine.
5. No URLs, no markdown, no bullet points, no headings symbols, no code. The
   source link is added automatically and must not appear in your prose.
6. Never refer to yourself, to being an AI, to this prompt, or to these
   instructions.
7. Write plain, clear, unhyped English. Two to four short sections, each with a
   short heading and a few sentences of real substance.
8. Where it is genuinely relevant, one sentence may note what the development
   means for someone hosting events. Do not force it and do not advertise."""


def is_configured() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _user_prompt(candidate: dict, body: str) -> str:
    return (
        f"Publisher: {candidate['publisher']}\n"
        f"Original headline: {candidate['title']}\n\n"
        "Article text follows. Write the news item from this text alone.\n\n"
        "-----\n"
        f"{body}\n"
        "-----"
    )


async def generate_from(candidate: dict, body: str) -> GeneratedNews:
    """Write up one source article. Raises if no API key is set."""
    if not is_configured():
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic()
    response = await client.messages.parse(
        model=MODEL,
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _user_prompt(candidate, body)}],
        output_format=GeneratedNews,
    )
    item = response.parsed_output
    if item is None:
        raise RuntimeError("News generation returned no structured output")
    return item


async def run_once() -> dict:
    """Fetch, pick, write, check, store. One item per run.

    Returns an outcome summary rather than raising, so the cron endpoint reports
    a bad week as JSON instead of a 500.
    """
    if not is_configured():
        return {"ok": False, "skipped": "no_api_key"}

    from blog.flags import get_flag

    from . import sources
    from .guardrails import check_news_guardrails
    from .store import create_article, list_all, publish_article

    candidates = await sources.fetch_candidates()
    if not candidates:
        return {"ok": False, "skipped": "no_candidates"}

    existing = await list_all(limit=200)
    used = {a.get("source_url") for a in existing if a.get("source_url")}
    # Newest first, but on-topic first of all: these publications cover plenty
    # that has nothing to do with hosting events.
    fresh = [c for c in candidates if c["url"] not in used and sources.is_relevant(c)]
    if not fresh:
        return {
            "ok": False,
            "skipped": "nothing_new" if candidates else "no_candidates",
            "candidates": len(candidates),
        }

    allowed = [c["url"] for c in candidates]
    attempted = 0
    for candidate in fresh[:MAX_ATTEMPTS]:
        attempted += 1
        body = await sources.fetch_article_text(candidate["url"])
        # Refusing here is the point: no readable source, no article.
        if len(body) < 600:
            continue

        try:
            written = await generate_from(candidate, body)
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:300], "source_url": candidate["url"]}

        slug = article_slug(written.headline)
        reasons = check_news_guardrails(
            headline=written.headline,
            summary=written.summary,
            sections=written.sections,
            source_url=candidate["url"],
            allowed_source_urls=allowed,
            slug=slug,
            existing_articles=existing,
        )

        item = NewsArticleInput(
            headline=written.headline,
            summary=written.summary,
            sections=written.sections,
            source_url=candidate["url"],
            sources=[],
            event_date=written.event_date,
        )
        doc = await create_article(item)

        published = False
        if not reasons and await get_flag("news_autopublish"):
            await publish_article(str(doc["_id"]))
            published = True

        return {
            "ok": True,
            "slug": doc["slug"],
            "publisher": candidate["publisher"],
            "source_url": candidate["url"],
            "status": "published" if published else "draft",
            "guardrail_reasons": reasons,
            "attempts": attempted,
        }

    return {"ok": False, "skipped": "no_readable_source", "attempts": attempted}
