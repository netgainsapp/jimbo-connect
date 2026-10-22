"""Pure rules for the event lead engine. No database, no FastAPI.

A lead is one organizer (`organizer_key`) with the events found for them. The
weekly sourcing job re-sends the same organizers every run, so the central
question here is what a re-send may change. Once an admin has acted on a lead
(approved, claimed, archived) the email they approved is built from its anchor,
score and contact, so those are frozen and a re-send can only add to the
event history. A lead nobody has acted on is still a draft and takes the
newest data wholesale.
"""
import copy
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

DENVER = ZoneInfo("America/Denver")

# Statuses a re-send may overwrite. Everything else is frozen except `events`.
REFRESHABLE_STATUSES = ("new", "unreachable")

TIER_RANK = {"A": 0, "B": 1, "C": 2}
UNKNOWN_TIER_RANK = 3
# Sorts a lead with no usable anchor date after every dated lead of its tier.
NO_DATE_DAYS = 10**6

CONTACT_FIELDS = ("name", "email", "linkedin_url", "website", "email_status")


def _contact(raw):
    raw = raw or {}
    contact = {field: (raw.get(field) or "") for field in CONTACT_FIELDS}
    contact["email"] = contact["email"].strip().lower()
    return contact


def initial_status(incoming, existing_user):
    """First status for a lead.

    `existing_user` is the `users` row matching the contact email, enriched by
    the caller with `hosts_events` (does it own any event). Someone who already
    hosts, or pays, is a customer and must never be cold emailed as a prospect.
    """
    if existing_user and (
        existing_user.get("hosts_events")
        or (existing_user.get("plan") or "free") != "free"
    ):
        return "existing_customer"
    contact = incoming.get("contact") or {}
    if not (contact.get("email") or "").strip() and not (
        contact.get("linkedin_url") or ""
    ).strip():
        return "unreachable"
    return "new"


def _new_doc(incoming, now, existing_user):
    events = copy.deepcopy(incoming.get("events") or [])
    doc = {
        "organizer_key": incoming["organizer_key"],
        "organizer_name": incoming.get("organizer_name") or "",
        "organizer_url": incoming.get("organizer_url") or "",
        "city": incoming.get("city") or "",
        "events_listed": incoming.get("events_listed", len(events)),
        "anchor": copy.deepcopy(incoming.get("anchor") or {}),
        "events": events,
        "score": copy.deepcopy(incoming.get("score") or {}),
        "contact": _contact(incoming.get("contact")),
        "status": initial_status(incoming, existing_user),
        "signal_scout": {},
        "linkedin": {"status": "none"},
        "funnel": {"found_at": now, "scored_at": now},
        "created_at": now,
        "updated_at": now,
    }
    if existing_user:
        doc["existing_user_id"] = str(existing_user["_id"])
    return doc


def _refresh(doc, incoming, existing_user):
    """Draft lead: take the newest anchor, events, score and contact."""
    events = copy.deepcopy(incoming.get("events") or [])
    doc["organizer_name"] = incoming.get("organizer_name") or doc["organizer_name"]
    doc["organizer_url"] = incoming.get("organizer_url") or doc["organizer_url"]
    doc["city"] = incoming.get("city") or doc["city"]
    doc["anchor"] = copy.deepcopy(incoming.get("anchor") or {})
    doc["events"] = events
    doc["events_listed"] = incoming.get("events_listed", len(events))
    doc["score"] = copy.deepcopy(incoming.get("score") or {})
    doc["contact"] = _contact(incoming.get("contact"))
    doc["status"] = initial_status(incoming, existing_user)
    if existing_user:
        doc["existing_user_id"] = str(existing_user["_id"])
    else:
        doc.pop("existing_user_id", None)


def _union_events(current, incoming_events):
    """Append incoming events whose source_event_id is not already listed."""
    merged = list(current)
    seen = {e.get("source_event_id") for e in merged if e.get("source_event_id")}
    for event in incoming_events:
        event_id = event.get("source_event_id")
        if event_id:
            if event_id in seen:
                continue
            seen.add(event_id)
        elif event in merged:
            continue
        merged.append(copy.deepcopy(event))
    return merged


def _without_updated_at(doc):
    return {k: v for k, v in doc.items() if k != "updated_at"}


