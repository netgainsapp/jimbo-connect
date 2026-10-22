"""Email step 1 and LinkedIn previews for event leads. Pure functions, no
database. Run from backend/: python -m pytest tests/test_event_leads_copy.py
"""
import os
import re
from datetime import datetime, timezone

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import event_leads_copy as copy
import sales_templates

FORBIDDEN = re.compile(r"[—–\U0001F300-\U0001FAFF]")
NOW = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
CLAIM = "https://app.example.com/claim/abc123"


def _event(title, start, tz="America/Denver"):
    return {"title": title, "start": start, "timezone": tz}


def _lead(**over):
    anchor = _event("Denver Tech Mixer", "2026-11-04T18:00:00-07:00")
    lead = {
        "organizer_name": "Denver Devs",
        "anchor": anchor,
        "events": [anchor],
        "contact": {"name": "Jane Doe", "email": "jane@host.org"},
        "claim_url": CLAIM,
    }
    lead.update(over)
    return lead


def _template(key="ic-event-step-1"):
    return next(t for t in sales_templates.STARTERS if t["key"] == key)


def _email(lead):
    return copy.email_preview(lead, _template(), now=NOW)


def _all_outputs(lead):
    email = _email(lead)
    return [
        email["subject"],
        email["body"],
        copy.linkedin_note(lead, now=NOW),
        copy.linkedin_followup(lead, now=NOW),
    ]


def test_seeds_exist_with_cold_category_and_clean_copy():
    for key in ("ic-event-step-1", "ic-linkedin-note", "ic-linkedin-followup"):
        seed = _template(key)
        assert seed["category"] == "cold"
        assert FORBIDDEN.search(seed["subject"] + seed["body"]) is None
        for var in re.findall(r"\{(\w+)\}", seed["subject"] + seed["body"]):
            assert var in copy.TEMPLATE_VARS


def test_subject_leads_with_event_name_and_date():
    out = _email(_lead())
    assert out["subject"] == (
        "Denver Tech Mixer on Wednesday, November 4: your attendee directory is ready"
    )


def test_body_merges_name_claim_link_and_time_until():
    body = _email(_lead())["body"]
    assert body.startswith("Hi Jane,")
    assert CLAIM in body
    assert "in 14 days" in body
    assert body.rstrip().endswith("Scott")
    assert "{" not in body


def test_time_until_event_words():
    start = lambda day: _event("X", f"2026-10-{day}T18:00:00-06:00")
    assert copy.time_until_event(start(21), NOW) == "today"
    assert copy.time_until_event(start(22), NOW) == "tomorrow"
    assert copy.time_until_event(start(25), NOW) == "in 4 days"


def test_event_date_uses_the_anchor_timezone():
    # 03:00 UTC on Nov 5 is still the evening of Nov 4 in Denver.
    lead = _lead(anchor=_event("Late Night", "2026-11-05T03:00:00+00:00"))
    assert "Wednesday, November 4" in _email(lead)["subject"]


def test_first_name_falls_back_to_there():
    for contact in ({}, {"name": ""}, {"name": "   "}):
        assert _email(_lead(contact=contact))["body"].startswith("Hi there,")


def test_claim_url_placeholder_before_approve():
    lead = _lead()
    del lead["claim_url"]
    assert "the claim link appears after Approve" in _email(lead)["body"]


def test_series_line_only_with_two_future_events():
    one = _email(_lead())["body"]
    assert "so this would carry over" not in one

    first = _event("Denver Tech Mixer", "2026-11-04T18:00:00-07:00")
    second = _event("Winter Demo Night", "2026-12-09T18:00:00-07:00")
    far = _event("Spring Social", "2027-03-02T18:00:00-07:00")
    past = _event("Old Mixer", "2026-09-01T18:00:00-06:00")
    lead = _lead(anchor=first, events=[far, second, past, first])
    body = _email(lead)["body"]
    assert (
        "You have Denver Tech Mixer on Wednesday, November 4 and Winter Demo Night "
        "on Wednesday, December 9, so this would carry over from one to the next."
    ) in body
    assert "Spring Social" not in body

    only_past = _lead(events=[first, past])
    assert "so this would carry over" not in _email(only_past)["body"]


def test_empty_series_line_leaves_no_double_blank_line():
    body = _email(_lead())["body"]
    assert "\n\n\n" not in body
    assert not body.startswith("\n") and not body.endswith("\n\n")


def test_note_is_under_the_limit_with_the_link_intact_for_a_long_name():
    long_name = "The Annual Front Range Founders and Operators Networking Mixer " * 5
    lead = _lead(anchor=_event(long_name, "2026-11-04T18:00:00-07:00"))
    note = copy.linkedin_note(lead, now=NOW)
    assert len(note) <= copy.LINKEDIN_NOTE_MAX == 300
    assert note.count(CLAIM) == 1
    assert "The Annual Front Range" in note
    assert "Hi Jane" in note and "free" in note


def test_short_event_name_is_not_truncated():
    note = copy.linkedin_note(_lead(), now=NOW)
    assert '"Denver Tech Mixer"' in note and CLAIM in note


def test_followup_names_event_and_date_and_repeats_the_link():
    text = copy.linkedin_followup(_lead(), now=NOW)
    assert "Denver Tech Mixer" in text
    assert "Wednesday, November 4" in text
    assert CLAIM in text
    assert "on us" in text


def test_stored_template_text_wins_over_the_seed():
    custom = {"subject": "Hello {first_name}", "body": "About {event_name}\n\n{series_line}\n\nBye"}
    out = copy.email_preview(_lead(), custom, now=NOW)
    assert out == {"subject": "Hello Jane", "body": "About Denver Tech Mixer\n\nBye"}
    assert copy.linkedin_note(_lead(), "Hi {first_name} {claim_url}", now=NOW) == f"Hi Jane {CLAIM}"


def test_no_dash_or_emoji_in_any_output():
    long_name = "Founders Mixer " * 30
    second = _event("Winter Demo Night", "2026-12-09T18:00:00-07:00")
    leads = [
        _lead(),
        _lead(contact={}),
        _lead(anchor=_event(long_name, "2026-11-04T18:00:00-07:00")),
        _lead(events=[_lead()["anchor"], second]),
    ]
    for lead in leads:
        for text in _all_outputs(lead):
            assert FORBIDDEN.search(text) is None
