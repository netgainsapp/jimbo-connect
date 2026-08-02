"""Where news comes from.

The whole point of this module is that **Intro Connect never invents a source**.
A news item carries a required `source_url` and is presented as attributable
reporting, so the URL cannot be something a language model produced. Here the
URL is an *input*: real feeds are fetched, a real item is chosen, and the model
is later asked to write about that item and nothing else.

Feeds were checked by hand on 2026-08-02 and all four returned parseable XML.
Publishers move and break feeds, so `fetch_candidates` treats every feed as
optional: one dead feed degrades the pool, it does not fail the run.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import httpx

#: Curated, on-topic, and deliberately short. These are trade publications for
#: the events, meetings and coworking industries, which is what the audience
#: actually is. Adding a general business feed would drown the section.
FEEDS = (
    ("Skift Meetings", "https://meetings.skift.com/feed/"),
    ("Allwork.Space", "https://allwork.space/feed/"),
    ("PCMA", "https://www.pcma.org/feed/"),
    ("TSNN", "https://www.tsnn.com/rss.xml"),
)

USER_AGENT = "IntroConnectBot/1.0 (+https://intro-connect.com)"
FEED_TIMEOUT = 15.0
ARTICLE_TIMEOUT = 20.0

#: Enough of the article for the model to write from, capped so one enormous
#: page cannot blow up the request.
MAX_ARTICLE_CHARS = 12000

_TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
_MARKUP_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t\r\f\v]+")
_BLANKS_RE = re.compile(r"\n{3,}")


def _text(el) -> str:
    return "".join(el.itertext()).strip() if el is not None else ""


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _parse_date(raw: str):
    """RSS uses RFC 2822, Atom uses ISO 8601. Accept either, give up quietly."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def parse_feed(xml_text: str, publisher: str) -> list:
    """Pull items out of an RSS or Atom document. Never raises on odd feeds."""
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return []

    items = []
    for node in root.iter():
        if _strip_ns(node.tag) not in ("item", "entry"):
            continue
        fields = {}
        link = ""
        for child in node:
            name = _strip_ns(child.tag)
            if name == "link":
                # RSS puts the URL in the text, Atom in an href attribute.
                link = link or (child.get("href") or _text(child))
            elif name in ("title", "description", "summary", "pubDate", "published", "updated"):
                fields.setdefault(name, _text(child))

        title = fields.get("title", "").strip()
        if not title or not link.startswith(("http://", "https://")):
            continue

        published = _parse_date(
            fields.get("pubDate") or fields.get("published") or fields.get("updated") or ""
        )
        summary = _MARKUP_RE.sub(" ", fields.get("description") or fields.get("summary") or "")
        items.append(
            {
                "publisher": publisher,
                "title": " ".join(title.split()),
                "url": link.strip(),
                "published": published,
                "summary": " ".join(summary.split())[:600],
            }
        )
    return items


#: These feeds are on-topic publications but not on-topic every day: the
#: coworking press covers healthcare AI and hiring, and picking purely by date
#: would put "Agentic AI Will Test Every Healthcare Workflow" on the news page
#: of a tool for event hosts. Observed, not hypothetical: that was the second
#: newest item the day this shipped. A candidate has to mention the subject.
#: Singular forms only. The pattern below allows an optional trailing "s", so
#: listing both spellings would be noise, and forgetting one (as happened with
#: "organizers") silently narrows the filter.
TOPIC_TERMS = (
    "event", "meeting", "conference", "convention", "attendee", "delegate",
    "venue", "coworking", "co-working", "networking", "network", "community",
    "trade show", "tradeshow", "exhibition", "expo", "summit", "hospitality",
    "organizer", "organiser", "planner", "host", "membership", "member",
    "in-person", "hybrid", "gathering",
)


#: Whole words only. Substring matching let "Employers That Ghost Candidates"
#: through, because "ghost" contains "host". Caught live on the first run.
_TOPIC_RE = re.compile(
    r"\b(?:"
    + "|".join(re.escape(t) for t in sorted(TOPIC_TERMS, key=len, reverse=True))
    + r")s?\b",
    re.IGNORECASE,
)


def is_relevant(candidate: dict) -> bool:
    """Whether a story is about the thing this audience does.

    Matched on the headline and the feed summary only. The full article is not
    fetched yet at this point, and a passing mention buried in paragraph nine
    does not make a story about events.
    """
    return bool(_TOPIC_RE.search(f"{candidate.get('title', '')} {candidate.get('summary', '')}"))


async def fetch_candidates(limit_per_feed: int = 10) -> list:
    """Every recent item across every feed, newest first.

    A feed that 403s, times out or returns junk contributes nothing and is
    skipped. Returning a short list is a normal outcome; raising is not.
    """
    candidates = []
    headers = {"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml"}
    async with httpx.AsyncClient(
        timeout=FEED_TIMEOUT, follow_redirects=True, headers=headers
    ) as client:
        for publisher, url in FEEDS:
            try:
                response = await client.get(url)
                if response.status_code != 200:
                    continue
                candidates.extend(parse_feed(response.text, publisher)[:limit_per_feed])
            except Exception:
                # One publisher's outage must not stop the week's article.
                continue

    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    candidates.sort(key=lambda c: c["published"] or epoch, reverse=True)
    return candidates


#: A line has to look like a sentence to survive. Without this the extracted
#: "article" is mostly navigation ("Latest News", "Advertise With Us", "Log in"),
#: and a page that blocked us or paywalled the body would still clear the
#: length check on menu items alone, leaving the model to write from nothing.
MIN_PROSE_LINE = 60


def _looks_like_prose(line: str) -> bool:
    if len(line) < MIN_PROSE_LINE:
        return False
    # Menus and breadcrumbs are long only because they are many short labels
    # glued together, and they almost never contain sentence punctuation.
    return any(mark in line for mark in (". ", "? ", "! ")) or line.endswith((".", "?", "!"))


def clean_article_text(html: str) -> str:
    """Crude but predictable readable-text extraction.

    Deliberately not a readability library: the model only needs the substance,
    and a dependency that guesses at article boundaries is one more thing that
    can break silently in a cron.
    """
    without_code = _TAG_RE.sub(" ", html)
    text = _MARKUP_RE.sub("\n", without_code)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&#8217;", "'")
        .replace("&#8216;", "'")
        .replace("&rsquo;", "'")
        .replace("&lsquo;", "'")
    )
    text = _WS_RE.sub(" ", text)
    lines = [line.strip() for line in text.split("\n")]
    prose = [line for line in lines if _looks_like_prose(line)]
    return _BLANKS_RE.sub("\n\n", "\n".join(prose)).strip()[:MAX_ARTICLE_CHARS]


async def fetch_article_text(url: str) -> str:
    """The source article's readable text, or "" when it cannot be read.

    An empty result is meaningful: the caller must refuse to write an article it
    could not actually read, rather than let the model fill the gap from memory.
    """
    headers = {"User-Agent": USER_AGENT}
    try:
        async with httpx.AsyncClient(
            timeout=ARTICLE_TIMEOUT, follow_redirects=True, headers=headers
        ) as client:
            response = await client.get(url)
            if response.status_code != 200:
                return ""
            return clean_article_text(response.text)
    except Exception:
        return ""
