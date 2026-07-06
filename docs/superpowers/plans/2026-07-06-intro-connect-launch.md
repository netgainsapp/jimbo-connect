# Intro Connect Public Launch — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take Intro Connect from "deployed but unverified" to a fully verified, polished, public launch on `intro-connect.com` this week.

**Architecture:** Verify-and-finish. Three Render services (FastAPI API, React web app, React marketing) are already live with a verified Resend domain and connected MongoDB. Work is: (Phase 0) audit the live product end-to-end, (Phase 1) fix the confirmed blockers, (Phase 2) content + growth readiness, (Phase 3) go public with a runbook and announcement assets.

**Tech Stack:** FastAPI + MongoDB (Motor), React 18 + Vite, Render (static + web), Resend (email), Anthropic (blog), GitHub Actions (crons).

## Global Constraints

- **Brand name (public surfaces):** "Intro Connect" — verbatim. Repo name `jimbo-connect` and internal identifiers stay as-is.
- **Domain:** apex `intro-connect.com` = marketing; `app.intro-connect.com` = web app; API at `https://jimbo-connect-api-rdkp.onrender.com`.
- **Support email (all public surfaces):** `hello@intro-connect.com`.
- **App register/login links (all marketing surfaces):** `https://app.intro-connect.com`.
- **Email sender:** `Intro Connect <hello@intro-connect.com>` (Resend domain `intro-connect.com` is verified).
- **Deploy trigger:** every merge to `main` auto-deploys all three Render services. Commit small, watch the deploy.
- **Owner-only steps** (cannot be done from this session) are marked **[OWNER]**: Render dashboard env vars, DNS records, GitHub repo secrets, sending outreach, go-public approval.
- **Repo git identity:** `Net Gains <netgainspb@gmail.com>` (set repo-local).

---

## Phase 0 — Reality Audit

### Task 1: End-to-end production smoke audit → populate `test_result.md`

**Files:**
- Modify: `test_result.md` (currently an empty template)

**Interfaces:**
- Produces: a ranked, evidence-backed blocker list consumed by Phase 1 tasks; a reusable smoke script at `tests/smoke_prod.py`.

- [ ] **Step 1: Create a production smoke script**

Create `tests/smoke_prod.py` (uses only stdlib + `httpx`, already a backend dep):

```python
"""Production smoke audit for Intro Connect. Read-only except one throwaway signup.
Run: python tests/smoke_prod.py
"""
import os, time, uuid, httpx

API = os.getenv("SMOKE_API", "https://jimbo-connect-api-rdkp.onrender.com")
APP_ORIGIN = os.getenv("SMOKE_APP_ORIGIN", "https://app.intro-connect.com")
results = []

def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")

# 1. Health
r = httpx.get(f"{API}/api/health", timeout=60)
check("api_health", r.status_code == 200 and r.json().get("ok") is True, str(r.status_code))

# 2. CORS preflight from the app origin
r = httpx.options(
    f"{API}/api/auth/login",
    headers={"Origin": APP_ORIGIN, "Access-Control-Request-Method": "POST",
             "Access-Control-Request-Headers": "content-type"},
    timeout=60)
acao = r.headers.get("access-control-allow-origin", "")
check("cors_allows_app_origin", acao == APP_ORIGIN, f"ACAO='{acao}'")

# 3. Blog is publicly reachable and is real blog HTML (not the SPA shell)
r = httpx.get(f"{API}/blog", timeout=60)
check("blog_api_serves_posts", r.status_code == 200 and "Intro Connect" in r.text, str(r.status_code))

# 4. Throwaway signup → triggers welcome email (branded, from intro-connect.com)
email = f"smoke+{uuid.uuid4().hex[:10]}@intro-connect-smoke.test"
r = httpx.post(f"{API}/api/auth/register",
               json={"email": email, "password": "SmokeTest!2026", "name": "Smoke Test"},
               headers={"Origin": APP_ORIGIN}, timeout=60)
check("signup", r.status_code in (200, 201), str(r.status_code))

for name, ok, _ in results:
    pass
print("\nSUMMARY:", sum(1 for _, ok, _ in results if ok), "/", len(results), "passed")
```

