# Intro Connect — Operations Runbook

How to operate, verify, and roll back the live product. Companion to
`docs/launch/OWNER-CHECKLIST.md` (one-time launch steps).

## Services (all on Render, auto-deploy on push to `main`)

| Service | What it is | Public URL | Render service |
| --- | --- | --- | --- |
| API | FastAPI + MongoDB backend | `https://jimbo-connect-api-rdkp.onrender.com` — **the `-rdkp` suffix is required** | `jimbo-connect-api` |
| Web app | React SPA (users) | `https://app.intro-connect.com` | `jimbo-connect-web` |
| Marketing | React static site | `https://intro-connect.com` (+ `www`) | `jimbo-connect-marketing` |

Source of truth for infra: `render.yaml`. DB: MongoDB Atlas (external). Email: Resend
(domain `intro-connect.com`, verified). Blog prose: Anthropic API. Blog cover
images: OpenAI Images API.

> ⚠️ **`jimbo-connect-api.onrender.com` (no `-rdkp`) is NOT this service.** It
> was listed here as an alias until 2026-08-02 and it is not one. Worse, it does
> not 404: requests **hang** until the caller times out. Five of the six
> scheduled workflows had been calling it since they were written, so the blog
> tick, the nurture drip, invite reminders and keep-warm had never once run, and
> the failures showed in Actions as `cancelled` (which sends no notification)
> rather than `failed`. `backend/tests/test_cron_targets.py` now asserts every
> workflow's host matches `API_PUBLIC_URL` in `render.yaml`.

## Inbound email (added + verified 2026-08-01)

`intro-connect.com` had **no MX records at all** until 2026-08-01, so every
reply to `hello@intro-connect.com` bounced. That silently broke the "reply to
this email" CTA in the one pager email, the "Schedule a 15-min demo" mailto on
the marketing site, and any guest replying to an invitation.

Fixed with **ImprovMX** (free tier, no DNS migration, nothing paid):

| Record | Name | Value | Priority |
| --- | --- | --- | --- |
| MX | `@` | `mx1.improvmx.com` | 10 |
| MX | `@` | `mx2.improvmx.com` | 20 |
| TXT | `@` | `v=spf1 include:spf.improvmx.com ~all` | |

`hello@intro-connect.com` forwards to **introconnectme@gmail.com**. Verified
delivering 2026-08-01. Dashboard + per message logs:
`https://app.improvmx.com/domains/intro-connect.com/logs`.

⚠️ **Do not test by mailing the alias from the destination account.** Gmail
drops a message that returns with a Message-ID it just sent, so a self test
looks like a total failure even when forwarding is fine. ImprovMX rewrites the
Message-ID and re-signs with its own DKIM to force it through, which then trips
DMARC and lands it in spam. Always test from a *different* address.

⚠️ The apex TXT record also holds the **Google site verification** string for
Search Console. Add records alongside it, never replace it.

Outbound is untouched by all of this: Resend sends via the `send.` subdomain,
which has its own MX/SPF/DKIM and is independent of the apex MX above.

## Where each secret / env var lives

| Key | Where set | Notes |
| --- | --- | --- |
| `MONGO_URL` | Render dashboard (API) | Atlas connection string; `sync: false` |
| `JWT_SECRET` | Render (auto-generated) | `generateValue: true` in `render.yaml` |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | `render.yaml` value / Render dashboard | bootstrap admin; password `sync: false` |
| `FRONTEND_URL` | Render dashboard (API) | CORS + email links; must include `https://app.intro-connect.com` |
| `EMAIL_FROM` | `render.yaml` | `Intro Connect <hello@intro-connect.com>` |
| `RESEND_API_KEY` / `RESEND_WEBHOOK_SECRET` | Render dashboard (API) | `sync: false` |
| `API_PUBLIC_URL` | `render.yaml` | unsubscribe link base |
| `REACT_APP_BACKEND_URL` | Render dashboard (web) | API base for the SPA build |
| `ANTHROPIC_API_KEY` | Render dashboard (API) | blog prose. Absent = the tick is a no-op reporting `{"skipped": "no_api_key"}` |
| `OPENAI_API_KEY` | Render dashboard (API) | blog cover images. Absent = posts fall back to the stock pool in `blog/images.py` |
| `BLOG_TICK_SECRET` | GitHub repo secret **and** Render (API) | must match byte for byte; gates every tick (header `X-Tick-Secret`). Unset on Render = a clean `401` on every tick, silently, because `_tick_authorized` fails closed |

