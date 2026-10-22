# Jimbo Connect

**Post-Event Connection Platform for High-Value Networking**

---

## Overview

Jimbo Connect is a lightweight, event-based platform that helps networking event attendees stay connected after the event ends. Instead of losing valuable connections to forgotten business cards and fading memories, attendees can browse everyone from their event, save contacts, and add private notes for follow-up.

---

## Features

### For Attendees
- **Event Directory** - Browse all attendees from your events in a searchable directory
- **Smart Search & Filters** - Find people by name, company, role, industry, or table/cohort
- **Save Contacts** - Bookmark interesting people and never forget who you met
- **Private Notes** - Add personal notes to remember conversation context
- **Quick Copy** - Instantly copy email, phone, or LinkedIn for follow-up
- **Profile Management** - Create a profile with your photo, bio, and what you're looking for

### For Event Hosts (Admin)
- **Event Creation** - Create events with name, date, location, and industry tags
- **Unique Join Links** - Generate shareable codes for attendees to join
- **Attendee Management** - View all attendees and engagement stats
- **Analytics Dashboard** - Track total users, events, and connections made

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Tailwind CSS, Shadcn/UI |
| Backend | FastAPI (Python) |
| Database | MongoDB |
| Auth | JWT with httpOnly cookies |
| Storage | Emergent Object Storage (for profile photos) |

---

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.11+
- MongoDB

### Installation

**Backend:**
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # Configure your environment variables
python -m uvicorn server:app --reload --port 8001
```

**Frontend:**
```bash
cd frontend
yarn install
cp .env.example .env  # Set REACT_APP_BACKEND_URL
yarn start
```

### Environment Variables

**Backend (.env):**
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=jimbo_connect
JWT_SECRET=your-secret-key-here
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your-admin-password
FRONTEND_URL=http://localhost:3000
```

**Frontend (.env):**
```
REACT_APP_BACKEND_URL=http://localhost:8001
```

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login user |
| POST | `/api/auth/logout` | Logout user |
| GET | `/api/auth/me` | Get current user |
| POST | `/api/auth/refresh` | Refresh access token |
| POST | `/api/auth/forgot-password` | Request password reset |
| POST | `/api/auth/reset-password` | Reset password with token |

### Profile
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/profile` | Get own profile |
| PUT | `/api/profile` | Update profile |
| POST | `/api/profile/photo` | Upload profile photo |
| GET | `/api/profile/{user_id}` | Get user profile |

### Events
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/events` | Create event (admin) |
| GET | `/api/events` | List all events (admin) |
| GET | `/api/events/{id}` | Get event details |
| PUT | `/api/events/{id}` | Update event (admin) |
| DELETE | `/api/events/{id}` | Delete event (admin) |
| POST | `/api/events/join/{code}` | Join event by code |
| GET | `/api/events/{id}/attendees` | Get event attendees |
| GET | `/api/my-events` | Get user's joined events |

### Contacts
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/contacts/save` | Save a contact |
| DELETE | `/api/contacts/{id}` | Remove saved contact |
| GET | `/api/contacts` | Get all saved contacts |
| PUT | `/api/contacts/{id}/note` | Update contact note |
| GET | `/api/contacts/{id}/is-saved` | Check if contact is saved |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/stats` | Get platform statistics |

### Event Leads

The event lead engine finds hosts who run events and gets each one a ready
made Intro Connect event. A weekly sourcing job on Scott's PC posts leads to
the ingest route. An admin approves a lead on `/admin/event-leads` (or
auto-approve does, when a minimum score is set). Approve creates the host
account, the event, a claim link and the Signal Scout push, and Signal Scout
sends the email drip to the host. The host opens the claim link, signs in
without a password, uploads their attendees, and the event goes live under
their name. A nightly poll asks Signal Scout what happened and fills in the
funnel on each lead. Intro Connect itself never mails a prospect. The full
operator steps are in `docs/EVENT-LEADS-OPERATOR.md` and the design is in
`docs/superpowers/specs/2026-10-21-ic-event-lead-engine-design.md`.

