# Intro Connect — Public Launch Design & Plan

**Date:** 2026-07-06
**Owner:** Scott
**Goal:** Full public launch of Intro Connect this week.
**Author of record:** Claude (brainstormed with owner)

---

## 1. Product summary

Intro Connect is an event-networking platform — "better events, stronger
connections." Attendees create profiles, join events by code, save contacts they
meet, and message each other afterward. Hosts create and manage events. The system
also includes an admin cockpit, an AI-generated SEO blog, and a growth engine
(nurture email drip, self-serve guest invites, and a cold-outreach kit).

**Brand name (canonical): "Intro Connect".** The git repo is named `jimbo-connect`
and a few internal artifacts still say "Jimbo Connect"; those are cosmetic and do
not need to change for launch (see §7).

---

## 2. Verified current state (probed 2026-07-06)

This launch is **verify-and-finish**, not build-from-scratch. Confirmed live:

| Surface | URL | Status |
| --- | --- | --- |
| Marketing site | `https://intro-connect.com` | **LIVE** — title "Intro Connect. Better events, stronger connections." |
| Web app (SPA) | `https://app.intro-connect.com` | **LIVE** — CNAME → `jimbo-connect-web-huph.onrender.com` |
| Backend API | `https://jimbo-connect-api-rdkp.onrender.com` | **LIVE** — `/api/health` returns `{"ok": true}` (cold-starts on free tier) |
| Database | MongoDB Atlas | **CONNECTED** — API cannot start without `MONGO_URL`, and it starts |
| Email (Resend) | domain `intro-connect.com` | **VERIFIED** — DKIM + SPF + SES feedback DNS present; owner confirmed verified in Resend dashboard |
| DNS | `intro-connect.com` | apex A → `216.24.57.1` (Render); `www` → apex; `app` → Render web service |

**Accounts already provisioned:** Render, MongoDB Atlas, Resend, Anthropic API key.

**Architecture (all on Render, auto-deploy on push to `main`):**
- `jimbo-connect-api` — FastAPI + MongoDB (Motor), JWT auth (httpOnly), Resend email,
  Anthropic for blog. 56 endpoints. Security-hardened. 14 backend test files.
- `jimbo-connect-web` — React 18 + Vite SPA, 18 pages incl. 7-route admin cockpit.
  No frontend tests.
- `jimbo-connect-marketing` — React + Vite marketing site, 12 sections, 17 images.
- 4 GitHub Actions crons — blog / nurture / invites / keep-warm.

---

## 3. Definition of done (launch criteria)

A real, first-time visitor can, on the public domain, complete the full loop with
zero broken surfaces:

1. Land on `intro-connect.com`, read polished marketing copy with **no staging/placeholder references**.
2. Read the blog at a public `intro-connect.com/blog` URL with real published posts.
3. Sign up in the web app, and **receive a correctly-branded email from `intro-connect.com`** (not the `resend.dev` sandbox).
4. Log in, create an event, join an event by code, save a contact, send a message — all working, no CORS/auth failures.
5. Receive the nurture welcome email; the unsubscribe link works and suppresses future sends.
6. Scheduled crons (blog/nurture/invites) run automatically and are authenticated.
7. Owner has a runbook to operate and roll back, plus ready-to-fire announcement assets.

**Recorded evidence:** `test_result.md` populated with a real per-feature pass/fail
from an end-to-end run, not the current empty template.

---

## 4. Out of scope (this week)

- `signal-scout` outreach **automation** — deferred; we use the manual outreach kit instead.
- Paid advertising campaigns.
- Custom `api.intro-connect.com` subdomain for the backend — the app calls the Render
  API URL directly and it works; a vanity API domain is a post-launch nicety.
- Redis-backed rate limiting (in-memory is fine for single-instance free tier).
- Renaming the git repo / purging every internal "Jimbo Connect" string.
- Native mobile apps, PWA/offline, service workers.

---

## 5. Plan (phased)

### Phase 0 — Reality audit (Claude, Day 1)
The verification nobody has done. Establishes truth vs assumption.
- Register a throwaway test account against production; confirm a **branded** email
  lands from `intro-connect.com` (screenshot/report to owner).