- [ ] **Step 2: Run the automated portion**

Run: `cd /c/Users/sweis/jimbo-connect && python tests/smoke_prod.py`
Expected: each check prints PASS/FAIL. Record which fail — these become Phase 1 priorities. (Known likely failures: `cors_allows_app_origin`, `blog` public URL.)

- [ ] **Step 3: Manual browser audit (record findings)**

In a browser, on `https://app.intro-connect.com`, perform and note pass/fail:
- Register with a throwaway address **you control** (so you can read the email).
- Confirm the welcome email arrives, sender is `hello@intro-connect.com` (NOT `onboarding@resend.dev`), branding says "Intro Connect".
- Log in; create an event; copy its join code; join it from a second account or incognito.
- Save a contact; send a message; confirm it appears in the thread and unread count updates.
- Click the unsubscribe link in the email footer; confirm the confirmation page and that a re-send is suppressed.
- On `https://intro-connect.com`: read every marketing section; click every CTA and note where each link actually goes (expect some pointing at `jimbo.frontrangedev.co`).

- [ ] **Step 4: Write results into `test_result.md`**

Replace the template with a dated table: one row per checked feature, columns `Feature | Result (PASS/FAIL) | Evidence/Notes`. Include the automated summary and the manual findings. End with a "Confirmed launch blockers (ranked)" list.

- [ ] **Step 5: Commit**

```bash
git add tests/smoke_prod.py test_result.md
git commit -m "test: production smoke audit + recorded launch-readiness results"
```

---

## Phase 1 — Fix Launch Blockers

### Task 2: Point the email sender at the verified domain

**Files:**
- Modify: `render.yaml:27-28` (`EMAIL_FROM`)
- Modify: `render.yaml:19-20` (`ADMIN_EMAIL`, brand consistency)

**Interfaces:**
- Produces: emails send from `hello@intro-connect.com`. No code depends on this beyond env.

- [ ] **Step 1: Update `EMAIL_FROM`**

In `render.yaml`, change line 28 from:
```yaml
        value: "Intro Connect <onboarding@resend.dev>"
```
to:
```yaml
        value: "Intro Connect <hello@intro-connect.com>"
```

- [ ] **Step 2: Update `ADMIN_EMAIL` for brand consistency**

In `render.yaml`, change line 20 from:
```yaml
        value: admin@jimboconnect.com
```
to:
```yaml
        value: admin@intro-connect.com
```

> **[OWNER]** If `EMAIL_FROM` or `ADMIN_EMAIL` was overridden in the Render dashboard, the dashboard value wins — update it there too, or delete the override so the `render.yaml` value applies. Note: changing `ADMIN_EMAIL` changes the bootstrap admin **login identity** on next deploy; the existing admin user (old email) remains in the DB. Keep using the old admin login, or create the new one — do not assume the old admin is gone.

- [ ] **Step 3: Commit & deploy**

```bash
git add render.yaml
git commit -m "fix(email): send from verified hello@intro-connect.com; align admin email"
git push
```

- [ ] **Step 4: Verify after deploy**

Re-run `python tests/smoke_prod.py` (triggers a signup email) and confirm in the throwaway inbox that the sender is now `hello@intro-connect.com`.
Expected: sender shows the intro-connect.com address; email lands in inbox (not spam) thanks to DKIM/SPF.

---

### Task 3: Harden CORS to allow `intro-connect.com` (+ fix backend URL fallbacks)

**Files:**
- Modify: `backend/server.py:538-553` (extract regex to a constant, add intro-connect.com)
- Modify: `backend/nurture.py:17` (default fallback URL)
- Modify: `backend/invites.py:17` (default fallback URL)
- Test: `backend/tests/test_cors_origins.py` (new)

