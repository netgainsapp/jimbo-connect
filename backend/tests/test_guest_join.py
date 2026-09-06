"""Guest join + email-less user safety.

A guest joins with a code and a name, no account, no email, no password.
These tests cover the pure pieces: the request model, the LinkedIn
normalizer, and every serializer that used to assume user["email"] exists.
The endpoint's DB path follows the suite's convention of being exercised
against the live app rather than mocked Mongo.

Run from backend/: python -m pytest tests/test_guest_join.py
"""
import pytest
from pydantic import ValidationError

from core import serialize_user, serialize_attendee
from models import GuestJoinRequest, ProfileUpdateRequest


def _guest_doc():
    # What the guest-join endpoint inserts: note there is NO email key and
    # NO password_hash. Serialization must not KeyError on that shape.
    return {
        "_id": "0" * 24,
        "is_admin": False,
        "is_guest": True,
        "profile": {"name": "Door Guest", "linkedin": "https://linkedin.com/in/guest"},
    }


def test_serialize_user_survives_missing_email():
    out = serialize_user(_guest_doc())
    assert out["email"] == ""
    assert out["profile"]["name"] == "Door Guest"


def test_serialize_attendee_include_email_survives_missing_email():
    out = serialize_attendee(_guest_doc(), include_email=True)
    assert out["email"] == ""


def test_serialize_attendee_still_omits_email_by_default():
    out = serialize_attendee(_guest_doc())
    assert "email" not in out


def test_guest_join_requires_a_real_name():
    with pytest.raises(ValidationError):
        GuestJoinRequest(name="")
    with pytest.raises(ValidationError):
        GuestJoinRequest(name="   ")


def test_guest_join_name_is_trimmed():
    req = GuestJoinRequest(name="  Ada Lovelace  ")
    assert req.name == "Ada Lovelace"


def test_guest_join_linkedin_optional_and_normalized():
    assert GuestJoinRequest(name="Ada").linkedin == ""
    req = GuestJoinRequest(name="Ada", linkedin="linkedin.com/in/ada")
    assert req.linkedin == "https://linkedin.com/in/ada"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("linkedin.com/in/scott", "https://linkedin.com/in/scott"),
        ("www.linkedin.com/in/scott", "https://www.linkedin.com/in/scott"),
        ("https://www.linkedin.com/in/scott", "https://www.linkedin.com/in/scott"),
        ("http://linkedin.com/in/scott", "http://linkedin.com/in/scott"),
        ("  linkedin.com/in/scott  ", "https://linkedin.com/in/scott"),
        # Anything that is not obviously a linkedin.com URL is left as typed:
        # normalization must never invent a link that was not there.
        ("scott-weiss", "scott-weiss"),
        ("", ""),
    ],
)
def test_profile_update_linkedin_normalization(raw, expected):
    req = ProfileUpdateRequest(linkedin=raw)
    assert req.linkedin == expected


def test_profile_update_linkedin_none_stays_none():
    # None means "field not sent" in a partial update and must survive.
    assert ProfileUpdateRequest().linkedin is None
