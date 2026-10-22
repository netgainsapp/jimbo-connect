# Intro Connect event-driven lead engine

Design, 2026-10-21. Spans two repos: `signal-scout` (sending, replies, tracking) and
`jimbo-connect` (the Intro Connect app: admin panel, host accounts, events, billing).
Approved by Scott in conversation; the "theirs" answers are folded in below.

## Intent

Event hosts are the Intro Connect customer. When a host lists a networking event
they are already spending to gather a room, and the event date is a deadline. This
engine finds those hosts from public event feeds, scores how well they fit, builds
their Intro Connect event for them before they are ever contacted, and reaches
them by email and LinkedIn with a message that names their event and a link to the
event we already built. The host clicks, signs in, uploads attendees, and is live.
The first event is free; they pay when they start a second one.

The pitch is not "manage attendees". It is: your guests keep the relationships
they made in the room after the event ends, in one simple directory where LinkedIn
and the rest are one click away.

## What already exists (build on it, do not rebuild)

| Piece | Where | State |
|---|---|---|
| Organizer finder: Eventbrite and Meetup organizer pages, website discovery, email extraction, MX check, output in import shape | `signal-scout` branch `feat/ic-organizer-finder` (758f3fe, unpushed), `scripts/ic-organizers/` | Pilot 2026-10-19: 249 organizers, 29 enriched, 5 usable emails, $0. Website coverage (about 1 in 3) is the bottleneck. Eventbrite listing pages rate-limit after roughly 100 requests. |
| Intro Connect import route: upserts `prospect_type='event_host'` and schedules the 5-step drip | `signal-scout` `app/api/intro-connect/import/route.js`, bearer `CRON_SECRET` | Live. Body `{ leads: [{ email, name, company, role }] }`. Rows land `paused`. |
| Intro Connect drip templates (5 steps, `{{first_name}}`, `{{company}}`, `{{unsubscribe_url}}`) | unified `templates` table, project `intro-connect` | Seeded (mig 029, copied by 036). Copy is the old generic pitch; it will be rewritten. |
| Daily release cron for Intro Connect, with ramp check | `app/api/cron/ic-release`, `app_settings.ic_release_per_window` | Shipped at 0. Releases nothing until set. |
| Reply capture, reply sorting, suppression, bounce handling, CRM | `signal-scout` | Live. |
| Outreach cockpit that pushes leads to Signal Scout | `jimbo-connect` `backend/outreach.py`, `routers/admin.py` (`/api/admin/outreach/*`), `frontend/src/pages/AdminOutreach.jsx` | Live, dormant until `SIGNAL_SCOUT_URL` and `SIGNAL_SCOUT_API_KEY` are set on Render. |
| Event creation (`create_event_for`), attendee import (`attendee_import.import_rows`), magic-link login (`/api/auth/magic/{token}`), per-host email templates | `jimbo-connect` backend | Live. |
| Stripe billing: free plan = 1 event, `BILLING_ENFORCED` switch | `jimbo-connect` `backend/billing.py` | Live. The pre-built event is the host's one free event. |

## Scope of this build

This project builds sections 1 to 8: sourcing, scoring, the admin panel, the
Signal Scout changes, the claim flow, LinkedIn, the host-as-sender rules with the
photo step, the inactive-attendee rules with the message-as-activation email,
and tracking. The event-anchored attendee sends, the returning-attendee
experience, and everything under "Attendee marketing" are settled here so the
data model keeps what they need, but they are the second project and are not
built now (see Later).

## Goals

1. A weekly batch of scored Front Range event hosts appears in the Intro Connect
   admin panel with no manual sourcing.
2. One button, Approve, does everything: host account, event, attendee upload
   slot, outreach by email and LinkedIn. The admin never opens Signal Scout.
3. The first email and the LinkedIn message both name the event and carry the
   claim link to the already-built event.
4. Every lead shows its funnel position from found to converted, and the panel
   shows weekly totals for the KPIs in the business case.
5. Spend is capped and visible.

## Non-goals (this version)

- Metros outside the Front Range by default. The metro list is a setting, and
  TechMeetups.io already covers 16 cities, so widening is a config change later.
  Sources that need their own parser are listed under "Later" and are not built
  now.
