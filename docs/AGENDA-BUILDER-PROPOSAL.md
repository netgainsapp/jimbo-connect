# Agenda Builder — implementation proposal

Free, standalone agenda builder that exports a Word document and converts into
an Intro Connect event. This is a proposal for review, not built code.

Reviewed against the codebase at `deac877`.

---

## 0. Three findings that change the plan

These came out of reading the existing code and are worth settling before any
implementation starts. None of them are reasons not to build it.

### 0.1 The Event model cannot receive most of the handoff data

This is the big one. The spec says "the user should not need to enter the same
information twice," but the current event record has almost nowhere to put that
information.

`EventCreateRequest` (`backend/models.py:112`) accepts exactly four fields:

| Event has today | Agenda Builder collects |
|---|---|
| `name` | event name |
| `date` (a single `datetime`) | start date **and** end date, start/end times |
| `location` (one free-text string) | venue name, address, virtual link |
| `industry_tags` | — |
| — | description |
| — | organizer name, company, email |
| — | event website |
| — | logo |
| — | the agenda itself |

So "carry it into event creation automatically" is not a mapping exercise. Nine
of the twelve collected fields have no column to land in. **Extending the event
model is the actual work here**; the builder UI is the easy half.

Two ways to go, and I recommend the second:

- **A. Extend `events` fully now.** Add every field, migrate, update
  `serialize_event`, `EventPublic`, the directory UI, admin event views. Correct
  end state, but it touches the most heavily used table in the product and drags
  the cross-surface work into what should be a standalone acquisition tool.
- **B. Land the agenda beside the event, extend `events` minimally.** Add only
  `description`, `end_date`, and `agenda_id` to `events`. Everything else stays
  on the agenda document, which the event links to. The event directory can
  render agenda data by following the link. It keeps the free tool decoupled,
  ships sooner, and defers the schema-wide change until you know which fields
  organizers actually fill in.

> **DECIDED (Scott, 2026-07-30): option B, minimal.** `events` gains only
> `description`, `end_date`, `agenda_id`. Accepted tradeoff: event data lives in
> two places until a later consolidation. Revisit once there is real usage data
> showing which fields organizers actually fill in.

### 0.2 The conversion CTA will 403 for a large share of its audience

`FREE_EVENT_LIMIT = 1` (`backend/billing.py:20`). `create_event` raises a 403
with "Your free plan includes 1 event. Upgrade to host more."

So the funnel is: free tool → polished agenda → "Create Your Event" → hard
paywall, for any free user who already has one event. That is the single worst
place in the flow to hit a wall, because the user has just done real work.

Note `BILLING_ENFORCED` (default `"true"`) currently gates this globally — worth
confirming its live value on Render, since if enforcement is off today the wall
is invisible in testing and appears the moment you turn billing on.

> **DECIDED (Scott, 2026-07-30): warn before they build.** Detect the at-limit
> state up front and surface the upgrade path *before* the user invests effort,
> rather than letting them hit a 403 after doing real work.

What that actually means in practice, because the scope is narrower than it
first appears:

- **Anonymous visitors are unaffected and cannot be warned.** They have no
  account, so there is no limit to read. They also do not need warning: a newly
  registered account has zero events, so their first conversion always succeeds.
- **The warning targets exactly one group** — signed-in users already at their
  limit. That is the only case where the wall can fire.
- **The warning must not block building or exporting.** The Word download is the
  free promise of this tool and stays unconditional for everyone, at limit or
  not. Only the "Create Your Event" step is gated. A user at their limit should
  still get a polished agenda document; they just learn early that publishing it
  into an event needs an upgrade.

Data source: `GET /api/billing/status` already exists
(`backend/routers/billing.py:20`) and returns `plan` and `event_limit`
(`null` = unlimited). It does **not** return how many events the user hosts, so
either add `events_hosted` to that response (one line, and cheaper than the
alternative) or count client-side from `GET /api/my-hosted-events`. Recommend
the former.

Placement: a notice on the `/agenda` landing page and a persistent,
non-blocking banner at the top of the builder for at-limit signed-in users,
linking to `/upgrade`.

Still worth confirming `BILLING_ENFORCED` on the `jimbo-connect-api` service.
The variable **is set** (confirmed on the Render dashboard) but its value is
masked. If enforcement is currently off, the wall is invisible in testing today
and appears the moment billing is switched on — so the warning path needs to be
built and tested against `event_limit` regardless of what the flag reads now.

