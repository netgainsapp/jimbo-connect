# Intro Connect — Technical SEO Audit + `/news` Section Blueprint

Date: 2026-07-10. Scope: marketing site (`intro-connect.com`), server-rendered
`/blog`, and a new `/news` section. Evidence-based; all findings cite exact
files. No traffic/ranking guarantees are made.

## 1. Repository findings (evidence)

| Concern | Finding | Evidence |
| --- | --- | --- |
| Backend | FastAPI (Python 3.12.7), routers split (M13) | `backend/server.py`, `backend/routers/` |
| Marketing site | Vite + React SPA, single landing page, **no client router** | `marketing/src/App.jsx`, `marketing/vite.config.js` |
| Blog | Server-rendered HTML by the backend (pure string builders) | `backend/blog/render.py`, `backend/routers/public.py:35-52` |
| Blog data | MongoDB `blog_post`; fields slug/title/summary/sections/cta/status/published_at | `backend/blog/store.py` |
| Blog schema | `Article` JSON-LD on single post only | `backend/blog/render.py:150-164` |
| Hosting | All 3 services on Render (static marketing + static app + python api) | `render.yaml` |
| Deploy | `git push origin main` → Render autoDeploy | `render.yaml` |

## 2. Business relevance profile

- Business: Intro Connect turns each hosted event into a private, searchable
  attendee directory (save contacts, notes, messaging). Free for guests; paid
  host tiers. Evidence: `marketing/index.html`, `backend/nurture.py` copy.
- Audience: event hosts (primary), event attendees (secondary).
- Commercial pages: `intro-connect.com` (landing + pricing), `app.intro-connect.com`.
- Existing topical authority: networking / event follow-up (the blog voice).
- Suitable news topics: professional networking, event hosting, community
  building, relevant industry/tooling news. Excluded: anything off-brand,
  unverifiable, or purely trend-chasing.

## 3. Technical SEO audit (severity-ranked)

**CRITICAL**
- C1. `intro-connect.com/sitemap.xml` returns the SPA landing HTML with HTTP 200
  and `content-type: text/html` (verified 2026-07-10), not XML. Any path returns
  index.html via the `/*` rewrite (`render.yaml:56-59`). A crawler asking for the
  sitemap gets a web page. Fix: real static `marketing/public/sitemap.xml`
  (existing files bypass the rewrite) + dynamic `GET /sitemap.xml` on the backend.
- C2. No `robots.txt` (`intro-connect.com/robots.txt` → 404, verified). Fix:
  add static robots + backend robots referencing the sitemap.

**HIGH**
- H1. Blog (and future news) is not on the primary domain. `intro-connect.com/blog`
  serves the SPA landing (verified: 1386-byte `id="root"` doc); the real
  server-rendered blog lives only at `jimbo-connect-api-rdkp.onrender.com/blog`.
  The primary-domain proxy (`marketing/vercel.json`) points at the **old orphaned
  backend** `jimbo-connect-api.onrender.com` AND Render ignores `vercel.json`.
  This is the one item requiring a hosting/DNS decision — see §6.
- H2. `backend/blog/render.py:12-13` defaults `BLOG_BASE_URL`/`SITE_URL` to the
  stale `jimbo-connect.vercel.app`. Canonical/JSON-LD `mainEntityOfPage` point at
  a dead domain unless env overrides are set. Fix: default to `intro-connect.com`,
  single configurable content-base var.

**MEDIUM**
- M1. Server-rendered blog pages have **no canonical**, **no Open Graph/Twitter**
  card, no breadcrumbs. `backend/blog/render.py:84-105`.
- M2. Blog `Article` JSON-LD lacks `dateModified`, `image`, `url`. `render.py:150`.
- M3. Blog index has no `CollectionPage`/`ItemList` structured data.
- M4. `marketing/index.html` head lacks canonical, `og:url`, `og:image`,
  Twitter card, and `Organization`/`WebSite` JSON-LD. `marketing/index.html:3-27`.

