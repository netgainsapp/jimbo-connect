# Intro Connect — Operations Runbook

How to operate, verify, and roll back the live product. Companion to
`docs/launch/OWNER-CHECKLIST.md` (one-time launch steps).

## Services (all on Render, auto-deploy on push to `main`)

| Service | What it is | Public URL | Render service |
| --- | --- | --- | --- |
| API | FastAPI + MongoDB backend | `https://jimbo-connect-api-rdkp.onrender.com` (also `jimbo-connect-api.onrender.com`; blog at `blog.intro-connect.com` once DNS is added) | `jimbo-connect-api` |
| Web app | React SPA (users) | `https://app.intro-connect.com` | `jimbo-connect-web` |
| Marketing | React static site | `https://intro-connect.com` (+ `www`) | `jimbo-connect-marketing` |

Source of truth for infra: `render.yaml`. DB: MongoDB Atlas (external). Email: Resend
(domain `intro-connect.com`, verified). Blog generation: Anthropic API.

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
| `ANTHROPIC_API_KEY` | Render dashboard (API) | blog generation |
| `BLOG_TICK_SECRET` | GitHub repo secret **and** Render (API) | must match; gates all three tick crons (header `X-Tick-Secret`) |

## Scheduled jobs (GitHub Actions → `.github/workflows/`)

| Workflow | Schedule (UTC) | Purpose |
| --- | --- | --- |
| `blog-tick` | Mon/Wed/Fri 15:00 | generate/store a blog post |
| `nurture-tick` | daily 16:00 | advance free-signup nurture drip |
| `invites-tick` | daily 16:30 | send guest-invite reminders |
| `keep-warm` | every 10 min | ping `/api/health` to avoid free-tier cold starts |

Troubleshoot a tick: GitHub → Actions → the workflow → Run workflow. A `401/403` means
`BLOG_TICK_SECRET` mismatches between GitHub and Render. If schedules stopped firing,
check Actions isn't disabled (GitHub auto-disables schedules after 60 days of no activity).

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
