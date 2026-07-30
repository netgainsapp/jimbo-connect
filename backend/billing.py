"""Stripe billing: plan-aware limits, Checkout session creation, and webhook
ingestion that promotes/downgrades a user's plan.

Dormant-safe, like the rest of the integrations: with no STRIPE_SECRET_KEY the
checkout endpoint returns a clear "not configured" and the webhook 401s. Until
Stripe is configured AND a user actually subscribes, every account stays on the
free plan, so wiring this in changes no current behavior.

Plans:
  free    - 1 event  (today's behavior for everyone)
  starter - 10 events ($39/mo)
  pro     - unlimited ($99/mo)

BILLING_ENFORCED (default "true") gates whether limits apply at all. Set it to
"false" for an early-access window where everyone is unlimited regardless of plan.
"""
import os
import sys

FREE_EVENT_LIMIT = 1
# Lowered from 10 to 3 on 2026-07-30 to match what the pricing page has always
# advertised, and done now because Stripe is still in test mode so no paying
# customer loses anything. Doing this once real subscriptions exist would cut
# events off people mid-plan, so it is not a change to repeat casually.
STARTER_EVENT_LIMIT = 3

# Attendees per event, matching what the pricing page advertises. Pro is a
# high ceiling rather than unlimited, so unlike the event limit there is a
# number for every paid plan.
FREE_ATTENDEE_LIMIT = 50
STARTER_ATTENDEE_LIMIT = 250
PRO_ATTENDEE_LIMIT = 2000
# pro / admin => unlimited (represented as None)

PLANS = ("free", "starter", "pro")


def is_configured() -> bool:
    """True when Stripe Checkout can actually be created."""
    return bool(os.getenv("STRIPE_SECRET_KEY"))


def _enforced() -> bool:
    return os.getenv("BILLING_ENFORCED", "true").strip().lower() == "true"


def plan_of(user: dict) -> str:
    plan = (user or {}).get("plan") or "free"
    return plan if plan in PLANS else "free"


def event_limit_for(user: dict):
    """Max events this user may host, or None for unlimited. Admins and the pro
    plan are unlimited. When BILLING_ENFORCED is off, everyone is unlimited."""
    if not _enforced():
        return None
    if user.get("is_admin"):
        return None
    plan = plan_of(user)
    if plan == "pro":
        return None
    if plan == "starter":
        return STARTER_EVENT_LIMIT
    return FREE_EVENT_LIMIT


def attendee_limit_for(user: dict):
    """Max attendees on one of this host's events, or None for unlimited.

    Keyed off the HOST, not the person joining: the cap belongs to whoever is
    paying for the event. Admins are unlimited, and so is everyone when
    BILLING_ENFORCED is off, matching event_limit_for.
    """
    if not _enforced():
        return None
    if user.get("is_admin"):
        return None
    plan = plan_of(user)
    if plan == "pro":
        return PRO_ATTENDEE_LIMIT
    if plan == "starter":
        return STARTER_ATTENDEE_LIMIT
    return FREE_ATTENDEE_LIMIT


def price_id_for(plan: str):
    return {
        "starter": os.getenv("STRIPE_PRICE_STARTER", ""),
        "pro": os.getenv("STRIPE_PRICE_PRO", ""),
    }.get(plan, "")


#: Subscription is paid up: grant the plan its price maps to.
ACTIVE_STATUSES = ("active", "trialing")
#: Payment is failing but Stripe is still retrying, which it does for weeks.
#: Access is KEPT here on purpose. Dropping someone to free the moment a card
#: is declined loses them their events over a temporary bank decline, and
#: Stripe will send a definitive cancellation if it never recovers.
GRACE_STATUSES = ("past_due", "unpaid")
#: Definitively over.
ENDED_STATUSES = ("canceled", "incomplete_expired")


def _plan_for_price(price_id: str):
    """The plan a Stripe price maps to, or None when the price is unrecognised.

    None rather than "free" on purpose. Returning "free" for an unknown price
    means a single wrong STRIPE_PRICE_* value silently DOWNGRADES paying
    customers on their next renewal, because every renewal sends
    customer.subscription.updated. Unknown must mean "I do not know", so the
    caller can leave a paying customer alone instead of quietly cancelling
    them.
    """
    if not price_id:
        return None
    if price_id == os.getenv("STRIPE_PRICE_PRO", ""):
        return "pro"
    if price_id == os.getenv("STRIPE_PRICE_STARTER", ""):
        return "starter"
    return None


