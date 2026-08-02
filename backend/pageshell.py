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

#: The marketing site's nav and footer, mirrored. These pages are served on the
#: marketing domain, so they must carry the same chrome as the homepage — but
#: the homepage's copy lives in a different deploy artifact (marketing/, its own
#: Render service with its own rootDir), so it cannot be imported. It is
#: mirrored here instead, and `tests/test_nav_consistency.py` fails when the two
#: fall out of step. That test is the only thing keeping them honest.
#:
#: Anchors route through "/" because a blog or news page is not the homepage the
#: sections live on. "/#one-pager" anchors to the section and NOT to the PDF on
#: purpose: the form is the only lead capture the site has.
_NAV_LINKS = (
    ("/#how", "How it works"),
    ("/#features", "Features"),
    ("/#pricing", "Pricing"),
    ("/#one-pager", "One pager"),
    ("/#faq", "FAQ"),
    ("/agenda", "Agenda Builder"),
    ("/blog", "Blog"),
    # News retired 2026-08-02; see marketing/src/components/Nav.jsx.
)

_FOOTER_LINKS = (
    ("/#features", "Features"),
    ("/#pricing", "Pricing"),
    ("/#faq", "FAQ"),
    ("/agenda", "Agenda Builder"),
    ("/blog", "Blog"),
    ("/privacy.html", "Privacy"),
    ("/terms.html", "Terms"),
    ("mailto:hello@intro-connect.com", "Contact"),
)


def _links_html(links) -> str:
    return "".join(f'<a href="{href}">{label}</a>' for href, label in links)


#: Built once. The desktop row and the mobile sheet render the SAME string, so a
#: link can never appear in one and not the other.
_NAV_HTML = _links_html(_NAV_LINKS)
_FOOTER_HTML = _links_html(_FOOTER_LINKS)

