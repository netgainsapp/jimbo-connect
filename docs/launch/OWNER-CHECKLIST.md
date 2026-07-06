# Intro Connect — Owner Launch Checklist

These are the steps only you can do (dashboard access, DNS, secrets, approvals).
Claude handles everything else. Ordered for a mid-week public launch.
References the plan: `docs/superpowers/plans/2026-07-06-intro-connect-launch.md`.

---

## A. Before the code merge (quick dashboard confirmations)

- [ ] **Render → `jimbo-connect-api` → Environment:** confirm `FRONTEND_URL` includes
      `https://app.intro-connect.com` (comma-separate if multiple). This drives email
      links and is a second CORS gate. If it lists the old `jimbo.frontrangedev.co`,
      add the new one (keep or drop the old).
- [ ] **Same page:** confirm neither `EMAIL_FROM` nor `ADMIN_EMAIL` is *overridden* in the
      dashboard. The merge sets them in `render.yaml` to `hello@intro-connect.com` /
      `admin@intro-connect.com`. A dashboard override would win — delete it or match it.
- [ ] **Confirm `ANTHROPIC_API_KEY` exists** on the `jimbo-connect-api` service (needed to
      generate blog posts). Not in `render.yaml` — must be a dashboard secret.

## B. The merge → production deploy (Claude does, on your go-ahead)

- [ ] Give Claude the word to merge `launch-prep` → `main`. That auto-deploys all three
      services with the four Phase 1 fixes (email sender, CORS, marketing CTAs, cleanup).
- [ ] After deploy, Claude re-runs the production smoke; you run one real signup with an
      inbox you control and confirm the welcome email arrives from `hello@intro-connect.com`.

## C. Blog public URL (Task 5)

- [ ] **Render → `jimbo-connect-api` → Settings → Custom Domains → Add** `blog.intro-connect.com`.
      Render shows a target host (e.g. `jimbo-connect-api-rdkp.onrender.com`).
- [ ] **At your DNS registrar:** add CNAME `blog` → that target host. Wait for Render to
      show "Verified" (minutes–hours).
- [ ] Tell Claude when verified — Claude points the marketing "Blog" link at
      `https://blog.intro-connect.com/blog`.

## D. Scheduled crons (Task 8)

The three tick workflows (blog / nurture / invites) all authenticate with **one** secret,
`BLOG_TICK_SECRET`, sent as header `X-Tick-Secret`. It must exist in **both** places with
the **same value**:

- [ ] Generate a strong random value (e.g. `openssl rand -hex 32`).
- [ ] **GitHub → repo → Settings → Secrets and variables → Actions → New repository secret:**
      name `BLOG_TICK_SECRET`, paste the value.
- [ ] **Render → `jimbo-connect-api` → Environment → Add** `BLOG_TICK_SECRET` = same value.
- [ ] **GitHub → Actions:** confirm workflows are **enabled** (Actions can be off, or
      scheduled workflows auto-disable after 60 days of no repo activity). Run the
      `blog-tick` workflow manually once — it should finish green (API returns 200, not 401).

## E. Cold-start fix (launch UX)

The API cold-starts in ~30–40s on Render's free tier, and keep-warm currently isn't
preventing it (both API URLs responded cold). A 40s first-load is bad for a public launch.
Pick one:

- [ ] **Free option:** ensure the `keep-warm` GitHub workflow is enabled and actually
      running every 10 min (check Actions → keep-warm → recent runs are green). Enabling
      Actions in step D may fix this.
- [ ] **Paid option (recommended for a public launch):** upgrade `jimbo-connect-api` to a
      Render paid instance (no spin-down). ~$7/mo. Eliminates cold starts entirely.

## F. Analytics (Task 9)

- [ ] Create a privacy-friendly analytics property (Plausible, or free Cloudflare Web
      Analytics) for `intro-connect.com` (and optionally `app.intro-connect.com`).
- [ ] Send Claude the embed snippet / site token — Claude adds it to both sites and deploys.

## G. Go public (Phase 3 — after everything above is green)

- [ ] Review the blog posts Claude seeds; approve publishing.
- [ ] Review the announcement assets Claude drafts (`docs/launch/announcement.md`).
- [ ] Publish the launch post, post social/Product Hunt, and send the first outreach batch
      (`growth/leads-seed.csv` + sequence).
- [ ] Watch analytics + Render logs for the first hour. Rollback steps are in `docs/RUNBOOK.md`.
