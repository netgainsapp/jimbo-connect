from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, UploadFile, File, Query, Header
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
import logging
import secrets
import uuid
import bcrypt
import jwt
import requests
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime, timezone, timedelta

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Config
JWT_ALGORITHM = "HS256"

def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]

# Storage Config
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "jimbo-connect"
storage_key = None

def init_storage():
    global storage_key
    if storage_key:
        return storage_key
    try:
        resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
        resp.raise_for_status()
        storage_key = resp.json()["storage_key"]
        logger.info("Storage initialized successfully")
        return storage_key
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
        return None

def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    if not key:
        raise HTTPException(status_code=500, detail="Storage not initialized")
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120
    )
    resp.raise_for_status()
    return resp.json()

def get_object(path: str) -> tuple:
    key = init_storage()
    if not key:
        raise HTTPException(status_code=500, detail="Storage not initialized")
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key}, timeout=60
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

# Password Hashing
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

# JWT Token Management
def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "exp": datetime.now(timezone.utc) + timedelta(minutes=15), "type": "access"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "refresh"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)

# Auth Helper
async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user["id"] = str(user["_id"])
        del user["_id"]
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_optional_user(request: Request) -> Optional[dict]:
    try:
        return await get_current_user(request)
    except HTTPException:
        return None

async def require_admin(request: Request) -> dict:
    user = await get_current_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# Brute Force Protection
async def check_brute_force(identifier: str):
    attempt = await db.login_attempts.find_one({"identifier": identifier})
    if attempt and attempt.get("count", 0) >= 5:
        lockout_time = attempt.get("locked_until")
        if lockout_time and datetime.now(timezone.utc) < lockout_time:
            raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.")
        elif lockout_time:
            await db.login_attempts.delete_one({"identifier": identifier})

async def record_failed_attempt(identifier: str):
    attempt = await db.login_attempts.find_one({"identifier": identifier})
    if attempt:
        new_count = attempt.get("count", 0) + 1
        update = {"$set": {"count": new_count}}
        if new_count >= 5:
            update["$set"]["locked_until"] = datetime.now(timezone.utc) + timedelta(minutes=15)
        await db.login_attempts.update_one({"identifier": identifier}, update)
    else:
        await db.login_attempts.insert_one({"identifier": identifier, "count": 1})

async def clear_failed_attempts(identifier: str):
    await db.login_attempts.delete_one({"identifier": identifier})

# Pydantic Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    role_title: Optional[str] = None
    company: Optional[str] = None
    bio: Optional[str] = None
    looking_for: Optional[str] = None
    industry: Optional[str] = None
    interests: Optional[List[str]] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    table_cohort: Optional[str] = None

class EventCreate(BaseModel):
    name: str
    description: Optional[str] = None
    date: str
    location: Optional[str] = None
    industries: Optional[List[str]] = None

class EventUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None
    location: Optional[str] = None
    industries: Optional[List[str]] = None
    is_active: Optional[bool] = None

class SaveContactRequest(BaseModel):
    contact_user_id: str

class NoteUpdate(BaseModel):
    note: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ============ AUTH ENDPOINTS ============

