"""Blog guardrails. Pure functions, fully unit-tested.

Runs after generation. ANY returned reason means the post is saved as a draft
and never published. This is where all the safety lives, so the pipeline can be
fully automated with no per-post human review.

Ported from the Attiq blog engine, adapted to Python. The non-negotiable rules:
numbers in a data post must be backed by enough real DB rows, the model never
writes dollar amounts or dashes, and near-duplicate posts never ship.
"""
import re

from .schema import GeneratedPost, post_text, doc_text

MIN_COMPS = 12
TITLE_MIN, TITLE_MAX = 20, 70
MIN_SECTIONS = 3
TEXT_MIN, TEXT_MAX = 600, 8000
SIMILARITY_THRESHOLD = 0.5

BANNED_PHRASES = (
    "as an ai",
    "as a language model",
    "lorem ipsum",
    "{{",
    "}}",
    "todo",
    "fixme",
    "click here",
)

_DASH_RE = re.compile(r" - |--|[–—]")
_PRICE_RE = re.compile(r"\$\s?\d")
_URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
_SCRIPT_RE = re.compile(r"<\s*script", re.IGNORECASE)
_WORD_RE = re.compile(r"\w+")


def _ngrams(text: str, n: int = 3):
    words = _WORD_RE.findall(text.lower())
    if len(words) < n:
        return set()
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def check_guardrails(
    post: GeneratedPost,
    existing_posts=(),
    *,
    slug: str,
    topic_id=None,
    is_data_post: bool = False,
    comp_count: int = 0,
) -> list:
    """Return a list of failure reasons (empty list == passes, may publish).

    existing_posts: iterable of dicts with keys slug, topic_id, and the post
    fields (title/summary/sections) so we can scan for duplicates/similarity.
    """
    reasons = []
    text = post_text(post)
    low = text.lower()

    if is_data_post and comp_count < MIN_COMPS:
        reasons.append("no_data_backing")

    if not (TITLE_MIN <= len(post.title) <= TITLE_MAX):
        reasons.append("title_length")

    if len(post.sections) < MIN_SECTIONS:
        reasons.append("too_few_sections")

    if not (TEXT_MIN <= len(text) <= TEXT_MAX):
        reasons.append("length_out_of_bounds")

    if _DASH_RE.search(text):
        reasons.append("contains_dash")

    if any(phrase in low for phrase in BANNED_PHRASES):
        reasons.append("banned_phrase")

    if _PRICE_RE.search(text):
        reasons.append("price_in_prose")

    if _URL_RE.search(text):
        reasons.append("url_in_prose")

    if _SCRIPT_RE.search(text):
        reasons.append("script_tag")

    existing = list(existing_posts)
    if slug in {p.get("slug") for p in existing}:
        reasons.append("duplicate_slug")

    if topic_id and topic_id in {p.get("topic_id") for p in existing if p.get("topic_id")}:
        reasons.append("duplicate_topic")

    grams = _ngrams(text)
    for p in existing:
        if jaccard(grams, _ngrams(doc_text(p))) > SIMILARITY_THRESHOLD:
            reasons.append("too_similar")
            break

    return reasons
