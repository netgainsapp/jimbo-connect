"""Stripe webhook plan changes, with real money in mind.

These are the cases that only cost something once live keys are in: a
misconfigured price id, and a card that fails temporarily.

Run from backend/: python -m pytest tests/test_billing_webhook.py
"""
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import pytest

import billing

PRO_PRICE = "price_live_pro_123"
STARTER_PRICE = "price_live_starter_456"


@pytest.fixture(autouse=True)
def _prices(monkeypatch):
    monkeypatch.setenv("STRIPE_PRICE_PRO", PRO_PRICE)
    monkeypatch.setenv("STRIPE_PRICE_STARTER", STARTER_PRICE)


def _sub_event(status, price_id, etype="customer.subscription.updated"):
    return {
        "type": etype,
        "data": {
            "object": {
                "customer": "cus_123",
                "status": status,
                "items": {"data": [{"price": {"id": price_id}}]},
            }
        },
    }


# ---------------------------------------------------------------------------
# Normal upgrades
# ---------------------------------------------------------------------------

def test_active_pro_subscription_grants_pro():
    match, fields = billing.plan_update_from_event(_sub_event("active", PRO_PRICE))
    assert match == {"stripe_customer_id": "cus_123"}
    assert fields["plan"] == "pro"


def test_active_starter_subscription_grants_starter():
    _, fields = billing.plan_update_from_event(_sub_event("active", STARTER_PRICE))
    assert fields["plan"] == "starter"


def test_trialing_counts_as_active():
    _, fields = billing.plan_update_from_event(_sub_event("trialing", PRO_PRICE))
    assert fields["plan"] == "pro"


def test_checkout_completed_grants_the_plan_and_stores_the_customer():
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {
            "client_reference_id": "user-1",
            "customer": "cus_123",
            "metadata": {"user_id": "user-1", "plan": "pro"},
        }},
    }
    match, fields = billing.plan_update_from_event(event)
    assert match == {"_id": "user-1"}
    assert fields["plan"] == "pro"
    assert fields["stripe_customer_id"] == "cus_123"


# ---------------------------------------------------------------------------
# The misconfigured price id: the expensive one
# ---------------------------------------------------------------------------

def test_an_unknown_price_never_downgrades_a_paying_customer():
    """A single wrong STRIPE_PRICE_* value must not cancel paying customers.
    Every renewal sends subscription.updated, so mapping unknown to 'free'
    would quietly drop everyone to free at their next billing date."""
    _, fields = billing.plan_update_from_event(_sub_event("active", "price_typo"))
    assert "plan" not in fields, "must not touch the plan when the price is unrecognised"
    assert fields["subscription_status"] == "active"


def test_an_unknown_price_is_distinguishable_from_no_plan():
    assert billing._plan_for_price("price_typo") is None
    assert billing._plan_for_price("") is None
    assert billing._plan_for_price(PRO_PRICE) == "pro"


def test_a_subscription_with_no_line_items_leaves_the_plan_alone():
    event = {
        "type": "customer.subscription.updated",
        "data": {"object": {"customer": "cus_123", "status": "active", "items": {"data": []}}},
    }
    _, fields = billing.plan_update_from_event(event)
    assert "plan" not in fields


# ---------------------------------------------------------------------------
# A failing card: keep access while Stripe retries
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status", ["past_due", "unpaid", "incomplete", "paused"])
def test_a_failing_payment_keeps_access_while_stripe_retries(status):
    """Stripe retries a declined card for weeks. Dropping someone to free on
    the first failure loses them their events over a temporary bank decline,
    and Stripe sends a definitive cancellation if it never recovers."""
    _, fields = billing.plan_update_from_event(_sub_event(status, PRO_PRICE))
    assert "plan" not in fields, f"{status} must not downgrade"
    assert fields["subscription_status"] == status


# ---------------------------------------------------------------------------
# Genuine endings do downgrade
# ---------------------------------------------------------------------------

def test_cancellation_downgrades_to_free():
    event = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"customer": "cus_123"}},
    }
    _, fields = billing.plan_update_from_event(event)
    assert fields["plan"] == "free"
    assert fields["subscription_status"] == "canceled"


@pytest.mark.parametrize("status", ["canceled", "incomplete_expired"])
def test_ended_statuses_downgrade_to_free(status):
    _, fields = billing.plan_update_from_event(_sub_event(status, PRO_PRICE))
    assert fields["plan"] == "free"


# ---------------------------------------------------------------------------
# Events we do not act on, and malformed ones
# ---------------------------------------------------------------------------

def test_unrelated_events_are_ignored():
    assert billing.plan_update_from_event({"type": "invoice.paid", "data": {"object": {}}}) is None


def test_a_subscription_event_with_no_customer_is_ignored():
    event = {"type": "customer.subscription.updated", "data": {"object": {"status": "active"}}}
    assert billing.plan_update_from_event(event) is None


def test_checkout_without_a_user_reference_is_ignored():
    event = {"type": "checkout.session.completed", "data": {"object": {"customer": "cus_1"}}}
    assert billing.plan_update_from_event(event) is None


def test_verify_webhook_fails_closed_without_a_secret(monkeypatch):
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    assert billing.verify_webhook(b"{}", "sig") is None


def test_verify_webhook_fails_closed_without_a_signature(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_x")
    assert billing.verify_webhook(b"{}", None) is None


def test_verify_webhook_rejects_a_bad_signature(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_x")
    assert billing.verify_webhook(b'{"a":1}', "t=1,v1=deadbeef") is None
