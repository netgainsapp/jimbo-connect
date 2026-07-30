"""Shared SEO helpers for the server-rendered public sections (blog, news):
canonical/Open Graph/Twitter head fragments, JSON-LD helpers, and the
sitemap.xml + robots.txt builders.

One env var, PUBLIC_CONTENT_URL, is the canonical origin for every public URL
(canonical tags, og:url, JSON-LD, sitemap entries). It defaults to the primary
marketing domain. Set it to whatever domain actually serves /blog and /news so
canonical never points somewhere the content is not (see docs/SEO-NEWS-BLUEPRINT.md).
"""
import html
import json
import os
from datetime import datetime, timezone

from app_url import APP_URL as _CANONICAL_APP_URL

# Canonical origin for all public content URLs. Falls back to the marketing
# domain, then to the legacy BLOG_BASE_URL if that is the only thing set.
def content_base() -> str:
    return (
        os.getenv("PUBLIC_CONTENT_URL")
        or os.getenv("BLOG_BASE_URL")
        or "https://intro-connect.com"
    ).rstrip("/")


def app_url() -> str:
    """Where the product app lives (for CTAs / home links). Delegates to the
    shared canonical resolver so public SEO-facing pages never link out to a
    bare *.onrender.com URL, the same leak already fixed for email links."""
    return _CANONICAL_APP_URL


def _esc(text) -> str:
    return html.escape(str(text or ""), quote=True)


def abs_url(path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{content_base()}/{path.lstrip('/')}"


def iso(value) -> str:
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    return ""


def json_ld(obj: dict) -> str:
    """A safe <script type=application/ld+json> block (escapes < to stop an
    embedded </script> or tag from breaking out)."""
    return (
        '<script type="application/ld+json">'
        + json.dumps(obj, separators=(",", ":")).replace("<", "\\u003c")
        + "</script>"
    )


def head_seo(
    *,
    path: str,
    title: str,
    description: str = "",
    og_type: str = "website",
    image: str = "",
    published: str = "",
    modified: str = "",
) -> str:
    """Canonical + Open Graph + Twitter Card head fragment for a public page.
    `path` is the canonical path (e.g. "/news/some-slug")."""
    url = abs_url(path)
    img = abs_url(image) if image else ""
    parts = [
        f'<link rel="canonical" href="{_esc(url)}"/>',
        f'<meta property="og:type" content="{_esc(og_type)}"/>',
        f'<meta property="og:title" content="{_esc(title)}"/>',
        f'<meta property="og:url" content="{_esc(url)}"/>',
        '<meta property="og:site_name" content="Intro Connect"/>',
        '<meta name="twitter:card" content="summary_large_image"/>',
        f'<meta name="twitter:title" content="{_esc(title)}"/>',
    ]
    if description:
        parts.append(
            f'<meta property="og:description" content="{_esc(description)}"/>'
        )
        parts.append(
            f'<meta name="twitter:description" content="{_esc(description)}"/>'
        )
    if img:
        parts.append(f'<meta property="og:image" content="{_esc(img)}"/>')
        parts.append(f'<meta name="twitter:image" content="{_esc(img)}"/>')
    if published:
        parts.append(
            f'<meta property="article:published_time" content="{_esc(published)}"/>'
        )
    if modified:
        parts.append(
            f'<meta property="article:modified_time" content="{_esc(modified)}"/>'
        )
    return "".join(parts)


def breadcrumb_ld(items) -> str:
    """BreadcrumbList JSON-LD. `items` is a list of (name, path) pairs."""
    return json_ld(
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i + 1,
                    "name": name,
                    "item": abs_url(path),
                }
                for i, (name, path) in enumerate(items)
            ],
        }
    )


# ---------- sitemap.xml ----------

def render_sitemap(entries) -> str:
    """entries: list of dicts {path, lastmod?(datetime|str), changefreq?, priority?}.
    Returns a valid urlset XML document with absolute <loc> on the canonical
    origin."""
    rows = []
    for e in entries:
        loc = abs_url(e["path"])
        row = [f"<loc>{_esc(loc)}</loc>"]
        lastmod = e.get("lastmod")
        if isinstance(lastmod, datetime):
            lastmod = (
                lastmod if lastmod.tzinfo else lastmod.replace(tzinfo=timezone.utc)
            ).date().isoformat()
        if lastmod:
            row.append(f"<lastmod>{_esc(lastmod)}</lastmod>")
        if e.get("changefreq"):
            row.append(f"<changefreq>{_esc(e['changefreq'])}</changefreq>")
        if e.get("priority") is not None:
            row.append(f"<priority>{_esc(e['priority'])}</priority>")
        rows.append("<url>" + "".join(row) + "</url>")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(rows)
        + "</urlset>"
    )


# ---------- robots.txt ----------

def render_robots() -> str:
    """Allow crawling of public content, disallow the API surface, and point at
    the sitemap on the canonical origin."""
    base = content_base()
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        f"Sitemap: {base}/sitemap.xml\n"
    )