_BURGER = (
    '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>'
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
.nav .links a{padding:7px 12px;border-radius:999px;font-size:14px;font-weight:600;color:var(--stone);white-space:nowrap}
.nav .links a:hover{color:var(--ink);background:var(--cream)}
.nav .navcta{display:none;align-items:center;gap:8px}
.btn-ghost{padding:9px 16px;border-radius:999px;font-size:14px;font-weight:600;color:var(--stone);white-space:nowrap}
.btn-ghost:hover{background:var(--cream)}
/* Nav CTA is plain blue text, matching Nav.jsx. A fixed-padding pill cannot
   shrink, so the label wrapped inside it at in-between widths and the button
   rendered as a tall blob. */
.nav-cta{padding:9px 12px;font-size:14px;font-weight:700;color:var(--primary);white-space:nowrap}
/* No !important on the colour. A class already beats the bare `a` rule above on
   specificity, so it was never needed, and it silently defeated `.cta a` (which
   wins the background) leaving white text on a white pill. */
.btn-primary{background:var(--primary);color:#fff;padding:9px 18px;border-radius:999px;font-size:14px;font-weight:700}
.btn-primary:hover{opacity:.92}
/* 1120, not 1024. Measured in a browser with the real webfont loaded: brand 144
   + links 672 + CTAs 191 + two 16px gaps = 1039px of content, so the row needs a
   1087px viewport once the 24px side padding is counted. At 1024 it overflowed
   the moment "One pager" and "Agenda Builder" joined the list. 1120 clears it
   with ~33px to spare and still keeps the full row on a 1152px laptop.
   Re-measure if a link is added: eight is already close to the ceiling.
   Below the breakpoint the sheet takes over — see .menu. Before that existed
   these pages had NO navigation at all under it, just the logo, because this
   shell never had the mobile menu Nav.jsx has. */
@media(min-width:1120px){.nav .links{display:flex}.nav .navcta{display:flex}.menu{display:none}}
/* CSS-only disclosure: this shell is server-rendered with no JavaScript, so the
   mobile menu is a <details>. Same links as the desktop row, same string. */
.menu{position:relative}
.menu summary{list-style:none;cursor:pointer;display:flex;align-items:center;padding:8px;border-radius:10px;color:var(--stone)}
.menu summary::-webkit-details-marker{display:none}
.menu summary:hover{background:var(--cream);color:var(--ink)}
.menu .sheet{display:flex;flex-direction:column;position:absolute;right:0;top:52px;min-width:230px;background:#fff;border:1px solid var(--line);border-radius:14px;padding:8px;box-shadow:0 14px 34px rgba(13,27,42,.13)}
.menu .sheet a{padding:10px 12px;border-radius:10px;font-size:15px;font-weight:600;color:var(--stone)}
.menu .sheet a:hover{background:var(--cream);color:var(--ink)}
.menu .sheet .sep{border-top:1px solid var(--line);margin:6px 0}
.menu .sheet .go{color:var(--primary);font-weight:700}
.wrap{max-width:760px;margin:0 auto;padding:48px 24px 96px}
/* Listing pages need the full container: three tiles do not fit in the 760px
   reading measure that suits an article. */
.wrap.wide{max-width:1120px}
/* Three to a row on a desktop, two on a tablet, one on a phone. auto-fill with
   a minimum rather than a fixed count, so a row of two does not stretch each
   tile across half the page. */
.grid{display:grid;grid-template-columns:1fr;gap:26px;margin-top:34px}
@media(min-width:680px){.grid{grid-template-columns:repeat(2,1fr)}}
@media(min-width:1000px){.grid{grid-template-columns:repeat(3,1fr)}}
.tile{display:flex;flex-direction:column;border:1px solid var(--line);border-radius:16px;overflow:hidden;background:#fff;transition:box-shadow .18s ease,transform .18s ease}
.tile:hover{box-shadow:0 16px 38px rgba(13,27,42,.12);transform:translateY(-2px)}
.tile:focus-within{box-shadow:0 0 0 3px rgba(37,99,235,.35)}
/* aspect-ratio reserves the space before the file arrives, so the text below
   does not jump when it does. Cheaper than carrying intrinsic dimensions for
   every photograph. */
.tile .thumb{display:block;width:100%;aspect-ratio:16/10;object-fit:cover;background:var(--cream)}
.tile .body{padding:18px 20px 22px;display:flex;flex-direction:column;gap:7px;flex:1}
.tile .title{font-size:18px;font-weight:700;letter-spacing:-0.01em;line-height:1.35;color:var(--ink)}
.tile:hover .title{color:var(--primary)}
.tile .summary{font-size:15px;margin:0;color:var(--stone)}
.tile .meta{font-size:11px}
/* The article's own copy of the same photograph, wider than the tile's. */
.hero{display:block;width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:16px;background:var(--cream);margin:22px 0 8px}
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
/* `p,li` sets a colour directly, and a direct rule always beats the colour a
   parent passes down by inheritance, so `.cta`'s white never reached the body
   text and it rendered near-black on the dark panel. Restate it for the panel. */
.cta p,.cta li{color:#d7dee7}
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
        f'<div class="links">{_NAV_HTML}</div>'
        '<div class="navcta">'
        f'<a class="btn-ghost" href="{seo.app_url()}">Log in</a>'
        '<a class="nav-cta" href="/#pricing">Start for free</a>'
        "</div>"
        '<details class="menu"><summary aria-label="Open navigation">'
        f"{_BURGER}</summary><div class=\"sheet\">{_NAV_HTML}"
        '<div class="sep"></div>'
        f'<a class="go" href="{seo.app_url()}">Log in</a>'
        '<a class="go" href="/#pricing">Start for free</a>'
        "</div></details>"
        "</div></nav>"
        f"{body}"
        '<footer class="foot"><div class="in"><div class="row">'
        '<div class="fbrand">' + _MARK + '<div><div class="word">Intro '
        '<span>Connect</span></div><div class="copy">© 2026 Intro Connect</div></div></div>'
        f'<div class="flinks">{_FOOTER_HTML}</div></div>'
        '<div class="tagline">Host better. Connect deeper.</div>'
        "</div></footer></body></html>"
    )
