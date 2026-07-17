"""Brand-consistent, email-client-safe HTML for outbound mail.

Gmail strips <style> blocks and SVG, and Outlook is picky, so this is
table-based with fully inline styles and a bulletproof button. One builder,
render(), takes structured content (heading + paragraphs + optional button) so
every email (welcome, verify, invites, drip) shares one professional look.

Brand: ink #0d1b2a, blue #2563eb, stone #51606f, cream #f7f8fa. No dashes or
emoji in any copy (brand voice).
"""
import html as _html

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


def _button(label: str, url: str) -> str:
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'style="margin:26px 0"><tr>'
        f'<td bgcolor="{BLUE}" style="border-radius:8px">'
        f'<a href="{_esc(url)}" style="display:inline-block;padding:13px 28px;'
        f'font-family:{FONT};font-size:15px;font-weight:700;color:#ffffff;'
        'text-decoration:none;border-radius:8px">' + _esc(label) + "</a>"
        "</td></tr></table>"
    )


def render(
    *,
    heading: str,
    paragraphs,
    button: dict | None = None,
    unsubscribe_url: str = "",
    preheader: str = "",
) -> str:
    """Full branded HTML email. `button` is {"label","url"} or None. When
    `unsubscribe_url` is given, the footer carries an unsubscribe link."""
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
        f'line-height:1.6;color:#26323f">{_esc(p)}</p>'
        for p in paragraphs
    )
    btn = _button(button["label"], button["url"]) if button else ""
    unsub = (
        f'<br><a href="{_esc(unsubscribe_url)}" '
        f'style="color:{STONE};text-decoration:underline">Unsubscribe</a>'
        if unsubscribe_url
        else ""
    )
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
        f'<tr><td style="padding:4px 4px 20px">{_logo()}</td></tr>'
        # card
        '<tr><td style="background:#ffffff;border:1px solid ' + LINE + ';'
        'border-radius:14px;padding:36px 32px">'
        f"{head}{body}{btn}"
        "</td></tr>"
        # footer
        '<tr><td style="padding:22px 8px;font-family:' + FONT + ';'
        f'font-size:13px;line-height:1.6;color:{STONE}">'
        "You are receiving this because you have an Intro Connect account."
        f"{unsub}<br><span style=\"color:#9aa5b1\">&copy; 2026 Intro Connect</span>"
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