**Interfaces:**
- Consumes: nothing.
- Produces: module-level constant `CORS_ORIGIN_REGEX` in `backend/server.py`, importable for tests.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_cors_origins.py`:

```python
import re
from server import CORS_ORIGIN_REGEX

pat = re.compile(CORS_ORIGIN_REGEX)

def test_allows_app_subdomain():
    assert pat.match("https://app.intro-connect.com")

def test_allows_apex():
    assert pat.match("https://intro-connect.com")

def test_allows_own_render_service():
    assert pat.match("https://jimbo-connect-web-huph.onrender.com")

def test_rejects_foreign_origin():
    assert not pat.match("https://evil.example.com")

def test_rejects_other_render_tenant():
    assert not pat.match("https://someone-else.onrender.com")
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `cd /c/Users/sweis/jimbo-connect/backend && python -m pytest tests/test_cors_origins.py -v`
Expected: FAIL — `ImportError: cannot import name 'CORS_ORIGIN_REGEX'`.

- [ ] **Step 3: Extract the constant and add intro-connect.com**

In `backend/server.py`, replace lines 542-553 (the `add_middleware(CORSMiddleware, ...)` block plus its inline regex) so the regex becomes a named constant defined just above the middleware, updated to include intro-connect.com:

```python
# Scope to this project's own Render services, the production intro-connect.com
# domain, and the legacy frontrangedev.co staging domain. A broad `.*\.onrender\.com`
# would match EVERY Render tenant's app, which with allow_credentials=True is a risk.
CORS_ORIGIN_REGEX = (
    r"^https://(jimbo-connect-[a-z0-9-]+\.onrender\.com"
    r"|([a-z0-9-]+\.)?intro-connect\.com"
    r"|([a-z0-9-]+\.)?frontrangedev\.co)$"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin"],
    expose_headers=[],
)
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `cd /c/Users/sweis/jimbo-connect/backend && python -m pytest tests/test_cors_origins.py -v`
Expected: 5 passed.

- [ ] **Step 5: Fix the fallback URLs in nurture/invites**

In both `backend/nurture.py:17` and `backend/invites.py:17`, change the default:
```python
APP_URL = os.getenv("FRONTEND_URL", "https://jimbo.frontrangedev.co").split(",")[0].rstrip("/")
```
to:
```python
APP_URL = os.getenv("FRONTEND_URL", "https://app.intro-connect.com").split(",")[0].rstrip("/")
```

- [ ] **Step 6: Run the full backend suite (no regressions)**

Run: `cd /c/Users/sweis/jimbo-connect/backend && python -m pytest -q`
Expected: all tests pass (14 existing files + the new one).

- [ ] **Step 7: Commit & deploy**

```bash
git add backend/server.py backend/nurture.py backend/invites.py backend/tests/test_cors_origins.py
git commit -m "fix(cors): allow intro-connect.com origins; repoint email link fallbacks"
git push
```

- [ ] **Step 8: Verify after deploy**

Re-run `python tests/smoke_prod.py`. Expected: `cors_allows_app_origin` now PASS.

> **[OWNER]** In the Render dashboard, confirm the API service's `FRONTEND_URL` includes `https://app.intro-connect.com` (comma-separated if multiple). The regex above is the safety net, but `FRONTEND_URL` should still be correct because it also drives email links.

---

### Task 4: Repoint all marketing CTAs and support emails to production

**Files:**
- Modify: `marketing/src/components/Nav.jsx:38,73`
- Modify: `marketing/src/components/CTA.jsx:29,37`
- Modify: `marketing/src/components/Pricing.jsx:3,67`
- Modify: `marketing/src/components/Footer.jsx:39`
- Modify: `marketing/src/components/FAQ.jsx:54`
- Modify: `marketing/public/privacy.html:95`
- Modify: `marketing/public/terms.html:111`
- Modify: `frontend/src/components/Footer.jsx:6`

**Interfaces:**
- Produces: zero `frontrangedev.co` references on any public surface.

- [ ] **Step 1: Swap the app domain in register/nav links**