async def create_checkout_session(user: dict, plan: str, *, success_url: str, cancel_url: str) -> dict:
    """Create a Stripe Checkout session for a subscription. Returns
    {"url": ...} or {"error"/"skipped": ...}. Never raises on config gaps."""
    if plan not in ("starter", "pro"):
        return {"error": "unknown plan"}
    if not is_configured():
        return {"skipped": "not_configured"}
    price = price_id_for(plan)
    if not price:
        return {"skipped": f"no_price_configured_for_{plan}"}
    import stripe

    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price, "quantity": 1}],
            customer_email=user["email"],
            client_reference_id=str(user["_id"]),
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": str(user["_id"]), "plan": plan},
        )
        return {"url": session.url}
    except Exception as exc:  # network / Stripe API error
        print(f"[billing] checkout create failed: {exc}", file=sys.stderr)
        return {"error": "checkout_failed"}


def verify_webhook(payload: bytes, sig_header: str):
    """Return the verified Stripe event dict, or None. Never raises."""
    secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not secret or not sig_header:
        return None
    try:
        import stripe

        return stripe.Webhook.construct_event(payload, sig_header, secret)
    except Exception as exc:
        print(f"[billing] webhook verify failed: {exc}", file=sys.stderr)
        return None


def plan_update_from_event(event: dict):
    """Map a verified Stripe event to a (user_selector, fields) plan change, or
    None if the event is not one we act on. user_selector is a dict that matches
    a user by client_reference_id (user id) or stripe customer id.

    Returns (match, set_fields) where match is {"_id": ...} or
    {"stripe_customer_id": ...} and set_fields is the $set payload.
    """
    etype = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}

    if etype == "checkout.session.completed":
        user_id = obj.get("client_reference_id") or (obj.get("metadata") or {}).get("user_id")
        plan = (obj.get("metadata") or {}).get("plan") or "starter"
        if not user_id:
            return None
        return (
            {"_id": user_id},
            {
                "plan": plan if plan in PLANS else "starter",
                "stripe_customer_id": obj.get("customer"),
                "subscription_status": "active",
            },
        )

    if etype in ("customer.subscription.updated", "customer.subscription.created"):
        customer = obj.get("customer")
        if not customer:
            return None
        items = ((obj.get("items") or {}).get("data") or [])
        price_id = items[0].get("price", {}).get("id") if items else ""
        status = obj.get("status", "")

        if status in ENDED_STATUSES:
            return (
                {"stripe_customer_id": customer},
                {"plan": "free", "subscription_status": status},
            )

        if status in ACTIVE_STATUSES:
            plan = _plan_for_price(price_id)
            if plan is None:
                # Unrecognised price on an ACTIVE subscription. Almost always a
                # misconfigured STRIPE_PRICE_* env var. Record the status but
                # leave the plan alone: the customer is paying, and guessing
                # "free" here would cancel someone mid-subscription over a
                # config mistake.
                print(
                    f"[billing] active subscription on unknown price {price_id!r}; "
                    "leaving plan unchanged. Check STRIPE_PRICE_STARTER/PRO.",
                    file=sys.stderr,
                )
                return (
                    {"stripe_customer_id": customer},
                    {"subscription_status": status},
                )
            return (
                {"stripe_customer_id": customer},
                {"plan": plan, "subscription_status": status},
            )

        # past_due, unpaid, incomplete, paused: record it, keep their access.
        # Stripe retries a failing card for weeks and sends a definitive
        # cancellation if it never recovers, which ENDED_STATUSES handles.
        return (
            {"stripe_customer_id": customer},
            {"subscription_status": status},
        )

    if etype == "customer.subscription.deleted":
        customer = obj.get("customer")
        if not customer:
            return None
        return (
            {"stripe_customer_id": customer},
            {"plan": "free", "subscription_status": "canceled"},
        )

    return None
