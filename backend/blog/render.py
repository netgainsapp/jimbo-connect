"""Server-rendered, brand-styled HTML for the public blog. Pure string builders:
they take plain dicts and return HTML, so they are easy to unit test. All
dynamic text is HTML-escaped; the single-post page carries Article JSON-LD, a
BreadcrumbList, canonical + Open Graph tags (via the shared page shell).

Surfaced under the marketing domain via a rewrite (/blog -> this backend). The
canonical origin comes from seo.content_base() (one env var), not a hardcoded
domain.
"""
import html
from datetime import datetime

import seo
import pageshell

from . import images


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


def _tile(p: dict) -> str:
    """One card. The whole tile is the link target rather than just the title,
    because a card whose picture is not clickable reads as broken."""
    slug = _esc(p.get("slug"))
    # Decorative: the headline directly beneath says the same thing, so an alt
    # text here would be read out twice by a screen reader.
    return (
        f'<article class="tile"><a href="/blog/{slug}" style="display:contents">'
        f'<img class="thumb" src="{_esc(images.image_for(p))}" alt="" loading="lazy"/>'
        '<div class="body">'
        f'<div class="meta">{_esc(_fmt_date(p.get("published_at")))}</div>'
        f'<div class="title">{_esc(p.get("title"))}</div>'
        f'<p class="summary">{_esc(p.get("summary"))}</p>'
        "</div></a></article>"
    )


def render_index(posts) -> str:
    if posts:
        listing = f'<div class="grid">{"".join(_tile(p) for p in posts)}</div>'
    else:
        listing = (
            '<div class="empty">New articles are on the way. '
            "Check back soon for practical advice on building a network that lasts.</div>"
        )
    body = (
        # "wide", not the article measure: three tiles do not fit in 760px.
        '<div class="wrap wide">'
        '<nav class="crumbs" aria-label="Breadcrumb">'
        f'<a href="{seo.app_url()}">Home</a> / Blog</nav>'
        '<div class="eyebrow">The Intro Connect blog</div>'
        "<h1>Notes on networking that lasts</h1>"
        '<div class="summary">Practical, specific advice for hosts and the people '
        "who network at their events.</div>"
        f"{listing}</div>"
    )
    return pageshell.page(
        "Blog — Intro Connect",
        body,
        canonical_path="/blog",
        description="Practical advice on networking and following up after events, from Intro Connect.",
        extra_head=seo.breadcrumb_ld([("Home", "/"), ("Blog", "/blog")]),
    )


def render_post(doc: dict) -> str:
    title = doc.get("title", "")
    summary = doc.get("summary", "")
    slug = doc.get("slug", "")
    sections = "".join(
        f"<h2>{_esc(s.get('heading'))}</h2>{_paragraphs(s.get('body'))}"
        for s in (doc.get("sections") or [])
    )
    cta = doc.get("cta", "")
    cta_html = (
        f'<div class="cta"><div>{_esc(cta)}</div>'
        f'<a href="{seo.app_url()}">Start for free with Intro Connect</a></div>'
        if cta
        else ""
    )
    published = doc.get("published_at")
    modified = doc.get("updated_at") or published
    article_ld = seo.json_ld(
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "description": summary,
            "datePublished": seo.iso(published),
            "dateModified": seo.iso(modified),
            "author": {"@type": "Organization", "name": "Intro Connect"},
            "publisher": {"@type": "Organization", "name": "Intro Connect"},
            "mainEntityOfPage": seo.abs_url(f"/blog/{slug}"),
        }
    )
    crumb_ld = seo.breadcrumb_ld(
        [("Home", "/"), ("Blog", "/blog"), (title, f"/blog/{slug}")]
    )
    image = images.image_for(doc)
    body = (
        '<article class="wrap">'
        '<nav class="crumbs" aria-label="Breadcrumb">'
        f'<a href="{seo.app_url()}">Home</a> / <a href="/blog">Blog</a> / Article</nav>'
        '<a class="back" href="/blog" aria-label="All articles">'
        '<span aria-hidden="true">&larr;</span> All articles</a>'
        f'<h1 style="margin-top:18px">{_esc(title)}</h1>'
        f'<div class="meta">{_esc(_fmt_date(published))}</div>'
        # The same photograph as the tile, larger. Eager, not lazy: it is above
        # the fold, and lazy-loading the thing the reader is already looking at
        # just delays it.
        f'<img class="hero" src="{_esc(image)}" alt="" fetchpriority="high"/>'
        f'<div class="summary">{_esc(summary)}</div>'
        f"{sections}{cta_html}</article>"
    )
    return pageshell.page(
        title + " — Intro Connect",
        body,
        canonical_path=f"/blog/{slug}",
        description=summary,
        og_type="article",
        image=image,  # head_seo absolutises it
        published=seo.iso(published),
        modified=seo.iso(modified),
        extra_head=article_ld + crumb_ld,
    )


def render_404() -> str:
    body = (
        '<div class="wrap"><h1>Article not found</h1>'
        '<div class="summary">That post does not exist or is not published yet.</div>'
        '<p style="margin-top:18px"><a href="/blog">Browse all articles →</a></p></div>'
    )
    return pageshell.page("Not found — Intro Connect", body, canonical_path="/blog")
