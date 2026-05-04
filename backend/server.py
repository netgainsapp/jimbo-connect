import os
import secrets
import string
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Response, Request, status
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId
from dotenv import load_dotenv

from database import users, events, event_attendees, saved_contacts, ensure_indexes
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    get_current_admin,
    COOKIE_NAME,
)
from models import (
    Profile,
    RegisterRequest,
    LoginRequest,
    ProfileUpdateRequest,
    PhotoUploadRequest,
    UserPublic,
    AttendeePublic,
    EventCreateRequest,
    EventUpdateRequest,
    EventPublic,
    SaveContactRequest,
    NoteUpdateRequest,
    SavedContactPublic,
    StatsResponse,
)

load_dotenv()

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@jimboconnect.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def generate_join_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def serialize_user(user: dict) -> dict:
    profile = user.get("profile") or {}
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "is_admin": bool(user.get("is_admin")),
        "profile": Profile(**profile).model_dump(),
        "created_at": user.get("created_at", datetime.now(timezone.utc)),
    }


def serialize_attendee(user: dict) -> dict:
    profile = user.get("profile") or {}
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "profile": Profile(**profile).model_dump(),
    }


def serialize_event(event: dict, attendee_count: int = 0) -> dict:
    return {
        "id": str(event["_id"]),
        "name": event["name"],
        "date": event["date"],
        "location": event.get("location", ""),
        "industry_tags": event.get("industry_tags", []),
        "join_code": event["join_code"],
        "created_by": str(event["created_by"]),
        "created_at": event["created_at"],
        "attendee_count": attendee_count,
    }


