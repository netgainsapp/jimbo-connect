# Intro Connect — Cost Review

Date: 2026-07-11. Honest assessment: the platform is already cost-lean. Current
run-rate is effectively **$0/month** on free tiers, with no cost landmines. The
open items are *paid-upgrade decisions* (yours), not code fixes.

## Current spend

| Service | Tier | Cost | Notes |
| --- | --- | --- | --- |
| Render API (jimbo-connect-api) | Free | $0 | Spins down after ~15 min idle → ~40s cold start |
| Render web (app) | Free static | $0 | Static, no cold start |
| Render marketing | Free static | $0 | Static |
| MongoDB Atlas | M0 | $0 | 512 MB cap |
| Resend | Pro (shared) | shared | Billed on the netgainspb Resend account across many domains, not IC-specific |
| Anthropic (blog gen) | pay-per-use | ~cents | Gated + bounded (see below); shared key |

So today the only real "cost" is a **UX tradeoff**, not dollars: the free-tier
API cold start. The first request after idle takes ~40s (HTTP 000/ERR then
recovers). This is why the E2E suite and cron ticks use long timeouts.

## No cost landmines (verified)

- **AI generation is bounded.** Blog gen uses `claude-sonnet-4-6`, `max_tokens=4000`
  per article, and only runs on a secret-gated tick when an unused topic exists
  (`backend/blog/topics.py` is a finite list). Guardrails + the `blog_autopublish`
  flag gate output. It cannot run away. News is human-authored (no AI spend).
- **List endpoints are capped.** `list_published` (50), `list_all` (100),
  outreach list (1000), threads/attendees are per-user scoped. No unbounded
  full-collection reads on hot paths.
- **Email is dormant-safe and suppression-gated.** Nurture/invite sends are
  no-ops without a Resend key and skip suppressed addresses, so no runaway sends.

## Scale note (not a cost issue today)

`GET /api/messages/threads` (`backend/routers/people.py:284`) scans all of a
user's messages and does one `users.find_one` + one `count_documents` per
thread (N+1). At pre-launch scale (a handful of contacts per user) this is
negligible. Revisit only if a single user accumulates thousands of messages:
replace with an aggregation pipeline that groups by `thread_id` and joins the
counterparty in one round trip. Not worth the rewrite risk now.

## Decisions for you (when, not if)

These are the paid levers. None are needed yet; here are the trigger points:

1. **Render API off free tier → Starter ($7/mo).** Trigger: when cold-start
   latency hurts real users (first-hit ~40s), or once outreach drives real
   signups. Removes spin-down entirely. This is the single highest-impact
   upgrade for perceived quality. Recommended before any public launch push.
2. **Atlas M0 → M2/M10.** Trigger: approaching 512 MB, or query latency climbs.
   Not close yet.
3. **A cheap external cron** (e.g. cron-job.org, GitHub Actions) hitting the
   blog/nurture/invite ticks. Free. Only matters once you want the drips/blog
   running on a schedule rather than manually. (No cron config exists in-repo
   today, so these ticks currently run only when triggered manually.)

## Bottom line

Nothing to optimize in code right now without trading quality or taking on
rewrite risk for zero present benefit. The platform is cheap and safe by
construction. The one upgrade worth doing *before a real launch push* is moving
the API off Render's free tier so users don't hit the 40s cold start.
