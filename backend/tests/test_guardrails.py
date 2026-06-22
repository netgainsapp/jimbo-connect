"""Unit tests for the blog guardrails. Pure, no DB. Run from backend/:
    python -m pytest tests/test_guardrails.py
"""
from blog.guardrails import check_guardrails, jaccard
from blog.schema import GeneratedPost, Section, slugify, post_text

FILLER = (
    "Following up after an event is where the real value lives. The people you "
    "met want to stay in touch, and a shared directory keeps everyone reachable "
    "long after the night ends. A good host turns one evening into a lasting "
    "network that benefits everyone who showed up. "
)


def make_post(
    title="How to follow up after a networking event",
    n_sections=3,
    body=None,
    summary="A practical look at staying in touch after the event ends.",
    cta="Start your private directory with Intro Connect.",
):
    body = body if body is not None else (FILLER * 2)
    sections = [
        Section(heading=f"Step {i + 1} toward staying in touch", body=body)
        for i in range(n_sections)
    ]
    return GeneratedPost(title=title, summary=summary, sections=sections, cta=cta)


def reasons_for(post, existing=(), **kw):
    kw.setdefault("slug", slugify(post.title))
    return check_guardrails(post, existing, **kw)


# --- the happy path ---

def test_clean_post_passes():
    assert reasons_for(make_post()) == []


def test_hyphenated_compound_word_is_not_a_dash():
    # "mobile-first" is a legitimate hyphen, not a dash
    post = make_post(body=FILLER + "It works in a mobile-first way for everyone. " + FILLER)
    assert "contains_dash" not in reasons_for(post)


# --- brand voice ---

def test_em_dash_flagged():
    post = make_post(body=FILLER + "This matters a lot — really it does. " + FILLER)
    assert "contains_dash" in reasons_for(post)


def test_spaced_hyphen_dash_flagged():
    post = make_post(body=FILLER + "We host events - lots of them - every month. " + FILLER)
    assert "contains_dash" in reasons_for(post)


def test_price_in_prose_flagged():
    post = make_post(body=FILLER + "It only costs $9 a month to run. " + FILLER)
    assert "price_in_prose" in reasons_for(post)


def test_banned_phrase_flagged():
    post = make_post(body=FILLER + "As an AI, I think networking is great. " + FILLER)
    assert "banned_phrase" in reasons_for(post)


def test_url_flagged():
    post = make_post(body=FILLER + "Read more at https://example.com today. " + FILLER)
    assert "url_in_prose" in reasons_for(post)


def test_script_tag_flagged():
    post = make_post(body=FILLER + "Sneaky <script>alert(1)</script> here. " + FILLER)
    assert "script_tag" in reasons_for(post)


# --- structure ---

def test_short_title_flagged():
    assert "title_length" in reasons_for(make_post(title="Networking"))


def test_long_title_flagged():
    long = "How to absolutely positively follow up after every single networking event you ever attend"
    assert "title_length" in reasons_for(make_post(title=long))


def test_too_few_sections_flagged():
    assert "too_few_sections" in reasons_for(make_post(n_sections=2))


def test_too_short_flagged():
    assert "length_out_of_bounds" in reasons_for(make_post(body="Short.", n_sections=3))


# --- dedupe / similarity ---

def test_duplicate_slug_flagged():
    existing = [{"slug": slugify("How to follow up after a networking event")}]
    assert "duplicate_slug" in reasons_for(make_post(), existing)


def test_duplicate_topic_flagged():
    existing = [{"slug": "other-slug", "topic_id": "t1"}]
    assert "duplicate_topic" in reasons_for(make_post(), existing, topic_id="t1")


def test_too_similar_flagged():
    post = make_post()
    existing = [
        {
            "slug": "different-slug",
            "title": post.title,
            "summary": post.summary,
            "sections": [s.model_dump() for s in post.sections],
            "cta": post.cta,
        }
    ]
    assert "too_similar" in reasons_for(post, existing)


def test_distinct_post_not_too_similar():
    post = make_post()
    existing = [
        {
            "slug": "x",
            "title": "Completely unrelated essay about gardening tomatoes",
            "summary": "Tomatoes need sun water and patience over a long warm summer.",
            "sections": [{"heading": "Soil", "body": "Compost helps the roots grow deep and strong."}],
            "cta": "Grow something.",
        }
    ]
    assert "too_similar" not in reasons_for(post, existing)


# --- data posts ---

def test_data_post_without_enough_comps_flagged():
    assert "no_data_backing" in reasons_for(make_post(), is_data_post=True, comp_count=5)


def test_data_post_with_enough_comps_ok():
    assert "no_data_backing" not in reasons_for(make_post(), is_data_post=True, comp_count=20)


def test_jaccard_basics():
    assert jaccard(set(), {1}) == 0.0
    assert jaccard({1, 2}, {1, 2}) == 1.0
    assert jaccard({1, 2}, {2, 3}) == 1 / 3
