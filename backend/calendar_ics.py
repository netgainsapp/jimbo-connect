"""iCalendar (.ics) generation for events.

RFC 5545 is unforgiving in two specific ways, and both are why this is a real
module rather than an f-string:

Escaping. A comma or semicolon inside SUMMARY or LOCATION is a field separator
unless it is backslash-escaped, so "Dinner, drinks and intros" silently
truncates in some clients and imports as junk in others. Newlines must become
a literal backslash-n.

Line folding. Lines over 75 octets must be folded with CRLF followed by a
single space. Unfolded long lines are the classic reason a file opens fine in
one calendar app and is rejected by another.

Everything here is a pure string builder, so it is testable without a calendar
client.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

PRODID = "-//Intro Connect//Event Calendar//EN"

# Used when an event has a start time but no end. Long enough to be useful in a
# calendar view, short enough not to block someone's whole evening.
DEFAULT_DURATION = timedelta(hours=2)

_MAX_OCTETS = 75


def escape_text(value) -> str:
    """Escape per RFC 5545 section 3.3.11. Order matters: backslashes first,
    or the escapes inserted below get escaped again."""
    text = str(value or "")
    text = text.replace("\\", "\\\\")
    text = text.replace(";", "\\;")
    text = text.replace(",", "\\,")
    text = text.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
    return text


def fold(line: str) -> str:
    """Fold to 75 octets per line, continuing with CRLF + one space.

    Counted in octets, not characters: a multi-byte character split across a
    fold boundary corrupts the file, so this measures the UTF-8 length.
    """
    raw = line.encode("utf-8")
    if len(raw) <= _MAX_OCTETS:
        return line
    parts, current = [], b""
    for char in line:
        encoded = char.encode("utf-8")
        # Continuation lines carry a leading space, so their budget is one less.
        budget = _MAX_OCTETS if not parts else _MAX_OCTETS - 1
        if len(current) + len(encoded) > budget:
            parts.append(current.decode("utf-8"))
            current = b""
        current += encoded
    if current:
        parts.append(current.decode("utf-8"))
    return "\r\n ".join(parts)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _stamp(value: datetime) -> str:
    return _utc(value).strftime("%Y%m%dT%H%M%SZ")


def _date_only(value: datetime) -> str:
    return value.strftime("%Y%m%d")


def build_event_ics(event: dict, *, url: str = "", now: datetime | None = None) -> str:
    """One VEVENT for an event, as a complete .ics document.

    An event stored at exactly midnight is treated as all day. The product only
    captures a single date for an event, so midnight almost always means "no
    time was given" rather than "starts at 00:00", and an all-day entry is the
    honest rendering of that.
    """
    start = event.get("date")
    if not isinstance(start, datetime):
        raise ValueError("event has no usable date")
    end = event.get("end_date")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        # PUBLISH, not REQUEST: this is a subscribe-style download, not a
        # meeting invitation that expects RSVP traffic back.
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{event.get('id') or event.get('_id')}@intro-connect.com",
        f"DTSTAMP:{_stamp(now or datetime.now(timezone.utc))}",
    ]

    all_day = start.hour == 0 and start.minute == 0 and not isinstance(end, datetime)
    if all_day:
        lines.append(f"DTSTART;VALUE=DATE:{_date_only(start)}")
        # DTEND is exclusive for all-day entries, so a one day event ends on
        # the following day. Without the +1 the event disappears from some
        # calendar views entirely.
        lines.append(f"DTEND;VALUE=DATE:{_date_only(start + timedelta(days=1))}")
    else:
        lines.append(f"DTSTART:{_stamp(start)}")
        finish = end if isinstance(end, datetime) and end > start else start + DEFAULT_DURATION
        lines.append(f"DTEND:{_stamp(finish)}")

    lines.append(f"SUMMARY:{escape_text(event.get('name') or 'Event')}")
    if event.get("location"):
        lines.append(f"LOCATION:{escape_text(event['location'])}")
    if event.get("description"):
        lines.append(f"DESCRIPTION:{escape_text(event['description'])}")
    if url:
        lines.append(f"URL:{escape_text(url)}")
    lines += ["STATUS:CONFIRMED", "END:VEVENT", "END:VCALENDAR"]

    # CRLF throughout, per spec. Some clients tolerate bare LF; others do not.
    return "\r\n".join(fold(line) for line in lines) + "\r\n"


def filename_for(event: dict) -> str:
    import re

    stem = re.sub(r"[^a-zA-Z0-9]+", "-", str(event.get("name") or "event")).strip("-").lower()
    return f"{(stem or 'event')[:60]}.ics"
