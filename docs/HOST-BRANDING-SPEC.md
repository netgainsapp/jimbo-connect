# Host Branding (Pro feature) — Spec

Status: BUILT AND LIVE (2026-07-17, `aec20c9` + hardening follow-ups). The
paid happy path is proven by the opt-in e2e suite: `E2E_PRO_FLOW=1` in e2e/
runs a real test-mode Stripe checkout and verifies branding end to end.
Not white-label: Intro Connect stays visible everywhere; the host's brand
rides on top of it.

## What a Pro host gets

- Upload a **logo** and pick one **accent color**.
- Both propagate automatically to every surface scoped to that host's events:
  - Event directory pages for their events (header logo, accent on primary
    buttons and pills).
  - The public join page for their join codes.
  - Guest emails about their events (invitation, invite reminders, day-of,
    invite-request notifications): host logo in the header row, accent on the
    button.
- Platform emails (password reset, verify, billing, nurture) and global app
  chrome stay 100% Intro Connect. A host's brand can never touch another
  host's surface or the platform shell, which is what makes zero-approval
  self-serve safe.
- Every branded surface keeps a small "via Intro Connect" mark (footer in
  emails, subtle line on directory pages). Removing it is not offered.

## Plan gating

- Available on **pro** only (and platform admin). `starter` and `free` see the
  settings card with a lock state and a "See plans" link to /upgrade.
- Enforcement server-side in the branding endpoints via the same
  `billing.plan_of(user)` used for event limits.
- **Downgrade behavior (automatic, no cleanup):** branding stays stored but
  goes dormant; all surfaces render platform defaults. Re-upgrade re-activates
  it. No admin action, no data loss.

## Why no human review is needed (automated guardrails)

1. **Raster only**: accept PNG/JPEG/WebP uploads, max 1 MB. SVG rejected
   outright (script risk).
2. **Server re-encode**: Pillow opens, validates it decodes as a real image,
   strips all metadata, resizes to fit 512x512, re-encodes to PNG. Whatever
   was in the file, only clean pixels survive.
3. **Blast radius**: logos render only on the host's own event surfaces, at
   fixed sizes, next to Intro Connect chrome. A hostile or ugly logo defaces
   only that host's own event.
4. **Accent color**: strict `#RRGGBB` validation. Contrast is handled
   automatically: if white text on the accent is below WCAG 4.5:1, the server
   derives and stores a darkened variant used for buttons/text while the raw
   accent is used for decorative fills. No taste gate, no rejects, no support
   tickets.
5. **Kill switch (response tool, not a gate)**: admin `DELETE
   /api/admin/branding/{user_id}` clears a host's branding and sets
   `branding_locked: true` so they cannot re-add without admin clearing the
   flag. For abuse response only.

## Data model

On the `users` document (host accounts):

```
branding: {
  accent: "#RRGGBB",          # raw pick
  accent_dark: "#RRGGBB",     # derived, contrast-safe for text/buttons
  logo: Binary,               # processed PNG bytes (<=100 KB typical)
  logo_updated_at: datetime,
}
branding_locked: bool          # admin kill switch, default absent/false
```

Logos live in Mongo (Atlas M0 is fine: 512px PNG is tens of KB; even 1,000
hosts is ~50 MB worst case). No new storage service, no new env vars, no new
infra. If logo volume ever matters, migration to object storage is internal
and invisible to hosts.

## API

- `GET  /api/branding` — own branding config (plan-aware: includes `active`).
- `PUT  /api/branding` — `{accent}`; validates, derives `accent_dark`.
- `POST /api/branding/logo` — multipart upload; validate/re-encode/store.
- `DELETE /api/branding` — reset own branding to defaults.
- `GET  /api/branding/{user_id}/logo.png` — public, serves processed bytes,
  `Cache-Control: public, max-age=3600`, 404 if none/dormant/locked.
- `DELETE /api/admin/branding/{user_id}` — kill switch (+`branding_locked`).
- All host endpoints 403 with an upgrade message when plan is not pro.

## Rendering

### App

- `serialize_event` gains `host_branding: {logo_url, accent, accent_dark} | null`
  (null unless the host's branding is active).
- EventDirectory and JoinEvent: when present, show host logo in the event
  header and apply accent to primary buttons/pills via inline CSS custom
  properties (`--host-accent`, `--host-accent-dark`) scoped to that page
  container. Everything else keeps platform tokens.
- Profile page gets a "Your brand" card (Pro): logo upload, color input with
  live preview of a button + directory header, reset link. Locked state for
  free/starter with the upsell link.

### Email

- `email_layout.render(...)` gains optional `brand={"logo_url", "accent"}`;
  default None renders exactly today's platform layout (existing tests prove
  no regression).
- With brand: header row = host logo (34px, from logo_url) + existing
  Intro Connect wordmark kept at right as "via Intro Connect"; button
  background uses `accent_dark`.
- Only event-scoped sends pass `brand` (invites.py sends, admin bulk-import
  invitation, invite-request notification in events.py). Everything else
  unchanged.
- Email clients cache remote images; logo URL gets `?v=<logo_updated_at ts>`.

## Copy (brand voice: no dashes, no emoji)

- Card title: "Your brand" / sub: "Your logo and color on your event pages
  and guest emails."
- Locked: "Pro hosts can put their own logo and color on event pages and
  guest emails." + "See plans"
- Upload errors: "That file is too large. Logos can be up to 1 MB." / "Use a
  PNG, JPEG, or WebP image."

## Tests (all automated)

- Unit: accent validation, contrast derivation (light accent darkens, dark
  accent passes through), plan gate 403s, downgrade dormancy, upload rejects
  (oversize, SVG, non-image, decompression bomb via Pillow limits), re-encode
  strips metadata, kill switch locks re-upload.
- Email: render with brand → logo img + accent button; without brand →
  byte-identical to current layout.
- E2E (live): free user gets 403 + locked card; branding logo URL 404s for
  unbranded host; admin uploads brand → own event directory shows logo and
  accent (admin bypasses plan gate, so no paid checkout needed in CI).

## Build plan (autonomous, ~1 session)

1. Backend: model + endpoints + Pillow processing + tests.
2. email_layout brand param + threaded through event-scoped sends + tests.
3. Frontend: settings card, directory/join rendering, upsell lock state.
4. Full suites + live e2e + screenshot proof; ship via git push (auto-deploy).

Dependencies: add `Pillow` to backend/requirements.txt. No new env vars, no
new services, no Scott actions required anywhere in the build.