@api_router.post("/auth/register")
async def register(data: UserRegister, response: Response, request: Request):
    email = data.email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_doc = {
        "email": email,
        "password_hash": hash_password(data.password),
        "name": data.name,
        "role": "user",
        "profile_photo": None,
        "role_title": None,
        "company": None,
        "bio": None,
        "looking_for": None,
        "industry": None,
        "interests": [],
        "linkedin_url": None,
        "phone": None,
        "table_cohort": None,
        "events": [],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=900, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    
    return {"id": user_id, "email": email, "name": data.name, "role": "user"}

@api_router.post("/auth/login")
async def login(data: UserLogin, response: Response, request: Request):
    email = data.email.lower()
    ip = request.client.host if request.client else "unknown"
    identifier = f"{ip}:{email}"
    
    await check_brute_force(identifier)
    
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(data.password, user["password_hash"]):
        await record_failed_attempt(identifier)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    await clear_failed_attempts(identifier)
    
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=900, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    
    return {
        "id": user_id,
        "email": user["email"],
        "name": user["name"],
        "role": user.get("role", "user"),
        "profile_photo": user.get("profile_photo")
    }

@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out"}

@api_router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user

@api_router.post("/auth/refresh")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        access_token = create_access_token(str(user["_id"]), user["email"])
        response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=900, path="/")
        return {"message": "Token refreshed"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@api_router.post("/auth/forgot-password")
async def forgot_password(data: ForgotPasswordRequest):
    email = data.email.lower()
    user = await db.users.find_one({"email": email})
    if user:
        token = secrets.token_urlsafe(32)
        await db.password_reset_tokens.insert_one({
            "token": token,
            "user_id": str(user["_id"]),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "used": False
        })
        logger.info(f"Password reset link: /reset-password?token={token}")
    return {"message": "If email exists, reset link was sent"}

@api_router.post("/auth/reset-password")
async def reset_password(data: ResetPasswordRequest):
    token_doc = await db.password_reset_tokens.find_one({"token": data.token, "used": False})
    if not token_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    if datetime.now(timezone.utc) > token_doc["expires_at"]:
        raise HTTPException(status_code=400, detail="Token expired")
    
    await db.users.update_one(
        {"_id": ObjectId(token_doc["user_id"])},
        {"$set": {"password_hash": hash_password(data.new_password)}}
    )
    await db.password_reset_tokens.update_one({"token": data.token}, {"$set": {"used": True}})
    return {"message": "Password reset successfully"}

# ============ PROFILE ENDPOINTS ============

@api_router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    return user

@api_router.put("/profile")
async def update_profile(data: ProfileUpdate, user: dict = Depends(get_current_user)):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": update_data})
    updated = await db.users.find_one({"_id": ObjectId(user["id"])}, {"_id": 0, "password_hash": 0})
    updated["id"] = user["id"]
    return updated

@api_router.post("/profile/photo")
async def upload_profile_photo(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    path = f"{APP_NAME}/profiles/{user['id']}/{uuid.uuid4()}.{ext}"
    data = await file.read()
    
    result = put_object(path, data, file.content_type or "image/jpeg")
    
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": {"profile_photo": result["path"]}})
    
    return {"path": result["path"]}

@api_router.get("/files/{path:path}")
async def get_file(path: str, auth: str = Query(None)):
    try:
        data, content_type = get_object(path)
        return Response(content=data, media_type=content_type)
    except Exception as e:
        raise HTTPException(status_code=404, detail="File not found")

@api_router.get("/profile/{user_id}")
async def get_user_profile(user_id: str, current_user: dict = Depends(get_current_user)):
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)}, {"password_hash": 0})
    except:
        raise HTTPException(status_code=404, detail="User not found")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["id"] = str(user["_id"])
    del user["_id"]
    return user

# ============ EVENT ENDPOINTS ============

def generate_event_code():
    return secrets.token_urlsafe(8)

