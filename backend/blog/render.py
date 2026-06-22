"""Server-rendered, brand-styled HTML for the public blog. Pure string builders:
they take plain dicts and return HTML, so they are easy to unit test. All
dynamic text is HTML-escaped; the single-post page carries Article JSON-LD.

Surfaced under the marketing domain via a Vercel rewrite (/blog -> this backend).
"""
import html
import json
import os
from datetime import datetime, timezone

BASE_URL = os.getenv("BLOG_BASE_URL", "https://jimbo-connect.vercel.app").rstrip("/")
SITE_URL = os.getenv("FRONTEND_URL", "https://jimbo-connect.vercel.app").split(",")[0].rstrip("/")

_MARK = (
    '<svg viewBox="0 0 64 64" width="30" height="30" aria-hidden="true">'
    '<g fill="#2563EB"><circle cx="18" cy="14" r="7"/>'
    '<path d="M8 28 a4 4 0 0 1 4 -4 h12 a4 4 0 0 1 4 4 v6 h-6 v8 h6 v6 a4 4 0 0 1 -4 4 h-12 a4 4 0 0 1 -4 -4 z"/></g>'
    '<g fill="#0D1B2A"><circle cx="46" cy="14" r="7"/>'
    '<path d="M56 28 a4 4 0 0 0 -4 -4 h-12 a4 4 0 0 0 -4 4 v6 h6 v8 h-6 v6 a4 4 0 0 0 4 4 h12 a4 4 0 0 0 4 -4 z"/></g>'
    "</svg>"
)

_CSS = """
:root{--ink:#0d1b2a;--stone:#51606f;--line:#e4e6ea;--primary:#2563eb;--cream:#f7f8fa}
*{box-sizing:border-box}
body{margin:0;font-family:"Plus Jakarta Sans",system-ui,sans-serif;color:var(--ink);background:#fff;line-height:1.7}
a{color:var(--primary);text-decoration:none}
.nav{border-bottom:1px solid var(--line)}
.nav .in{max-width:760px;margin:0 auto;padding:16px 24px;display:flex;align-items:center;gap:9px}
.brand{font-weight:800;letter-spacing:-0.01em;color:var(--ink)}
.brand span{font-weight:500}
.wrap{max-width:760px;margin:0 auto;padding:48px 24px 96px}
.eyebrow{font-size:12px;font-weight:600;letter-spacing:0.18em;text-transform:uppercase;color:var(--primary)}
h1{font-size:38px;font-weight:800;letter-spacing:-0.02em;line-height:1.1;margin:10px 0 8px}
h2{font-size:22px;font-weight:700;letter-spacing:-0.01em;margin:36px 0 8px}
.meta{color:var(--stone);font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em}
.summary{font-size:19px;color:var(--stone);margin-top:14px}
p,li{font-size:17px;color:#26323f}
.posts{list-style:none;padding:0;margin:32px 0 0}
.posts li{padding:24px 0;border-top:1px solid var(--line)}
.posts a.title{font-size:22px;font-weight:700;letter-spacing:-0.01em;color:var(--ink);display:inline-block}
.posts a.title:hover{color:var(--primary)}
.posts .summary{font-size:16px;margin-top:6px}
.empty{color:var(--stone);background:var(--cream);border:1px solid var(--line);border-radius:12px;padding:28px;text-align:center}
.cta{margin-top:44px;background:var(--ink);color:#fff;border-radius:14px;padding:28px}
.cta a{display:inline-block;margin-top:14px;background:#fff;color:var(--ink);font-weight:700;padding:11px 20px;border-radius:999px}
.foot{border-top:1px solid var(--line);margin-top:64px}
.foot .in{max-width:760px;margin:0 auto;padding:24px;color:var(--stone);font-size:13px;display:flex;gap:18px;flex-wrap:wrap}
.back{font-size:14px;font-weight:600}
"""

_HEAD_FONT = (
    '<link rel="preconnect" href="https://fonts.googleapis.com"/>'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>'
    '<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>'
)


def _esc(text) -> str:
    return html.escape(str(text or ""))


def _fmt_date(value) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%B %d, %Y")
    return str(value)


def _iso(value) -> str:
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    return ""


