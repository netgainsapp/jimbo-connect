"""Weekly news generation: feed parsing, text extraction, and the guardrails.

The rule under test that actually matters is `unsourced`. Everything else here
is quality control, but a news item carries a required source URL and is
presented as attributable reporting, so a source the model invented would be a
fabricated citation on a live page. The pipeline supplies the URL and the
guardrail refuses anything else.

Run from backend/: python -m pytest tests/test_news_pipeline.py
"""
from news import sources
from news.guardrails import check_news_guardrails

RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <title>Trade Weekly</title>
  <item>
    <title>Coworking Grew Again Last Quarter</title>
    <link>https://example.com/coworking-grew</link>
    <pubDate>Tue, 29 Jul 2026 09:00:00 +0000</pubDate>
    <description>&lt;p&gt;Growth continued.&lt;/p&gt;</description>
  </item>
  <item>
    <title>Older Story</title>
    <link>https://example.com/older</link>
    <pubDate>Mon, 01 Jun 2026 09:00:00 +0000</pubDate>
  </item>
</channel></rss>"""

ATOM = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Attendance Is Up</title>
    <link href="https://example.org/attendance"/>
    <updated>2026-07-30T12:00:00Z</updated>
    <summary>More people came.</summary>
  </entry>
</feed>"""


def _sections(body="Body text with enough substance to clear the minimum length. " * 6):
    return [
        {"heading": "What happened", "body": body},
        {"heading": "Why it matters", "body": body},
    ]


def _check(**overrides):
    kwargs = {
        "headline": "Coworking Locations Grew Again Last Quarter",
        "summary": "Skift Meetings reports that operators opened more locations, "
        "continuing a trend that began last year.",
        "sections": _sections(),
        "source_url": "https://example.com/coworking-grew",
        "allowed_source_urls": ["https://example.com/coworking-grew"],
        "slug": "coworking-locations-grew-again-last-quarter",
        "existing_articles": (),
    }
    kwargs.update(overrides)
    return check_news_guardrails(**kwargs)


# --- feed parsing -----------------------------------------------------------


def test_parses_rss_items_with_dates():
    items = sources.parse_feed(RSS, "Trade Weekly")
    assert [i["title"] for i in items] == [
        "Coworking Grew Again Last Quarter",
        "Older Story",
    ]
    assert items[0]["url"] == "https://example.com/coworking-grew"
    assert items[0]["published"].year == 2026
    assert items[0]["publisher"] == "Trade Weekly"


def test_parses_atom_link_href_not_element_text():
    """Atom puts the URL in an attribute; reading the text would yield ''."""
    items = sources.parse_feed(ATOM, "Other")
    assert items[0]["url"] == "https://example.org/attendance"


def test_description_markup_is_stripped():
    assert "<p>" not in sources.parse_feed(RSS, "Trade Weekly")[0]["summary"]


def test_items_without_a_usable_link_are_dropped():
    broken = RSS.replace("<link>https://example.com/older</link>", "<link>javascript:x</link>")
    urls = [i["url"] for i in sources.parse_feed(broken, "Trade Weekly")]
    assert urls == ["https://example.com/coworking-grew"]


def test_malformed_xml_returns_nothing_rather_than_raising():
    """A publisher serving an HTML error page must not break the cron."""
    assert sources.parse_feed("<html><body>nope", "Trade Weekly") == []


SENTENCE = (
    "Operators reported that demand held steady through the quarter, with more "
    "members renewing than in the same period last year. "
)


def test_article_text_drops_scripts_and_markup():
    html = f"<html><script>var a = 1;</script><body><p>{SENTENCE}</p></body></html>"
    text = sources.clean_article_text(html)
    assert "var a" not in text
    assert "Operators reported" in text


def test_navigation_chrome_is_not_mistaken_for_an_article():
    """A blocked or paywalled page still serves its menus. Without this, the
    length check passes on navigation alone and the model is asked to write
    about a story it was never shown."""
    chrome = "".join(
        f"<a>{label}</a>"
        for label in ("Latest News", "Advertise With Us", "Log in", "Coworking", "Design")
    )
    assert len(sources.clean_article_text(f"<body>{chrome}</body>")) < 600