- A paid B2B contact database (Apollo, Clay, ZoomInfo). Free lookups plus one
  email verifier only.
- Auto-approve. The switch ships but is off.
- Scraping attendee lists. Eventbrite and Meetup keep them private; attendees are
  uploaded by the host.
- Moving the Intro Connect drip out of Signal Scout. Signal Scout stays the sender.

## Anti-goals (a failure even if it works)

- Any mail or LinkedIn message to a host whose event date has passed.
- Any outreach copy that mentions Revel, or the `.com` lookalike of the brand domain
  (the real domain is `signal-scout.email`).
- Dumping a whole batch into one send. The Intro Connect release cap stays the
  throttle; the engine never bypasses it.
- A second automatic action on the same message or lead (double accounts,
  double events, double emails). Every write is idempotent on a stable key.
- Sending from, or automating, Scott's Gmail. Email goes through Signal Scout's
  `signal-scout.email` sender only.

## Constraints

- Sourcing runs on Scott's PC as a Claude Code scheduled task, never on Vercel or
  Render. Same shape as the Baseline Drips lead supply job (`scripts/bd-supply/`).
- Revel (`https://revelco.org`) is a third party. Its robots file allows general
  access with Content-Signal `use=reference, ai-train=no`. We read it as reference
  data, never train on it, and pace the job to one pass a week of at most about
  40 requests. Its name never appears in outreach.
- Revel's feed: `GET /events?limit=&offset=&from=&category=&city=&source=`, JSON
  `{ data: [...], meta }`, 200 per page honoured. Each event carries `title`,
  `description_plain`, `start_time`, `timezone`, `venue_name`, `venue_address`,
  `venue_city`, `is_free`, `price`, `categories` (JSON string), `rsvp_count`,
  `capacity`, `source` (`eventbrite`, `meetup`, `luma`, `ical`, `catalyzer`),
  `source_url`, `organizer_name`, `organizer_url`, `organizer_id`. University
  calendar (`ical`) rows have no organizer and are mostly out of scope.
  `/categories` and `/cities` list the filter values.
- Weekly spend cap: $10, covering the email verifier (and nothing else in this
  version). Scott can raise it in the job's settings.
- LinkedIn automation runs on Scott's personal LinkedIn account through a
  third-party desktop tool. That account carries the restriction risk. Daily
  action cap in the tool: 20 invites and 20 messages, well under the vendor's
  150-action guidance.
- Signal Scout's Supabase REST caps at 1000 rows; paginate any read that can
  exceed it. Check every `{ error }` from supabase-js.
- Jimbo Connect is FastAPI + Mongo on Render; React frontend. Signal Scout is
  Next.js 16 App Router on Vercel with Supabase. Keep each piece in the repo that
  owns the data it touches.

## The decisions, as decided

### 1. Sourcing (Scott's PC, weekly)

Extend `scripts/ic-organizers/run.mjs` with subcommands, keeping the existing
organizer-page enrichment:

- `fetch`: pull upcoming events for the next 60 days from every enabled source
  into one normalized shape (`source`, `source_event_id`, `title`, `description`,
  `start`, `timezone`, `venue`, `city`, `price`, `categories`, `rsvp`, `capacity`,
  `source_url`, `organizer_name`, `organizer_url`, `organizer_key`). Sources are
  plug-ins under `scripts/ic-organizers/sources/`, each a file with `fetch(cfg)`,
  enabled by a `sources` list in the job's settings (default: `revel`,
  `techmeetups`, `coloradostartups`). Metros are a setting too (default: the
  Front Range: Denver, Boulder, Colorado Springs, Fort Collins and the suburbs
  Revel lists). Sources in this version:
  - `revel`: the JSON feed, filtered to the in-scope categories (networking,
    startup, business, tech, technology, b2b, community, conference, panel,
    workshop, happy hour, social, meeting/conference, sales, marketing, product,
    saas, ai, women, non-profit, career) and the metro cities. Drop `ical` rows
    with no organizer.
  - `ldjson`: a generic source for pages that embed schema.org `Event` objects in
    `ld+json`. Configured with page URLs. Two configured now: TechMeetups.io city
    pages (`https://techmeetups.io/<city>`, 16 cities, about 20 events per page
    plus an RSS feed at `/feed.xml`, outbound Meetup, Eventbrite and Luma links)
    and the Colorado Startups calendar
    (`https://coloradostartups.org/event-calendar`, about 60 events with outbound
    links). The organizer comes from the `organizer` field when present, else
    from the outbound Meetup group or Eventbrite organizer link the way the
    existing finder reads them.
  De-duplicate across sources by `organizer_key` (the Meetup group slug, the
  Eventbrite organizer id, or a normalized organizer name plus city). The
  "anchor event" is the organizer's soonest event at least 7 days out, so the
  drip has room before the date; if none is 7 days out, the soonest one. Keep
  every upcoming event in `events` and the count as `events_listed`. Write
  `events.json`.
