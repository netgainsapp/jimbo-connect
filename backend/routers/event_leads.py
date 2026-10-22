"""Event lead engine routes: the ingest door and the admin list, detail,
archive and edit routes. Approve and claim build on the same store and rules."""
import hmac
import os
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

import event_leads_copy as copy
import event_leads_rules as rules
import sales_templates
import event_leads_store as store
from auth import get_current_admin
from database import events, users

router = APIRouter()

BEARER_PREFIX = "Bearer "
HIDDEN_FIELDS = ("_id", "claim_token_hash")


def require_ingest_key(authorization: Optional[str] = Header(None)):
    """Bearer auth for the weekly sourcing job. Fails closed: with no
    EVENT_LEADS_INGEST_KEY configured nothing can authenticate, so a missing
    env var locks the route instead of opening it. This is a dependency so it
    runs before the body is validated and a bad caller learns nothing."""
    secret = os.getenv("EVENT_LEADS_INGEST_KEY")
    header = authorization or ""
    token = header[len(BEARER_PREFIX):] if header.startswith(BEARER_PREFIX) else ""
    if not secret or not token or not hmac.compare_digest(
        token.encode(), secret.encode()
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")


class IngestLead(BaseModel):
    model_config = ConfigDict(extra="allow")

    organizer_key: str = Field(min_length=1)
    anchor: dict
    score: dict
    events: list[dict] = Field(default_factory=list)
    contact: dict = Field(default_factory=dict)


class IngestRequest(BaseModel):
    run: Optional[dict] = None
    leads: list[IngestLead] = Field(default_factory=list)


async def _matching_user(email):
    """The user owning `email`, plus whether they host any event."""
    if not email:
        return None
    user = await users.find_one({"email": email})
    if not user:
        return None
    hosts = await events.count_documents({"created_by": user["_id"]}) > 0
    return {**user, "hosts_events": hosts}


async def _ingest_one(incoming, now):
    """Merge and store one lead. Returns (outcome, resulting status)."""
    email = ((incoming.get("contact") or {}).get("email") or "").strip().lower()
    existing = await store.get_by_organizer_key(incoming["organizer_key"])
    user = await _matching_user(email)
    merged = rules.merge_ingest(existing, incoming, now, existing_user=user)
    if existing is None:
        outcome = "inserted"
    elif merged == existing:
        outcome = "unchanged"
    else:
        outcome = "updated"
    if outcome != "unchanged":
        await store.upsert_lead(merged)
    return outcome, merged["status"]


@router.post("/api/admin/event-leads/ingest", dependencies=[Depends(require_ingest_key)])
async def ingest_event_leads(body: IngestRequest):
    now = datetime.now(timezone.utc)
    counts = {"inserted": 0, "updated": 0, "unchanged": 0, "existing_customer": 0}
    for lead in body.leads:
        outcome, status = await _ingest_one(lead.model_dump(), now)
        counts[outcome] += 1
        if status == "existing_customer":
            counts["existing_customer"] += 1
    if body.run is not None:
        await store.record_run(body.run)
    return {"ok": True, **counts}


# Declare static routes (ingest, linkedin-queue.csv, settings) above this line:
# the `/{lead_id}` routes below would otherwise swallow them.

class ContactBody(BaseModel):
    name: str = ""
    email: str = ""
    linkedin_url: str = ""


class ScoreOverrideBody(BaseModel):
    score: int = Field(strict=True, ge=0, le=100)


def serialize_lead(doc, now=None):
    """Admin payload for one lead: `id` for `_id`, no claim hash, plus the
    whole days left until the anchor event (None without a usable start)."""
    out = {k: v for k, v in doc.items() if k not in HIDDEN_FIELDS}
    out["id"] = str(doc["_id"])
    for key, value in out.items():
        if isinstance(value, ObjectId):
            out[key] = str(value)
    start = (doc.get("anchor") or {}).get("start")
    try:
        out["days_until"] = (
            rules.days_until(start, now or datetime.now(timezone.utc)) if start else None
        )
    except ValueError:
        out["days_until"] = None
    return out


async def _load_or_404(lead_id):
    doc = await store.get_lead(lead_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return doc


async def _reload(doc):
    return serialize_lead(await _load_or_404(str(doc["_id"])))


async def _stored_or_seed(key):
    """The template row an admin may have edited, else the seeded copy."""
    row = await sales_templates.sales_templates.find_one({"seed_key": key})
    return row or copy.seed_template(key)


async def _previews(doc):
    """Step 1 email and both LinkedIn messages as the admin would send them."""
    email = await _stored_or_seed(copy.EMAIL_KEY)
    note = await _stored_or_seed(copy.NOTE_KEY)
    followup = await _stored_or_seed(copy.FOLLOWUP_KEY)
    return {
        "email_preview": copy.email_preview(doc, email),
        "linkedin_preview": {
            "note": copy.linkedin_note(doc, note["body"]),
            "followup": copy.linkedin_followup(doc, followup["body"]),
        },
    }


@router.get("/api/admin/event-leads")
async def list_event_leads(show_c: bool = False, admin: dict = Depends(get_current_admin)):
    now = datetime.now(timezone.utc)
    docs = await store.list_leads(show_c)
    docs.sort(key=lambda d: (d.get("status") == "archived", rules.tier_sort_key(d, now)))
    return {"leads": [serialize_lead(d, now) for d in docs], "kpis": []}


@router.get("/api/admin/event-leads/{lead_id}")
async def get_event_lead(lead_id: str, admin: dict = Depends(get_current_admin)):
    doc = await _load_or_404(lead_id)
    return {**serialize_lead(doc), **await _previews(doc)}


@router.post("/api/admin/event-leads/{lead_id}/archive")
async def archive_event_lead(lead_id: str, admin: dict = Depends(get_current_admin)):
    doc = await _load_or_404(lead_id)
    if doc.get("status") != "archived":
        await store.update_lead(doc["_id"], {
            "status": "archived",
            "archived_at": datetime.now(timezone.utc),
            "status_before_archive": doc.get("status") or "new",
        })
    return await _reload(doc)


@router.post("/api/admin/event-leads/{lead_id}/unarchive")
async def unarchive_event_lead(lead_id: str, admin: dict = Depends(get_current_admin)):
    doc = await _load_or_404(lead_id)
    if doc.get("status") == "archived":
        await store.update_lead(
            doc["_id"],
            {"status": doc.get("status_before_archive") or "new"},
            unset=("archived_at", "status_before_archive"),
        )
    return await _reload(doc)


@router.put("/api/admin/event-leads/{lead_id}/contact")
async def edit_event_lead_contact(
    lead_id: str, body: ContactBody, admin: dict = Depends(get_current_admin)
):
    doc = await _load_or_404(lead_id)
    old = doc.get("contact") or {}
    email = body.email.strip().lower()
    contact = {
        **old,
        "name": body.name.strip(),
        "email": email,
        "linkedin_url": body.linkedin_url.strip(),
    }
    if email != (old.get("email") or ""):
        contact["email_status"] = ""
    fields, unset = {"contact": contact}, ()
    if doc.get("status") in rules.REFRESHABLE_STATUSES:
        user = await _matching_user(email)
        fields["status"] = rules.initial_status({"contact": contact}, user)
        if user:
            fields["existing_user_id"] = str(user["_id"])
        else:
            unset = ("existing_user_id",)
    await store.update_lead(doc["_id"], fields, unset=unset)
    return await _reload(doc)


@router.put("/api/admin/event-leads/{lead_id}/score-override")
async def override_event_lead_score(
    lead_id: str, body: ScoreOverrideBody, admin: dict = Depends(get_current_admin)
):
    doc = await _load_or_404(lead_id)
    await store.update_lead(doc["_id"], {"score_override": body.score})
    return await _reload(doc)
