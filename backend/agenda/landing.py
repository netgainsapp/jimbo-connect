"""Server-rendered landing page for the free Agenda Builder.

This page is the SEO surface, and it is why the page is rendered here rather
than in the React app. It is served on the marketing domain via the same
rewrite mechanism as /blog and /news, so its content exists in the raw HTML for
any crawler, with no JavaScript required. The interactive builder itself stays
in the app at APP_URL/agenda/new; this page's job is to be findable and to send
people there.

Pure string builders, like blog/render.py: easy to unit test, everything
escaped through the shared shell.
"""
from __future__ import annotations

import html

import pageshell
import seo
from app_url import APP_URL

PATH = "/agenda"
BUILDER_URL = f"{APP_URL}/agenda/new"

TITLE = "Free Event Agenda Builder | Intro Connect"
DESCRIPTION = (
    "Build a professional event agenda in your browser and download it as a "
    "Word document. Free, no account needed, multi day events supported."
)

STEPS = [
    (
        "Add your event details",
        "Name, dates, times, venue, and your logo. Nothing is required except a "
        "name, so you can start with what you have and fill in the rest later.",
    ),
    (
        "Build the schedule",
        "Add a session for each thing on your agenda: a welcome, a talk, a "
        "break, dinner. Give each one a time, a room, and a speaker. Drag them "
        "into the order you want, and events running over several days group "
        "themselves by date.",
    ),
    (
        "Download a Word document",
        "You get a clean, professional agenda as a .docx file. It stays fully "
        "editable, so you can adjust it in Word, print it, or email it to "
        "everyone who is coming.",
    ),
]

FAQS = [
    (
        "Is it really free?",
        "Yes. You can build an agenda and download it as many times as you like "
        "without paying and without creating an account.",
    ),
    (
        "Do I need an account?",
        "No. Your agenda is saved in your own browser as you type, so you can "
        "close the tab and come back to it later on the same device.",
    ),
    (
        "Can I edit the document after I download it?",
        "Yes. It is a real Word file, not a picture or a locked PDF, so you can "
        "change anything in it.",
    ),
    (
        "Does it handle events that run over more than one day?",
        "Yes. Give each session its date and the agenda groups itself by day, "
        "in order, both on screen and in the downloaded document.",
    ),
    (
        "What happens to my information?",
        "The agenda lives in your browser. It is sent to us only at the moment "
        "you download the document, and it is not stored on our side.",
    ),
]


def _esc(text) -> str:
    return html.escape(str(text or ""))


def _steps_html() -> str:
    rows = "".join(
        f"<h3>{_esc(name)}</h3><p>{_esc(body)}</p>" for name, body in STEPS
    )
    return f"<h2>How it works</h2>{rows}"


def _faq_html() -> str:
    rows = "".join(f"<h3>{_esc(q)}</h3><p>{_esc(a)}</p>" for q, a in FAQS)
    return f"<h2>Common questions</h2>{rows}"


def _structured_data() -> str:
    """WebApplication plus an FAQPage. The FAQ block mirrors the visible copy
    above, which is the condition search engines put on using it."""
    app_ld = seo.json_ld(
        {
            "@context": "https://schema.org",
            "@type": "WebApplication",
            "name": "Intro Connect Agenda Builder",
            "url": seo.abs_url(PATH),
            "applicationCategory": "BusinessApplication",
            "operatingSystem": "Any",
            "description": DESCRIPTION,
            "offers": {
                "@context": "https://schema.org",
                "@type": "Offer",
                "price": "0",
                "priceCurrency": "USD",
            },
            "publisher": {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "Intro Connect",
                "url": seo.content_base(),
            },
        }
    )
    faq_ld = seo.json_ld(
        {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@context": "https://schema.org",
                    "@type": "Question",
                    "name": q,
                    "acceptedAnswer": {
                        "@context": "https://schema.org",
                        "@type": "Answer",
                        "text": a,
                    },
                }
                for q, a in FAQS
            ],
        }
    )
    return app_ld + faq_ld


def render_landing() -> str:
    body = (
        '<div class="wrap">'
        '<p class="eyebrow">Free tool</p>'
        '<h1 class="title">Free event agenda builder</h1>'
        '<p class="summary">Put your event schedule together in your browser and '
        "download it as a polished Word document. No account, no payment, and "
        "nothing to install.</p>"
        f'<p class="copy"><a class="btn-primary" href="{_esc(BUILDER_URL)}">'
        "Start building an agenda</a></p>"
        '<div class="copy">'
        "<p>Every organizer ends up building an agenda in a word processor, "
        "fighting with tab stops to get the times to line up. This does that "
        "part for you. Enter your sessions, drag them into order, and take away "
        "a document that looks like someone designed it.</p>"
        f"{_steps_html()}"
        "<h2>What you get in the document</h2>"
        "<p>Your logo and event name at the top, the dates and venue, your "
        "description, then each day laid out as a clean table of times and "
        "sessions with their speakers and rooms, and your organizer details at "
        "the end. It is a normal Word file, so it is yours to change.</p>"
        "<h2>Who it is for</h2>"
        "<p>Anyone running something where the schedule matters: conferences, "
        "founder dinners, workshops, retreats, meetups, community days, and "
        "internal offsites. It works just as well for a single evening as for a "
        "conference that runs across several days.</p>"
        f"{_faq_html()}"
        "</div>"
        '<div class="cta">'
        "<h2>After the agenda, the introductions</h2>"
        "<p>An agenda tells people what is happening. It does not help them "
        "remember who they met. Intro Connect turns your guest list into a "
        "private directory for the people who were actually in the room, so the "
        "connections made at your event outlast the event itself.</p>"
        f'<p><a class="btn-primary" href="{_esc(BUILDER_URL)}">'
        "Build your agenda free</a></p>"
        "</div>"
        "</div>"
    )
    return pageshell.page(
        TITLE,
        body,
        canonical_path=PATH,
        description=DESCRIPTION,
        extra_head=_structured_data(),
    )
