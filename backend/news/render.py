"""Server-rendered HTML for the public news section. Pure string builders that
take plain dicts and return HTML, mirroring backend/blog/render.py. The single
article carries NewsArticle JSON-LD, a BreadcrumbList, canonical + Open Graph
tags (via pageshell), and a visible source list so every claim is attributable.
"""
import html
from datetime import datetime

import seo
import pageshell


def _esc(text) -> str:
    return html.escape(str(text or ""))


def _fmt_date(value) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%B %d, %Y")
    return str(value)


def _paragraphs(body: str) -> str:
    chunks = [c.strip() for c in (body or "").split("\n\n") if c.strip()]
    return "".join(f"<p>{_esc(c)}</p>" for c in chunks)


def render_index(articles) -> str:
    if articles:
        items = "".join(
            f'<li><a class="title" href="/news/{_esc(a.get("slug"))}">{_esc(a.get("headline"))}</a>'
            f'<div class="meta" style="margin-top:6px">{_esc(_fmt_date(a.get("published_at")))}</div>'
            f'<div class="summary">{_esc(a.get("summary"))}</div></li>'
            for a in articles
        )
        listing = f'<ul class="posts">{items}</ul>'
    else:
        listing = (
            '<div class="empty">No news yet. Check back for updates relevant to '
            "event hosts and the people who network at their events.</div>"
        )
    body = (
        '<div class="wrap">'
        '<nav class="crumbs" aria-label="Breadcrumb">'
        f'<a href="{seo.app_url()}">Home</a> / News</nav>'
        '<div class="eyebrow">Intro Connect news</div>'
        "<h1>News for hosts and networkers</h1>"
        '<div class="summary">Updates and reporting relevant to running events '
        "and keeping the connections that come out of them.</div>"
        f"{listing}</div>"
    )
    ld = seo.breadcrumb_ld([("Home", "/"), ("News", "/news")])
    return pageshell.page(
        "News — Intro Connect",
        body,
        canonical_path="/news",
        description="News and updates for event hosts and networkers, from Intro Connect.",
        extra_head=ld,
    )


def _sources_block(doc: dict) -> str:
    urls = []
    primary = doc.get("source_url")
    if primary:
        urls.append(primary)
    for u in doc.get("sources") or []:
        if u and u not in urls:
            urls.append(u)
    if not urls:
        return ""
    lis = "".join(
        f'<li><a href="{_esc(u)}" rel="nofollow noopener" target="_blank">{_esc(u)}</a></li>'
        for u in urls
    )
    return f'<div class="sources"><h2>Sources</h2><ul>{lis}</ul></div>'


def render_article(doc: dict) -> str:
    headline = doc.get("headline", "")
    summary = doc.get("summary", "")
    slug = doc.get("slug", "")
    sections = "".join(
        f"<h2>{_esc(s.get('heading'))}</h2>{_paragraphs(s.get('body'))}"
        for s in (doc.get("sections") or [])
    )
    published = doc.get("published_at")
    modified = doc.get("modified_at") or published
    news_ld = seo.json_ld(
        {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": headline,
            "description": summary,
            "datePublished": seo.iso(published),
            "dateModified": seo.iso(modified),
            "author": {"@type": "Organization", "name": "Intro Connect"},
            "publisher": {"@type": "Organization", "name": "Intro Connect"},
            "mainEntityOfPage": seo.abs_url(f"/news/{slug}"),
            **({"image": seo.abs_url(doc["image_url"])} if doc.get("image_url") else {}),
        }
    )
    crumb_ld = seo.breadcrumb_ld(
        [("Home", "/"), ("News", "/news"), (headline, f"/news/{slug}")]
    )
    event = doc.get("event_date")
    event_line = (
        f'<div class="meta" style="margin-top:2px">Event: {_esc(event)}</div>'
        if event
        else ""
    )
    body = (
        f'<article class="wrap">'
        '<nav class="crumbs" aria-label="Breadcrumb">'
        f'<a href="{seo.app_url()}">Home</a> / <a href="/news">News</a> / Article</nav>'
        f'<a class="back" href="/news" aria-label="All news">'
        '<span aria-hidden="true">&larr;</span> All news</a>'
        f'<h1 style="margin-top:18px">{_esc(headline)}</h1>'
        f'<div class="meta">{_esc(_fmt_date(published))}</div>'
        f"{event_line}"
        f'<div class="summary">{_esc(summary)}</div>'
        f"{sections}"
        f"{_sources_block(doc)}"
        '<div class="cta"><div>Turn your next event into a directory that keeps '
        'the connections going.</div>'
        f'<a href="{seo.app_url()}">Start for free with Intro Connect</a></div>'
        "</article>"
    )
    return pageshell.page(
        headline + " — Intro Connect",
        body,
        canonical_path=f"/news/{slug}",
        description=summary,
        og_type="article",
        image=doc.get("image_url") or "",
        published=seo.iso(published),
        modified=seo.iso(modified),
        extra_head=news_ld + crumb_ld,
    )


def render_404() -> str:
    body = (
        '<div class="wrap"><h1>Article not found</h1>'
        '<div class="summary">That news item does not exist or is not published yet.</div>'
        '<p style="margin-top:18px"><a href="/news">Browse all news →</a></p></div>'
    )
    return pageshell.page("Not found — Intro Connect", body, canonical_path="/news")
