"""Seeded email template copy. The system templates are what the server
actually sends, so their copy is a brand-voice invariant, not a preference.
Run from backend/: python -m pytest tests/test_template_seeds.py
"""
from core import _seed_for
from template_seeds import DEFAULT_TEMPLATES


def test_no_dashes_anywhere_in_seed_copy():
    """Brand voice: no em or en dashes in any field a human ever reads. This is
    the check that would have caught the drifted password reset copy."""
    offenders = []
    for t in DEFAULT_TEMPLATES:
        for field in ("subject", "body", "title", "blurb"):
            value = t.get(field) or ""
            if "—" in value or "–" in value:
                offenders.append(f"{t['template_id']}.{field}")
    assert not offenders, f"dashes found in: {offenders}"


def test_system_templates_are_the_two_the_server_sends():
    system = {t["template_id"] for t in DEFAULT_TEMPLATES if t.get("system")}
    assert system == {"password-reset", "invitation"}


def test_system_copy_uses_the_host_name_token_not_a_baked_name():
    """The drift we repaired had "Intro Admin" written into the body. The seed
    must use the merge token so the signoff stays correct per send."""
    for tid in ("password-reset", "invitation"):
        body = _seed_for(tid)["body"]
        assert "{host_name}" in body
        assert "Intro Admin" not in body


def test_password_reset_carries_the_reset_url_token():
    body = _seed_for("password-reset")["body"]
    assert "{reset_url}" in body


def test_seed_lookup_returns_none_for_unknown():
    assert _seed_for("nope-not-a-template") is None
