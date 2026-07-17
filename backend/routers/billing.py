"""Billing routes: Checkout session creation, plan status, and the Stripe
webhook that promotes/downgrades a user's plan. Dormant-safe: checkout returns
a clear not-configured signal without Stripe keys, and the webhook 401s until
STRIPE_WEBHOOK_SECRET is set. Moved-in style matches the other routers."""
import os

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request

import billing
from auth import get_current_user
from core import serialize_user
from database import users

router = APIRouter()

# Where Stripe returns the user after checkout (the product app).
_APP_URL = os.getenv("FRONTEND_URL", "https://app.intro-connect.com").split(",")[0].rstrip("/")


@router.get("/api/billing/status")
async def billing_status(user: dict = Depends(get_current_user)):
    limit = billing.event_limit_for(user)
    return {
        "plan": billing.plan_of(user),
        "configured": billing.is_configured(),
        "event_limit": limit,  # null = unlimited
        "subscription_status": user.get("subscription_status"),
    }


@router.post("/api/billing/checkout")
async def billing_checkout(payload: dict, user: dict = Depends(get_current_user)):
    plan = (payload or {}).get("plan", "")
    if plan not in ("starter", "pro"):
        raise HTTPException(status_code=400, detail="Choose the starter or pro plan")
    result = await billing.create_checkout_session(
        user,
        plan,
        success_url=f"{_APP_URL}/events?upgraded=1",
        cancel_url=f"{_APP_URL}/events",
    )
    if result.get("url"):
        return {"url": result["url"]}
    if result.get("skipped") == "not_configured":
        raise HTTPException(status_code=503, detail="Billing is not enabled yet")
    raise HTTPException(status_code=502, detail="Could not start checkout")


@router.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Signature-verified plan updates from Stripe. Disabled until
    STRIPE_WEBHOOK_SECRET is set."""
    if not os.getenv("STRIPE_WEBHOOK_SECRET"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    payload = await request.body()
    event = billing.verify_webhook(payload, request.headers.get("stripe-signature"))
    if event is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    change = billing.plan_update_from_event(event)
    if change is None:
        return {"ok": True, "ignored": event.get("type")}

    match, fields = change
    # Resolve the user selector: {"_id": <str>} needs an ObjectId; a
    # {"stripe_customer_id": ...} selector is used as-is.
    if "_id" in match:
        try:
            match = {"_id": ObjectId(match["_id"])}
        except Exception:
            return {"ok": True, "ignored": "bad_user_id"}
    res = await users.update_one(match, {"$set": fields})
    return {"ok": True, "matched": res.matched_count, "plan": fields.get("plan")}
