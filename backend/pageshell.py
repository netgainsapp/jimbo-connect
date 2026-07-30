"""Shared brand chrome for the server-rendered public sections (blog + news).

One page shell so the two sections look identical and both get canonical +
Open Graph + Twitter head tags for free. Pure string builder: takes plain
strings, returns HTML, easy to unit test. All caller-supplied text must be
escaped by the caller (headings/titles); this module escapes what it owns.
"""
import html

import seo

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
.nav{border-bottom:1px solid var(--line);position:sticky;top:0;background:rgba(255,255,255,.85);backdrop-filter:blur(8px);z-index:40}
.nav .in{max-width:1120px;margin:0 auto;padding:0 24px;height:64px;display:flex;align-items:center;justify-content:space-between;gap:16px}
.nav .brandlink{display:flex;align-items:center;gap:9px}
.brand{font-weight:800;letter-spacing:-0.01em;color:var(--ink)}
.brand span{font-weight:500}
.nav .links{display:none;align-items:center;gap:2px}
.nav .links a{padding:7px 12px;border-radius:999px;font-size:14px;font-weight:600;color:var(--stone)}
.nav .links a:hover{color:var(--ink);background:var(--cream)}
.nav .navcta{display:none;align-items:center;gap:8px}
.btn-ghost{padding:9px 16px;border-radius:999px;font-size:14px;font-weight:600;color:var(--stone)}
.btn-ghost:hover{background:var(--cream)}
.btn-primary{background:var(--primary);color:#fff!important;padding:9px 18px;border-radius:999px;font-size:14px;font-weight:700}
.btn-primary:hover{opacity:.92}
@media(min-width:768px){.nav .links{display:flex}.nav .navcta{display:flex}}
.wrap{max-width:760px;margin:0 auto;padding:48px 24px 96px}
.crumbs{font-size:13px;color:var(--stone);margin-bottom:8px}
.crumbs a{color:var(--stone)}
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
.sources{margin-top:40px;padding-top:20px;border-top:1px solid var(--line)}
.sources h2{font-size:15px;text-transform:uppercase;letter-spacing:0.1em;color:var(--stone);margin:0 0 8px}
.sources ul{margin:0;padding-left:18px}
.sources li{font-size:15px;word-break:break-word}
.cta{margin-top:44px;background:var(--ink);color:#fff;border-radius:14px;padding:28px}
.cta a{display:inline-block;margin-top:14px;background:#fff;color:var(--ink);font-weight:700;padding:11px 20px;border-radius:999px}
.foot{border-top:1px solid var(--line);margin-top:64px}
.foot .in{max-width:1120px;margin:0 auto;padding:48px 24px}
.foot .row{display:flex;flex-direction:column;align-items:center;justify-content:space-between;gap:24px;font-size:14px}
.foot .fbrand{display:flex;align-items:center;gap:12px}
.foot .fbrand .word{font-weight:800;letter-spacing:-0.01em;color:var(--ink);line-height:1}
.foot .fbrand .word span{font-weight:500}
.foot .fbrand .copy{font-size:10px;text-transform:uppercase;letter-spacing:0.18em;font-weight:700;color:var(--stone);margin-top:4px}
.foot .flinks{display:flex;align-items:center;gap:20px;flex-wrap:wrap;justify-content:center;color:var(--stone)}
.foot .flinks a{font-weight:600;color:var(--stone)}
.foot .flinks a:hover{color:var(--ink)}
.foot .tagline{margin-top:32px;padding-top:24px;border-top:1px solid var(--line);text-align:center;font-size:10px;text-transform:uppercase;letter-spacing:0.22em;font-weight:800;color:var(--primary)}
@media(min-width:640px){.foot .row{flex-direction:row}}
.back{font-size:14px;font-weight:600}
"""

_HEAD_FONT = (
    '<link rel="preconnect" href="https://fonts.googleapis.com"/>'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>'
    '<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>'
)


def _esc(text) -> str:
    return html.escape(str(text or ""))


def page(
    title: str,
    body: str,
    *,
    canonical_path: str,
    description: str = "",
    og_type: str = "website",
    image: str = "",
    published: str = "",
    modified: str = "",
    extra_head: str = "",
) -> str:
    """Full HTML document with brand nav/footer, meta description, and the
    shared canonical + Open Graph + Twitter head fragment."""
    desc = (
        f'<meta name="description" content="{_esc(description)}"/>'
        if description
        else ""
    )
    seo_head = seo.head_seo(
        path=canonical_path,
        title=title,
        description=description,
        og_type=og_type,
        image=image,
        published=published,
        modified=modified,
    )
    return (
        '<!doctype html><html lang="en"><head>'
        '<meta charset="UTF-8"/>'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0"/>'
        '<meta name="theme-color" content="#2563EB"/>'
        '<link rel="icon" type="image/svg+xml" href="/favicon.svg"/>'
        f"<title>{_esc(title)}</title>{desc}{seo_head}{_HEAD_FONT}{extra_head}"
        f"<style>{_CSS}</style></head><body>"
        # Same chrome as the marketing homepage (Nav.jsx / Footer.jsx): these
        # pages are served on the marketing domain, not the logged-in app, so
        # they share that site's header and footer, not the app's. Anchor
        # links go through "/" first since a blog or news page is not the
        # homepage those sections live on.
        '<nav class="nav"><div class="in">'
        f'<a class="brandlink" href="/">{_MARK}'
        '<span class="brand">Intro <span>Connect</span></span></a>'
        '<div class="links">'
        '<a href="/#how">How it works</a><a href="/#features">Features</a>'
        '<a href="/#pricing">Pricing</a><a href="/#faq">FAQ</a>'
        '<a href="/blog">Blog</a><a href="/news">News</a>'
        "</div>"
        '<div class="navcta">'
        f'<a class="btn-ghost" href="{seo.app_url()}">Log in</a>'
        '<a class="btn-primary" href="/#pricing">Start for free</a>'
        "</div></div></nav>"
        f"{body}"
        '<footer class="foot"><div class="in"><div class="row">'
        '<div class="fbrand">' + _MARK + '<div><div class="word">Intro '
        '<span>Connect</span></div><div class="copy">© 2026 Intro Connect</div></div></div>'
        '<div class="flinks">'
        '<a href="/#features">Features</a><a href="/#pricing">Pricing</a>'
        '<a href="/#faq">FAQ</a><a href="/blog">Blog</a><a href="/news">News</a>'
        '<a href="/privacy.html">Privacy</a><a href="/terms.html">Terms</a>'
        '<a href="mailto:hello@intro-connect.com">Contact</a>'
        "</div></div>"
        '<div class="tagline">Host better. Connect deeper. Build what matters.</div>'
        "</div></footer></body></html>"
    )
