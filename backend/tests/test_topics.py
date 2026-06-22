"""Unit tests for blog topic selection (pure parts). Run from backend/:
    python -m pytest tests/test_topics.py
"""
from blog.topics import (
    EVERGREEN_TITLES,
    EVERGREEN_SCORE,
    evergreen_topics,
    select_topic,
)


def test_slugs_are_unique():
    topics = evergreen_topics()
    slugs = [t["id"] for t in topics]
    assert len(slugs) == len(set(slugs)), "topic slugs must be unique"
    assert len(topics) == len(EVERGREEN_TITLES)


def test_every_topic_has_a_nonempty_slug():
    for t in evergreen_topics():
        assert t["id"], f"empty slug for {t['title']!r}"
        assert t["score"] == EVERGREEN_SCORE
        assert t["kind"] == "evergreen"


def test_select_returns_first_unused():
    topics = evergreen_topics()
    first = topics[0]
    assert select_topic(topics, used_ids=[]) == first


def test_select_skips_used():
    topics = evergreen_topics()
    used = [topics[0]["id"], topics[1]["id"]]
    assert select_topic(topics, used) == topics[2]


def test_select_none_when_all_used():
    topics = evergreen_topics()
    all_ids = [t["id"] for t in topics]
    assert select_topic(topics, all_ids) is None


def test_higher_score_wins_over_order():
    topics = [
        {"id": "a", "title": "A", "kind": "evergreen", "score": 1000},
        {"id": "b", "title": "B", "kind": "data", "score": 1500},
    ]
    assert select_topic(topics, [])["id"] == "b"