Replace every `https://jimbo.frontrangedev.co` with `https://app.intro-connect.com` in:
- `marketing/src/components/Nav.jsx` (lines 38 and 73 — `href="https://jimbo.frontrangedev.co"`)
- `marketing/src/components/CTA.jsx:29` (`href="https://jimbo.frontrangedev.co/register"` → `https://app.intro-connect.com/register`)
- `marketing/src/components/Pricing.jsx:3` (`const REGISTER = "https://jimbo.frontrangedev.co/register";` → `"https://app.intro-connect.com/register";`)

- [ ] **Step 2: Swap the support mailto to `hello@intro-connect.com`**

Replace every `hello@frontrangedev.co` with `hello@intro-connect.com` in:
- `marketing/src/components/CTA.jsx:37`
- `marketing/src/components/Pricing.jsx:67`
- `marketing/src/components/Footer.jsx:39`
- `marketing/src/components/FAQ.jsx:54`
- `marketing/public/privacy.html:95`
- `marketing/public/terms.html:111`

- [ ] **Step 3: Update the frontend footer credit link**

In `frontend/src/components/Footer.jsx:6`, change `href="https://frontrangedev.co"` to `href="https://intro-connect.com"`.

- [ ] **Step 4: Verify no references remain**

Run: `cd /c/Users/sweis/jimbo-connect && git grep -n "frontrangedev" -- marketing frontend`
Expected: **no output** (only the backend CORS comment and the spec/plan docs may still mention it; those are intentional/non-public — verify none are in `marketing/` or `frontend/`).

- [ ] **Step 5: Build the marketing site locally to confirm no breakage**

Run: `cd /c/Users/sweis/jimbo-connect/marketing && yarn install && yarn build`
Expected: build succeeds, `dist/` produced, no errors.

- [ ] **Step 6: Commit & deploy**

```bash
git add marketing/src/components/*.jsx marketing/public/privacy.html marketing/public/terms.html frontend/src/components/Footer.jsx
git commit -m "fix(marketing): repoint CTAs to app.intro-connect.com + support hello@intro-connect.com"
git push
```

- [ ] **Step 7: Verify after deploy**

Load `https://intro-connect.com`, click "Get started" / register CTAs; confirm each lands on `https://app.intro-connect.com/register`. Confirm mailto links open `hello@intro-connect.com`.

---

### Task 5: Make the blog publicly reachable

**Problem:** Both static services rewrite `/*` → `/index.html` (`render.yaml:44-47` and `56-59`), so `intro-connect.com/blog` serves the marketing SPA shell, not the backend blog. Render static sites cannot reverse-proxy to another origin, so `/blog` on the apex cannot transparently serve API content. **Recommended solution:** give the API service a `blog.intro-connect.com` custom domain and point the marketing "Blog" link there. (Fallback: a 301 redirect from `/blog`.)

**Files:**
- Modify: marketing nav/footer "Blog" link target (search below)
- Modify: `render.yaml` (only if fallback redirect is chosen)

**Interfaces:**
- Produces: a public, SEO-clean blog URL linked from marketing.

- [ ] **Step 1: Locate the existing Blog link in marketing**

Run: `cd /c/Users/sweis/jimbo-connect && git grep -n -i "blog" -- marketing/src`
Note the component(s) linking to the blog and their current href.

- [ ] **Step 2 [OWNER]: Add the blog custom domain in Render**

In the Render dashboard → `jimbo-connect-api` service → Settings → Custom Domains → add `blog.intro-connect.com`. Render shows a target host.

- [ ] **Step 3 [OWNER]: Add the DNS record**

At the domain registrar, add a CNAME: `blog` → the host Render shows (e.g. `jimbo-connect-api-rdkp.onrender.com`). Wait for Render to show "Verified" (minutes to a couple hours).

- [ ] **Step 4: Point the marketing Blog link at the new URL**

Update the href found in Step 1 to `https://blog.intro-connect.com/blog` (or `/blog` root as the backend serves it). Keep it opening in the same tab.

