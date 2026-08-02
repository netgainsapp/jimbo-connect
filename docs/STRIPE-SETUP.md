# Stripe Billing — Setup

The billing code is built and shipped **dormant**. Until the env vars below are
set, checkout returns "not enabled", the webhook 401s, and every account stays
on the free plan (1 event) — i.e. nothing changes. This doc is the exact
checklist to turn it on. All steps are yours (they need the Stripe account).

## ✅ LIVE ACCOUNT STATE (verified in the dashboard 2026-08-01)

Account `acct_1TuDnLPFMQathI2d` ("Intro Connect") is **activated for live
payments** (publishable key is `pk_live_`). These live objects exist and were
read directly off the dashboard, so they are exact:

All four live prices, read off the dashboard 2026-08-01:

| Plan | Env var | Live price ID | Product | Amount |
| --- | --- | --- | --- | --- |
| Starter monthly | `STRIPE_PRICE_STARTER` | `price_1Tz2mlPFMQathI2dmaZuXlIi` | `prod_Uz0oGr7m6tjW45` | $39 / mo |
| Starter annual | `STRIPE_PRICE_STARTER_ANNUAL` | `price_1Tz33qPFMQathI2dbD6DkS4Q` | `prod_Uz16SmXKBylFWZ` | $390 / yr |
| Pro monthly | `STRIPE_PRICE_PRO` | `price_1Tz30uPFMQathI2d89z8wMwp` | `prod_Uz12vWJXaF3Lho` | $99 / mo |
| Pro annual | `STRIPE_PRICE_PRO_ANNUAL` | `price_1Tz339PFMQathI2dcz0chSQy` | `prod_Uz15VBto5pji6x` | $990 / yr |

✅ **All four verified live 2026-08-01.** The annual pair was compared by eye on
Render; then all four were proven *functionally* by creating a real checkout
session for each plan/period against the live API. Every one returned a session
URL, which a stale test-mode price could not do — Stripe rejects a test price
under a live key.

⭐ **Reusable check, costs nothing:** register a throwaway account, `POST
/api/billing/checkout` for each of the four plan/period pairs, assert a `url`
comes back, delete the account. Creating a session never charges anyone, so
this is safe to re-run any time the price vars change. Beats reading the env
vars, which Render masks anyway. Note `available_periods()` only tests that a
`STRIPE_PRICE_*` var is non-empty — it never validates the value, so a bad ID
would still show the option in the UI and only fail at checkout.

### ✅ Founding host coupons CREATED LIVE 2026-08-01

| Coupon | ID | Discount | Duration | Cap | Code | Restricted to |
| --- | --- | --- | --- | --- | --- | --- |
| Founding Host Starter | `BqbuVvqz` | $191.00 off | once | 15 | `FOUNDINGHOST` | Starter Annual |
| Founding Host Pro | `Z2yFlKFk` | $291.00 off | once | 5 | `FOUNDINGPRO` | Pro Annual |

Net to the customer: **$199** and **$699** for year one, renewing at full
price. Both were verified after creation: the "Applicable Products" restriction
attached on each, which is what stops the Pro code being spent on the cheaper
plan. Checkout already passes `allow_promotion_codes`, so the code field
renders on the hosted page with no further code change.

### ✅ Both codes proven on the real hosted checkout (2026-08-01)

Opened live checkout (`cs_live_…`) for each annual plan and applied each code:

| Plan | Subtotal | Code | Total today | Renewal shown |
| --- | --- | --- | --- | --- |
| Starter Annual | $390.00 | `FOUNDINGHOST` −$191.00 | **$199.00** | $390 / yr next year |
| Pro Annual | $990.00 | `FOUNDINGPRO` −$291.00 | **$699.00** | $990 / yr next year |

Confirms the discounts compute exactly, and that `duration: once` behaves —
Stripe itself renders "then $X per year starting next year". Merchant shows as
"Net Gains, Inc. dba Intro Connect".

⚠️ Still NOT proven: a **completed** payment. Everything above stops at the
checkout page. The webhook signing secret is only exercised once money actually
moves, so the plan-upgrade half of the loop remains untested.

### ⏭ REMAINING BEFORE ANYONE CAN ACTUALLY PAY

Creating live objects in Stripe does nothing on its own — the API has to be
pointed at them. On Render (`jimbo-connect-api`), confirm:

- `STRIPE_SECRET_KEY` starts with **`sk_live_`**, not `sk_test_`
- `STRIPE_PRICE_STARTER_ANNUAL` = `price_1Tz33qPFMQathI2dbD6DkS4Q`
- `STRIPE_PRICE_PRO_ANNUAL` = `price_1Tz339PFMQathI2dcz0chSQy`
- `STRIPE_WEBHOOK_SECRET` = the **live** endpoint's `whsec_`

⚠️ **Triple-check the variable NAMES, not just the values.** A previous
outage was caused by `STRIPE_WEBHOOK_SECRE` (truncated, missing the T): the
secret itself was fine and the webhook still 401'd. See the 2026-07-17 note.

⚠️ A wrong `STRIPE_PRICE_*` value silently downgrades paying customers rather
than erroring — `billing.py` has an explicit comment about this. Verify by
reading, not by assuming.

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