### 0.3 The event logo collides with a Pro feature

Host logo already exists as **Pro-gated branding** (`backend/branding.py`, logo
stored on the user, served from `/api/branding/{id}/logo.png`).

The Agenda Builder needs a logo from anonymous free users. If we reuse the
branding logo we either gate a free tool behind Pro or hand out a paid feature.

Keep them separate: the agenda logo is a **per-agenda asset used only in the
exported document**, not the branding logo, and it does not style event pages.
Reuse `branding.process_logo()` as a *function* (it is good, hardened image
sanitation) without reusing the Pro storage or entitlement path.

---

## 1. Route and component structure

The app shell is auth-gated: `App.jsx` sends `/` to `/login` when logged out,
and every route except `/login`, `/register`, `/forgot-password`,
`/reset-password/:token`, `/join/:code` is wrapped in `RequireAuth`.

The builder must sit **outside** `RequireAuth`, alongside `/join/:code`, which is
the existing precedent for a public page inside the app shell.

```
frontend/src/pages/
  AgendaBuilder.jsx        # the tool: details + items + preview, autosaving
  AgendaLanding.jsx        # free-tool marketing entry, "Start building"

frontend/src/components/agenda/
  AgendaDetailsForm.jsx    # event details, progressive disclosure
  AgendaItemRow.jsx        # one item: edit / delete / duplicate / drag handle
  AgendaItemEditor.jsx     # add-or-edit form for a single item
  AgendaDayGroup.jsx       # a date heading plus its items
  AgendaPreview.jsx        # live preview, mirrors docx layout
  AgendaExportBar.jsx      # download + conversion CTA

frontend/src/hooks/
  useAgendaDraft.js        # state, autosave, localStorage <-> API
```

Routes to add in `App.jsx`, unwrapped:

```jsx
<Route path="/agenda" element={<AgendaLanding />} />
<Route path="/agenda/new" element={<AgendaBuilder />} />
<Route path="/agenda/:id" element={<AgendaBuilder />} />   // authed drafts
```

Design system: no component library to adopt — the frontend runs four runtime
deps (`react`, `react-dom`, `react-router-dom`, `lucide-react`) and Tailwind with
custom tokens in `tailwind.config.js` (`primary #2563EB`, `text-primary`,
`text-muted`, `rounded-card`, `shadow-card`, Calibri stack). Build from those
tokens and the existing `Modal.jsx` / `Avatar.jsx` primitives. Do not introduce
shadcn or a UI kit for this.

**One caveat on the public route:** `Nav.jsx` and `Footer.jsx` in `frontend/` are
the *app* chrome, which differs from the marketing chrome on intro-connect.com.
A free acquisition tool linked from marketing should probably wear marketing
chrome, or at least a stripped nav with a "Log in" affordance. Worth deciding.

---

## 2. Data model and database changes

MongoDB via motor; collections are declared as module-level handles in
`backend/database.py`. Add one:

```python
agendas = db["agendas"]
```

**Embed items, do not split them into a second collection.** Your suggested
structure has `AgendaItem` with an `agendaId` foreign key, which is relational
thinking. In Mongo, agenda items are always read and written with their parent
and are never queried independently, so embedding gives:

- atomic autosave in a single `update_one` (no partial-write states),
- ordering for free from array position, killing the `sortOrder` bookkeeping,
- one round trip to load the builder.

```python
# agendas
{
  "_id": ObjectId,
  "user_id": ObjectId | None,       # None only for a server-side anon draft
  "event_name": str,
  "description": str,
  "start_date": datetime,
  "end_date": datetime | None,
  "start_time": str,                # "09:00", local wall time, not UTC
  "end_time": str,
  "venue_name": str,
  "venue_address": str,
  "virtual_url": str,
  "organizer_name": str,
  "organizer_company": str,
  "organizer_email": str,
  "event_website": str,
  "logo": bytes | None,             # sanitized PNG, same as branding
  "logo_updated_at": datetime | None,
  "status": "draft" | "exported" | "converted",
  "event_id": ObjectId | None,      # set once converted
  "items": [
    {
      "id": str,                    # uuid4, client-generated, stable for DnD keys
      "date": datetime,
      "start_time": str,
      "end_time": str,
      "title": str,
      "description": str,
      "location": str,
      "speaker": str,
      "external_url": str,
      "notes": str
    }
  ],
  "created_at": datetime,
  "updated_at": datetime
}
```

