"""Tests for the Stripe billing layer: plan-aware event limits, the enforce
flag, dormant-safe checkout, and mapping Stripe webhook events to plan changes.
No live Stripe (the SDK is imported lazily and never reached here).

Run from backend/: python -m pytest tests/test_billing.py
"""
import asyncio
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import billing


def _clean_env(monkeypatch):
    for k in [
        "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET",
        "STRIPE_PRICE_STARTER", "STRIPE_PRICE_PRO", "BILLING_ENFORCED",
    ]:
        monkeypatch.delenv(k, raising=False)


# ---- plan + limits ----

def test_plan_of_defaults_to_free(monkeypatch):
    _clean_env(monkeypatch)
    assert billing.plan_of({}) == "free"
    assert billing.plan_of({"plan": "bogus"}) == "free"
    assert billing.plan_of({"plan": "pro"}) == "pro"


def test_free_user_limited_to_one_event(monkeypatch):
    _clean_env(monkeypatch)
    assert billing.event_limit_for({"plan": "free"}) == 1


def test_starter_and_pro_limits(monkeypatch):
    _clean_env(monkeypatch)
    assert billing.event_limit_for({"plan": "starter"}) == billing.STARTER_EVENT_LIMIT
    assert billing.event_limit_for({"plan": "pro"}) is None  # unlimited


def test_admin_is_unlimited(monkeypatch):
    _clean_env(monkeypatch)
    assert billing.event_limit_for({"is_admin": True, "plan": "free"}) is None


def test_billing_disabled_makes_everyone_unlimited(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("BILLING_ENFORCED", "false")
    assert billing.event_limit_for({"plan": "free"}) is None


def test_default_is_enforced(monkeypatch):
    # No BILLING_ENFORCED set => enforced => free capped at 1 (current behavior).
    _clean_env(monkeypatch)
    assert billing.event_limit_for({"plan": "free"}) == 1


# ---- configuration gate ----

def test_not_configured_without_secret_key(monkeypatch):
    _clean_env(monkeypatch)
    assert billing.is_configured() is False


def test_checkout_dormant_without_config(monkeypatch):
    _clean_env(monkeypatch)
    out = asyncio.run(
        billing.create_checkout_session(
            {"_id": "u1", "email": "a@b.com"}, "starter",
            success_url="s", cancel_url="c",
        )
    )
    assert out == {"skipped": "not_configured"}


def test_checkout_rejects_unknown_plan(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    out = asyncio.run(
        billing.create_checkout_session(
            {"_id": "u1", "email": "a@b.com"}, "enterprise",
            success_url="s", cancel_url="c",
        )
    )
    assert out == {"error": "unknown plan"}


def test_checkout_configured_but_no_price(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")  # key but no price id
    out = asyncio.run(
        billing.create_checkout_session(
            {"_id": "u1", "email": "a@b.com"}, "pro",
            success_url="s", cancel_url="c",
        )
    )
    # The reason now names the period too, since a plan can have a monthly
    # price configured and an annual one missing.
    assert out == {"skipped": "no_price_configured_for_pro_monthly"}


# ---- webhook signature gate ----

def test_verify_webhook_none_without_secret(monkeypatch):
    _clean_env(monkeypatch)
    assert billing.verify_webhook(b"{}", "sig") is None


def test_verify_webhook_none_without_sig(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_x")
    assert billing.verify_webhook(b"{}", "") is None


# ---- webhook event -> plan change mapping ----

def test_checkout_completed_promotes_by_user_id(monkeypatch):
    _clean_env(monkeypatch)
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {
            "client_reference_id": "507f1f77bcf86cd799439011",
            "customer": "cus_123",
            "metadata": {"user_id": "507f1f77bcf86cd799439011", "plan": "pro"},
        }},
    }
    match, fields = billing.plan_update_from_event(event)
    assert match == {"_id": "507f1f77bcf86cd799439011"}
    assert fields["plan"] == "pro"
    assert fields["stripe_customer_id"] == "cus_123"
    assert fields["subscription_status"] == "active"


def test_subscription_deleted_downgrades_to_free(monkeypatch):
    _clean_env(monkeypatch)
    event = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"customer": "cus_123"}},
    }
    match, fields = billing.plan_update_from_event(event)
    assert match == {"stripe_customer_id": "cus_123"}
    assert fields["plan"] == "free"
    assert fields["subscription_status"] == "canceled"


def test_subscription_updated_maps_price_to_plan(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("STRIPE_PRICE_STARTER", "price_starter")
    monkeypatch.setenv("STRIPE_PRICE_PRO", "price_pro")
    event = {
        "type": "customer.subscription.updated",
        "data": {"object": {
            "customer": "cus_9",
            "status": "active",
            "items": {"data": [{"price": {"id": "price_pro"}}]},
        }},
    }
    match, fields = billing.plan_update_from_event(event)
    assert match == {"stripe_customer_id": "cus_9"}
    assert fields["plan"] == "pro"


def test_canceled_status_downgrades_even_on_update(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("STRIPE_PRICE_PRO", "price_pro")
    event = {
        "type": "customer.subscription.updated",
        "data": {"object": {
            "customer": "cus_9",
            "status": "canceled",
            "items": {"data": [{"price": {"id": "price_pro"}}]},
        }},
    }
    _, fields = billing.plan_update_from_event(event)
    assert fields["plan"] == "free"


def test_unrelated_event_is_ignored(monkeypatch):
    _clean_env(monkeypatch)
    assert billing.plan_update_from_event({"type": "invoice.paid", "data": {"object": {}}}) is None