def _paragraphs(body: str) -> str:
    chunks = [c.strip() for c in (body or "").split("\n\n") if c.strip()]
    return "".join(f"<p>{_esc(c)}</p>" for c in chunks)


def _page(title: str, body: str, *, description: str = "", extra_head: str = "") -> str:
    desc = (
        f'<meta name="description" content="{_esc(description)}"/>' if description else ""
    )
    return (
        "<!doctype html><html lang=\"en\"><head>"
        '<meta charset="UTF-8"/>'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0"/>'
        '<meta name="theme-color" content="#2563EB"/>'
        '<link rel="icon" type="image/svg+xml" href="/favicon.svg"/>'
        f"<title>{_esc(title)}</title>{desc}{_HEAD_FONT}{extra_head}"
        f"<style>{_CSS}</style></head><body>"
        f'<nav class="nav"><a class="in" href="{SITE_URL}">{_MARK}'
        '<span class="brand">Intro <span>Connect</span></span></a></nav>'
        f"{body}"
        '<footer class="foot"><div class="in">'
        "<span>© 2026 Intro Connect</span>"
        '<a href="/blog">Blog</a><a href="/privacy.html">Privacy</a>'
        '<a href="/terms.html">Terms</a>'
        f'<a href="{SITE_URL}">Home</a>'
        "</div></footer></body></html>"
    )


def render_index(posts) -> str:
    if posts:
        items = "".join(
            f'<li><a class="title" href="/blog/{_esc(p.get("slug"))}">{_esc(p.get("title"))}</a>'
            f'<div class="meta" style="margin-top:6px">{_esc(_fmt_date(p.get("published_at")))}</div>'
            f'<div class="summary">{_esc(p.get("summary"))}</div></li>'
            for p in posts
        )
        listing = f'<ul class="posts">{items}</ul>'
    else:
        listing = (
            '<div class="empty">New articles are on the way. '
            "Check back soon for practical advice on building a network that lasts.</div>"
        )
    body = (
        '<div class="wrap"><div class="eyebrow">The Intro Connect blog</div>'
        "<h1>Notes on networking that lasts</h1>"
        '<div class="summary">Practical, specific advice for hosts and the people '
        "who network at their events.</div>"
        f"{listing}</div>"
    )
    return _page(
        "Blog — Intro Connect",
        body,
        description="Practical advice on networking and following up after events, from Intro Connect.",
    )


def render_post(doc: dict) -> str:
    title = doc.get("title", "")
    summary = doc.get("summary", "")
    sections = "".join(
        f"<h2>{_esc(s.get('heading'))}</h2>{_paragraphs(s.get('body'))}"
        for s in (doc.get("sections") or [])
    )
    cta = doc.get("cta", "")
    cta_html = (
        f'<div class="cta"><div>{_esc(cta)}</div>'
        f'<a href="{SITE_URL}">Start for free with Intro Connect</a></div>'
        if cta
        else ""
    )
    ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": summary,
        "datePublished": _iso(doc.get("published_at")),
        "author": {"@type": "Organization", "name": "Intro Connect"},
        "publisher": {"@type": "Organization", "name": "Intro Connect"},
        "mainEntityOfPage": f"{BASE_URL}/blog/{doc.get('slug', '')}",
    }
    json_ld = (
        '<script type="application/ld+json">'
        + json.dumps(ld).replace("<", "\\u003c")
        + "</script>"
    )
    body = (
        f'<article class="wrap"><a class="back" href="/blog">← All articles</a>'
        f"<h1 style=\"margin-top:18px\">{_esc(title)}</h1>"
        f'<div class="meta">{_esc(_fmt_date(doc.get("published_at")))}</div>'
        f'<div class="summary">{_esc(summary)}</div>'
        f"{sections}{cta_html}</article>"
    )
    return _page(title + " — Intro Connect", body, description=summary, extra_head=json_ld)


def render_404() -> str:
    body = (
        '<div class="wrap"><h1>Article not found</h1>'
        '<div class="summary">That post does not exist or is not published yet.</div>'
        '<p style="margin-top:18px"><a href="/blog">Browse all articles →</a></p></div>'
    )
    return _page("Not found — Intro Connect", body)
