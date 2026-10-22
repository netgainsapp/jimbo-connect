"""Pure tests for LinkedIn URL normalization, result row mapping and the
forward-only status rule. No database, no web.

Run from backend/: python -m pytest tests/test_linkedin_results.py
"""
from datetime import datetime, timezone

import pytest

import linkedin_results as lr

NOW = datetime(2026, 11, 2, 15, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("raw", [
    "https://www.linkedin.com/in/Jane-Doe/",
    "http://linkedin.com/in/jane-doe?utm_source=x#top",
    "HTTPS://WWW.LINKEDIN.COM/in/jane-doe",
    "linkedin.com/in/jane-doe",
    "  https://ca.linkedin.com/in/jane-doe/  ",
])
def test_url_variants_normalize_to_one_key(raw):
    assert lr.normalize_linkedin_url(raw) == "linkedin.com/in/jane-doe"


@pytest.mark.parametrize("raw", ["", None, "   ", "not a url at all"])
def test_blank_or_junk_url_normalizes_to_empty(raw):
    assert lr.normalize_linkedin_url(raw) == ""


def test_status_rank_runs_forward():
    order = ["none", "queued", "exported", "invited", "connected", "replied"]
    ranks = [lr.STATUS_RANK[s] for s in order]
    assert ranks == sorted(ranks) and len(set(ranks)) == len(order)


def test_minimal_format_maps_status_and_iso_time():
    row = {"linkedin_url": "https://www.linkedin.com/in/jane-doe/",
           "status": "Connected", "at": "2026-11-01T10:30:00Z"}
    assert lr.map_row(row) == {
        "url": "linkedin.com/in/jane-doe",
        "status": "connected",
        "at": datetime(2026, 11, 1, 10, 30, tzinfo=timezone.utc),
    }


def test_headers_are_case_insensitive_and_empty_at_is_none():
    row = {"LinkedIn_URL": "linkedin.com/in/a", "STATUS": "failed", "At": ""}
    assert lr.map_row(row) == {"url": "linkedin.com/in/a", "status": "failed", "at": None}


def test_unknown_status_value_is_not_mapped_and_is_reported():
    row = {"linkedin_url": "linkedin.com/in/a", "status": "ghosted"}
    assert lr.map_row(row) is None
    assert "ghosted" in lr.skip_reason(row)


def test_row_without_a_url_is_reported():
    row = {"status": "invited"}
    assert lr.map_row(row) is None
    assert lr.skip_reason(row) == "missing profile url"


def test_linked_helper_csv_replied_beats_connected_beats_invited():
    base = {"profile_url": "https://www.linkedin.com/in/jane-doe/",
            "invited_date_iso": "2026-10-28T09:00:00Z",
            "connected_at": "2026-10-30T09:00:00Z"}
    invited = lr.map_row({**base, "connected_at": ""})
    connected = lr.map_row(base)
    replied = lr.map_row({**base, "replied_message_1_text": "Sounds great"})
    assert (invited["status"], connected["status"], replied["status"]) == (
        "invited", "connected", "replied")
    assert invited["at"] == datetime(2026, 10, 28, 9, 0, tzinfo=timezone.utc)
    assert connected["at"] == datetime(2026, 10, 30, 9, 0, tzinfo=timezone.utc)
    assert replied["at"] is None


def test_linked_helper_webhook_camel_case_maps_the_same_way():
    row = {"profileUrl": "https://www.linkedin.com/in/jane-doe/",
           "invitedDateIso": "2026-10-28T09:00:00Z",
           "connectedAtIso": "2026-10-30T09:00:00Z",
           "repliedMessageText": "  "}
    mapped = lr.map_row(row)
    assert mapped["status"] == "connected"
    assert mapped["url"] == "linkedin.com/in/jane-doe"


def test_locale_string_dates_parse_when_no_iso_field_exists():
    row = {"profile_url": "linkedin.com/in/a", "invited_date": "May 21, 2021 07:11:52 PM"}
    assert lr.map_row(row)["at"] == datetime(2021, 5, 21, 19, 11, 52, tzinfo=timezone.utc)


def test_a_row_with_no_dates_and_no_reply_changes_nothing_and_is_not_an_error():
    row = {"profile_url": "linkedin.com/in/a", "invited_date": "", "connected_at": None}
    assert lr.map_row(row) is None
    assert lr.skip_reason(row) == ""


def test_absence_is_never_failed():
    assert lr.map_row({"profile_url": "linkedin.com/in/a"}) is None


def test_next_status_only_moves_forward():
    assert lr.next_status("exported", "invited") == "invited"
    assert lr.next_status("invited", "replied") == "replied"
    assert lr.next_status("connected", "invited") is None
    assert lr.next_status("replied", "connected") is None
    assert lr.next_status("connected", "connected") is None


def test_failed_is_only_set_from_exported_or_invited():
    assert lr.next_status("exported", "failed") == "failed"
    assert lr.next_status("invited", "failed") == "failed"
    for current in ("none", "queued", "failed"):
        assert lr.next_status(current, "failed") is None


def test_failed_never_overwrites_connected_or_replied():
    assert lr.next_status("connected", "failed") is None
    assert lr.next_status("replied", "failed") is None


def test_a_failed_lead_can_still_be_invited_again():
    assert lr.next_status("failed", "invited") == "invited"


def test_profile_subpages_match_the_profile():
    base = lr.normalize_linkedin_url("https://www.linkedin.com/in/jane-doe")
    for extra in ("/details/experience/", "/recent-activity/all", "/overlay/contact-info/"):
        assert lr.normalize_linkedin_url(f"https://www.linkedin.com/in/jane-doe{extra}") == base


def test_non_profile_paths_keep_their_full_path():
    assert lr.normalize_linkedin_url("https://linkedin.com/company/acme/about/") ==         "linkedin.com/company/acme/about"


def test_build_update_sets_status_its_timestamp_and_updated_at():
    lead = {"linkedin": {"status": "exported"}}
    at = datetime(2026, 11, 1, tzinfo=timezone.utc)
    fields = lr.build_update(lead, {"url": "u", "status": "connected", "at": at}, NOW)
    assert fields == {
        "linkedin.status": "connected",
        "linkedin.connected_at": at,
        "linkedin.updated_at": NOW,
    }


def test_build_update_uses_now_when_at_is_missing_and_stamps_the_funnel_on_reply():
    lead = {"linkedin": {"status": "invited"}, "funnel": {"found_at": NOW}}
    fields = lr.build_update(lead, {"url": "u", "status": "replied", "at": None}, NOW)
    assert fields["linkedin.replied_at"] == NOW
    assert fields["funnel.linkedin_replied_at"] == NOW


def test_build_update_keeps_an_existing_funnel_reply_time():
    earlier = datetime(2026, 10, 1, tzinfo=timezone.utc)
    lead = {"linkedin": {"status": "connected"}, "funnel": {"linkedin_replied_at": earlier}}
    fields = lr.build_update(lead, {"url": "u", "status": "replied", "at": None}, NOW)
    assert "funnel.linkedin_replied_at" not in fields


def test_build_update_is_none_when_nothing_moves():
    lead = {"linkedin": {"status": "replied"}}
    assert lr.build_update(lead, {"url": "u", "status": "invited", "at": None}, NOW) is None
