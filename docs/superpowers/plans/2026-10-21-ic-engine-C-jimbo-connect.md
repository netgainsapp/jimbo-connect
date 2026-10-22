# Intro Connect Event Lead Engine, Plan C: Intro Connect App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An Event Leads page in the Intro Connect admin where one Approve button builds the host's account and event, starts the Signal Scout drip with the event details, queues the LinkedIn step, and tracks every lead from found to converted; plus the claim flow, host-as-sender email rules, and the inactive-attendee rules.

**Architecture:** A new Mongo collection `event_leads` (one document per organizer) with a bearer-keyed ingest endpoint fed by the weekly job, an admin router `routers/event_leads.py` for the panel and Approve, a public claim route that reuses the magic-login mechanics, a nightly status poll into Signal Scout, and small changes to `email_send`/`email_layout` so attendee mail carries the host's name, headshot and reply-to. Pure rules live in `backend/event_leads_rules.py` with pytest tests; routers stay thin.

**Tech Stack:** FastAPI + Motor (Mongo) backend in `backend/`, React 18 + Vite frontend in `frontend/src/` (admin pages follow `pages/AdminOutreach.jsx`, API calls through `lib/api.js`), pytest (`cd backend && python -m pytest`), GitHub Actions ticks (`.github/workflows/*-tick.yml` hitting `/api/*/tick` with the tick secret), Render for deploy.

**Spec:** `docs/superpowers/specs/2026-10-21-ic-event-lead-engine-design.md` (copied into this repo), sections 2, 4, 5, 6, 7, 8.

**Sibling plans:** Plan A (`signal-scout/docs/superpowers/plans/2026-10-21-ic-engine-A-sourcing.md`) posts the ingest payload defined in Task 1. Plan B (`...-B-signal-scout.md`) owns the Signal Scout import, claimed and status contracts, reproduced here in Contracts.

## Global Constraints

- No email address is ever returned in an admin list payload beyond the lead's own contact field; never in logs. No attendee email in any attendee-facing payload (existing rule).
- Copy voice: plain, no dashes, no emoji. Intro Connect appears in attendee mail once, in the footer.
- Every new admin route depends on `get_current_admin`; the ingest route uses its own bearer `EVENT_LEADS_INGEST_KEY` (constant-time compare); the claim route is public and rate limited (`rate_limit.guard(request, "claim", limit=10, window_seconds=300)`).
- Approve is idempotent: a second call reports what exists and changes nothing. Every write keys on `event_leads._id`.
- Env vars (Render): `EVENT_LEADS_INGEST_KEY`, `SIGNAL_SCOUT_URL`, `SIGNAL_SCOUT_API_KEY` (existing), `APP_URL` (existing, for the claim link).
- `BILLING_ENFORCED` and `create_event_for` stay the only plan-limit logic; never bypass them.
- Nothing in this plan sends mail to a prospect host; the only host-facing mail is Signal Scout's. Attendee mail changes here are to existing sends (invites, reminders) plus the new message-waiting email.

## Contracts

**Ingest** `POST /api/admin/event-leads/ingest`, bearer `EVENT_LEADS_INGEST_KEY` (payload from Plan A):
```json
{ "run": { "week": "2026-10-18", "ingested": 212, "by_tier": {"A":31,"B":58,"C":123}, "with_email": 24, "with_linkedin": 19, "verifier_checks": 40, "spend_usd": 1.2, "errors": [] },
  "leads": [ { "organizer_key": "meetup:denver-devs", "organizer_name": "Denver Devs", "organizer_url": "https://www.meetup.com/denver-devs", "city": "Denver", "events_listed": 3,
               "anchor": { "source": "revel", "source_event_id": "…", "title": "Denver Tech Mixer", "description": "…", "start": "2026-11-04T18:00:00-07:00", "timezone": "America/Denver", "venue": "Galvanize", "city": "Denver", "price": "Free", "categories": ["networking"], "rsvp": 40, "capacity": null, "source_url": "https://…" },
               "events": [ "same shape" ],
               "score": { "tier": "A", "score": 94, "reason": "…", "format": "mixer", "vertical": "tech", "networking_block": true, "content_hash": "388d90c1" },
               "contact": { "name": "Jane Doe", "email": "jane@host.org", "linkedin_url": "", "website": "https://host.org", "email_status": "verified" } } ] }
```
Response `{ "ok": true, "inserted": n, "updated": n, "unchanged": n, "existing_customer": n }`.

