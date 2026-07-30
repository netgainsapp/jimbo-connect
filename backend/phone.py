"""Phone number normalising and validation.

One rule, applied everywhere a number can enter the system: a phone number is
exactly ten digits, stored and shown as XXX-XXX-XXXX. Anything with more or
fewer digits is rejected rather than quietly truncated or padded, because a
silently mangled phone number is worse than no phone number: it looks correct
and fails only when somebody tries to use it.

Punctuation is forgiving on the way in. "(303) 555-0101", "303.555.0101" and
"3035550101" are all the same number, so all three are accepted and stored in
one canonical shape. What is not forgiven is the digit count.
"""
from __future__ import annotations

import re

DIGITS = re.compile(r"\D")
REQUIRED_DIGITS = 10

# Deliberately not accepted, even though it is a common way to type a US
# number: a leading country code makes eleven digits, and the rule is exactly
# ten. Revisit only as a deliberate decision, not by loosening this quietly.
ERROR = "Enter a 10 digit phone number, for example 303-555-0101."


def normalize_phone(value) -> str:
    """Return "" for blank input, or the number as XXX-XXX-XXXX.

    Raises ValueError with a user-facing message when the digit count is not
    exactly ten. Phone is an optional field, so blank stays blank; it is only a
    non-empty value that has to be a real number.
    """
    if value is None:
        return ""
    digits = DIGITS.sub("", str(value))
    if not digits:
        return ""
    if len(digits) != REQUIRED_DIGITS:
        raise ValueError(ERROR)
    return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"


def is_valid_phone(value) -> bool:
    """True when the value is blank or a valid ten digit number."""
    try:
        normalize_phone(value)
        return True
    except ValueError:
        return False