Local scripts read `backend/.env`, which is git-ignored. `backend/.env.example`
lists every key. ⚠️ Scripts in `scripts/` run from the repo ROOT and load that
path explicitly: a bare `load_dotenv()` reads the current directory and finds
nothing, which reads as "the key is unset" when it is sitting right there.

## Scheduled jobs (GitHub Actions → `.github/workflows/`)

| Workflow | Schedule (UTC) | Purpose |
| --- | --- | --- |
| `blog-tick` | Mondays 15:00 | generate/store a blog post (was Mon/Wed/Fri until 2026-08-02) |
| `nurture-tick` | daily 16:00 | advance free-signup nurture drip |
| `invites-tick` | daily 16:30 | send guest-invite reminders |
| `keep-warm` | every 10 min | ping `/api/health` to avoid free-tier cold starts |
| `keepalive` | scheduled | second health ping (the only workflow that ever had the right host) |
| `news-tick` | **PAUSED** | news section retired 2026-08-02; cron commented out, `news_autopublish` off |

Troubleshoot a tick: GitHub → Actions → the workflow → Run workflow, then read the
curl output in the job log — the endpoints return JSON saying what they did.

- `401` → `BLOG_TICK_SECRET` mismatch between GitHub and Render.
- Run `cancelled` at ~5 minutes → it is calling the wrong host and hanging. See
  the warning at the top of this file. Cancelled runs send no notification.
- `{"skipped": "no_api_key"}` → `ANTHROPIC_API_KEY` missing on Render.
- Schedules stopped entirely → check Actions isn't disabled (GitHub auto-disables
  schedules after 60 days of repository inactivity).

## Health check / smoke test

```
python tests/smoke_prod.py
# with a real signup email (sends mail — use an inbox you control):
SMOKE_SIGNUP_EMAIL=you+test@yourdomain.com python tests/smoke_prod.py
```
Checks API health, CORS from the app origin, and blog reachability. Exit 0 = all pass.

## Logs

Render dashboard → the service → **Logs** (live tail). API request logs, startup
(`ensure_indexes`, `seed_data`), and email/tick activity appear here.

## Admin

Log in at `https://app.intro-connect.com/admin` with `ADMIN_EMAIL` / `ADMIN_PASSWORD`.
Cockpit: users, events, email templates, blog publish/unpublish, outreach.

## Rollback

**Fastest (no code change):** Render dashboard → the affected service → **Deploys** →
find the last-good deploy → **Rollback**. Each service rolls back independently.

**Via git (redeploys all services on push):**
```
git revert <bad-sha>        # or: git revert <merge-sha> -m 1  for a merge commit
git push origin main
```

**Config-only issue (e.g. bad env var):** fix it in the Render dashboard → the service
redeploys automatically; no code change needed.

## Common incidents

- **Login fails / CORS errors in browser console** → confirm `FRONTEND_URL` (API) includes
  the exact app origin; `CORS_ORIGIN_REGEX` in `backend/server.py` allows `intro-connect.com`.
- **Emails not arriving** → `RESEND_API_KEY` set? sender is `hello@intro-connect.com`?
  check Resend dashboard for bounces/suppression; check recipient not on suppression list.
- **Slow first load (~30-40s)** → free-tier cold start; ensure `keep-warm` is running or
  upgrade the API off free tier.
- **Blog empty** → posts live in MongoDB; generate via admin or `POST /api/admin/blog/run`;
  `ANTHROPIC_API_KEY` must be set.