**Signal Scout import** `POST {SIGNAL_SCOUT_URL}/api/intro-connect/import`, bearer `SIGNAL_SCOUT_API_KEY`:
```json
{ "leads": [ { "email", "name", "company", "role",
  "event": { "anchor": { "name", "date", "venue", "city", "source_url" }, "upcoming": [ { "name", "date", "venue", "city", "source_url" } ], "claim_url", "lead_id" } } ] }
```
→ `{ "results": [ { "email", "prospect_id", "outcome": "imported"|"already_scheduled"|"error", "reason"? } ], ... }`

**Signal Scout claimed** `POST .../api/intro-connect/claimed` `{ "prospect_id", "lead_id", "email" }` → `{ "ok": true, "skipped": n }`.

**Signal Scout status** `GET .../api/intro-connect/status?prospect_ids=a,b` → `{ "prospects": [ { "prospect_id", "sent_at", "opened_at", "clicked_at", "replied_at", "bounced_at", "unsubscribed_at", "next_step_at", "anchor_rolled_since_last_send", "anchor": { "name", "date" } } ] }`.

**`event_leads` document:**
```
_id, organizer_key (unique), organizer_name, organizer_url, city, events_listed, anchor, events[], score, score_override?,
contact { name, email, linkedin_url, website, email_status }, status: new|approved|claimed|archived|unreachable|existing_customer,
existing_user_id?, event_id?, host_user_id?, claim_token_hash?, claim_expires_at?, claim_url?,
signal_scout { prospect_id?, outcome?, error?, pushed_at? },
linkedin { status: none|queued|exported|invited|connected|replied|failed, exported_at?, updated_at? },
funnel { found_at, scored_at, approved_at, emailed_at, opened_at, clicked_at, claimed_at, attendees_uploaded_at, event_passed_at, converted_at },
created_at, updated_at, archived_at?
```

## Review Focus

1. Ingest re-sent for an organizer already `approved`: anchor, score and contact must not change; `events` history grows (Task 1 test).
2. Approve on a lead whose contact email belongs to a user who already hosts an event: the lead becomes `existing_customer`, no account or event is created, 409 returned (Task 4 test).
3. Claim link visited twice from two devices: both sign in; `claimed_at` keeps the first time; Signal Scout `claimed` is called once (Task 5 test).
4. Claim token after `claim_expires_at`: plain expired page, no login, no writes (Task 5 test).
5. Message-waiting email to an inactive attendee from the same sender twice in a day: second one is not sent (Task 8 test).

---

### Task 1: Collection, rules and ingest

**Files:**
- Create: `backend/event_leads_rules.py` (pure), `backend/event_leads_store.py` (Mongo), `backend/routers/event_leads.py` (ingest route only in this task)
- Modify: `backend/database.py` (`event_leads = db["event_leads"]`, `event_lead_runs = db["event_lead_runs"]`), `backend/server.py` (include the router)
- Test: `backend/tests/test_event_leads_rules.py`, `backend/tests/test_event_leads_ingest.py`

**Interfaces:**
- Produces (rules): `merge_ingest(existing: dict|None, incoming: dict, now) -> dict` (new doc when None; when `status in ("new","unreachable")` replace anchor, events, score, contact and recompute `events_listed`; otherwise only union `events` by `source_event_id`); `initial_status(incoming, existing_user: dict|None) -> str` (`existing_customer` when the user hosts any event or has a non-free plan; `unreachable` when no email and no linkedin_url; else `new`); `days_until(iso, now) -> int` (Denver calendar days); `tier_sort_key(doc) -> tuple` (A first, then days until anchor ascending).
- Produces (store): `upsert_lead(doc)`, `get_lead(id)`, `list_leads(show_c: bool)`, `record_run(run)`.
- Produces (route): the Ingest contract.