**LOW / INFORMATIONAL**
- L1. `marketing/vercel.json` is dead config on Render and references a dead
  backend; remove or repoint to avoid confusion.
- L2. Admin welcome-tour UI prints demo credentials as copy (app, not SEO).

Performance/CWV: not measured here; no measurement data is claimed.

## 4. Search intent + architecture

- Blog = informational/evergreen (kept). News = freshness-driven, dated,
  source-attributed. Distinct `@type` (`NewsArticle`) and update cadence justify
  a sibling section rather than folding into the blog.
- URL structure: `/news` (listing), `/news/{slug}` (article). Mirrors `/blog`.

## 5. `/news` section design (mirrors `/blog`)

- `backend/news/schema.py` — `NewsArticle` Pydantic model (headline, summary,
  sections, source_url(s), event_date), `slugify` reuse.
- `backend/news/store.py` — `news_article` collection; create/list_published/
  get_by_slug/list_all/publish/unpublish (mirror `blog/store.py`).
- `backend/news/render.py` — index + article; `NewsArticle` JSON-LD
  (headline, description, datePublished, dateModified, author/publisher
  Organization, mainEntityOfPage, image optional), canonical, OG, Twitter,
  breadcrumbs, visible source attribution + exact dates. HTML-escaped.
- Routes: `GET /news`, `GET /news/{slug}` (`routers/public.py`), edge-cacheable.
- Admin: `GET/POST /api/admin/news/...` mirroring blog admin (list/create/
  publish/unpublish), admin-gated.
- Launches with an empty state (no fabricated articles; content is a separate,
  approval-gated step per the news rules).

## 6. The one decision requiring user input — primary-domain routing

Surfacing `/blog` and `/news` under `intro-connect.com` (best for SEO) needs a
hosting choice, because Render static sites cannot reverse-proxy a subpath to
another service the way Vercel rewrites can:

- Option A (recommended, Render-native): add a branded custom domain to the API
  service (e.g. `read.intro-connect.com` or `blog.intro-connect.com`) and set the
  content-base env var to it. Subdomain SEO is well supported. Needs a DNS record
  + Render dashboard action (yours).
- Option B: move the marketing static site to Vercel so `vercel.json` rewrites
  proxy `/blog` and `/news` to the backend on the **same** primary domain (best
  SEO). Contradicts the deliberate Render rebuild; needs Vercel project + DNS.
- Option C: confirm whether Render now supports external-URL rewrites for static
  sites; if so, add `/blog`+`/news` rewrites in `render.yaml`.

All canonical/sitemap URLs are driven by ONE env var (`PUBLIC_CONTENT_URL`,
default `https://intro-connect.com`) so whichever option is chosen, canonical
points at the real serving domain by changing one value. Until then, content is
correct and live on the API subdomain and the code is routing-agnostic.

## 7. Files expected to change

New: `backend/news/{__init__,schema,store,render}.py`, `backend/seo.py`,
`marketing/public/robots.txt`, `marketing/public/sitemap.xml`, tests
(`test_news_render`, `test_news_store`, `test_seo`), this doc.
Modified: `backend/routers/public.py` (news + robots + sitemap routes),
`backend/routers/admin.py` (news admin), `backend/blog/render.py` (domain +
canonical/OG/JSON-LD), `backend/database.py` (news_article indexes),
`backend/server.py` (re-exports if needed), `marketing/index.html`,
`backend/tests/test_route_auth.py` + `route_inventory.json`.

## 8. Validation

`pytest tests/` (backend), `npx vite build` (marketing), live probes for
`/robots.txt`, `/sitemap.xml` (XML content-type), `/news`, `/news/{slug}`,
JSON-LD presence, canonical correctness.

## 9. Non-goals / honesty notes

- No news articles are fabricated; `/news` ships empty-ready.
- No ranking/traffic/CWV guarantees.
- Primary-domain routing is flagged, not silently migrated.