**Routes.** Auth column: "admin cookie" is the normal admin login, "ingest key"
is `Authorization: Bearer $EVENT_LEADS_INGEST_KEY`, "tick secret" is the
`X-Tick-Secret` header (the same `BLOG_TICK_SECRET` every tick uses),
"webhook secret" is `?secret=` matching `LINKED_HELPER_WEBHOOK_SECRET`. Every
secret route fails closed: with its env var unset it answers 401 to everyone.

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/admin/event-leads/ingest` | ingest key | Weekly job posts `{run, leads}`; returns `inserted`, `updated`, `unchanged`, `existing_customer`, `auto_approved` |
| GET | `/api/admin/event-leads` | admin cookie | Lead list (`show_c` includes tier C), KPI strip, settings |
| GET | `/api/admin/event-leads/{id}` | admin cookie | One lead with the email and LinkedIn previews |
| POST | `/api/admin/event-leads/{id}/approve` | admin cookie | Approve; idempotent, 409 while another Approve runs |
| POST | `/api/admin/event-leads/{id}/retry-outreach` | admin cookie | Re-run the Signal Scout push for an approved lead |
| POST | `/api/admin/event-leads/{id}/archive` | admin cookie | Archive a lead (kills its claim link) |
| POST | `/api/admin/event-leads/{id}/unarchive` | admin cookie | Restore the status it had before |
| PUT | `/api/admin/event-leads/{id}/contact` | admin cookie | Edit name, email, LinkedIn URL |
| PUT | `/api/admin/event-leads/{id}/score-override` | admin cookie | Set a 0 to 100 score override |
| GET | `/api/admin/event-leads/settings` | admin cookie | `auto_approve_min_score` (null = off) |
| PUT | `/api/admin/event-leads/settings` | admin cookie | Set or clear the auto-approve minimum |
| GET | `/api/admin/event-leads/linkedin-queue.csv` | admin cookie | Linked Helper queue CSV; marks leads exported unless `dry_run=true`; `include_exported=true` re-sends; skip count in the `X-Linkedin-Skipped` header |
| POST | `/api/admin/event-leads/linkedin-results` | admin cookie | Campaign results: CSV file upload (field `file`) or JSON `{rows}`; 2 MB and 5000 rows at most |
| POST | `/api/admin/event-leads/linkedin-webhook` | webhook secret | Linked Helper outgoing webhook; one object or a list; returns `updated`, `unchanged`, `unknown` |
| POST | `/api/event-leads/tick` | tick secret | Nightly Signal Scout status poll (daily 07:00 UTC) |
| GET | `/api/claim/{token}` | public | Preview the claim link; writes nothing, signs nobody in |
| POST | `/api/claim/{token}` | public | Complete the claim: sign the host in, mark the event claimed. Runs only when the host presses "Set up my event"; if the host account existed before Approve, only that account's signed-in session can claim (else 409 `account_exists`) |
| GET | `/api/invites/remove/{token}` | public | Remove-me confirm page for an imported guest; writes nothing |
| POST | `/api/invites/remove/{token}` | public | The confirm button; removes that guest from that event only |
| GET | `/api/public/host-photo/{user_id}` | public | Host headshot bytes for email clients; 404 unless the user hosts an event |

The claim page completes only when the host presses the button, and a host whose
account existed before Approve must be signed in to claim. The message waiting
email buttons open `/magic/:token`, which signs the guest in only when they press
the button. An admin edit to a lead's contact survives later ingests.

The claim routes share one rate limit bucket (10 per IP per 5 minutes). The
remove-me routes allow 30 per IP per hour. Static `/event-leads/...` routes are
declared before `/{id}`; the LinkedIn router is included first in `server.py`
for the same reason.

**Collections.**

| Collection | Holds |
|------------|-------|
| `event_leads` | One lead per organizer (`organizer_key`, unique): anchor event, score, contact, status, `claim_token_hash` and expiry, `signal_scout` outcome, `linkedin` status, `funnel` timestamps |
| `event_lead_runs` | One record per weekly sourcing run, read by the KPI strip |
| `message_notify_state` | One document per recipient per event for message-waiting emails |

New fields on existing collections:

| Collection | Field | Meaning |
|------------|-------|---------|
| `users` | `activated_at` | Set when the person first signs in or joins on their own; unset means "not yet active" |
| `users` | `magic_tokens` | Hashed one-use sign-in tokens (newest kept) for message-waiting emails |
| `users` | `host_origin` | `event_lead` for hosts Approve or the claim page created |
| `events` | `provenance` | `event_lead_id` (unique index when present), `claimed_at`, `pending_host`; an event with an `event_lead_id` and no `claimed_at` stays out of discover |
| `event_attendees` | `activated` | False for a guest the host imported who has not signed in |
| `event_invites` | `removed_at` | Set by the remove-me link; keeps reminders and re-invites off |

**Environment variables** (API service; secrets are `sync: false` in
`render.yaml`, documented in `backend/.env.example`):

| Variable | Used for |
|----------|----------|
| `EVENT_LEADS_INGEST_KEY` | Bearer key the weekly job sends to the ingest route |
| `SIGNAL_SCOUT_URL` | Base URL of Signal Scout; Approve pushes to `{url}/api/intro-connect/import` |
| `SIGNAL_SCOUT_API_KEY` | Bearer key for Signal Scout (its `CRON_SECRET`) |
| `LINKED_HELPER_WEBHOOK_SECRET` | Secret in the Linked Helper webhook URL; optional if results come by CSV upload |
| `BLOG_TICK_SECRET` | Already exists; also guards `/api/event-leads/tick` |
| `FRONTEND_URL` | Already exists; claim links are built on it (through `app_url.APP_URL`) |
| `API_PUBLIC_URL` | Already exists; base for the host photo URL in attendee mail |

**Attendee rules in brief.** Attendees belong to the host until they activate.
An imported guest shows in that one event's directory right away, tagged "not
yet active", and in no cross-event directory. Their invite and the reminders
(none later than the day before the event) carry a remove-me link. The first
message to a not yet active guest sends them one email in the host's name,
within about a minute, naming who wrote and where they met, with one button
that signs them in to read it; nothing from the message text is included. Limits:
one email per sender per Denver day, a second message from the same sender waits
for a reply, and senders inside an hour share one email. The platform never
sends a LinkedIn connection on an attendee's behalf.

---

## User Flows

### Attendee Flow
1. Receive event join link from host
2. Click link → Register/Login
3. Complete profile (name, role, company, photo, etc.)
4. Browse event directory
5. Search/filter to find relevant people
6. Save contacts and add notes
7. Copy contact info for follow-up

### Host Flow
1. Login as admin
2. Create new event with details
3. Copy join link
4. Share link with attendees
5. Monitor attendee signups
6. View engagement stats

---

## Design System

### Colors
- **Light Mode**: White background (#FFFFFF), Blue primary (#2563EB)
- **Dark Mode**: Navy background (#0F172A), Blue primary (#3B82F6)

### Typography
- **Font Family**: Calibri, Segoe UI, system fonts
- **Headings**: Semi-bold (600)
- **Body**: Regular (400)

### Components
- Built on Shadcn/UI component library
- Phosphor Icons (duotone weight)
- Responsive design (mobile-first)

---

## Deployment

The application is configured for deployment on Emergent platform:

- Backend runs on port 8001
- Frontend runs on port 3000
- All API routes prefixed with `/api`
- CORS configured for production URLs

---

## Test Credentials

For development/testing:
- **Admin**: admin@jimboconnect.com / ***REMOVED***

---

## License

MIT License - See LICENSE file for details.

---

## Support

For questions or issues, contact the Jimbo Connect team.
