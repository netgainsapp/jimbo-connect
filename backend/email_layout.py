"""Brand-consistent, email-client-safe HTML for outbound mail.

Gmail strips <style> blocks and SVG, and Outlook is picky, so this is
table-based with fully inline styles and a bulletproof button. One builder,
render(), takes structured content (heading + paragraphs + optional button) so
every email (welcome, verify, invites, drip) shares one professional look.

Brand: ink #0d1b2a, blue #2563eb, stone #51606f, cream #f7f8fa. No dashes or
emoji in any copy (brand voice).
"""
import html as _html

from app_url import APP_URL

INK = "#0d1b2a"
BLUE = "#2563eb"
STONE = "#51606f"
CREAM = "#f7f8fa"
LINE = "#e4e6ea"
FONT = (
    "'Plus Jakarta Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',"
    "Roboto,Helvetica,Arial,sans-serif"
)


def _esc(t) -> str:
    return _html.escape(str(t or ""))


# The official app mark (Logo.jsx), pre-rendered to a transparent PNG served by
# the web app. Gmail strips SVG, so emails embed this raster copy at 2x+ density.
LOGO_URL = "https://app.intro-connect.com/email-logo.png"


def _logo() -> str:
    """Icon + wordmark lockup: the official interlocking-figures mark beside the
    two-tone Intro Connect wordmark, matching the app nav."""
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
        '<td style="vertical-align:middle">'
        f'<img src="{LOGO_URL}" width="34" height="34" alt="Intro Connect" '
        'style="display:block;border:0;outline:none"></td>'
        '<td style="padding-left:10px;vertical-align:middle;font-family:' + FONT + ';'
        f'font-size:18px;font-weight:800;letter-spacing:-0.01em;color:{INK}">'
        f'Intro <span style="font-weight:500;color:{STONE}">Connect</span></td>'
        "</tr></table>"
    )


def _host_logo(brand: dict) -> str:
    """Header lockup for a Pro host's branded event email: the host's logo on
    the left, a small 'via Intro Connect' credit on the right. The platform
    stays visible on every branded surface (not white-label)."""
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0"><tr>'
        '<td style="vertical-align:middle">'
        f'<img src="{_esc(brand["logo_url"])}" height="34" alt="Event host" '
        'style="display:block;border:0;outline:none;max-width:180px"></td>'
        f'<td align="right" style="vertical-align:middle;font-family:{FONT};'
        f'font-size:12px;font-weight:600;color:{STONE}">via Intro Connect</td>'
        "</tr></table>"
    )


def _button(label: str, url: str, color: str = BLUE) -> str:
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'style="margin:26px 0"><tr>'
        f'<td bgcolor="{color}" style="border-radius:8px">'
        f'<a href="{_esc(url)}" style="display:inline-block;padding:13px 28px;'
        f'font-family:{FONT};font-size:15px;font-weight:700;color:#ffffff;'
        'text-decoration:none;border-radius:8px">' + _esc(label) + "</a>"
        "</td></tr></table>"
    )


def _footer_mark() -> str:
    """The footer lockup for host mail: the mark beside a one run wordmark. The
    image alt is empty on purpose, so the wordmark is the single place the
    brand name appears in the message."""
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'style="margin:0 0 8px"><tr>'
        f'<td style="vertical-align:middle"><img src="{LOGO_URL}" width="22" '
        'height="22" alt="" style="display:block;border:0;outline:none"></td>'
        f'<td style="padding-left:8px;vertical-align:middle;font-family:{FONT};'
        f'font-size:14px;font-weight:800;color:{INK}">Intro Connect</td>'
        "</tr></table>"
    )


def _host_header(host: dict, brand: dict | None) -> str:
    """Header for mail sent as a host: round headshot (only when they have a
    photo) above their name, and a Pro host's logo on the right. The platform
    lockup lives in the footer instead."""
    photo = (
        f'<img src="{_esc(host["photo_url"])}" width="56" height="56" '
        f'alt="{_esc(host.get("name"))}" style="display:block;border:0;'
        'outline:none;border-radius:50%;width:56px;height:56px;margin:0 0 10px">'
        if host.get("photo_url")
        else ""
    )
    name = (
        f'<div style="font-family:{FONT};font-size:18px;font-weight:800;'
        f'letter-spacing:-0.01em;color:{INK}">{_esc(host.get("name"))}</div>'
    )
    logo = (
        f'<td align="right" style="vertical-align:middle"><img src="'
        f'{_esc(brand["logo_url"])}" height="34" alt="" style="display:block;'
        'border:0;outline:none;max-width:180px"></td>'
        if brand and brand.get("logo_url")
        else ""
    )
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'border="0"><tr><td style="vertical-align:middle">{photo}{name}</td>'
        f"{logo}</tr></table>"
    )