- Log in; exercise: create event → join by code → save contact → send message → read messages.
- Trigger and confirm the nurture welcome email; click the unsubscribe link; verify suppression.
- Verify CORS **preflight** (OPTIONS) allows `https://app.intro-connect.com` so login can't silently fail.
- Confirm `EMAIL_FROM` resolves to a verified `intro-connect.com` sender (not `resend.dev`).
- Confirm keep-warm cron actually prevents cold starts (or note first-load latency).
- **Deliverable:** `test_result.md` filled with real pass/fail per feature; a ranked
  list of confirmed blockers feeding Phase 1.

### Phase 1 — Fix launch blockers (Claude, Day 1)
Fix what Phase 0 confirms is actually broken. Known/expected:
- **Blog public routing:** make `intro-connect.com/blog` serve the real blog (currently
  returns the marketing SPA shell). Fix the marketing/render rewrite to proxy `/blog` to the API.
- **Staging refs:** replace all `frontrangedev.co` / `hello@frontrangedev.co` occurrences
  in marketing components with `intro-connect.com` support addresses.
- **CORS / email-sender / branding** gaps surfaced in Phase 0.
- **Dead weight:** remove/relocate standalone `jimbo_connect_landing.html`, the duplicate
  `yarn.lock` (npm is authoritative for frontend), and the stray `backend/vercel.json`
  (Render is the deploy target) — verify none are referenced before deleting.
- **Deliverable:** clean re-deploy; Phase 0 re-run passes.

### Phase 2 — Content & growth readiness (Claude + Owner, Day 2)
- Seed **3–5 quality blog posts** live via the existing Anthropic-backed generator.
- Confirm nurture drip fires on signup (validated in Phase 0) and the day-2/5/10 sequence is scheduled.
- **GitHub cron secrets:** owner pastes the tick secret into GitHub repo secrets so
  blog/nurture/invite workflows authenticate; Claude verifies the workflows fire.
- Prepare the manual outreach kit for send (`growth/leads-seed.csv` + 3-touch sequence).
- Optional: add privacy-friendly analytics to marketing + app for launch-day visibility.
- **Deliverable:** blog populated, crons green, outreach queued, analytics (if chosen) reporting.

### Phase 3 — Go public (Owner-driven, Claude-prepped, Day 3–4)
- Final production smoke test (re-run Phase 0 loop).
- Claude writes: **launch runbook** (operate + roll back) and **announcement assets**
  (launch blog post, outreach send copy, Product Hunt / social copy — ready to fire).
- Owner flips the switch: publish blog, seed first real events, start outreach.
- **Deliverable:** publicly launched, monitored, owner in control.

---

## 6. Division of labor

**Claude does (all code/config/content/QA/docs):** Phase 0 audit + `test_result.md`,
all Phase 1 code fixes, blog seeding, workflow wiring, runbook, announcement drafts,
re-testing.

**Owner does (requires their hands/credentials):**
- Confirm Resend domain verified. ✅ (done)
- Paste the GitHub cron tick secret into repo secrets.
- Approve going public / decide launch timing.
- Send the outreach sequence.
- (If any Render dashboard env var needs changing, owner applies it — Claude can't see/set dashboard secrets.)

---

## 7. Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| Render free-tier cold starts → slow first load | keep-warm cron; verify in Phase 0; note upgrade path if UX suffers |
| Real emails sent during QA | Use throwaway test address; suppression list prevents repeat sends |
| Blog rewrite fix breaks marketing SPA routing | Test both `/` and `/blog` after change; deploy is reversible |
| Deleting `vercel.json`/landing HTML breaks something referenced | Grep for references before deleting; commits are revertible |
| CORS misconfig blocks login on `app.` subdomain | Explicit preflight test in Phase 0 before declaring done |
| Leftover "Jimbo Connect" strings surface publicly | Grep public surfaces (marketing/app/blog/email) specifically; internal refs out of scope |

---

## 8. Timeline

- **Day 1 (today):** Phase 0 audit + Phase 1 fixes + re-test.
- **Day 2:** Phase 2 content/growth + re-test.
- **Day 3:** Runbook + announcement assets + final smoke test.
- **Day 4:** Go public. (Buffer: Day 5.)

---

## 9. Confirmed decisions (owner-approved 2026-07-06)

- **GTM scope:** blog SEO + manual outreach + PLG for launch; Product Hunt/social copy
  prepared as ready-to-fire assets, no paid ads this week. **Confirmed.**
- **Analytics:** include a lightweight, privacy-friendly analytics tool on marketing + app. **Confirmed.**
- **Support email:** replace all `frontrangedev.co` references with **`hello@intro-connect.com`**. **Confirmed.**
