"""Agenda schemas and boundary validation.

Everything the client sends is untrusted and ends up inside a Word document
that gets emailed around, so validation is stricter than for ordinary web
output: URLs become clickable hyperlinks in a file that travels outside the
browser's protections, and control characters can corrupt the Open XML stream.
"""
from __future__ import annotations

import re
from datetime import date as _date
from typing import List, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

# A generous ceiling. This exists to bound docx build time and memory on an
# endpoint that anonymous callers can hit, not to constrain real agendas.
MAX_ITEMS = 300

# Data-URL logo cap. Base64 inflates by ~4/3, so this admits roughly a 1.5MB
# image before decoding.
MAX_LOGO_DATA_URL_CHARS = 2_000_000

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_ALLOWED_SCHEMES = {"http", "https"}
# "scheme:" per RFC 3986. Used to tell "already has a scheme" from a bare
# domain, so a scheme is never silently prepended onto one that exists.
_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")
_WHITESPACE_RE = re.compile(r"\s+")

# Strip C0/C1 control characters. Tab and newline are kept: python-docx handles
# them, and multi-line session descriptions are legitimate.
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def clean_text(value: Optional[str]) -> str:
    """Normalize free text before it reaches the document writer."""
    if not value:
        return ""
    return _CONTROL_RE.sub("", str(value)).strip()


def clean_url(value: Optional[str]) -> str:
    """Allow only http(s). A javascript:, data: or file: URI embedded in a
    distributed Word document is a real attack surface, so anything else is
    dropped rather than rejected: one bad link should not cost the organizer
    their whole export.

    Two traps this has to avoid, both of which bit an earlier version:

    1. Do not prefix "https://" onto a string that already carries a scheme.
       "javascript:alert(1)" has no "//", so a naive prefix turns it into
       "https://javascript:alert(1)", which parses with scheme "https" and
       passes the allowlist. Detect an existing scheme first and fail closed.
    2. Strip whitespace throughout, not just at the ends. Consumers routinely
       discard interior whitespace in a URL, so "java\\nscript:alert(1)" can be
       reconstituted into a live javascript: URI after it passes validation.
    """
    raw = _WHITESPACE_RE.sub("", clean_text(value))
    if not raw:
        return ""
    if _SCHEME_RE.match(raw):
        parsed = urlparse(raw)
        if parsed.scheme.lower() not in _ALLOWED_SCHEMES or not parsed.netloc:
            return ""
        return parsed.geturl()
    # No scheme at all, so treat it as a bare domain the organizer typed.
    parsed = urlparse(f"https://{raw}")
    if not parsed.netloc:
        return ""
    return parsed.geturl()


def _validate_time(value: Optional[str], field: str) -> str:
    raw = clean_text(value)
    if not raw:
        return ""
    if not _TIME_RE.match(raw):
        raise ValueError(f"{field} must be a 24 hour time like 09:00")
    return raw


class AgendaItem(BaseModel):
    """One session. Times are wall clock at the venue, stored as "HH:MM"
    strings rather than datetimes on purpose: an agenda is local to its room,
    and a UTC datetime renders a 9am session as 4pm for a reader in another
    timezone."""

    id: Optional[str] = Field(default=None, max_length=64)
    date: _date
    start_time: str = Field(default="")
    end_time: str = Field(default="")
    title: str = Field(default="", max_length=300)
    description: str = Field(default="", max_length=5000)
    location: str = Field(default="", max_length=200)
    speaker: str = Field(default="", max_length=200)
    external_url: str = Field(default="", max_length=2000)
    # Collected by the builder for the organizer's own use. Deliberately NOT
    # rendered into the export: the spec's Word-export contents list omits it,
    # so notes stay private to the builder.
    notes: str = Field(default="", max_length=5000)

    @field_validator("start_time")
    @classmethod
    def _start(cls, v):
        return _validate_time(v, "start_time")

    @field_validator("end_time")
    @classmethod
    def _end(cls, v):
        return _validate_time(v, "end_time")

    @field_validator("title", "description", "location", "speaker", "notes")
    @classmethod
    def _text(cls, v):
        return clean_text(v)

    @field_validator("external_url")
    @classmethod
    def _url(cls, v):
        return clean_url(v)

    @model_validator(mode="after")
    def _end_after_start(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class AgendaExportRequest(BaseModel):
    """A complete agenda, sent in one shot. Nothing is persisted."""

    event_name: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=5000)
    start_date: Optional[_date] = None
    end_date: Optional[_date] = None
    start_time: str = Field(default="")
    end_time: str = Field(default="")
    venue_name: str = Field(default="", max_length=200)
    venue_address: str = Field(default="", max_length=400)
    virtual_url: str = Field(default="", max_length=2000)
    organizer_name: str = Field(default="", max_length=200)
    organizer_company: str = Field(default="", max_length=200)
    organizer_email: str = Field(default="", max_length=320)
    event_website: str = Field(default="", max_length=2000)
    # Optional data URL ("data:image/png;base64,..."). Decoded and re-encoded
    # through Pillow before it is placed in the document.
    logo: Optional[str] = Field(default=None, max_length=MAX_LOGO_DATA_URL_CHARS)
    items: List[AgendaItem] = Field(default_factory=list, max_length=MAX_ITEMS)

    @field_validator(
        "event_name",
        "description",
        "venue_name",
        "venue_address",
        "organizer_name",
        "organizer_company",
        "organizer_email",
    )
    @classmethod
    def _text(cls, v):
        return clean_text(v)

    @field_validator("virtual_url", "event_website")
    @classmethod
    def _url(cls, v):
        return clean_url(v)

    @field_validator("start_time")
    @classmethod
    def _start(cls, v):
        return _validate_time(v, "start_time")

    @field_validator("end_time")
    @classmethod
    def _end(cls, v):
        return _validate_time(v, "end_time")

    @model_validator(mode="after")
    def _coherent_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self

    def display_name(self) -> str:
        return self.event_name or "Untitled event"

    def location_line(self) -> str:
        """Venue, address, or virtual link, whichever the organizer gave."""
        parts = [p for p in (self.venue_name, self.venue_address) if p]
        if parts:
            return ", ".join(parts)
        return self.virtual_url


def slugify_filename(name: str) -> str:
    """Filename stem for the download. ASCII only, so Content-Disposition needs
    no RFC 5987 encoding."""
    base = re.sub(r"[^a-zA-Z0-9]+", "-", clean_text(name)).strip("-").lower()
    base = re.sub(r"-{2,}", "-", base)
    return (base or "agenda")[:60]


def group_by_day(items: List[AgendaItem]) -> List[tuple]:
    """Items grouped into (date, [items]) pairs, days in chronological order
    and sessions ordered by start time within a day. Items without a start
    time sort last so an unscheduled placeholder never displaces real ones."""
    days: dict = {}
    for item in items:
        days.setdefault(item.date, []).append(item)
    out = []
    for day in sorted(days):
        ordered = sorted(days[day], key=lambda i: (i.start_time == "", i.start_time))
        out.append((day, ordered))
    return out
