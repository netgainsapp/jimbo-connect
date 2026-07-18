# Stripe Billing — Setup

The billing code is built and shipped **dormant**. Until the env vars below are
set, checkout returns "not enabled", the webhook 401s, and every account stays
on the free plan (1 event) — i.e. nothing changes. This doc is the exact
checklist to turn it on. All steps are yours (they need the Stripe account).

## What exists in code

- `backend/billing.py` — plan limits (free=1, starter=10, pro=unlimited),
  Checkout session creation, webhook signature verification, event→plan mapping.
- Routes: `POST /api/billing/checkout`, `GET /api/billing/status`,
  `POST /api/webhooks/stripe` (all in `backend/routers/billing.py`).
- Event creation is gated by `billing.event_limit_for(user)` — free users are
  still capped at 1 event exactly as before; starter/pro lift it only once
  Stripe sets `user.plan`.
- `serialize_user` now returns `plan`, so the frontend can show it.
- Frontend: `billingApi.status()` / `billingApi.checkout(plan)` in
  `frontend/src/lib/api.js`.

## Turn it on

1. **Stripe Dashboard → Products.** Create two recurring prices:
   - Starter — $39/month → copy its `price_...` id
   - Pro — $99/month → copy its `price_...` id
2. **Stripe → Developers → API keys.** Copy the secret key (`sk_live_...`).
3. **Stripe → Developers → Webhooks.** Add an endpoint:
   - URL: `https://jimbo-connect-api-rdkp.onrender.com/api/webhooks/stripe`
     (or your branded API domain)
   - Events: `checkout.session.completed`, `customer.subscription.updated`,
     `customer.subscription.created`, `customer.subscription.deleted`
   - Copy the signing secret (`whsec_...`).
4. **Render → jimbo-connect-api → Environment**, add:
   - `STRIPE_SECRET_KEY` = `sk_live_...`
   - `STRIPE_WEBHOOK_SECRET` = `whsec_...`
   - `STRIPE_PRICE_STARTER` = `price_...`
   - `STRIPE_PRICE_PRO` = `price_...`
   - `BILLING_ENFORCED` = `true` (or `false` for an unlimited early-access window)
   - Redeploy.
5. **Verify:** `GET /api/billing/status` (as a logged-in user) should return
   `"configured": true`. Then run a test checkout in Stripe test mode and confirm
   the webhook flips the user's `plan`.

## Still to build (not blocking, needs the above first)

- ~~An in-app upgrade UI~~ DONE: the /upgrade plans page (frontend/src/pages/
  Upgrade.jsx) calls `billingApi.checkout(plan)` and redirects to Stripe; the
  event-limit 403 routes hosts there. Verified live, including a full paid
  test checkout (see e2e/tests/pro-flow.spec.js, opt-in via E2E_PRO_FLOW=1).
- Optionally a Stripe Customer Portal link for managing/canceling subscriptions.

## Test-mode note

Use `sk_test_...` + a test webhook secret first. Stripe test card `4242 4242
4242 4242` completes a subscription so you can watch the webhook set the plan
end to end before going live.