Times as `"HH:MM"` strings, deliberately. An agenda is wall-clock local to the
venue; storing them as UTC datetimes invites the classic bug where a 9am session
renders as 4pm for a viewer in another timezone.

Indexes: `user_id`, and `event_id` sparse.

Event changes, per option B above: add `description`, `end_date`, `agenda_id`.

---

## 3. Word export approach and library

**Recommendation: `python-docx` on the backend.** Add `python-docx==1.1.2` to
`backend/requirements.txt`.

Why backend rather than client-side:

- It produces a genuine `.docx` (Open XML), so it stays **editable** after
  download, which is an explicit requirement.
- The logo is already server-side and already sanitized by Pillow, which the
  backend has (`Pillow==11.0.0`). Client-side export would need the raw image
  back in the browser.
- The frontend is deliberately tiny — four runtime dependencies. The `docx` npm
  package plus its zip/stream deps would be the largest thing in the bundle, and
  paid for by every visitor, not just those who export.
- One endpoint serves anonymous and authenticated users identically.

Rejected: writing HTML and serving it as `.doc`. It opens in Word but is not a
real Word file — styles degrade, images often break, and "polished and
professional" is exactly what this approach fails at.

New module `backend/agenda/`, mirroring how `blog/` and `news/` are structured
(`store.py` + `render.py` + schema, router in `routers/`):

```
backend/agenda/
  __init__.py
  schema.py     # pydantic models, validation
  store.py      # mongo reads/writes
  docx.py       # build_docx(agenda) -> bytes
backend/routers/agenda.py
```

Document layout: logo (scaled to a max width, centered), event name as Heading 1,
date range and venue line, description paragraph, then per day a Heading 2 date
followed by a session table (time | title+description+speaker | room), organizer
block, and a small footer — "Agenda created with Intro Connect / intro-connect.com".
A real Word table rather than tab-aligned text, so it survives editing.

Streamed back as `StreamingResponse` with
`application/vnd.openxmlformats-officedocument.wordprocessingml.document` and a
`Content-Disposition` filename derived from a slugified event name.

---

## 4. Anonymous and authenticated save flows

`backend/auth.py` has `get_current_user` and `get_current_admin` only — there is
**no optional-user dependency**, so an "authed or not" endpoint needs a small new
`get_current_user_optional` that returns `None` instead of raising.

**Anonymous users should not get database rows.** Recommended split:

- **Anonymous:** the draft lives in `localStorage` under one key, autosaved on
  change (debounced). Export is a **stateless** `POST /api/agenda/export` that
  takes the whole agenda as JSON and streams back the `.docx`. Nothing persists.
  No orphan-row cleanup, no anonymous session plumbing, no abuse surface beyond
  rate limiting the endpoint.
- **Authenticated:** the same draft syncs to the `agendas` collection via
  `PUT /api/agenda/{id}`, debounced autosave.

**Preserving the draft across signup** — the requirement that the agenda survives
if the user registers midway. Because the draft is in `localStorage` and
registration is a normal in-app navigation, it simply persists. On successful
auth, `useAgendaDraft` sees a local draft with no server id and POSTs it once to
claim it, then clears the local copy. No token juggling, no server-side anonymous
records to reconcile.

Endpoints:

```
POST   /api/agenda/export      # anonymous or authed, stateless, returns .docx
POST   /api/agenda             # authed: claim/create
GET    /api/agenda             # authed: list my agendas
GET    /api/agenda/{id}        # authed: load
PUT    /api/agenda/{id}        # authed: autosave
DELETE /api/agenda/{id}
POST   /api/agenda/{id}/logo   # authed: upload
POST   /api/agenda/{id}/convert  # authed: create the event from this agenda
```

---

## 5. Transferring agenda data into event creation

On "Create Your Event":

1. Not signed in → route to `/register?next=/agenda/convert`. The draft stays in
   `localStorage` and is claimed on first authenticated load (section 4).
2. Signed in → `POST /api/agenda/{id}/convert`, which server-side builds the
   `EventCreateRequest` from the agenda, reusing the existing creation path
   (join-code generation, plan check) rather than duplicating it, then writes
   `agenda.event_id` and `event.agenda_id` and flips status to `converted`.

