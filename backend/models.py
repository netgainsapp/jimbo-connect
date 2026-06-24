from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


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


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=200)
    name: Optional[str] = Field(default="", max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=6)


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


class PhotoUploadRequest(BaseModel):
    # base64 data URL; cap ~1.6MB decoded to avoid unbounded Mongo growth / OOM
    photo_data: str = Field(max_length=2_200_000)


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


class BulkImportRow(BaseModel):
    email: EmailStr
    name: Optional[str] = Field(default="", max_length=100)
    role: Optional[str] = Field(default="", max_length=100)
    company: Optional[str] = Field(default="", max_length=200)
    industry: Optional[str] = Field(default="", max_length=120)
    bio: Optional[str] = Field(default="", max_length=2000)
    looking_for: Optional[str] = Field(default="", max_length=1000)
    phone: Optional[str] = Field(default="", max_length=40)
    linkedin: Optional[str] = Field(default="", max_length=300)


class BulkImportRequest(BaseModel):
    rows: List[BulkImportRow]
    event_id: Optional[str] = None
    default_password: Optional[str] = None


class SponsorCreateRequest(BaseModel):
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    active: Optional[bool] = True


class SponsorUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
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
