"""Previews for the event lead engine: the step 1 email and the two LinkedIn
messages. The Signal Scout side owns the real step 1 send; this is its mirror
so the admin sees what a host will receive before approving.

Pure: no database or web imports at module level. Template text is passed in;
without it each function falls back to the seed in `sales_templates.STARTERS`.
"""
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import core
import event_leads_rules as rules

LINKEDIN_NOTE_MAX = 300
EMAIL_KEY = "ic-event-step-1"
NOTE_KEY = "ic-linkedin-note"
FOLLOWUP_KEY = "ic-linkedin-followup"
TEMPLATE_VARS = frozenset({
    "event_name", "event_date", "time_until_event", "first_name", "company",
    "claim_url", "series_line",
})
CLAIM_PLACEHOLDER = "the claim link appears after Approve"
DEFAULT_TZ = "America/Denver"
NO_DATE_TEXT = "your event date"
NO_DATE_UNTIL = "soon"
FIRST_NAME_FALLBACK = "there"
SERIES_MIN_EVENTS = 2
BLANK_RUN = re.compile(r"\n{3,}")


def seed_template(key):
    """The seeded template dict for `key`. Imported lazily because the seed
    module opens the database handle; nothing here touches Mongo."""
    import sales_templates
    return next(t for t in sales_templates.STARTERS if t["key"] == key)


def _zone(event):
    try:
        return ZoneInfo((event or {}).get("timezone") or DEFAULT_TZ)
    except Exception:
        return ZoneInfo(DEFAULT_TZ)


def _start(event):
    try:
        return datetime.fromisoformat(event["start"])
    except (KeyError, TypeError, ValueError):
        return None


def format_date(event):
    """'Wednesday, November 4' in the event's own timezone, or ''."""
    start = _start(event)
    if start is None:
        return ""
    if start.tzinfo is None:
        start = start.replace(tzinfo=_zone(event))
    local = start.astimezone(_zone(event))
    return f"{local:%A, %B} {local.day}"


def time_until_event(event, now):
    """'today', 'tomorrow' or 'in N days' by Denver calendar day."""
    try:
        days = rules.days_until(event["start"], now)
    except (KeyError, TypeError, ValueError):
        return NO_DATE_UNTIL
    if days <= 0:
        return "today"
    return "tomorrow" if days == 1 else f"in {days} days"


def _future_events(lead, now):
    """Distinct events that have not passed, soonest first. The anchor counts
    even when the events list leaves it out."""
    seen, found = set(), []
    for event in [lead.get("anchor") or {}, *(lead.get("events") or [])]:
        start = _start(event)
        identity = (event.get("title"), event.get("start"))
        if start is None or identity in seen:
            continue
        if rules.days_until(event["start"], now) < 0:
            continue
        seen.add(identity)
        found.append((start.astimezone(timezone.utc), event))
    return [event for _, event in sorted(found, key=lambda pair: pair[0])]


def series_line(lead, now):
    upcoming = _future_events(lead, now)
    if len(upcoming) < SERIES_MIN_EVENTS:
        return ""
    first, second = upcoming[:2]
    return (
        f"You have {first.get('title', '')} on {format_date(first)} and "
        f"{second.get('title', '')} on {format_date(second)}, so this would "
        "carry over from one to the next."
    )


def _first_name(lead):
    words = ((lead.get("contact") or {}).get("name") or "").split()
    return words[0] if words else FIRST_NAME_FALLBACK


def _context(lead, now):
    anchor = lead.get("anchor") or {}
    return {
        "event_name": anchor.get("title") or "",
        "event_date": format_date(anchor) or NO_DATE_TEXT,
        "time_until_event": time_until_event(anchor, now),
        "first_name": _first_name(lead),
        "company": lead.get("organizer_name") or "",
        "claim_url": lead.get("claim_url") or CLAIM_PLACEHOLDER,
        "series_line": series_line(lead, now),
    }


def _tidy(text):
    """Collapse the blank paragraph an empty {series_line} leaves behind."""
    return BLANK_RUN.sub("\n\n", text).strip()


def email_preview(lead, template=None, now=None):
    """Step 1 email as {subject, body} after variable merge."""
    ctx = _context(lead, now or datetime.now(timezone.utc))
    template = template or seed_template(EMAIL_KEY)
    return {
        "subject": core.merge_vars(template["subject"], ctx),
        "body": _tidy(core.merge_vars(template["body"], ctx)),
    }


def _shorten_name(text, ctx, limit):
    """Cut the event name, never the link, until the render fits `limit`."""
    name, rendered = ctx["event_name"], core.merge_vars(text, ctx)
    while len(rendered) > limit and name:
        name = name[: max(0, len(name) - (len(rendered) - limit))].rstrip()
        rendered = core.merge_vars(text, {**ctx, "event_name": name})
    return rendered


def linkedin_note(lead, template_body=None, now=None):
    """Connection note, at most LINKEDIN_NOTE_MAX characters."""
    ctx = _context(lead, now or datetime.now(timezone.utc))
    text = template_body or seed_template(NOTE_KEY)["body"]
    return _shorten_name(text, ctx, LINKEDIN_NOTE_MAX)


def linkedin_followup(lead, template_body=None, now=None):
    """Message sent once the connection request is accepted."""
    ctx = _context(lead, now or datetime.now(timezone.utc))
    return core.merge_vars(template_body or seed_template(FOLLOWUP_KEY)["body"], ctx)