- [ ] **Step 5: Verify**

Run: `curl -sSI https://blog.intro-connect.com/blog | head -1`
Expected: `HTTP/... 200`. Load it in a browser — real blog list renders (not the marketing shell). Click a post → `/blog/<slug>` renders with content.

- [ ] **Step 6: Commit & deploy**

```bash
git add marketing/src render.yaml
git commit -m "feat(blog): serve blog at blog.intro-connect.com and link from marketing"
git push
```

> **Fallback if a subdomain is undesirable:** instead of Steps 2-4, add a redirect route to the marketing service in `render.yaml` above the catch-all: a `redirect` from `source: /blog` and `/blog/*` to `https://jimbo-connect-api-rdkp.onrender.com/blog`. URL bar changes to the API host, but the blog is reachable. The subdomain approach is cleaner for branding/SEO.

---

### Task 6: Remove dead weight

**Files:**
- Delete: `jimbo_connect_landing.html` (standalone, unreferenced older landing page)
- Delete: `frontend/yarn.lock` (npm is authoritative for frontend per `package-lock.json`) — **verify first**
- Delete: `backend/vercel.json` (Render is the deploy target, not Vercel)

**Interfaces:**
- Produces: no functional change; removes launch-risk ambiguity.

- [ ] **Step 1: Confirm nothing references the dead files**

Run:
```bash
cd /c/Users/sweis/jimbo-connect
git grep -n "jimbo_connect_landing" || echo "landing: no refs"
git grep -n "vercel" -- backend || echo "vercel: no code refs"
```
Expected: no references to the landing HTML; the only `vercel.json` mentions are the file itself.

- [ ] **Step 2: Confirm frontend package manager**

Check `render.yaml:38` — frontend `buildCommand` is `yarn install && yarn build`. **The frontend deploys with yarn**, so `frontend/yarn.lock` is REQUIRED — do NOT delete it. Instead delete the stray root `package-lock.json` if it is unused. Verify: `git grep -n "package-lock" -- . ':!**/node_modules'`. Keep whichever lockfile matches each service's build command; delete only a truly orphaned root lockfile.

- [ ] **Step 3: Delete confirmed-dead files**

```bash
cd /c/Users/sweis/jimbo-connect
git rm jimbo_connect_landing.html backend/vercel.json
# root package-lock.json only if Step 2 confirmed it is orphaned:
# git rm package-lock.json
```

- [ ] **Step 4: Verify builds still work**

Run: `cd /c/Users/sweis/jimbo-connect/frontend && yarn install && yarn build`
Expected: succeeds. Backend unaffected (no vercel usage).

- [ ] **Step 5: Commit & deploy**

```bash
git add -A
git commit -m "chore: remove dead landing HTML, stray vercel config, orphaned lockfile"
git push
```

---

## Phase 2 — Content & Growth Readiness

### Task 7: Seed 3–5 live blog posts

**Files:**
- No source changes; uses the existing admin blog generation endpoint.

**Interfaces:**
- Consumes: admin auth; `ANTHROPIC_API_KEY` (already provisioned).
- Produces: 3–5 published posts visible on the public blog.

- [ ] **Step 1 [OWNER]: Confirm `ANTHROPIC_API_KEY` is set on the API service**

Render dashboard → `jimbo-connect-api` → Environment → confirm `ANTHROPIC_API_KEY` exists. (Not in `render.yaml`; must be a dashboard secret.) If missing, add it.

- [ ] **Step 2: Log in as admin and generate posts**

From the admin cockpit (`app.intro-connect.com/admin/blog`) or via `POST /api/admin/blog/run` (auth required), generate posts until 3–5 exist. Review each for quality/on-brand voice.

- [ ] **Step 3: Publish the good ones**

Publish via the admin UI or `POST /api/admin/blog/{post_id}/publish`. Unpublish/flag any low-quality generations.

- [ ] **Step 4: Verify**

