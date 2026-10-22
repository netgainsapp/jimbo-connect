"""The LinkedIn queue CSV: which leads belong in it and how a row reads.

Pure: the router loads leads and templates and marks the export. Every cell
passes the formula-injection guard the Outreach export uses, and there is no
email column: Linked Helper never needs one.
"""
import csv
import io

import event_leads_copy as copy
from outreach import _csv_safe

QUEUE_FIELDS = [
    "profile_url", "first_name", "last_name", "company", "event_name",
    "event_date", "claim_url", "note", "followup",
]


def has_url(lead):
    return bool(((lead.get("contact") or {}).get("linkedin_url") or "").strip())


def _split_name(name):
    first, _, last = (name or "").strip().partition(" ")
    return first, last.strip()


def queue_row(lead, note_body, followup_body, now):
    """One CSV row (a dict keyed by QUEUE_FIELDS) for a queued lead."""
    contact = lead.get("contact") or {}
    anchor = lead.get("anchor") or {}
    first, last = _split_name(contact.get("name"))
    row = {
        "profile_url": (contact.get("linkedin_url") or "").strip(),
        "first_name": first,
        "last_name": last,
        "company": lead.get("organizer_name") or "",
        "event_name": anchor.get("title") or "",
        "event_date": copy.format_date(anchor),
        "claim_url": lead.get("claim_url") or "",
        "note": copy.linkedin_note(lead, note_body, now),
        "followup": copy.linkedin_followup(lead, followup_body, now),
    }
    return {key: _csv_safe(value) for key, value in row.items()}


def to_csv(rows):
    """The header plus `rows`; an empty queue is a header-only file."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=QUEUE_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def export_filename(now):
    return f"linkedin-queue-{now:%Y-%m-%d}.csv"