async def seed_data():
    """Create admin user and sample data on first run."""
    admin = await users.find_one({"email": ADMIN_EMAIL})
    if admin:
        return

    now = datetime.now(timezone.utc)

    admin_doc = {
        "email": ADMIN_EMAIL,
        "password_hash": hash_password(ADMIN_PASSWORD),
        "is_admin": True,
        "created_at": now,
        "profile": {
            "name": "Jimbo Admin",
            "role": "Platform Host",
            "company": "Jimbo Connect",
            "industry": "Events",
            "bio": "Running the show.",
            "looking_for": "",
            "phone": "",
            "linkedin": "",
            "photo_url": "",
        },
    }
    admin_result = await users.insert_one(admin_doc)
    admin_id = admin_result.inserted_id

    sample_attendees = [
        {
            "email": "ava@example.com",
            "profile": {
                "name": "Ava Reynolds",
                "role": "Founder & CEO",
                "company": "Trailhead Labs",
                "industry": "SaaS",
                "bio": "Building developer tools for outdoor brands.",
                "looking_for": "Seed investors, design partners",
                "phone": "303-555-0101",
                "linkedin": "linkedin.com/in/avareynolds",
                "photo_url": "",
            },
        },
        {
            "email": "ben@example.com",
            "profile": {
                "name": "Ben Carter",
                "role": "VP of Engineering",
                "company": "Summit Robotics",
                "industry": "Hardware",
                "bio": "Robotics nerd. Coffee snob.",
                "looking_for": "Senior engineers",
                "phone": "303-555-0102",
                "linkedin": "linkedin.com/in/bencarter",
                "photo_url": "",
            },
        },
        {
            "email": "cara@example.com",
            "profile": {
                "name": "Cara Liu",
                "role": "Product Designer",
                "company": "Aspen Studio",
                "industry": "Design",
                "bio": "Designing calm interfaces.",
                "looking_for": "Freelance projects",
                "phone": "303-555-0103",
                "linkedin": "linkedin.com/in/caraliu",
                "photo_url": "",
            },
        },
        {
            "email": "diego@example.com",
            "profile": {
                "name": "Diego Martinez",
                "role": "Operating Partner",
                "company": "Range Capital",
                "industry": "Venture Capital",
                "bio": "Backing operators in the mountain west.",
                "looking_for": "Pre-seed founders",
                "phone": "303-555-0104",
                "linkedin": "linkedin.com/in/diegomartinez",
                "photo_url": "",
            },
        },
        {
            "email": "elena@example.com",
            "profile": {
                "name": "Elena Park",
                "role": "Head of Marketing",
                "company": "Foothill Foods",
                "industry": "CPG",
                "bio": "Brand and growth in food and beverage.",
                "looking_for": "Agency referrals",
                "phone": "303-555-0105",
                "linkedin": "linkedin.com/in/elenapark",
                "photo_url": "",
            },
        },
    ]

    sample_ids = []
    for s in sample_attendees:
        doc = {
            "email": s["email"],
            "password_hash": hash_password("password123"),
            "is_admin": False,
            "created_at": now,
            "profile": s["profile"],
        }
        result = await users.insert_one(doc)
        sample_ids.append(result.inserted_id)

    event_doc = {
        "name": "Denver Founders Dinner",
        "date": datetime(2026, 6, 15, 18, 30, tzinfo=timezone.utc),
        "location": "Denver, CO",
        "industry_tags": ["SaaS", "Hardware", "Venture Capital", "CPG"],
        "join_code": "DENVER01",
        "created_by": admin_id,
        "created_at": now,
    }
    event_result = await events.insert_one(event_doc)
    event_id = event_result.inserted_id

    for uid in sample_ids:
        await event_attendees.insert_one(
            {"event_id": event_id, "user_id": uid, "joined_at": now}
        )

    if len(sample_ids) >= 3:
        await saved_contacts.insert_one(
            {
                "owner_id": sample_ids[0],
                "contact_id": sample_ids[3],
                "note": "Great fit for our seed round. Follow up Monday.",
                "saved_at": now,
            }
        )
        await saved_contacts.insert_one(
            {
                "owner_id": sample_ids[1],
                "contact_id": sample_ids[2],
                "note": "Interested in design contract for Q3.",
                "saved_at": now,
            }
        )
        await saved_contacts.insert_one(
            {
                "owner_id": sample_ids[2],
                "contact_id": sample_ids[4],
                "note": "Wants to swap notes on brand strategy.",
                "saved_at": now,
            }
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_indexes()
    await seed_data()
    yield


app = FastAPI(title="Jimbo Connect API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def set_auth_cookie(response: Response, token: str):
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 7,
        path="/",
    )


# ---------- Auth ----------

@app.post("/api/auth/register")
async def register(payload: RegisterRequest, response: Response):
    existing = await users.find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    now = datetime.now(timezone.utc)
    doc = {
        "email": payload.email,
        "password_hash": hash_password(payload.password),
        "is_admin": False,
        "created_at": now,
        "profile": Profile(name=payload.name or "").model_dump(),
    }
    result = await users.insert_one(doc)
    doc["_id"] = result.inserted_id
    token = create_access_token(str(result.inserted_id))
    set_auth_cookie(response, token)
    return {"user": serialize_user(doc), "token": token}


@app.post("/api/auth/login")
async def login(payload: LoginRequest, response: Response):
    user = await users.find_one({"email": payload.email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(str(user["_id"]))
    set_auth_cookie(response, token)
    return {"user": serialize_user(user), "token": token}


@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@app.get("/api/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return serialize_user(user)


@app.post("/api/auth/refresh")
async def refresh(response: Response, user: dict = Depends(get_current_user)):
    token = create_access_token(str(user["_id"]))
    set_auth_cookie(response, token)
    return {"token": token}


# ---------- Profile ----------

@app.get("/api/profile")
async def get_my_profile(user: dict = Depends(get_current_user)):
    return serialize_user(user)


@app.put("/api/profile")
async def update_my_profile(
    payload: ProfileUpdateRequest, user: dict = Depends(get_current_user)
):
    current = Profile(**(user.get("profile") or {})).model_dump()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    current.update(updates)
    await users.update_one({"_id": user["_id"]}, {"$set": {"profile": current}})
    user["profile"] = current
    return serialize_user(user)


@app.post("/api/profile/photo")
async def upload_photo(
    payload: PhotoUploadRequest, user: dict = Depends(get_current_user)
):
    profile = user.get("profile") or {}
    profile["photo_url"] = payload.photo_data
    await users.update_one({"_id": user["_id"]}, {"$set": {"profile": profile}})
    user["profile"] = profile
    return serialize_user(user)


@app.get("/api/profile/{user_id}")
async def get_profile_by_id(user_id: str, _: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")
    target = await users.find_one({"_id": oid})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    return serialize_attendee(target)


# ---------- Events ----------

@app.post("/api/events")
async def create_event(
    payload: EventCreateRequest, admin: dict = Depends(get_current_admin)
):
    code = generate_join_code()
    while await events.find_one({"join_code": code}):
        code = generate_join_code()
    now = datetime.now(timezone.utc)
    doc = {
        "name": payload.name,
        "date": payload.date,
        "location": payload.location or "",
        "industry_tags": payload.industry_tags or [],
        "join_code": code,
        "created_by": admin["_id"],
        "created_at": now,
    }
    result = await events.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_event(doc, 0)


@app.get("/api/events")
async def list_events(_: dict = Depends(get_current_admin)):
    out = []
    async for e in events.find().sort("date", -1):
        count = await event_attendees.count_documents({"event_id": e["_id"]})
        out.append(serialize_event(e, count))
    return out


@app.get("/api/events/{event_id}")
async def get_event(event_id: str, user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    e = await events.find_one({"_id": oid})
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    if not user.get("is_admin"):
        joined = await event_attendees.find_one(
            {"event_id": oid, "user_id": user["_id"]}
        )
        if not joined:
            raise HTTPException(status_code=403, detail="Not joined to this event")
    count = await event_attendees.count_documents({"event_id": oid})
    return serialize_event(e, count)


@app.put("/api/events/{event_id}")
async def update_event(
    event_id: str,
    payload: EventUpdateRequest,
    _: dict = Depends(get_current_admin),
):
    try:
        oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if updates:
        await events.update_one({"_id": oid}, {"$set": updates})
    e = await events.find_one({"_id": oid})
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    count = await event_attendees.count_documents({"event_id": oid})
    return serialize_event(e, count)


@app.delete("/api/events/{event_id}")
async def delete_event(event_id: str, _: dict = Depends(get_current_admin)):
    try:
        oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    await event_attendees.delete_many({"event_id": oid})
    await events.delete_one({"_id": oid})
    return {"ok": True}


@app.post("/api/events/join/{code}")
async def join_event(code: str, user: dict = Depends(get_current_user)):
    e = await events.find_one({"join_code": code.upper()})
    if not e:
        raise HTTPException(status_code=404, detail="Invalid join code")
    existing = await event_attendees.find_one(
        {"event_id": e["_id"], "user_id": user["_id"]}
    )
    if not existing:
        await event_attendees.insert_one(
            {
                "event_id": e["_id"],
                "user_id": user["_id"],
                "joined_at": datetime.now(timezone.utc),
            }
        )
    count = await event_attendees.count_documents({"event_id": e["_id"]})
    return serialize_event(e, count)


@app.get("/api/events/{event_id}/attendees")
async def get_event_attendees(event_id: str, user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(event_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
    e = await events.find_one({"_id": oid})
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    if not user.get("is_admin"):
        joined = await event_attendees.find_one(
            {"event_id": oid, "user_id": user["_id"]}
        )
        if not joined:
            raise HTTPException(status_code=403, detail="Not joined to this event")
    out = []
    async for link in event_attendees.find({"event_id": oid}):
        attendee = await users.find_one({"_id": link["user_id"]})
        if attendee and not attendee.get("is_admin"):
            out.append(serialize_attendee(attendee))
    return out


@app.get("/api/my-events")
async def my_events(user: dict = Depends(get_current_user)):
    out = []
    async for link in event_attendees.find({"user_id": user["_id"]}).sort("joined_at", -1):
        e = await events.find_one({"_id": link["event_id"]})
        if e:
            count = await event_attendees.count_documents({"event_id": e["_id"]})
            out.append(serialize_event(e, count))
    return out


# ---------- Contacts ----------

@app.post("/api/contacts/save")
async def save_contact(
    payload: SaveContactRequest, user: dict = Depends(get_current_user)
):
    try:
        contact_oid = ObjectId(payload.contact_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid contact id")
    if contact_oid == user["_id"]:
        raise HTTPException(status_code=400, detail="Cannot save yourself")
    target = await users.find_one({"_id": contact_oid})
    if not target:
        raise HTTPException(status_code=404, detail="Contact not found")
    existing = await saved_contacts.find_one(
        {"owner_id": user["_id"], "contact_id": contact_oid}
    )
    if existing:
        if payload.note is not None:
            await saved_contacts.update_one(
                {"_id": existing["_id"]}, {"$set": {"note": payload.note}}
            )
            existing["note"] = payload.note
        return {
            "id": str(existing["_id"]),
            "contact_id": str(contact_oid),
            "note": existing.get("note", ""),
            "saved_at": existing["saved_at"],
            "contact": serialize_attendee(target),
        }
    now = datetime.now(timezone.utc)
    doc = {
        "owner_id": user["_id"],
        "contact_id": contact_oid,
        "note": payload.note or "",
        "saved_at": now,
    }
    result = await saved_contacts.insert_one(doc)
    return {
        "id": str(result.inserted_id),
        "contact_id": str(contact_oid),
        "note": doc["note"],
        "saved_at": now,
        "contact": serialize_attendee(target),
    }


@app.delete("/api/contacts/{contact_id}")
async def delete_saved_contact(
    contact_id: str, user: dict = Depends(get_current_user)
):
    try:
        contact_oid = ObjectId(contact_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid contact id")
    result = await saved_contacts.delete_one(
        {"owner_id": user["_id"], "contact_id": contact_oid}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Saved contact not found")
    return {"ok": True}


@app.get("/api/contacts")
async def list_saved_contacts(user: dict = Depends(get_current_user)):
    out = []
    async for sc in saved_contacts.find({"owner_id": user["_id"]}).sort("saved_at", -1):
        target = await users.find_one({"_id": sc["contact_id"]})
        if target:
            out.append(
                {
                    "id": str(sc["_id"]),
                    "contact_id": str(sc["contact_id"]),
                    "note": sc.get("note", ""),
                    "saved_at": sc["saved_at"],
                    "contact": serialize_attendee(target),
                }
            )
    return out


@app.put("/api/contacts/{contact_id}/note")
async def update_contact_note(
    contact_id: str,
    payload: NoteUpdateRequest,
    user: dict = Depends(get_current_user),
):
    try:
        contact_oid = ObjectId(contact_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid contact id")
    result = await saved_contacts.update_one(
        {"owner_id": user["_id"], "contact_id": contact_oid},
        {"$set": {"note": payload.note}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Saved contact not found")
    return {"ok": True, "note": payload.note}


@app.get("/api/contacts/{contact_id}/is-saved")
async def is_contact_saved(
    contact_id: str, user: dict = Depends(get_current_user)
):
    try:
        contact_oid = ObjectId(contact_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid contact id")
    sc = await saved_contacts.find_one(
        {"owner_id": user["_id"], "contact_id": contact_oid}
    )
    if not sc:
        return {"saved": False}
    return {
        "saved": True,
        "id": str(sc["_id"]),
        "note": sc.get("note", ""),
    }


# ---------- Admin ----------

@app.get("/api/admin/stats")
async def admin_stats(_: dict = Depends(get_current_admin)):
    total_users = await users.count_documents({"is_admin": {"$ne": True}})
    total_events = await events.count_documents({})
    total_connections = await saved_contacts.count_documents({})
    return {
        "total_users": total_users,
        "total_events": total_events,
        "total_connections": total_connections,
    }


@app.get("/api/health")
async def health():
    return {"ok": True}
