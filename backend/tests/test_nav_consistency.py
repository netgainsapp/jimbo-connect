"""The site header and footer must be identical on every public page.

There are three copies of the nav, and there have to be: the marketing site,
this backend's server-rendered blog/news shell, and the SPA's chrome for public
app pages are three separate Render services with three different rootDirs, so
none of them can import the others. Nothing stops them drifting except this
test.

They already had drifted. "One pager" was added to the marketing nav in PR #64
and to neither of the other two, and "Agenda Builder" was missing from the
blog/news shell — which are the two pages search traffic actually lands on, and
therefore the two pages that were missing the site's only lead capture.

Run from backend/: python -m pytest tests/test_nav_consistency.py
"""
import re
from pathlib import Path

import pageshell

REPO = Path(__file__).resolve().parents[2]
MARKETING_NAV = REPO / "marketing" / "src" / "components" / "Nav.jsx"
MARKETING_FOOTER = REPO / "marketing" / "src" / "components" / "Footer.jsx"
SPA_LINKS = REPO / "frontend" / "src" / "components" / "marketing" / "marketingLinks.js"

#: The SPA is served from app.intro-connect.com, so its links are absolute
#: against the marketing origin. Strip it to compare like with like.
MARKETING_ORIGIN = "https://intro-connect.com"


def _normalize(href: str) -> str:
    """One shape for a link, whatever origin style the copy happens to use.

    The marketing site is *on* the homepage so it writes "#faq"; the blog shell
    is not, so it writes "/#faq"; the SPA is on another host entirely so it
    writes the absolute URL. All three mean the same destination.
    """
    href = href.strip()
    if href.startswith(MARKETING_ORIGIN):
        href = href[len(MARKETING_ORIGIN) :] or "/"
    if href.startswith("#"):
        href = "/" + href
    return href


def _pairs_from_js_array(source: str, name: str) -> list:
    """Extract [{href, label}] entries from a named JS array literal.

    Handles both `href: "/blog"` and `href: at("/blog")`, since the SPA wraps
    every path in a helper that prefixes the marketing origin.
    """
    block = re.search(rf"{name}\s*=\s*\[(.*?)\n\];", source, re.S)
    assert block, f"could not find the {name} array"
    entries = re.findall(
        r'href:\s*(?:at\(\s*)?"([^"]+)"\s*\)?\s*,\s*label:\s*"([^"]+)"', block.group(1)
    )
    return [(_normalize(h), lbl) for h, lbl in entries]


def _pairs_from_jsx_anchors(source: str) -> list:
    """Extract every <a href=...>Label</a> from a JSX block, in order."""
    found = re.findall(r'<a\s[^>]*?href="([^"]+)"[^>]*?>\s*([^<]+?)\s*</a>', source, re.S)
    return [(_normalize(h), " ".join(lbl.split())) for h, lbl in found]


def _pairs_from_html(html: str, class_name: str) -> list:
    """Extract the anchors inside one <div class="..."> of rendered HTML."""
    block = re.search(rf'<div class="{class_name}">(.*?)</div>', html, re.S)
    assert block, f'could not find a <div class="{class_name}"> in the rendered page'
    found = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block.group(1), re.S)
    return [(_normalize(h), " ".join(re.sub(r"<[^>]*>", "", lbl).split())) for h, lbl in found]


def _rendered_shell() -> str:
    return pageshell.page(title="t", body="<main></main>", canonical_path="/blog")


# --- the canonical lists, taken from the marketing site ----------------------


def test_marketing_nav_is_the_expected_set():
    """Pins the canonical list itself, so a deletion on the marketing site
    cannot quietly propagate to the other two copies and still pass."""
    assert _pairs_from_js_array(MARKETING_NAV.read_text(encoding="utf-8"), "LINKS") == [
        ("/#how", "How it works"),
        ("/#features", "Features"),
        ("/#pricing", "Pricing"),
        ("/#one-pager", "One pager"),
        ("/#faq", "FAQ"),
        ("/agenda", "Agenda Builder"),
        ("/blog", "Blog"),
        ("/news", "News"),
    ]


# --- every other copy must match it -----------------------------------------


def test_blog_and_news_nav_matches_the_marketing_site():
    canonical = _pairs_from_js_array(MARKETING_NAV.read_text(encoding="utf-8"), "LINKS")
    assert [(_normalize(h), l) for h, l in pageshell._NAV_LINKS] == canonical


def test_blog_and_news_footer_matches_the_marketing_site():
    canonical = _pairs_from_jsx_anchors(MARKETING_FOOTER.read_text(encoding="utf-8"))
    assert [(_normalize(h), l) for h, l in pageshell._FOOTER_LINKS] == canonical


def test_spa_nav_matches_the_marketing_site():
    canonical = _pairs_from_js_array(MARKETING_NAV.read_text(encoding="utf-8"), "LINKS")
    assert _pairs_from_js_array(SPA_LINKS.read_text(encoding="utf-8"), "NAV_LINKS") == canonical


def test_spa_footer_matches_the_marketing_site():
    canonical = _pairs_from_jsx_anchors(MARKETING_FOOTER.read_text(encoding="utf-8"))
    assert _pairs_from_js_array(SPA_LINKS.read_text(encoding="utf-8"), "FOOTER_LINKS") == canonical


# --- the rendered page, not just the constants -------------------------------


def test_rendered_shell_actually_emits_the_nav_links():
    """The constants being right is not the same as the page using them."""
    canonical = [(_normalize(h), l) for h, l in pageshell._NAV_LINKS]
    assert _pairs_from_html(_rendered_shell(), "links") == canonical


def test_rendered_shell_actually_emits_the_footer_links():
    canonical = [(_normalize(h), l) for h, l in pageshell._FOOTER_LINKS]
    assert _pairs_from_html(_rendered_shell(), "flinks") == canonical


def test_mobile_sheet_carries_the_same_links_as_the_desktop_row():
    """Below the breakpoint the desktop row is display:none, so if the sheet
    ever falls behind, the nav silently disappears on phones — which is exactly
    what this shell did before the sheet existed."""
    html = _rendered_shell()
    assert _pairs_from_html(html, "sheet")[: len(pageshell._NAV_LINKS)] == _pairs_from_html(
        html, "links"
    )


def test_one_pager_link_never_points_straight_at_the_pdf():
    """A direct file link hands over the asset and skips the only lead capture
    the site has. It must anchor to the section."""
    for href, label in pageshell._NAV_LINKS:
        if label == "One pager":
            assert href == "/#one-pager"
            break
    else:
        raise AssertionError("the One pager link is missing from the blog/news nav")
