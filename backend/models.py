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
    password: str = Field(min_length=6)
    name: Optional[str] = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=6)


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    bio: Optional[str] = None
    looking_for: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    photo_url: Optional[str] = None


class PhotoUploadRequest(BaseModel):
    photo_data: str  # base64 data URL


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
    name: str
    date: datetime
    location: Optional[str] = ""
    industry_tags: List[str] = []


class EventUpdateRequest(BaseModel):
    name: Optional[str] = None
    date: Optional[datetime] = None
    location: Optional[str] = None
    industry_tags: Optional[List[str]] = None


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
    note: Optional[str] = ""


class NoteUpdateRequest(BaseModel):
    note: str


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
    name: Optional[str] = ""
    role: Optional[str] = ""
    company: Optional[str] = ""
    industry: Optional[str] = ""
    bio: Optional[str] = ""
    looking_for: Optional[str] = ""
    phone: Optional[str] = ""
    linkedin: Optional[str] = ""


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
