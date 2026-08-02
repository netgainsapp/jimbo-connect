"""News guardrails. Pure functions, unit tested.

Deliberately NOT the blog's guardrails. The two sections have opposite rules
about numbers: the blog bans them because an evergreen post has nothing to back
them with, while a news item about coworking growth is worthless without them.
Reusing `blog.guardrails.check_guardrails` here would reject every real story.

What is shared is the tone rule (no dashes) and the refusal to let a model put a
URL in prose.

The rule that matters most is `unsourced`. A news item is presented as
attributable reporting, so the `source_url` must be a URL the pipeline handed
to the model, never one the model produced. Everything else on this list is
quality control; that one is the difference between aggregation and fabrication.
"""
import re

from blog.guardrails import jaccard, _ngrams  # same similarity maths as the blog

HEADLINE_MIN, HEADLINE_MAX = 20, 140
SUMMARY_MIN = 40
MIN_SECTIONS = 2
TEXT_MIN, TEXT_MAX = 400, 9000
SIMILARITY_THRESHOLD = 0.5

BANNED_PHRASES = (
    "as an ai",
    "as a language model",
    "according to the article",
    "the article states",
    "lorem ipsum",
    "{{",
    "}}",
    "todo",
    "fixme",
    "click here",
)

_DASH_RE = re.compile(r" - |--|[–—]")
_URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
_SCRIPT_RE = re.compile(r"<\s*script", re.IGNORECASE)


def article_text(headline: str, summary: str, sections) -> str:
    parts = [headline, summary]
    for s in sections or []:
        heading = s.heading if hasattr(s, "heading") else s.get("heading", "")
        body = s.body if hasattr(s, "body") else s.get("body", "")
        parts.extend([heading, body])
    return "\n".join(p for p in parts if p)


def doc_text(doc: dict) -> str:
    return article_text(doc.get("headline", ""), doc.get("summary", ""), doc.get("sections") or [])


def check_news_guardrails(
    *,
    headline: str,
    summary: str,
    sections,
    source_url: str,
    allowed_source_urls,
    slug: str,
    existing_articles=(),
) -> list:
    """Return failure reasons. Empty list means it may publish.

    allowed_source_urls: the URLs the pipeline fetched this run. The source must
    be one of them.
    """
    reasons = []
    text = article_text(headline, summary, sections)
    low = text.lower()

    if source_url not in set(allowed_source_urls or ()):
        reasons.append("unsourced")

    if not (HEADLINE_MIN <= len(headline or "") <= HEADLINE_MAX):
        reasons.append("headline_length")

    if len(summary or "") < SUMMARY_MIN:
        reasons.append("summary_too_short")

    if len(sections or []) < MIN_SECTIONS:
        reasons.append("too_few_sections")

    if not (TEXT_MIN <= len(text) <= TEXT_MAX):
        reasons.append("length_out_of_bounds")

    if _DASH_RE.search(text):
        reasons.append("contains_dash")

    if any(phrase in low for phrase in BANNED_PHRASES):
        reasons.append("banned_phrase")

    if _URL_RE.search(text):
        # Sources belong in the sources list, where they are rendered and
        # checked, not loose in the prose where nothing validates them.
        reasons.append("url_in_prose")

    if _SCRIPT_RE.search(text):
        reasons.append("script_tag")

    existing = list(existing_articles)
    if slug in {a.get("slug") for a in existing}:
        reasons.append("duplicate_slug")

    if source_url and source_url in {a.get("source_url") for a in existing if a.get("source_url")}:
        reasons.append("duplicate_source")

    grams = _ngrams(text)
    for a in existing:
        if jaccard(grams, _ngrams(doc_text(a))) > SIMILARITY_THRESHOLD:
            reasons.append("too_similar")
            break

    return reasons