Load the public blog (`https://blog.intro-connect.com/blog` from Task 5). Expected: 3–5 posts listed, each opens to a full post with title/body and JSON-LD.

- [ ] **Step 5: Record**

Append the published slugs to `test_result.md` under a "Blog content" heading. No code commit needed (content lives in MongoDB).

---

### Task 8: Authorize and verify scheduled crons

**Files:**
- Reference: `.github/workflows/{blog-tick,nurture-tick,invites-tick,keep-warm}.yml`

**Interfaces:**
- Produces: automated blog/nurture/invite ticks that authenticate against the API.

- [ ] **Step 1: Identify the tick secret each workflow expects**

Run: `cd /c/Users/sweis/jimbo-connect && git grep -n -i "secret" -- .github/workflows`
Note the exact secret name(s) (e.g. `BLOG_TICK_SECRET`) and the header they send (`x-tick-secret`).

- [ ] **Step 2 [OWNER]: Set the secret in both places**

The same value must exist as (a) a GitHub repo secret (Settings → Secrets and variables → Actions) and (b) the API service env var in Render that the tick endpoints validate against. Generate a strong random value once and paste it to both.

- [ ] **Step 3: Manually trigger one workflow to verify auth**

In GitHub → Actions → the blog-tick workflow → "Run workflow". Expected: it completes green; the API responds 200 (not 401/403). If 401/403, the secret mismatches — re-check Step 2.

- [ ] **Step 4: Confirm keep-warm is running**

Check the keep-warm workflow's recent runs (every ~10 min). Expected: recent green runs; the API responded quickly on the last smoke run (no long cold start). Record in `test_result.md`.

---

### Task 9: Add privacy-friendly analytics

**Files:**
- Modify: `marketing/index.html` (analytics snippet in `<head>`)
- Modify: `frontend/index.html` (analytics snippet in `<head>`)

**Interfaces:**
- Produces: pageview/visit reporting for both public surfaces.

- [ ] **Step 1 [OWNER]: Create the analytics site(s)**

Create a privacy-friendly analytics property (e.g. Plausible or Cloudflare Web Analytics — cookieless, GDPR-friendly) for `intro-connect.com` (and optionally `app.intro-connect.com`). Obtain the embed snippet / site token.

- [ ] **Step 2: Add the snippet to marketing**

In `marketing/index.html`, add the provider's single-line script tag inside `<head>` (exact tag from Step 1). For Plausible this is:
```html
<script defer data-domain="intro-connect.com" src="https://plausible.io/js/script.js"></script>
```

- [ ] **Step 3: Add the snippet to the app**

In `frontend/index.html`, add the same tag with `data-domain="app.intro-connect.com"`.

- [ ] **Step 4: Build both to confirm no breakage**

Run: `cd /c/Users/sweis/jimbo-connect/marketing && yarn build` and `cd ../frontend && yarn build`
Expected: both succeed.

- [ ] **Step 5: Commit & deploy, then verify**

```bash
git add marketing/index.html frontend/index.html
git commit -m "feat(analytics): add privacy-friendly analytics to marketing + app"
git push
```
After deploy, load each site and confirm a pageview appears in the analytics dashboard within a minute.

---

### Task 10: Prepare the manual outreach kit

**Files:**
- Reference/verify: `growth/leads-seed.csv`, `growth/host-outreach-sequence.md`

**Interfaces:**
- Produces: a ready-to-send outreach batch (owner sends in Phase 3).

- [ ] **Step 1: Review the seed leads**

Open `growth/leads-seed.csv`; confirm the ~10 host contacts are current and relevant. Note any obviously stale rows.

- [ ] **Step 2: Verify the sequence copy is on-brand and links to production**

Open `growth/host-outreach-sequence.md`; confirm all URLs point to `intro-connect.com` / `app.intro-connect.com` (not staging), the value prop is current, and the CTA is clear. Fix any staging links.

- [ ] **Step 3: Commit any copy fixes**