- `score`: send each anchor event (title, description, date, venue, price,
  categories, rsvp/capacity, organizer name, events_listed) to Claude once and
  get back `{ tier: 'A'|'B'|'C', score: 0-100, reason, format, vertical,
  networking_block: bool }`. Tier rules from the business case: A = recurring
  tech/business meetups, startup weeks, mixers with an explicit networking or
  community element; B = one-off workshops, panels, educational events with
  networking secondary; C = purely social, single-speaker lectures, non-business,
  university administrative entries, or expos in the thousands. Batch requests,
  cache by `content_hash` so a re-run never re-scores an unchanged event. Model
  from `IC_SCORE_MODEL`, default chosen by the builder from the `claude-api`
  skill (a current Sonnet-class model). Builder reads that skill before writing
  the call.
- `enrich` (existing finder steps, renamed): for A and B only, fetch the organizer
  page, find the website, extract emails, MX check, then the paid verifier under
  the $10 weekly cap (Reoon, else ZeroBounce, else pass unverified, as bd-supply
  does). Also capture a LinkedIn company or person URL when the organizer page or
  website links one. A lead with neither email nor LinkedIn is kept as
  `unreachable` so the panel can show it and the admin can add a contact by hand.
- `publish`: POST the batch to Jimbo Connect `POST /api/admin/event-leads/ingest`
  (bearer, a new `EVENT_LEADS_INGEST_KEY` env var on Render, mirrored in the
  job's local env file). Idempotent on `(source, organizer_id, event source_id)`.
  Re-publishing an existing lead updates event fields and score but 
  touches status, contact edits, or anything the admin changed.
- `report`: summary line for the week (ingested, A/B/C counts, with email, with
  LinkedIn, spend) posted to the same ingest endpoint as a `run` record.

Lead identity (settled here, builder check question 1): a lead is one
organizer, not one event. The lead row carries the current anchor event and an
`events` history. A re-publish of an organizer whose lead is `new` or
`unreachable` updates the anchor, score and event fields. A lead that is
`approved`, `claimed` or `archived` is never re-pitched by the engine: its new
events are appended to the history for the drawer, nothing else changes. A
claimed host's next event is a paying event and a different conversation, which
Jimbo Connect's own host mail handles. "Ingested" in the KPI strip counts
organizers, with events as a second number.

Scheduled task: Sunday 7pm Denver (after the bd-supply task), prompt file
`scripts/ic-organizers/weekly-task.md`, run order `fetch`, `score`, `enrich`,
`publish`, `report`. Secrets live in `scripts/ic-organizers/.env.ic.local`
(git-ignored): `ANTHROPIC_API_KEY`, `JIMBO_CONNECT_URL`,
`EVENT_LEADS_INGEST_KEY`, optional `REOON_API_KEY` or `ZEROBOUNCE_API_KEY`,
`IC_WEEKLY_CAP_USD` (default 10).

### 2. The admin panel (Jimbo Connect)

New page `AdminEventLeads.jsx` at `/admin/event-leads`, new Mongo collection
`event_leads`, new router `routers/event_leads.py`. One row per lead:

| Column | Source |
|---|---|
| Event name, date, days until | Revel, re-computed on render |
| Host organization | organizer name |
| Category (format, vertical) | Claude |
| Score and tier, with the reason in the drawer | Claude |
| Contact: name, email, LinkedIn URL, or "none found" | enrich step or admin edit |
| Status | `new`, `approved`, `archived`, `unreachable`, plus funnel fields below |

Default sort: tier A first, then days until the event ascending. C-tier rows are
hidden behind a toggle. The row opens a drawer with: the reason block, the event
description and source link, the contact fields (editable), score override, the
email preview (the step-1 template with this lead's variables substituted), the
LinkedIn message preview, and the funnel timeline.

Buttons:

- **Approve**: the one action. Runs, in order, inside one request:
  1. Host user: find by email, else create with a random password, name from the
     contact, `plan: free`, `nurture_enabled: false`, a `host_origin: 'event_lead'`
     marker. No welcome mail, no verification mail (the claim link signs them in).
  2. Event: `create_event_for(user, ...)` with name, date, location (venue name
     and city), description, `industry_tags` from the Claude vertical, and a
     `provenance: { source, source_url, event_lead_id }` field. The lead stores the
     `event_id`.
  3. Claim token: a random 32-byte token stored hashed on the lead, with
     `claim_url = <APP_URL>/claim/<token>`, expiring at the event date plus 30
     days.
  4. Outreach: POST to Signal Scout `/api/intro-connect/import` with the lead's
     email, name, company, role, and the new `event` object (section 3). Store the
     returned prospect id on the lead. If Signal Scout answers an error, the lead
     stays `approved` with `outreach_error` set and a Retry button; the account and
     event are not rolled back (they are idempotent on the next Approve).
  5. LinkedIn: if the lead has a LinkedIn URL, add it to the LinkedIn queue
     (section 5).
  6. Status `approved`, `approved_at`, funnel `emailed` pending until Signal Scout
     reports the send.
  A second Approve on the same lead is a no-op that reports what already exists.

  Two cases settled here (builder check questions 2 and 3):
  - **LinkedIn only, no email.** Approve still builds the event, but under no
    user yet: the event is created with `created_by` null and `provenance.pending_host`
    true, hidden from every list until claimed. The LinkedIn note carries the
    claim link. The claim page, for a lead with no email on file, asks for the
    host's email first, then creates the user, attaches the event, and continues
    as normal. Signal Scout is not called at Approve time for these leads; it is
    called at claim time if a drip is still wanted (it is not: a claimed host gets
    Jimbo Connect's own onboarding mail). The funnel for these leads starts at
    `linkedin_status`, not `emailed_at`.
  - **Email already belongs to a Jimbo Connect user.** At ingest, the publish
    endpoint checks the email. A user who hosts one or more events, or has a paid
    plan, marks the lead `existing_customer` with a badge; Approve is disabled on
    it and the drawer links to the user. A user with no hosted events (an attendee
    account created by an import, or a signup that never built anything) is a
    normal lead: Approve reuses that user, and the free-plan limit is not hit
    because they host nothing. `create_event_for` is called as the host, so the
    plan limit stays enforced by the existing code and a 403 there is shown as an
    error on the lead rather than bypassed.
- **Archive**: status `archived`, nothing else. Reversible.
- **Retry outreach**: step 4 again.
- **Save contact / score override**: edits the lead only; an override is recorded
  as `score_override` beside the Claude score, never over it.

Auto-approve: setting `event_leads_auto_approve_min_score` (null = off, ships
null). When set, the ingest endpoint approves leads at or above it that have an
email, using the same Approve code path. Off until Scott has watched a few
batches by hand.

KPI strip at the top, for the current week and the previous four: ingested,
qualification rate (A+B over all), approved, emailed, opened, claim link clicked,
claimed, attendees uploaded, converted (a second event or a paid plan).

### 3. Signal Scout changes

- Import body gains an optional `event` object per lead:
  `{ anchor: { name, date (ISO, with timezone), venue, city, source_url },
     upcoming: [ { name, date, venue, city, source_url }, ... ], claim_url, lead_id }`.
  Stored on the prospect in a new jsonb column `prospects.event_context`
  (migration, RLS stays on, no policies). `buildVarsFromProspect` exposes
  `{{event_name}}`, `{{event_date}}` (formatted "Tuesday, November 4"),
  `{{time_until_event}}` ("in 12 days", "next week", "tomorrow"),
  `{{event_venue}}`, `{{series_line}}` and `{{claim_url}}`, computed at send
  time, not import time.
- The event resolves at send time. `{{event_name}}` and friends refer to the
  soonest event in `upcoming` whose date is still at least 2 days away; if the
  anchor passed before step 3, step 3 names the next event on its own. When
  that happens the prospect's `event_context.anchor` is advanced and a flag
  `anchor_rolled_since_last_send` is set; the Jimbo Connect status poll picks it
  up and re-dates and renames the unclaimed, hidden pre-built event to match,
  so the claim link never points at a past event. `event_passed` only fires when
  nothing in `upcoming` is still ahead.
- `{{series_line}}` is filled only when the host has more than one upcoming
  event: "You have Denver Tech Mixer on Nov 4 and the Founder Breakfast on Nov
  18, so this would carry over from one to the next." It is used in step 1
  always, and in a later step only when the anchor rolled since the previous
  send, so the reader learns why the event name changed. Steps 2, 4 and 5 name
  one event and stay short. One ask per email.
- Subjects lead with the event name: "Denver Tech Mixer on Nov 4: your
  attendee directory is ready." Copy never promises more than one free event;
  "the first one is on us" is the line.
- Weekly re-publish keeps `upcoming` current on prospects that are still in the
  drip (`new` and `approved` leads only).
- Cadence fits the deadline. The import computes the five step dates from the
  cadence array but clamps every step to land at least 2 days before the event;
  steps that cannot fit are inserted as `skipped` (reason `event_too_soon` in the
  log). An event under 5 days out gets step 1 only.
- The sequence cron and the release cron skip any Intro Connect row whose
  `event_context.date` has passed (reason `event_passed`), the same way Creditor
  Ready skips after its close date.
- Release order and re-anchoring (settled here, builder check question 4). The
  Intro Connect release cron today releases step 1 oldest-scheduled first and
  re-dates steps 2 to 5 from the real step-1 send. For rows with an
  `event_context`, it instead orders by event date ascending (soonest event
  first), skips step 1 for an event inside the 2-day line (reason
  `event_too_soon`), and re-applies the 2-day clamp when it re-dates the later
  steps. The cap per window is unchanged. Rows without an `event_context` keep
  today's behavior.
- Import response. The import route today returns only counts. It gains a
  `results` array, one entry per submitted lead, with `email`, `prospect_id`,
  and `outcome` (`imported`, `already_scheduled`, `error` with a message), so
  Jimbo Connect can store the prospect id. Counts stay for the old caller.
- Open and click timestamps. `prospects` carries only the `engagement` state.
  The migration adds `prospects.opened_at` and `prospects.clicked_at` (first
  occurrence), written by the Brevo webhook beside `engagement`, so the status
  route reads columns and never calls Brevo.
- Templates: the five Intro Connect drip rows are rewritten, one angle each,
  every step naming the event and date in the subject and carrying
  `{{claim_url}}` and `{{unsubscribe_url}}`:
  1. The built event and the claim link. Guests keep the relationships they made
     in the room. `{{series_line}}` when there is more than one event.
  2. Short nudge. The directory is waiting, two minutes to upload the list, the
     first one is on us.
  3. Attendance. The event is put in front of Intro Connect attendees nearby who
     fit it, and guests who have been to an Intro Connect event before join in
     one tap. States the mechanism, never a number; `{{nearby_attendees}}`
     renders only when the real count is above a floor the builder sets, else
     the sentence is dropped.
  4. Proof for the host. The morning-after recap: who joined, who connected,
     survey replies, the thing they show the next sponsor or venue.
  5. The deadline. Event in `{{time_until_event}}`, the link expires after the
     event, the first one is on us.
  The LinkedIn note and follow-up mirror step 1 only. Written as a migration
  that inserts new inactive rows (never overwrites an edited row); Scott reads
  and test-sends each in `/dashboard/project-templates`, then activates. Copy
  voice: plain, no dashes, no emoji, no calendar links, no Revel, and never the
  `.com` lookalike of the brand domain (the real one is `signal-scout.email`).
- Claim and reply stop the drip. New bearer route
  `POST /api/intro-connect/claimed` `{ lead_id, prospect_id, email }` sets
  `replied_at`, marks the remaining Intro Connect sequences `skipped`, and writes
  a `claimed` event on the prospect. A human reply already does this through the
  existing reply handling.
- Status back to Jimbo Connect: `GET /api/intro-connect/status?prospect_ids=…`
  (bearer) returns per prospect `{ sent_at, opened_at, clicked_at, replied_at,
  bounced_at, unsubscribed_at, next_step_at }`, paginated. Jimbo Connect polls it
  nightly for every approved lead not yet claimed or archived, and fills the
  funnel fields. One direction of secrets, which already exists.
- Release: `ic_release_per_window` stays the only throttle. Suggested starting
  value when turned on: 10 per window, raised with the ramp check.

### 4. The claim flow (Jimbo Connect)

`GET /claim/<token>`: look up the hashed token; if valid and unexpired, log the
host in (reuse the magic-login mechanics), mark the lead `claimed` with
`claimed_at`, call Signal Scout's `claimed` route, and land on the event page
with the attendee upload box open and a one-line banner: "This event was set up
for you. Add your attendee list to go live." An expired or unknown token shows a
plain page with a contact link. A token works any number of times until expiry
(the host may come back from a second device); only the first use writes
`claimed_at`.

The host sees their event as any host does. Billing is unchanged: this event is
their free one, and starting a second one hits the existing plan limit and
Checkout.

### 5. LinkedIn (fully automated, Scott's account)

Tool: **Linked Helper**, Standard plan, about $15 a month (cheapest tool whose
plan includes campaigns, a CRM export and integration hooks; Octopus CRM is
cheaper but has no way to read replies back on its low tiers). Desktop app on
Scott's PC, logged into Scott's LinkedIn account. Scott installs and logs in by
hand; nothing in the code touches LinkedIn directly.

- Jimbo Connect exposes `GET /api/admin/event-leads/linkedin-queue.csv`
  (admin cookie): approved leads with a LinkedIn URL, not yet exported, with the
  rendered message (connection note under 300 characters, then a follow-up
  message after accept, both naming the event and carrying the claim link).
  Export marks each lead `linkedin_exported_at`.
- Linked Helper campaign: visit, invite with note, message after accept, stop on
  reply. Daily caps 20 and 20.
- Results come back by Linked Helper's export (CSV) or its webhook if the Standard
  plan has it (builder verifies on the vendor's current plan page; CSV is the
  fallback). Jimbo Connect accepts `POST /api/admin/event-leads/linkedin-results`
  (CSV upload in the panel, or the webhook with a secret) and sets
  `linkedin_status` to `invited`, `connected`, `replied` or `failed` with
  timestamps.
- The weekly scheduled task does the export and, when the tool has no webhook,
  the result import, as part of its run.

### 6. The host is the star (Jimbo Connect)

Intro Connect is plumbing. Everything an attendee receives comes from their host.

- **Sender.** Every attendee email for an event goes out with the host's name as
  the display name, "Jane Doe via Intro Connect", on the Intro Connect sending
  address (the host's own domain cannot sign our mail), with reply-to set to the
  host. Replies go to the host, never to us.
- **Headshot and name at the top of every attendee email, for every plan.** The
  host's profile photo (`photo_url`) and name render in the email header through
  the existing `email_layout.render` brand slot. Logo and accent color stay the
  Pro feature as built.
- **The claim page asks for the photo.** One optional step after the attendee
  upload: "Add your photo so your guests see you, not us." Skippable.
- **Intro Connect appears once, in the footer**, with the attendee's own sign-in
  link. That footer is the only door through which an attendee becomes our user.
- **Subjects lead with the event name**, host side and attendee side.
- **Per-host template overrides** (`host_templates.py`) cover every attendee
  email added here, so a host can rewrite the wording and it still goes out in
  their name.

### 7. Attendee rules (Jimbo Connect)

Attendees are the host's customers, not ours, until they activate.

- **Imported, not yet active.** An uploaded guest shows in that one event's
  directory right away with the name, role and company the host supplied, marked
  "not yet active" so others know a message reaches them by email. They 
  appear in the cross-event directory (opt-in per event, and they opted into
  nothing). The invite carries a "remove me" link, since the host put them
  there, not us. The platform sends them nothing beyond the host's invite and
  the two existing reminders, which are capped at the day before the event.
- **A message to an inactive attendee is their activation email.** Sent in the
  host's name within a minute of the message: subject "Denver Tech Mixer: Marcus
  from Ramble Labs sent you a message"; body with the sender's first name,
  company, role and headshot, the event name and date, and one button that
  signs them in to read it. Nothing from the message itself. Rules: only when a
  real message exists, never manufactured; one email per sender per day, and a
  second message from the same sender waits for a reply; two senders inside an
  hour share one email naming both.
- **LinkedIn for attendees** is a button, not an automation. If the import or
  the profile carries a LinkedIn URL, show it; the requester clicks and sends
  the connection themselves. The platform never sends a LinkedIn connection on
  an attendee's behalf (see the decision on 2026-10-21 in conversation).
- **Returning attendees.** Accounts are already one per email across events. A
  guest already on Intro Connect gets a one-click join from a new host's
  invite, profile pre-filled, no password; the host's import result says "14 of
  your 80 guests are already on Intro Connect." A profile belongs to the
  attendee and a host sees it only inside their own event after the guest
  joins; an import never reveals that a guest attended someone else's event.
  Built in the second project (see Later), named here so the import keeps the
  data it needs.

### 8. Tracking

Per lead, in `event_leads`: `found_at`, `scored_at`, `approved_at`, `emailed_at`,
`opened_at`, `clicked_at`, `claimed_at`, `attendees_uploaded_at`,
`event_passed_at`, `converted_at`, `linkedin_status` with timestamps, and
`archived_at`. Signal Scout fills the email ones through the status poll; Jimbo
Connect fills the rest from its own events (`attendees_uploaded_at` from
`import_rows` on an event with provenance, `converted_at` from a second event or a
plan change). The click that counts is the claim link, which bots cannot complete,
not a Brevo open.

Weekly run records (`event_lead_runs`): ingested, by tier, with email, with
LinkedIn, verifier checks, spend, errors. The KPI strip reads these plus the
lead timestamps.

## Later (named so nobody builds it now)

- **Second project: the event-anchored attendee sends and the returning-attendee
  experience** (Jimbo Connect only, written as its own design after this ships).
  Four sends anchored to the event date, all in the host's name: the day before
  to everyone invited ("who is in the room tomorrow", with the join link); the
  morning after to everyone who joined ("keep the people you met"); three days
  after to joined attendees who have not answered the host's survey; the day
  after to the host (joined count, saves, survey replies, one line about their
  next event, which is the paid one). Plus the one-click join for returning
  attendees and the "already on Intro Connect" count on import.
- **Marketing to attendees.** See the rules under "Attendee marketing" below.

- More sources and metros. Each is a new file under `sources/`, or a new URL in
  the `ldjson` config, plus a metro in the settings. Checked on 2026-10-21:
  - TechMeetups.io covers 16 cities with the same page shape as Denver, so other
    metros are a config change, not code.
  - Gary's Guide (New York, `garysguide.com`; San Francisco,
    `garysguide.com/events?region=sf`): hand-curated HTML tables, no structured
    data, no feed. Needs its own parser.
  - StartupEvents.org: global conference list, plain HTML, no feed. Conferences
    are mostly C-tier for this pitch; low priority.
  - Luma tech-week directories (`luma.com/sftw`, `luma.com/a16z_SF_Tech_Week`,
    and the `/latw`, `/nytw`, `/atlw`, `/austintw` style paths as a16z publishes
    them): Next.js pages with some `ld+json`, Luma events only, seasonal. The
    `ldjson` source can read them once a tech week is live.
  - Startup Valley (`startupvalley.club`): their own pitch nights in 25 cities, one
    organizer. One lead, not a source.
  - Meetup's tech category directory
    (`meetup.com/lp/tech-activities-and-groups/`): a landing page; Meetup group
    pages are already read by the finder.
  - Built In city sites, GeekWire's Seattle calendar, Cerebral Valley for AI
    events: not checked yet.
- A paid contact lookup to raise the one-in-six email yield.
- Auto-approve turned on.
- SMS. Not in scope.

## Attendee marketing (settled with Scott, 2026-10-21)

Rules, in order of weight:

1. Never to an attendee who has not activated. Host mail only.
2. One Intro Connect-branded email a month at most to any activated attendee:
   "three events near you." Discoverable Intro Connect events first (the host's
   existing per-event switch; a perk offered on the claim page with the first
   free event), matched on the attendee's city and the industry tags of events
   they attended, never on people they met or who else is going. Fewer than
   three on Intro Connect: fill from the public event feed the lead engine
   already ingests, labelled "not on Intro Connect yet" with the public link.
   A "want this on Intro Connect?" tap on a public event writes a host lead
   with source `attendee_request` and a request count; no mail goes to that
   host automatically. A host's event is never recommended to that host's own
   past attendees. Skipped in a month with nothing to say. Its own unsubscribe,
   separate from host mail. The same email carries "your contacts are here"
   and, once, the "be discoverable to other events?" opt-in nudge.
   2a. Cross-host fit. When an activated attendee of Host A's event is a strong
   fit for Host B's discoverable event, the recommendation goes to the attendee
   only. Fit is scored by the same Claude node from the attendee's own profile
   (industry, role, "looking for") plus the city and industry tags of events
   they attended; never from saved contacts or messages. A strong fit for an
   event inside two weeks may send now instead of waiting for the monthly
   email, and that send is the month's one email. Host B sees counts only
   ("shown to 12 attendees nearby, 3 joined") on the event page, free with a
   discoverable event; a name appears to Host B only after the attendee joins.
   Host A is never told. No host ever gets a list, an export, or "find me
   attendees." A Pro boost for recommendations is a later upsell, not built now.
   2b. Opt out, not opt in. Suggestions are on for every activated attendee.
   The promise is printed in the first suggestion email and beside the profile
   toggle: "One email a month at most, only about events near you, never about
   your contacts or messages. We do not like spam either. One tap turns it
   off." The switch is its own, separate from host mail and from
   message-waiting emails, so turning suggestions off never silences a host or
   a person trying to reach them. The first suggestion email goes out only when
   a real match exists.
   2c. Paid events and referral credit. A suggestion shows the price from the
   feed (free or the ticket price). Every suggested link goes through an Intro
   Connect redirect that records the click per attendee and event, and
   Eventbrite links carry Eventbrite's organizer tracking tag so the host sees
   "Intro Connect" as a traffic source on their own dashboard. Payment is 
   observed directly; a referral is confirmed only when the host uploads their
   attendee list and a recommended attendee is on it. The host sees counts on
   the event page (shown, clicked through, and after upload "N of your
   attendees came through Intro Connect"), and a "via Intro Connect" tag beside
   an attendee only once that attendee is on the host's own list; the tag 
   names the event they came from. No referral fee or revenue share in this
   version: the count is the proof line in the morning-after recap and in drip
   step 3 once real. A paid recommendation boost for hosts is the later upsell.
3. Attendees who run events are host leads. An activated attendee whose role or
   company reads like an organizer (founder, community manager, event or
   marketing lead, a Meetup group in their profile) gets one email from Intro
   Connect, "You run events too? The first one is on us", with a claim-style
   link that pre-builds nothing but opens the host signup. One email, no drip,
   and a reply or a click hands them to the host pipeline as a lead with source
   `attendee`.
4. Refer a host. Every activated attendee's profile has a "give a host a free
   event" link. The host who signs up through it is a lead with source
   `referral` and the referrer's id.
5. No paid attendee tier in this version. Attendees are what the host buys.

## Left to the builder

- Exact Mongo field names and the React layout of the panel (use the existing
  admin pages as the pattern).
- The Claude prompt and JSON schema for scoring, and the batch size.
- Token format and hashing for the claim link.
- The Linked Helper CSV column mapping and whether the Standard plan's webhook
  exists today.
- The migration numbers in Signal Scout (next free after the current branch's).
- Test plan: pure rules (tier clamping, cadence clamp, event_passed skip, idempotent
  Approve, claim token expiry) get unit tests first; routes get the walk-the-files
  guard test pattern used by the CRM.
