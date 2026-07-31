"""Who gets to see an attendee's email address.

serialize_attendee used to include the address unconditionally, so every
attendee could read every other attendee's email just by opening an event page,
while the product routes contact through messaging precisely so addresses do
not have to be handed around.

Run from backend/: python -m pytest tests/test_attendee_email_scope.py
"""
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

from bson import ObjectId

import core

USER = {
    "_id": ObjectId(),
    "email": "ann@example.com",
    "profile": {"name": "Ann", "role": "VP"},
}


def test_email_is_omitted_by_default():
    """Default off, so a new call site leaks nothing until somebody
    deliberately asks for the address."""
    out = core.serialize_attendee(USER)
    assert "email" not in out
    assert "ann@example.com" not in repr(out)
    # The rest of the person still comes through.
    assert out["profile"]["name"] == "Ann"
    assert out["id"] == str(USER["_id"])


def test_email_is_included_only_when_explicitly_requested():
    out = core.serialize_attendee(USER, include_email=True)
    assert out["email"] == "ann@example.com"


def test_include_email_is_keyword_only():
    """A positional second argument must not be able to switch this on by
    accident, which is the way a flag like this usually gets flipped."""
    try:
        core.serialize_attendee(USER, True)
    except TypeError:
        return
    raise AssertionError("include_email should be keyword only")