@api_router.post("/events")
async def create_event(data: EventCreate, admin: dict = Depends(require_admin)):
    event_doc = {
        "name": data.name,
        "description": data.description,
        "date": data.date,
        "location": data.location,
        "industries": data.industries or [],
        "code": generate_event_code(),
        "created_by": admin["id"],
        "is_active": True,
        "attendees": [],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.events.insert_one(event_doc)
    event_doc["id"] = str(result.inserted_id)
    del event_doc["_id"]
    return event_doc

@api_router.get("/events")
async def list_events(admin: dict = Depends(require_admin)):
    events = await db.events.find({}, {"_id": 1, "name": 1, "date": 1, "location": 1, "code": 1, "is_active": 1, "attendees": 1}).to_list(1000)
    for e in events:
        e["id"] = str(e["_id"])
        del e["_id"]
        e["attendee_count"] = len(e.get("attendees", []))
    return events

@api_router.get("/events/{event_id}")
async def get_event(event_id: str, user: dict = Depends(get_current_user)):
    try:
        event = await db.events.find_one({"_id": ObjectId(event_id)})
    except:
        raise HTTPException(status_code=404, detail="Event not found")
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event["id"] = str(event["_id"])
    del event["_id"]
    return event

@api_router.put("/events/{event_id}")
async def update_event(event_id: str, data: EventUpdate, admin: dict = Depends(require_admin)):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        await db.events.update_one({"_id": ObjectId(event_id)}, {"$set": update_data})
    event = await db.events.find_one({"_id": ObjectId(event_id)})
    event["id"] = str(event["_id"])
    del event["_id"]
    return event

@api_router.delete("/events/{event_id}")
async def delete_event(event_id: str, admin: dict = Depends(require_admin)):
    await db.events.delete_one({"_id": ObjectId(event_id)})
    return {"message": "Event deleted"}

@api_router.post("/events/join/{code}")
async def join_event(code: str, user: dict = Depends(get_current_user)):
    event = await db.events.find_one({"code": code})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not event.get("is_active", True):
        raise HTTPException(status_code=400, detail="Event is no longer active")
    
    user_id = user["id"]
    event_id = str(event["_id"])
    
    # Add user to event attendees if not already
    if user_id not in event.get("attendees", []):
        await db.events.update_one({"_id": event["_id"]}, {"$addToSet": {"attendees": user_id}})
    
    # Add event to user's events if not already
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$addToSet": {"events": event_id}})
    
    return {"event_id": event_id, "name": event["name"]}

@api_router.get("/events/{event_id}/attendees")
async def get_event_attendees(
    event_id: str,
    search: str = Query(None),
    industry: str = Query(None),
    interests: str = Query(None),
    table_cohort: str = Query(None),
    user: dict = Depends(get_current_user)
):
    try:
        event = await db.events.find_one({"_id": ObjectId(event_id)})
    except:
        raise HTTPException(status_code=404, detail="Event not found")
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    attendee_ids = event.get("attendees", [])
    if not attendee_ids:
        return []
    
    # Build query
    query = {"_id": {"$in": [ObjectId(aid) for aid in attendee_ids]}}
    
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"company": {"$regex": search, "$options": "i"}},
            {"role_title": {"$regex": search, "$options": "i"}},
            {"looking_for": {"$regex": search, "$options": "i"}}
        ]
    
    if industry:
        query["industry"] = {"$regex": industry, "$options": "i"}
    
    if interests:
        interest_list = [i.strip() for i in interests.split(",")]
        query["interests"] = {"$in": interest_list}
    
    if table_cohort:
        query["table_cohort"] = {"$regex": table_cohort, "$options": "i"}
    
    attendees = await db.users.find(query, {"password_hash": 0}).to_list(1000)
    
    for a in attendees:
        a["id"] = str(a["_id"])
        del a["_id"]
    
    return attendees

@api_router.get("/my-events")
async def get_my_events(user: dict = Depends(get_current_user)):
    event_ids = user.get("events", [])
    if not event_ids:
        return []
    
    events = await db.events.find(
        {"_id": {"$in": [ObjectId(eid) for eid in event_ids]}},
        {"_id": 1, "name": 1, "date": 1, "location": 1, "code": 1, "is_active": 1, "attendees": 1}
    ).to_list(100)
    
    for e in events:
        e["id"] = str(e["_id"])
        del e["_id"]
        e["attendee_count"] = len(e.get("attendees", []))
    
    return events

# ============ CONTACTS & NOTES ENDPOINTS ============