```bash
git add growth/host-outreach-sequence.md growth/leads-seed.csv
git commit -m "chore(growth): refresh outreach kit links and copy for launch"
```
Deliverable: outreach kit is send-ready. (Sending is an [OWNER] Phase 3 step.)

---

## Phase 3 — Go Public

### Task 11: Write the launch runbook and rollback doc

**Files:**
- Create: `docs/RUNBOOK.md`

**Interfaces:**
- Produces: an operational reference for the owner.

- [ ] **Step 1: Write `docs/RUNBOOK.md`**

Include, with exact values from this repo: the three service URLs; where each env var/secret lives (Render dashboard vs `render.yaml` vs GitHub secrets) as a table; how to read logs (Render dashboard → service → Logs); how to roll back (Render dashboard → service → Deploys → "Rollback" to the prior deploy, or `git revert <sha> && git push`); how to trigger/troubleshoot the crons; the admin login location; and how to run `tests/smoke_prod.py` as a post-deploy health check.

- [ ] **Step 2: Verify it's accurate**

Cross-check every URL and secret name against `render.yaml`, `.github/workflows`, and `backend/.env.example`. No placeholders.

- [ ] **Step 3: Commit**

```bash
git add docs/RUNBOOK.md
git commit -m "docs: launch runbook + rollback procedure"
```

---

### Task 12: Draft announcement assets

**Files:**
- Create: `docs/launch/announcement.md` (launch blog post + social copy + Product Hunt copy)

**Interfaces:**
- Produces: ready-to-fire launch content (owner publishes/posts in Task 13).

- [ ] **Step 1: Write `docs/launch/announcement.md`**

Include: (a) a 400–600 word launch blog post introducing Intro Connect (problem → solution → how it works → CTA to `app.intro-connect.com`); (b) 3 short social posts (X/LinkedIn) with the value prop and link; (c) a Product Hunt tagline + description + first-comment maker note. Brand: "Intro Connect". No paid-ad copy (out of scope).

- [ ] **Step 2: Commit**

```bash
git add docs/launch/announcement.md
git commit -m "docs: launch announcement assets (blog post, social, Product Hunt)"
```

---

### Task 13: Final smoke + go live

**Files:**
- Modify: `test_result.md` (final go/no-go record)

**Interfaces:**
- Consumes: all prior tasks.

- [ ] **Step 1: Re-run the full production smoke**

Run: `cd /c/Users/sweis/jimbo-connect && python tests/smoke_prod.py`
Expected: all checks PASS. Repeat the Task 1 manual browser loop once more on production.

- [ ] **Step 2: Confirm the go/no-go checklist**

In `test_result.md`, confirm every launch-criteria row from spec §3 is PASS: marketing clean, blog public with posts, branded signup email, full app loop works, nurture + unsubscribe work, crons green, runbook + announcement ready.

- [ ] **Step 3: Commit the final record**

```bash
git add test_result.md
git commit -m "test: final pre-launch go/no-go — all criteria pass"
git push
```

- [ ] **Step 4 [OWNER]: Go public**

Publish the launch blog post, post the social/Product Hunt content, and send the first outreach batch from Task 10. Watch analytics + Render logs for the first hour.

---

## Self-Review Notes

- **Spec coverage:** every spec §3 launch criterion maps to a task — marketing clean (T4), public blog (T5, T7), branded email (T2), full app loop (T1/T13 verify), nurture+unsubscribe (T1/T13 verify), crons (T8), runbook+announcement (T11/T12). Spec §5 phases map 1:1 to plan phases. Confirmed decisions (§9): analytics (T9), support email (T4), GTM/outreach (T10, T12).
- **Owner steps** are explicitly tagged **[OWNER]** where dashboard/DNS/secrets/sending are required and cannot be done from the session.
- **Corrections folded in:** frontend uses **yarn** (per `render.yaml:38`) so `frontend/yarn.lock` is kept, not deleted (Task 6 Step 2) — this overrides the earlier subagent suggestion to delete it.
