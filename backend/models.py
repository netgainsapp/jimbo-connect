from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator

from phone import normalize_phone


class _EmailNormalized(BaseModel):
    """Mixin that lowercases and trims any `email` field, so registration,
    login, and password reset all key on the same canonical value and the
    unique email index behaves case-insensitively."""

    @field_validator("email", check_fields=False)
    @classmethod
    def _normalize_email(cls, v):
        return v.lower().strip() if isinstance(v, str) else v


class Profile(BaseModel):
    name: Optional[str] = ""
    role: Optional[str] = ""
    company: Optional[str] = ""
    industry: Optional[str] = ""
    bio: Optional[str] = ""
    looking_for: Optional[str] = ""
    phone: Optional[str] = ""
    linkedin: Optional[str] = ""
    photo_url: Optional[str] = ""


class RegisterRequest(_EmailNormalized):
    email: EmailStr
    password: str = Field(min_length=6, max_length=200)
    name: Optional[str] = Field(default="", max_length=100)


class LoginRequest(_EmailNormalized):
    email: EmailStr
    password: str


class ForgotPasswordRequest(_EmailNormalized):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=6)


# A photo may be an https URL or an inline base64 data URL of a real image
# type. Anything else (javascript:, http:, file:, plain text) is rejected at
# the boundary; stored legacy values are not re-validated on read.
_PHOTO_DATA_PREFIXES = (
    "data:image/png;base64,",
    "data:image/jpeg;base64,",
    "data:image/jpg;base64,",
    "data:image/webp;base64,",
    "data:image/gif;base64,",
)


def _check_photo_value(v):
    if v is None or v == "":
        return v
    if v.startswith("https://") or v.startswith(_PHOTO_DATA_PREFIXES):
        return v
    raise ValueError("photo must be an https URL or an image data URL")


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    role: Optional[str] = Field(default=None, max_length=100)
    company: Optional[str] = Field(default=None, max_length=200)
    industry: Optional[str] = Field(default=None, max_length=120)
    bio: Optional[str] = Field(default=None, max_length=2000)
    looking_for: Optional[str] = Field(default=None, max_length=1000)
    phone: Optional[str] = Field(default=None, max_length=40)
    linkedin: Optional[str] = Field(default=None, max_length=300)
    photo_url: Optional[str] = Field(default=None, max_length=2_200_000)

    @field_validator("phone")
    @classmethod
    def _phone_is_ten_digits(cls, v):
        # None means the client did not send the field at all, which is a
        # partial update and must not be turned into "".
        if v is None:
            return v
        return normalize_phone(v)

    @field_validator("photo_url")
    @classmethod
    def _photo_url_scheme(cls, v):
        return _check_photo_value(v)


class PhotoUploadRequest(BaseModel):
    # base64 data URL; cap ~1.6MB decoded to avoid unbounded Mongo growth / OOM
    photo_data: str = Field(max_length=2_200_000)

    @field_validator("photo_data")
    @classmethod
    def _photo_data_is_image(cls, v):
        if not v or not v.startswith(_PHOTO_DATA_PREFIXES):
            raise ValueError("photo_data must be an image data URL")
        return v


class UserPublic(BaseModel):
    id: str
    email: str
    is_admin: bool
    profile: Profile
    created_at: datetime


class AttendeePublic(BaseModel):
    id: str
    email: str
    profile: Profile


class EventCreateRequest(BaseModel):
    name: str = Field(max_length=200)
    date: datetime
    location: Optional[str] = Field(default="", max_length=200)
    industry_tags: List[str] = Field(default_factory=list, max_length=50)
    # Added for the Agenda Builder handoff. Optional, so nothing that creates
    # an event today has to change.
    description: Optional[str] = Field(default="", max_length=5000)
    end_date: Optional[datetime] = None


class EventUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    date: Optional[datetime] = None
    location: Optional[str] = Field(default=None, max_length=200)
    industry_tags: Optional[List[str]] = Field(default=None, max_length=50)


class EventPublic(BaseModel):
    id: str
    name: str
    date: datetime
    location: str
    industry_tags: List[str]
    join_code: str
    created_by: str
    created_at: datetime
    attendee_count: Optional[int] = 0
    description: Optional[str] = ""
    end_date: Optional[datetime] = None
    agenda_id: Optional[str] = None


class SaveContactRequest(BaseModel):
    contact_id: str
    note: Optional[str] = Field(default="", max_length=2000)


class NoteUpdateRequest(BaseModel):
    note: str = Field(max_length=2000)


class SavedContactPublic(BaseModel):
    id: str
    contact_id: str
    note: str
    saved_at: datetime
    contact: AttendeePublic


class StatsResponse(BaseModel):
    total_users: int
    total_events: int
    total_connections: int


class BulkImportRow(_EmailNormalized):
    email: EmailStr
    name: Optional[str] = Field(default="", max_length=100)
    role: Optional[str] = Field(default="", max_length=100)
    company: Optional[str] = Field(default="", max_length=200)
    industry: Optional[str] = Field(default="", max_length=120)
    bio: Optional[str] = Field(default="", max_length=2000)
    looking_for: Optional[str] = Field(default="", max_length=1000)
    phone: Optional[str] = Field(default="", max_length=40)
    linkedin: Optional[str] = Field(default="", max_length=300)

    @field_validator("phone")
    @classmethod
    def _phone_is_ten_digits(cls, v):
        # A spreadsheet is the likeliest source of a malformed number, so this
        # is the path that most needs the check. A bad row fails validation and
        # names the field, rather than importing a broken contact.
        return normalize_phone(v)


class BulkImportRequest(BaseModel):
    rows: List[BulkImportRow] = Field(max_length=500)
    event_id: Optional[str] = None
    default_password: Optional[str] = Field(default=None, max_length=200)


class SponsorCreateRequest(BaseModel):
    url: str = Field(max_length=2048)
    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    image_url: Optional[str] = Field(default=None, max_length=2048)
    active: Optional[bool] = True


class SponsorUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    image_url: Optional[str] = Field(default=None, max_length=2048)
    active: Optional[bool] = None


class SendMessageRequest(BaseModel):
    to_user_id: str
    text: str = Field(min_length=1, max_length=4000)


class SponsorPublic(BaseModel):
    id: str
    event_id: str
    url: str
    title: str
    description: str
    image_url: str
    site_name: str
    active: bool
    added_at: datetime


class BlogFlagRequest(BaseModel):
    name: str
    value: bool


class RequestInviteRequest(BaseModel):
    message: Optional[str] = Field(default="", max_length=2000)


class CheckEmailsRequest(BaseModel):
    # EmailStr forces each element to be a real email string, so the list can be
    # safely used in a Mongo $in query (no operator-object injection).
    emails: List[EmailStr] = Field(default_factory=list, max_length=1000)


class TemplateUpdateRequest(BaseModel):
    subject: Optional[str] = Field(default=None, max_length=300)
    body: Optional[str] = Field(default=None, max_length=20000)


class InviteGuestsRequest(BaseModel):
    emails: List[EmailStr] = Field(default_factory=list, max_length=200)


class OutreachLeadIn(BaseModel):
    email: EmailStr
    name: Optional[str] = Field(default="", max_length=120)
    company: Optional[str] = Field(default="", max_length=200)
    role: Optional[str] = Field(default="", max_length=120)
    source: Optional[str] = Field(default="", max_length=300)


class OutreachAddRequest(BaseModel):
    leads: List[OutreachLeadIn] = Field(default_factory=list, max_length=500)