def merge_ingest(existing, incoming, now, existing_user=None):
    """Return the document to store for one incoming lead.

    Never mutates `existing`. When the merge changes nothing it returns a copy
    of `existing` untouched (same `updated_at`), so `merged == existing` is the
    caller's "unchanged" test.
    """
    if existing is None:
        return _new_doc(incoming, now, existing_user)

    doc = copy.deepcopy(existing)
    if doc.get("status") in REFRESHABLE_STATUSES:
        _refresh(doc, incoming, existing_user)
    else:
        doc["events"] = _union_events(
            doc.get("events") or [], incoming.get("events") or []
        )

    if _without_updated_at(doc) == _without_updated_at(existing):
        return copy.deepcopy(existing)
    doc["updated_at"] = now
    return doc


def _as_denver(moment):
    if moment.tzinfo is None:
        return moment.replace(tzinfo=DENVER)
    return moment.astimezone(DENVER)


def days_until(iso, now):
    """Whole Denver calendar days from `now` to the ISO instant `iso`."""
    target = _as_denver(datetime.fromisoformat(iso))
    return (target.date() - _as_denver(now).date()).days


def tier_sort_key(doc, now=None):
    """Sort key: tier A first, then soonest anchor first."""
    tier = (doc.get("score") or {}).get("tier")
    rank = TIER_RANK.get(tier, UNKNOWN_TIER_RANK)
    start = (doc.get("anchor") or {}).get("start")
    try:
        days = days_until(start, now or datetime.now(DENVER)) if start else NO_DATE_DAYS
    except ValueError:
        days = NO_DATE_DAYS
    return (rank, days)


# ---------- KPI strip ----------

KPI_WEEKS = 5
DAYS_PER_WEEK = 7
QUALIFYING_TIERS = ("A", "B")
RATE_PLACES = 3
# KPI field -> the lead's funnel timestamp it counts.
KPI_FUNNEL_FIELDS = {
    "approved": "approved_at",
    "emailed": "emailed_at",
    "opened": "opened_at",
    "clicked": "clicked_at",
    "claimed": "claimed_at",
    "attendees_uploaded": "attendees_uploaded_at",
    "converted": "converted_at",
}


def as_utc(value):
    """A datetime or ISO string as an aware UTC datetime, else None. Mongo hands
    datetimes back naive, and they are UTC."""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _week_monday(moment):
    """The Denver Monday on or before `moment`, as a date."""
    day = _as_denver(moment).date()
    return day - timedelta(days=day.weekday())


def _count(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def _tally(rows, key_of, weeks):
    """Rows per week key, for the weeks asked about only."""
    out = {week: [] for week in weeks}
    for row in rows:
        week = key_of(row)
        if week in out:
            out[week].append(row)
    return out


def _run_week(run):
    received = as_utc(run.get("received_at"))
    return _week_monday(received) if received else None


def _ingest_totals(runs):
    ingested = sum(_count(run.get("ingested")) for run in runs)
    qualified = sum(
        _count((run.get("by_tier") or {}).get(tier))
        for run in runs for tier in QUALIFYING_TIERS
    )
    rate = round(qualified / ingested, RATE_PLACES) if ingested else 0.0
    return ingested, rate


def _funnel_counts(leads, weeks):
    """For each KPI field, how many leads hit it in each of the weeks."""
    counts = {name: {week: 0 for week in weeks} for name in KPI_FUNNEL_FIELDS}
    for lead in leads:
        funnel = lead.get("funnel") or {}
        for name, stamp in KPI_FUNNEL_FIELDS.items():
            moment = as_utc(funnel.get(stamp))
            week = _week_monday(moment) if moment else None
            if week in counts[name]:
                counts[name][week] += 1
    return counts


def kpis(leads, runs, now, weeks=KPI_WEEKS):
    """The KPI strip: one row per Denver week (Monday to Sunday), newest first.

    Ingest numbers come from the runs received that week, the funnel counts
    from the lead timestamps that fall in it. Pure; archived leads count too,
    since a lead archived after it was emailed was still emailed."""
    this_monday = _week_monday(now)
    mondays = [this_monday - timedelta(days=DAYS_PER_WEEK * i) for i in range(weeks)]
    runs_by_week = _tally(runs, _run_week, mondays)
    counts = _funnel_counts(leads, mondays)
    rows = []
    for monday in mondays:
        ingested, rate = _ingest_totals(runs_by_week[monday])
        rows.append({
            "week": monday.isoformat(),
            "ingested": ingested,
            "qualification_rate": rate,
            **{name: counts[name][monday] for name in KPI_FUNNEL_FIELDS},
        })
    return rows