@api_router.post("/contacts/save")
async def save_contact(data: SaveContactRequest, user: dict = Depends(get_current_user)):
    existing = await db.saved_contacts.find_one({
        "user_id": user["id"],
        "contact_user_id": data.contact_user_id
    })
    if existing:
        raise HTTPException(status_code=400, detail="Contact already saved")
    
    contact_doc = {
        "user_id": user["id"],
        "contact_user_id": data.contact_user_id,
        "note": "",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.saved_contacts.insert_one(contact_doc)
    return {"message": "Contact saved"}

@api_router.delete("/contacts/{contact_user_id}")
async def remove_contact(contact_user_id: str, user: dict = Depends(get_current_user)):
    await db.saved_contacts.delete_one({
        "user_id": user["id"],
        "contact_user_id": contact_user_id
    })
    return {"message": "Contact removed"}

@api_router.get("/contacts")
async def get_saved_contacts(user: dict = Depends(get_current_user)):
    saved = await db.saved_contacts.find({"user_id": user["id"]}).to_list(1000)
    
    if not saved:
        return []
    
    contact_ids = [s["contact_user_id"] for s in saved]
    users = await db.users.find(
        {"_id": {"$in": [ObjectId(cid) for cid in contact_ids]}},
        {"password_hash": 0}
    ).to_list(1000)
    
    users_map = {str(u["_id"]): u for u in users}
    
    result = []
    for s in saved:
        contact_user = users_map.get(s["contact_user_id"])
        if contact_user:
            contact_user["id"] = str(contact_user["_id"])
            del contact_user["_id"]
            contact_user["note"] = s.get("note", "")
            contact_user["saved_at"] = s.get("created_at")
            result.append(contact_user)
    
    return result

@api_router.put("/contacts/{contact_user_id}/note")
async def update_contact_note(contact_user_id: str, data: NoteUpdate, user: dict = Depends(get_current_user)):
    result = await db.saved_contacts.update_one(
        {"user_id": user["id"], "contact_user_id": contact_user_id},
        {"$set": {"note": data.note}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"message": "Note updated"}

@api_router.get("/contacts/{contact_user_id}/is-saved")
async def check_if_saved(contact_user_id: str, user: dict = Depends(get_current_user)):
    existing = await db.saved_contacts.find_one({
        "user_id": user["id"],
        "contact_user_id": contact_user_id
    })
    return {"is_saved": existing is not None, "note": existing.get("note", "") if existing else ""}

# ============ ADMIN STATS ============

@api_router.get("/admin/stats")
async def get_admin_stats(admin: dict = Depends(require_admin)):
    total_users = await db.users.count_documents({})
    total_events = await db.events.count_documents({})
    active_events = await db.events.count_documents({"is_active": True})
    total_connections = await db.saved_contacts.count_documents({})
    
    return {
        "total_users": total_users,
        "total_events": total_events,
        "active_events": active_events,
        "total_connections": total_connections
    }

# ============ STARTUP & SHUTDOWN ============

@app.on_event("startup")
async def startup():
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.events.create_index("code", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.saved_contacts.create_index([("user_id", 1), ("contact_user_id", 1)], unique=True)
    
    # Initialize storage
    init_storage()
    
    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@jimboconnect.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        hashed = hash_password(admin_password)
        await db.users.insert_one({
            "email": admin_email,
            "password_hash": hashed,
            "name": "Admin",
            "role": "admin",
            "profile_photo": None,
            "role_title": "Platform Administrator",
            "company": "Jimbo Connect",
            "bio": "Platform administrator",
            "looking_for": None,
            "industry": "Technology",
            "interests": [],
            "linkedin_url": None,
            "phone": None,
            "table_cohort": None,
            "events": [],
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        logger.info(f"Admin user created: {admin_email}")
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})
        logger.info("Admin password updated")
    
    # Write test credentials
    Path("/app/memory").mkdir(parents=True, exist_ok=True)
    with open("/app/memory/test_credentials.md", "w") as f:
        f.write(f"# Test Credentials\n\n")
        f.write(f"## Admin Account\n")
        f.write(f"- Email: {admin_email}\n")
        f.write(f"- Password: {admin_password}\n")
        f.write(f"- Role: admin\n\n")
        f.write(f"## Auth Endpoints\n")
        f.write(f"- POST /api/auth/register\n")
        f.write(f"- POST /api/auth/login\n")
        f.write(f"- POST /api/auth/logout\n")
        f.write(f"- GET /api/auth/me\n")
        f.write(f"- POST /api/auth/refresh\n")

@app.on_event("shutdown")
async def shutdown():
    client.close()

# Include the router in the main app
app.include_router(api_router)

# CORS
frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
cors_origins = os.environ.get('CORS_ORIGINS', '*')
origins = [frontend_url] if cors_origins == '*' else cors_origins.split(',')

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

@api_router.get("/")
async def root():
    return {"message": "Jimbo Connect API"}
