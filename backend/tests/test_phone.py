"""Phone numbers are exactly ten digits, stored as XXX-XXX-XXXX.

Run from backend/: python -m pytest tests/test_phone.py
"""
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import pytest
from pydantic import ValidationError

from models import BulkImportRow, ProfileUpdateRequest
from phone import is_valid_phone, normalize_phone


# ---------------------------------------------------------------------------
# Accepted, and canonicalised to one shape
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw",
    [
        "3035550101",
        "303-555-0101",
        "303.555.0101",
        "303 555 0101",
        "(303) 555-0101",
        "  303-555-0101  ",
        "303/555/0101",
    ],
)
def test_ten_digits_in_any_punctuation_becomes_one_canonical_form(raw):
    assert normalize_phone(raw) == "303-555-0101"


def test_blank_stays_blank_because_phone_is_optional():
    assert normalize_phone("") == ""
    assert normalize_phone(None) == ""
    assert normalize_phone("   ") == ""
    # Punctuation with no digits is still nothing.
    assert normalize_phone("--") == ""


# ---------------------------------------------------------------------------
# Rejected: anything that is not exactly ten digits
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,why",
    [
        ("303555010", "nine digits"),
        ("30355501011", "eleven digits"),
        ("1-303-555-0101", "leading country code makes eleven"),
        ("+1 303 555 0101", "plus one country code"),
        ("555-0101", "seven digits, local only"),
        ("303-555-010A", "letter where a digit should be"),
        ("0", "one digit"),
        ("123456789012345", "far too long"),
    ],
)
def test_wrong_digit_counts_are_refused(raw, why):
    with pytest.raises(ValueError):
        normalize_phone(raw)
    assert not is_valid_phone(raw), why


def test_the_error_message_shows_the_expected_shape():
    with pytest.raises(ValueError) as exc:
        normalize_phone("12345")
    assert "10 digit" in str(exc.value)
    assert "303-555-0101" in str(exc.value)


def test_a_bad_number_is_never_silently_truncated_or_padded():
    """The failure mode this rule exists to prevent: a number that looks
    plausible and does not work."""
    for raw in ("30355501011", "303555010"):
        with pytest.raises(ValueError):
            normalize_phone(raw)


# ---------------------------------------------------------------------------
# Enforced at both entry points
# ---------------------------------------------------------------------------

def test_profile_update_normalises_a_valid_number():
    assert ProfileUpdateRequest(phone="(303) 555-0101").phone == "303-555-0101"


def test_profile_update_rejects_a_bad_number():
    with pytest.raises(ValidationError):
        ProfileUpdateRequest(phone="303-555-01011")


def test_profile_update_omitting_phone_stays_none():
    """None means the field was not sent. A partial update must not turn that
    into an empty string and wipe a saved number."""
    assert ProfileUpdateRequest(name="Scott").phone is None


def test_bulk_import_row_normalises_a_valid_number():
    row = BulkImportRow(email="importer@acme.co", phone="303.555.0101")
    assert row.phone == "303-555-0101"


def test_bulk_import_row_rejects_a_bad_number():
    """Assert the failure is about the phone. An earlier version of this test
    used a reserved .test email and passed for the wrong reason: it raised on
    the address before the phone was ever looked at."""
    with pytest.raises(ValidationError) as exc:
        BulkImportRow(email="importer@acme.co", phone="555-0101")
    assert "phone" in str(exc.value)
    assert "10 digit" in str(exc.value)


def test_bulk_import_row_allows_no_phone():
    assert BulkImportRow(email="importer@acme.co").phone == ""


# ---------------------------------------------------------------------------
# The seeded sample data has to satisfy the rule it ships with
# ---------------------------------------------------------------------------

def test_seeded_sample_phone_numbers_are_valid():
    import re
    from pathlib import Path

    source = (Path(__file__).parent.parent / "core.py").read_text(encoding="utf-8")
    seeded = re.findall(r'"phone":\s*"([^"]+)"', source)
    assert seeded, "expected the sample profiles to carry phone numbers"
    for number in seeded:
        assert is_valid_phone(number), f"seed data has an invalid phone: {number}"