- [x] **Step 1: Write the failing tests** (rules): new doc from incoming; approved doc keeps anchor and score but gains an event; `initial_status` three cases; `days_until("2026-11-04T18:00:00-07:00", now=Oct 22 10am Denver) == 13`; sort puts an A event in 20 days before a B event in 3 days. Ingest route test (TestClient with a fake collection the way `test_attendee_import.py` fakes Mongo): 401 without bearer, counts in the response, one run record written.
- [x] **Step 2: Run** `cd backend && python -m pytest tests/test_event_leads_rules.py tests/test_event_leads_ingest.py -q` → FAIL.
- [x] **Step 3: Implement.** Bearer compare with `hmac.compare_digest`. Ingest looks up `users` by each contact email to feed `initial_status`.
- [x] **Step 4: Run** → PASS.
- [x] **Step 5: Commit** `git commit -m "feat(leads): event_leads collection, merge rules and ingest endpoint"`.

---

### Task 2: Admin list, detail, archive, edits

**Files:**
- Modify: `backend/routers/event_leads.py`
- Test: `backend/tests/test_event_leads_admin.py`

**Interfaces:**
- Produces: `GET /api/admin/event-leads?show_c=false` → `{ leads: [serialized], kpis }` sorted by `tier_sort_key`; `GET /api/admin/event-leads/{id}` → serialized with `email_preview` and `linkedin_preview` (Task 3); `POST /api/admin/event-leads/{id}/archive`; `POST /api/admin/event-leads/{id}/unarchive`; `PUT /api/admin/event-leads/{id}/contact` `{ name, email, linkedin_url }` (re-runs `initial_status` when the lead is `new`/`unreachable`); `PUT /api/admin/event-leads/{id}/score-override` `{ score: int }` stored beside `score`, never over it. `serialize_lead(doc) -> dict` adds `days_until`.

- [x] **Step 1: Tests**: non-admin 403; C hidden by default and shown with `show_c=true`; archive sets `archived_at` and status; contact edit on an `unreachable` lead with an email makes it `new`; score override keeps `score.score`.
- [x] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [x] **Step 5: Commit** `git commit -m "feat(leads): admin list, detail, archive and edits"`.

---

### Task 3: Previews: the email step 1 and the LinkedIn messages

