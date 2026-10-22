"""Pure helpers for LinkedIn campaign results: URL normalization, mapping one
result row to a status, and the forward-only status rule.

Two row shapes are understood, detected by header name, case-insensitively and
ignoring underscores so the CSV export (`profile_url`) and the webhook payload
(`profileUrl`) read the same way:

- minimal: `linkedin_url, status, at` with status invited, connected, replied
  or failed;
- Linked Helper: `profile_url` plus `invited_date_iso` / `invited_date`,
  `connected_at(_iso)` and `replied_message_1_text` (webhook:
  `repliedMessageText`). The status is the furthest step reached, replied over
  connected over invited. An empty date never means failed.

No database or web imports: the callers do the reading and the writing.
"""
import re
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit

STATUS_RANK = {
    "none": 0, "queued": 1, "exported": 2, "invited": 3, "connected": 4, "replied": 5,
}
RESULT_STATUSES = frozenset({"invited", "connected", "replied", "failed"})
FAILABLE_FROM = frozenset({"exported", "invited"})
LINKEDIN_HOST = "linkedin.com"
WWW_PREFIX = "www."
URL_KEYS = ("linkedinurl", "profileurl")
REPLY_KEYS = ("repliedmessage1text", "repliedmessagetext")
CONNECTED_KEYS = ("connectedatiso", "connectedat")
INVITED_KEYS = ("inviteddateiso", "inviteddate")
LOCALE_DATE_FORMATS = ("%B %d, %Y %I:%M:%S %p", "%b %d, %Y %I:%M:%S %p")
MAX_REASON_VALUE_CHARS = 40
NON_ALNUM = re.compile(r"[^a-z0-9]")


def normalize_linkedin_url(url):
    """`linkedin.com/in/<public-id>` for any spelling of a profile URL: no
    scheme, no `www.` or regional subdomain, no query, fragment or trailing
    slash, lowercase. Empty for a blank or unparseable value."""
    text = url.strip() if isinstance(url, str) else ""
    if not text:
        return ""
    if "://" not in text:
        text = "https://" + text
    try:
        parts = urlsplit(text)
        host = (parts.hostname or "").lower()
    except ValueError:
        return ""
    host = host[len(WWW_PREFIX):] if host.startswith(WWW_PREFIX) else host
    if host.endswith("." + LINKEDIN_HOST):
        host = LINKEDIN_HOST
    path = _profile_path(unquote(parts.path).rstrip("/").lower())
    if "." not in host or not path:
        return ""
    return host + path


def _profile_path(path):
    """`/in/<id>` for a profile path with extra segments such as /details/."""
    segments = path.split("/")
    return "/".join(segments[:3]) if path.startswith("/in/") else path


def parse_at(value):
    """An aware UTC datetime from an ISO or a Linked Helper locale string, or
    None when the value is empty or unreadable."""
    text = value.strip() if isinstance(value, str) else ""
    if not text:
        return None
    parsed = _parse_iso(text) or _parse_locale(text)
    if parsed is None:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def _parse_iso(text):
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _parse_locale(text):
    for pattern in LOCALE_DATE_FORMATS:
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue
    return None


def _fields(row):
    """The row keyed by lowercase letters and digits only."""
    return {
        NON_ALNUM.sub("", key.lower()): value
        for key, value in row.items() if isinstance(key, str)
    }


def _text(value):
    return "" if value is None else str(value).strip()


def _first(fields, keys):
    return next((text for text in (_text(fields.get(k)) for k in keys) if text), "")


def _derived(fields):
    """(status, at) from the Linked Helper columns, or (None, None)."""
    if _first(fields, REPLY_KEYS):
        return "replied", None
    for status, keys in (("connected", CONNECTED_KEYS), ("invited", INVITED_KEYS)):
        found = [fields.get(k) for k in keys if _text(fields.get(k))]
        if found:
            return status, next((d for d in map(parse_at, found) if d), None)
    return None, None


def map_row(row):
    """{url, status, at} for one result row, or None when the row names no
    profile, carries an unusable status, or reports nothing to apply."""
    fields = _fields(row)
    url = normalize_linkedin_url(_first(fields, URL_KEYS))
    if not url:
        return None
    explicit = _text(fields.get("status")).lower()
    if explicit:
        if explicit not in RESULT_STATUSES:
            return None
        return {"url": url, "status": explicit, "at": parse_at(fields.get("at"))}
    status, at = _derived(fields)
    return {"url": url, "status": status, "at": at} if status else None


def skip_reason(row):
    """Why `map_row` returned None: a message for a bad row, or '' for a row
    that is fine but has nothing to apply yet."""
    fields = _fields(row)
    if not normalize_linkedin_url(_first(fields, URL_KEYS)):
        return "missing profile url"
    explicit = _text(fields.get("status")).lower()
    if explicit and explicit not in RESULT_STATUSES:
        return f"unknown status '{explicit[:MAX_REASON_VALUE_CHARS]}'"
    return ""


def map_rows(rows):
    """(mapped, errors, idle) for a list of rows. Errors carry the 1-based
    data row number; idle counts rows with nothing to apply."""
    mapped, errors, idle = [], [], 0
    for number, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            errors.append({"row": number, "reason": "row is not an object"})
            continue
        item = map_row(row)
        if item:
            mapped.append(item)
            continue
        reason = skip_reason(row)
        if reason:
            errors.append({"row": number, "reason": reason})
        else:
            idle += 1
    return mapped, errors, idle


def _rank(status):
    """A failed lead sits where an exported one does, so a later invite
    (a retry) still counts as forward."""
    if status == "failed":
        return STATUS_RANK["exported"]
    return STATUS_RANK.get(status or "none", STATUS_RANK["none"])


def next_status(current, incoming):
    """`incoming` when it is a step forward from `current`, else None.
    Failed can be set only from exported or invited: it never overwrites a
    lead that has connected or replied, and it is set once."""
    if incoming not in RESULT_STATUSES:
        return None
    if incoming == "failed":
        return "failed" if current in FAILABLE_FROM else None
    return incoming if STATUS_RANK[incoming] > _rank(current) else None


def build_update(lead, item, now):
    """Dotted `$set` fields for one mapped row against one lead, or None when
    the status would not move forward."""
    current = (lead.get("linkedin") or {}).get("status")
    status = next_status(current, item["status"])
    if status is None:
        return None
    stamp = item["at"] or now
    fields = {
        "linkedin.status": status,
        f"linkedin.{status}_at": stamp,
        "linkedin.updated_at": now,
    }
    if status == "replied" and not (lead.get("funnel") or {}).get("linkedin_replied_at"):
        fields["funnel.linkedin_replied_at"] = stamp
    return fields


def apply_dotted(doc, fields):
    """Mirror dotted `$set` fields onto the in-memory document, so a second
    row for the same lead sees the first row's result."""
    for key, value in fields.items():
        *parents, leaf = key.split(".")
        target = doc
        for part in parents:
            if not isinstance(target.get(part), dict):
                target[part] = {}
            target = target[part]
        target[leaf] = value
