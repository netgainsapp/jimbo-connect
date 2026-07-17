# Intro Connect E2E

End-to-end tests that run against a **live deployment** (there is no local
database; the only Mongo instance is prod Atlas). Built with Playwright's API
request context, so they need no browser binary.

## Run

```bash
cd e2e
npm install
npx playwright test                 # full suite against production
E2E_API_URL=https://staging... npx playwright test   # or another environment
```

## What it covers

- `public.spec.js` — read-only, always safe against prod: API health, anonymous
  routes return 401, robots.txt + sitemap, the published news pages + their
  NewsArticle/canonical SEO markup, 404 for unknown slugs.
- `flow.spec.js` — the full networking flow: two users register (cookie-only
  auth), the cross-user authorization gate (opaque 404 before a shared event),
  event create → join → attendee directory, the gate unlocking after the shared
  event, contact save with a private note, messaging, and logout.

## Side-effect discipline

`flow.spec.js` creates real data on the target. It is written to be safe:

- Test accounts use Gmail plus-addressing on the owner's own inbox
  (`sdwbouldah55+e2e-...@gmail.com`) — clean delivery, **no bounces, no
  suppression-list pollution**.
- Everything created is deleted in `afterAll` (event, then both accounts).
- Verified after each run: zero `e2e` accounts remain.

Cold starts: the free-tier API can take ~40s to wake, so the config uses long
timeouts and one retry. A first run against an idle service may be slow; a
second run is fast.