def _footer(host: dict | None, unsubscribe_url: str, sign_in_url: str) -> str:
    """Footer copy. The platform footer is unchanged. In host mail it carries
    the Intro Connect lockup (the one mention), who the mail was sent for, and
    the attendee's own sign in link, the only door into the product."""
    unsub = (
        f'<br><a href="{_esc(unsubscribe_url)}" '
        f'style="color:{STONE};text-decoration:underline">Unsubscribe</a>'
        if unsubscribe_url
        else ""
    )
    if host:
        return (
            f"{_footer_mark()}Sent for {_esc(host.get('name'))}. "
            f'<a href="{_esc(sign_in_url)}" style="color:{STONE};'
            f'text-decoration:underline">Sign in to your directory</a>.{unsub}'
        )
    return (
        "You are receiving this because you have an Intro Connect account."
        f"{unsub}<br><span style=\"color:#9aa5b1\">&copy; 2026 Intro Connect</span>"
    )


AVATAR_PX = 48


def _avatars(avatars) -> str:
    """A row of round headshots. Empty when none has an https URL."""
    imgs = "".join(
        f'<img src="{_esc(a["url"])}" width="{AVATAR_PX}" height="{AVATAR_PX}" '
        f'alt="{_esc(a.get("alt"))}" style="display:inline-block;border:0;'
        f'width:{AVATAR_PX}px;height:{AVATAR_PX}px;border-radius:50%;'
        'object-fit:cover;margin:0 8px 0 0">'
        for a in avatars or ()
        if str(a.get("url") or "").startswith("https://")
    )
    return f'<div style="margin:0 0 16px">{imgs}</div>' if imgs else ""


def render(
    *,
    heading: str,
    paragraphs,
    button: dict | None = None,
    unsubscribe_url: str = "",
    preheader: str = "",
    brand: dict | None = None,
    host: dict | None = None,
    sign_in_url: str = "",
    avatars=(),
) -> str:
    """Full branded HTML email. `button` is {"label","url"} or None. When
    `unsubscribe_url` is given, the footer carries an unsubscribe link.
    `brand` is an optional host brand {"logo_url","accent_dark"} (Pro hosts):
    it swaps the header for the host's logo lockup and colors the button with
    the host's contrast-safe accent. None renders the platform default.
    `host` ({name,email,photo_url} from core.host_block) makes the mail the
    host's: their name and headshot lead the header, a Pro logo sits beside
    them, and the Intro Connect lockup moves to a footer that links the
    attendee's own sign in (`sign_in_url`, default the app login).
    `avatars` ({url, alt} each) are small round headshots of the people the
    mail is about, shown above the body. Only https URLs render: an email
    client will not load an inline data URL, so those are dropped."""
    pre = (
        f'<div style="display:none;max-height:0;overflow:hidden;opacity:0">'
        f"{_esc(preheader)}</div>"
        if preheader
        else ""
    )
    head = (
        f'<h1 style="margin:0 0 18px;font-family:{FONT};font-size:23px;'
        f'font-weight:800;letter-spacing:-0.02em;line-height:1.2;color:{INK}">'
        f"{_esc(heading)}</h1>"
        if heading
        else ""
    )
    body = "".join(
        f'<p style="margin:0 0 16px;font-family:{FONT};font-size:16px;'
        # Single newlines inside a paragraph (credential blocks, addresses)
        # must survive as line breaks, not collapse into spaces.
        f'line-height:1.6;color:#26323f">{_esc(p).replace(chr(10), "<br>")}</p>'
        for p in paragraphs
    )
    faces = _avatars(avatars)
    accent = (brand or {}).get("accent_dark") or BLUE
    btn = _button(button["label"], button["url"], color=accent) if button else ""
    if host:
        header = _host_header(host, brand)
    else:
        header = _host_logo(brand) if brand and brand.get("logo_url") else _logo()
    footer = _footer(host, unsubscribe_url, sign_in_url or f"{APP_URL}/login")
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'</head><body style="margin:0;padding:0;background:{CREAM}">'
        f"{pre}"
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'border="0" style="background:{CREAM}"><tr><td align="center" '
        'style="padding:32px 16px">'
        '<table role="presentation" width="600" cellpadding="0" cellspacing="0" '
        'border="0" style="width:600px;max-width:100%">'
        # header
        f'<tr><td style="padding:4px 4px 20px">{header}</td></tr>'
        # card
        '<tr><td style="background:#ffffff;border:1px solid ' + LINE + ';'
        'border-radius:14px;padding:36px 32px">'
        f"{head}{faces}{body}{btn}"
        "</td></tr>"
        # footer
        '<tr><td style="padding:22px 8px;font-family:' + FONT + ';'
        f'font-size:13px;line-height:1.6;color:{STONE}">'
        f"{footer}"
        "</td></tr>"
        "</table></td></tr></table></body></html>"
    )


def to_text(paragraphs, button: dict | None = None, unsubscribe_url: str = "") -> str:
    """Plain-text alternative for the multipart email."""
    parts = list(paragraphs)
    if button:
        parts.append(f"{button['label']}: {button['url']}")
    text = "\n\n".join(parts)
    if unsubscribe_url:
        text += f"\n\nUnsubscribe: {unsubscribe_url}"
    return text
