"""Event lead engine routes. This task adds only the ingest door; the admin
list, approve and claim routes build on the same store and rules."""
import hmac
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

import event_leads_rules as rules
import event_leads_store as store
from database import events, users

router = APIRouter()

BEARER_PREFIX = "Bearer "


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
