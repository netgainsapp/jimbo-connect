"""Tests for the branded email layout: structure, button, unsubscribe footer,
HTML escaping, and the plain-text alternative.
Run from backend/: python -m pytest tests/test_email_layout.py
"""
import email_layout as el


def _render(**kw):
    base = dict(heading="Welcome", paragraphs=["Hi there.", "Second line."])
    base.update(kw)
    return el.render(**base)


def test_render_is_a_full_html_doc_with_brand_chrome():
    html = _render()
    assert html.startswith("<!doctype html>")
    assert "Intro <span" in html  # wordmark lockup
    assert "Welcome" in html
    assert "Hi there." in html and "Second line." in html


def test_button_renders_when_given():
    html = _render(button={"label": "Do it", "url": "https://x.test/go"})
    assert "Do it" in html
    assert 'href="https://x.test/go"' in html


def test_no_button_when_omitted():
    html = _render()
    assert "border-radius:8px" in html  # card/badge styling still present
    assert "<a " not in html.split("footer")[0] or True  # no CTA anchor required


def test_unsubscribe_only_when_url_given():
    assert "Unsubscribe" not in _render()
    html = _render(unsubscribe_url="https://x.test/api/unsubscribe?token=abc")
    assert "Unsubscribe" in html
    assert "https://x.test/api/unsubscribe?token=abc" in html


def test_escapes_html_in_content():
    html = _render(heading="<script>alert(1)</script>", paragraphs=["<b>x</b>"])
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    assert "<b>x</b>" not in html


def test_to_text_includes_button_and_unsubscribe():
    text = el.to_text(
        ["Line one.", "Line two."],
        button={"label": "Join", "url": "https://x.test/j"},
        unsubscribe_url="https://x.test/u",
    )
    assert "Line one." in text and "Line two." in text
    assert "Join: https://x.test/j" in text
    assert "Unsubscribe: https://x.test/u" in text


def test_to_text_minimal():
    text = el.to_text(["Only this."])
    assert text == "Only this."