Doing the mapping server-side in one call matters: it keeps join-code uniqueness
and the billing check in exactly one place, and means the client never has to
re-send data it already stored.

Field mapping, given option B:

| Agenda | Event |
|---|---|
| `event_name` | `name` |
| `start_date` + `start_time` | `date` |
| `end_date` | `end_date` *(new)* |
| `description` | `description` *(new)* |
| `venue_name` + `venue_address`, else `virtual_url` | `location` |
| everything else | stays on the agenda, reachable via `agenda_id` |

Per the decision in 0.2, the 403 should never be how an at-limit user finds out.
The builder checks `event_limit` against the hosted count on load and warns then.
Keep the server-side 403 anyway as the backstop — the client warning is a UX
courtesy, not an authorization boundary, and `create_event` must stay the single
place the limit is actually enforced.

---

## 6. Security, validation, file upload

- **Unauthenticated docx generation is the main new risk.** `/api/agenda/export`
  does CPU and memory work for anyone on the internet. Guard it with the existing
  `rate_limit.guard` (already used in `routers/branding.py`, `auth.py`, `events.py`),
  keyed by IP for anonymous callers. Cap items per agenda (300 is generous) and
  cap total request body size; reject oversized payloads before parsing.
- **URL fields are the sharpest edge.** `external_url`, `virtual_url`, and
  `event_website` become clickable hyperlinks inside a document that gets emailed
  around. Allow `http`/`https` only, and reject `javascript:`, `data:`, `file:`
  outright. This is more important here than in normal web output, because the
  artifact travels outside the browser's protections.
- **Logo upload:** reuse `branding.process_logo()` — it re-encodes through Pillow,
  strips metadata, caps dimensions, and sets `Image.MAX_IMAGE_PIXELS` against
  decompression bombs. Read at most `cap + 1` bytes so a huge upload is rejected
  without buffering, matching the existing branding hardening. Raster only.
- **Validation:** Pydantic `Field(max_length=...)` on every string, consistent
  with `models.py`. Server-side enforcement of end-after-start; overlap detection
  is a **client-side warning only**, per spec, and must not reject the write.
- **Ownership:** every `/api/agenda/{id}` route must confirm
  `agenda.user_id == user["_id"]`. Compare as strings — `_can_manage_event` was
  fixed for exactly this ObjectId-vs-string mismatch, and the same trap applies.
- Strip control characters from text before it reaches `python-docx`.

---

## 7. Phased implementation plan

**Phase 1 — export path, anonymous only.** `backend/agenda/` module, schema and
validation, `docx.py`, stateless `POST /api/agenda/export` with rate limiting.
Builder page with event details, add/edit/delete/duplicate items, day grouping,
live preview, localStorage autosave, reorder via up/down controls. Download works
end to end. *Ships a complete, useful free tool with no database changes at all.*

**Phase 2 — drag and drop.** Add `@dnd-kit/core` + `@dnd-kit/sortable`. Note the
tradeoff: native HTML5 drag events are free but effectively broken on touch, and
this tool has to work on a phone. `@dnd-kit` has proper pointer/touch sensors and
keyboard accessibility. Keep the Phase 1 up/down controls as the accessible path.

**Phase 3 — accounts.** `agendas` collection, `get_current_user_optional`, CRUD
plus autosave, logo upload, claim-on-signup.

**Phase 4 — conversion.** Per the decisions above: `events` gains only
`description`, `end_date`, `agenda_id` (option B); `/convert` endpoint;
post-export CTA screen; `events_hosted` added to `GET /api/billing/status`; and
the at-limit warning on the landing page and builder for signed-in users, which
never blocks building or exporting. `create_event`'s 403 stays as the
server-side backstop.

**Phase 5 — surfacing.** Render the agenda inside `EventDirectory`, link the tool
from marketing, add `/agenda` to the sitemap. This is where the SEO value lands,
since a free tool page is far more linkable than the app.

Each phase is independently shippable. Phase 1 alone is a real product.

Testing: backend suite is 261 tests and green; `backend/tests/route_inventory.json`
is a route snapshot that **must be regenerated** when routes are added, and
`test_route_auth` needs the anonymous export route explicitly allowlisted, the
same way the public branding logo route was.