def test_real_prose_survives_the_chrome_filter():
    html = "<body><a>Latest News</a><a>Log in</a><p>" + SENTENCE * 6 + "</p></body>"
    assert len(sources.clean_article_text(html)) >= 600


def test_article_text_is_capped():
    long_prose = ("<p>" + SENTENCE + "</p>") * 400
    assert len(sources.clean_article_text(long_prose)) <= sources.MAX_ARTICLE_CHARS


# --- relevance --------------------------------------------------------------


def test_off_topic_story_from_an_on_topic_feed_is_filtered_out():
    """Observed on the day this shipped: the coworking press runs healthcare and
    hiring stories, and picking by date alone would publish them."""
    assert not sources.is_relevant(
        {"title": "Agentic AI Will Test Every Healthcare Workflow", "summary": "Clinics adapt."}
    )


def test_topic_terms_match_whole_words_only():
    """"ghost" contains "host". This got a hiring story past the filter on the
    first live run, so it is pinned."""
    assert not sources.is_relevant(
        {"title": "New Website Lets Job Seekers Report Employers That Ghost Candidates", "summary": ""}
    )


def test_on_topic_story_is_kept():
    assert sources.is_relevant(
        {"title": "How Coworking Spaces Can Turn Members Into Community Leaders", "summary": ""}
    )
    assert sources.is_relevant(
        {"title": "Attendance Rose Sharply", "summary": "Organizers of trade shows reported gains."}
    )


def test_plurals_match_without_being_listed_twice():
    """Word boundaries stopped "organizer" matching "organizers"; the optional
    trailing s in the pattern is what fixes it, so it is pinned here."""
    for headline in ("Organizers Report Gains", "Venues Fill Up", "Attendees Return"):
        assert sources.is_relevant({"title": headline, "summary": ""}), headline


# --- the guardrail that matters ---------------------------------------------


def test_source_the_pipeline_never_fetched_is_rejected():
    """A plausible URL the model produced is exactly the failure mode here."""
    assert "unsourced" in _check(source_url="https://example.com/invented-by-the-model")


def test_real_fetched_source_passes():
    assert _check() == []


def test_same_story_is_not_written_up_twice():
    existing = [{"slug": "other", "source_url": "https://example.com/coworking-grew"}]
    assert "duplicate_source" in _check(existing_articles=existing)


# --- tone and shape ---------------------------------------------------------


def test_numbers_are_allowed_unlike_the_blog():
    """The blog bans numbers because it has nothing to back them with. A news
    item about growth is worthless without them, so this must pass."""
    body = (
        "Operators reported 9,400 locations open at the end of the quarter, up 3 percent "
        "on the previous three months, and revenue per desk held steady. "
    ) * 3
    assert _check(sections=_sections(body)) == []


def test_dashes_are_still_rejected():
    assert "contains_dash" in _check(summary="Growth continued " + "—" + " again, operators said, across the quarter.")


def test_urls_in_prose_are_rejected():
    body = "Read more at https://example.com/somewhere for the full detail. " * 8
    assert "url_in_prose" in _check(sections=_sections(body))


def test_ai_tells_are_rejected_and_the_phrase_is_named():
    """The reason has to say which phrase. The first live run came back with a
    bare "banned_phrase" against a draft in the database, which is unreadable
    from a cron log."""
    body = "According to the article, operators opened more locations last quarter. " * 8
    assert "banned_phrase:according to the article" in _check(sections=_sections(body))


def test_one_section_is_not_enough():
    assert "too_few_sections" in _check(sections=_sections()[:1])


def test_near_duplicate_of_an_existing_article_is_rejected():
    existing = [
        {
            "slug": "prior",
            "source_url": "https://example.com/prior",
            "headline": "Coworking Locations Grew Again Last Quarter",
            "summary": "Skift Meetings reports that operators opened more locations, "
            "continuing a trend that began last year.",
            "sections": _sections(),
        }
    ]
    assert "too_similar" in _check(existing_articles=existing)