**Files:**
- Create: `backend/event_leads_copy.py` (pure): `linkedin_note(lead) -> str` (under 300 chars, event name, claim link), `linkedin_followup(lead) -> str`, `email_preview(lead, template: dict) -> {subject, body}` using `core.merge_vars` with `event_name`, `event_date`, `time_until_event`, `first_name`, `company`, `claim_url`, `series_line`
- Modify: `backend/sales_templates.py` seeds: add `ic-event-step-1` (the mirror of Signal Scout's step 1 copy, for the preview) and `ic-linkedin-note`, `ic-linkedin-followup`
- Test: `backend/tests/test_event_leads_copy.py`

- [x] **Step 1: Tests**: note length ≤ 300 with a long event name (truncate the name, never the link); series line present only with two events; no dash or emoji characters in any output (`re.search(r"[—–\U0001F300-\U0001FAFF]", s) is None`).
- [x] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [x] **Step 5: Commit** `git commit -m "feat(leads): email and LinkedIn previews for event leads"`.

---

### Task 4: Approve

**Files:**
- Create: `backend/event_leads_approve.py` (`approve(lead_id, actor, now) -> dict` orchestrating the six steps from spec section 2)
- Modify: `backend/routers/event_leads.py` (`POST /api/admin/event-leads/{id}/approve`, `POST .../retry-outreach`), `backend/outreach.py` (add `push_event_lead(lead, claim_url) -> dict` using the Signal Scout import contract with `event`), `backend/routers/events.py` (`create_event_for` accepts an optional `provenance: dict` stored on the event; `serialize_event` unchanged)
- Test: `backend/tests/test_event_leads_approve.py`

**Interfaces:**
- Consumes: `create_event_for(user, EventCreateRequest, provenance=None)`; `billing.plan_of`; `core._new_reset_token`, `core._hash_token` for the claim token.
- Produces: `approve` returns `{ status, event_id, host_user_id, claim_url, signal_scout: { prospect_id, outcome } }`. Steps: (1) user by email, else insert `{ email, password_hash: hash_password(random), profile: { name }, plan: "free", nurture_enabled: False, host_origin: "event_lead", email_verified: True }`; for a LinkedIn-only lead skip the user and set `pending_host: True` on the event provenance with `created_by: None`; (2) `create_event_for` with name = anchor.title, date = anchor.start, location = f"{venue}, {city}", description = anchor.description[:5000], industry_tags = [score.vertical], provenance `{ source, source_url, event_lead_id, pending_host }`; (3) token: `_new_reset_token()`, store `_hash_token(token)` and `claim_expires_at = anchor.start + 30 days`, `claim_url = f"{APP_URL}/claim/{token}"`; (4) `push_event_lead` unless LinkedIn-only; failure stores `signal_scout.error` and leaves status `approved`; (5) `linkedin.status = "queued"` when `contact.linkedin_url`; (6) status `approved`, `funnel.approved_at`. `existing_customer` → 409 before any write. Second call → same response, no writes (assert via fake collection call counts).
- Auto-approve: `app_flags` key `event_leads_auto_approve_min_score` (int or absent; absent means off, and it ships absent). When set, the ingest route (Task 1) calls `approve` for each inserted lead with `status == "new"`, a contact email, and `score.score >= min_score`, after the ingest response is computed; failures are recorded on the lead, never raised. Admin route `PUT /api/admin/event-leads/settings` `{ auto_approve_min_score: int|null }` edits it; `GET` returns it with the list.

- [x] **Step 1: Tests**: happy path creates user, event, token, pushes once; auto-approve absent → ingest approves nothing, set to 90 → approves the one lead at 94 with an email and skips the 94 without one; LinkedIn-only creates event with no user and no push; existing host → 409 and nothing written; Signal Scout 500 → status `approved`, `signal_scout.error` set, event exists; second approve → zero inserts; plan-limit 403 from `create_event_for` surfaces as 409 with the message and the lead unchanged.
- [x] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [x] **Step 5: Commit** `git commit -m "feat(leads): one-button Approve builds the host, the event and the drip"`.

---

### Task 5: Claim flow

**Files:**
- Create: `backend/routers/claim.py` (`GET /api/claim/{token}` JSON for the SPA: `{ state: "ok"|"needs_email"|"expired"|"unknown", event, host }`; `POST /api/claim/{token}` `{ email? , name? }` completes the claim and sets the auth cookie), `frontend/src/pages/Claim.jsx` (route `/claim/:token`)
- Modify: `backend/server.py` (include), `frontend/src/App.jsx` (public route), `frontend/src/lib/api.js` (`claimApi.get`, `claimApi.complete`)
- Test: `backend/tests/test_claim.py`, `frontend/src/pages/Claim.test.mjs` (render states)

**Interfaces:**
- Consumes: `_hash_token`, `create_access_token`, `set_auth_cookie`, `outreach.notify_claimed(lead) -> dict` (new: POST the Signal Scout claimed contract; never raises).
- Produces: on first completion: `funnel.claimed_at`, status `claimed`, `notify_claimed` once; for `pending_host` events: create the user from the posted email (Task 4 step 1 rules), set `created_by`, clear `pending_host`. Response includes `redirect: f"/host/events/{event_id}?claimed=1"` (use the existing host event page route; confirm its path in `App.jsx`). Expired or unknown: no cookie, no writes.

- [x] **Step 1: Tests**: ok state for a valid token; `needs_email` for a pending-host lead; second completion from another device signs in and does not call Signal Scout again; expired → `expired`, no writes; unknown → `unknown`; rate limit after 10 calls.
- [x] **Step 2: Run** → FAIL. **Step 3: Implement** backend, then the page: banner "This event was set up for you. Add your attendee list to go live.", the attendee upload modal open (`AttendeeImportModal`), and the optional photo step (Task 6) after upload.
- [x] **Step 4: Run** backend and `cd frontend && npm test` → PASS.
- [x] **Step 5: Commit** `git commit -m "feat(claim): one-tap claim of a pre-built event"`.

---

### Task 6: Host as sender

**Files:**
- Modify: `backend/email_send.py` (`send_branded` and `send_template_branded` accept `host: dict|None`; when given, `from` becomes `f"{host_name} via Intro Connect <{EMAIL_FROM_ADDRESS}>"` and `reply_to` defaults to the host's email), `backend/email_layout.py` (`render(..., host=None)`: name and 56px round headshot above the heading when `host.photo_url`; the Intro Connect lockup moves to the footer when `host` is given), `backend/invites.py` and the reminder tick (pass `host`), `backend/core.py` (`host_block(user) -> dict` = `{ name, email, photo_url }`)
- Modify: `frontend/src/pages/Claim.jsx` (photo step: "Add your photo so your guests see you, not us.", uses `POST /api/profile/photo`, skippable)
- Test: `backend/tests/test_host_sender.py`

- [x] **Step 1: Tests**: `from` header format and reply-to for a host send; headshot `<img>` present only with `photo_url`; footer carries the lockup exactly once; an attendee send without `host` is unchanged (snapshot against the current output of one existing template).
- [x] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [x] **Step 5: Commit** `git commit -m "feat(email): attendee mail goes out in the host's name with their photo"`.

---

### Task 7: Inactive attendees and the reminder cap

**Files:**
- Modify: `backend/attendee_import.py` (membership gains `activated: False` on import; `activated_at` set on first login or claim, in `routers/auth.py` login/magic and the join flow), `backend/core.py` `serialize_attendee` (adds `active: bool`), `backend/invites.py` (reminders skip when `days_until(event.date) < 1`; invite and reminder bodies carry a "remove me" link `GET /api/invites/remove/{token}` that deletes the membership and suppresses re-import for that event), `backend/directory.py` (no change: cross-event directory already excludes non-opted rows; add a test asserting an imported inactive member is absent)
- Frontend: the event directory card shows a quiet "not yet active" tag when `active` is false (find the attendee card component under `frontend/src/components/`)
- Test: `backend/tests/test_inactive_attendees.py`

- [x] **Step 1: Tests**: import sets `activated False`; login sets `activated_at`; reminder not sent the day before or after the event; remove link deletes the membership and a re-import skips that email with reason `removed`; inactive member never in `/api/directory`.
- [x] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [x] **Step 5: Commit** `git commit -m "feat(attendees): inactive state, reminder cap and remove-me link"`.

---

### Task 8: Message-as-activation email

**Files:**
- Create: `backend/message_notify.py` (`maybe_notify(sender: dict, recipient: dict, event: dict, now) -> dict` with the rules: recipient inactive, real message, one per sender per day, a second message from the same sender waits for a reply, two senders inside an hour share one email via a 60-second coalescing window stored on `message_notify_state`), template `message-waiting` added to `template_seeds.py` and `HOST_EDITABLE`
- Modify: `backend/routers/people.py` (`POST /api/messages` calls `maybe_notify` after insert), `backend/database.py` (`message_notify_state = db["message_notify_state"]`)
- Test: `backend/tests/test_message_notify.py`

**Interfaces:**
- Produces: subject `f"{event.name}: {sender_first} from {sender_company} sent you a message"`; body: sender first name, company, role, headshot, event name and date, one button to a magic sign-in that opens the thread; sent in the host's name (Task 6 `host`). Nothing from the message text.

- [x] **Step 1: Tests**: active recipient → no email; inactive → one email with the subject format; second message same sender same day → none; sender B within the hour → one email naming both; body never contains the message text.
- [x] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [x] **Step 5: Commit** `git commit -m "feat(messages): a message to an inactive attendee is their activation email"`.

---

### Task 9: LinkedIn queue export and results import

**Files:**
- Modify: `backend/routers/event_leads.py` (`GET /api/admin/event-leads/linkedin-queue.csv` marks exported; `POST /api/admin/event-leads/linkedin-results` accepts a CSV upload with columns `linkedin_url, status, at` and the Linked Helper export columns the builder maps after checking the vendor's current export format; sets `linkedin.status` and timestamps; `POST /api/admin/event-leads/linkedin-webhook` with `?secret=` if Linked Helper Standard offers webhooks today, else omitted)
- Test: `backend/tests/test_linkedin_queue.py`

- [x] **Step 1: Tests**: queue holds only `approved` leads with a LinkedIn URL and `linkedin.status == "queued"`; export sets `exported`; results import maps `connected`/`replied`/`failed`; unknown URL rows are reported, not fatal.
- [x] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [x] **Step 5: Commit** `git commit -m "feat(leads): Linked Helper queue export and results import"`.

---

### Task 10: Status poll, funnel and KPIs

**Files:**
- Create: `backend/event_leads_poll.py` (`poll_status(now) -> dict`: approved, not claimed, not archived leads with a `prospect_id`, in chunks of 200, map the Status contract into `funnel.*`; when `anchor_rolled_since_last_send`, rename and re-date the pre-built event to the new anchor and store the new anchor on the lead; `event_passed_at` when `anchor.start < now`), route `POST /api/event-leads/tick` guarded by `_tick_authorized`, workflow `.github/workflows/event-leads-tick.yml` daily `0 7 * * *` UTC
- Modify: `backend/routers/events.py` import route (`funnel.attendees_uploaded_at` on an event with `provenance.event_lead_id`), `backend/event_leads_rules.py` (`kpis(leads, runs, weeks=5) -> list[dict]` per spec section 2 KPI strip; `converted_at` when the host has a second event or a non-free plan)
- Test: `backend/tests/test_event_leads_poll.py`

- [x] **Step 1: Tests**: funnel fields filled from a fake status response; anchor roll renames the event; attendee import stamps the funnel; `kpis` returns five weekly rows with `qualification_rate = (A+B)/ingested`.
- [x] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [x] **Step 5: Commit** `git commit -m "feat(leads): nightly status poll, funnel timestamps and KPI strip"`.

---

### Task 11: The Event Leads page

**Files:**
- Create: `frontend/src/pages/AdminEventLeads.jsx` (table + drawer per spec section 2), `frontend/src/pages/AdminEventLeads.test.mjs`
- Modify: `frontend/src/App.jsx` (route `/admin/event-leads`, admin nav link beside Outreach), `frontend/src/lib/api.js` (`eventLeadsApi`: `list`, `get`, `approve`, `retryOutreach`, `archive`, `unarchive`, `saveContact`, `overrideScore`, `linkedinQueueUrl`, `uploadLinkedinResults`)

**Interfaces:** consumes every route from Tasks 2, 4, 9, 10.

- [x] **Step 1: Test** (node test runner, render with a fake api): rows sorted A then days-until; C hidden until the toggle; Approve button disabled for `existing_customer` and `archived`; drawer shows the reason block and the email preview; KPI strip renders five weeks.
- [x] **Step 2: Run** `cd frontend && npm test` → FAIL. **Step 3: Implement** following `AdminOutreach.jsx` conventions (`useToast`, `useConfirm`; Approve confirms once with the event name). **Step 4: Run** → PASS; `npm run build` → clean.
- [x] **Step 5: Commit** `git commit -m "feat(admin): Event Leads page with Approve, drawer and KPIs"`.

---

### Task 12: Docs and the operator checklist

**Files:**
- Modify: `JIMBO_CONNECT_DOCS.md` (Event Leads section: the flow, the routes, the collections, env vars), `docs/RUNBOOK.md` (the daily tick, what to do when Approve shows an outreach error)
- Create: `docs/EVENT-LEADS-OPERATOR.md`: Scott's steps in order (set the three env vars on Render, install Linked Helper Standard and log in, create the Linked Helper campaign with the caps 20 and 20, first supervised ingest, first Approve on one A-tier lead, watch the status poll the next morning).

- [x] **Step 1: Write them.** **Step 2: Run** `cd backend && python -m pytest -q` and `cd frontend && npm test && npm run build` → all PASS.
- [x] **Step 3: Commit** `git commit -m "docs(leads): event leads reference and operator checklist"`.
