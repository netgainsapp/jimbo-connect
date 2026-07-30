import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException, Request, status
from passlib.context import CryptContext
import jwt
from bson import ObjectId
from dotenv import load_dotenv

from database import users

load_dotenv()

# Never ship a hardcoded fallback secret: a known signing key lets anyone forge
# tokens for any account. In production JWT_SECRET is provided by the platform
# (render.yaml generateValue). If it is somehow unset, fall back to a random
# per-process secret (sessions reset on restart) rather than a guessable literal.
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    JWT_SECRET = secrets.token_urlsafe(64)
    print(
        "WARNING: JWT_SECRET is not set; using a random per-process secret. "
        "Sessions will be invalidated on restart. Set JWT_SECRET in the "
        "environment for stable, secure tokens.",
        file=sys.stderr,
    )
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

COOKIE_NAME = "jimbo_token"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except jwt.InvalidTokenError:
        return None


async def get_current_user(request: Request) -> dict:
    # Cookie-only: the token rides the httpOnly session cookie (set on every
    # login/register/refresh). The frontend no longer sends a Bearer header, so
    # accepting one would only widen the surface for no benefit.
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = await users.find_one({"_id": oid})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_current_admin(request: Request) -> dict:
    user = await get_current_user(request)
    if not user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


async def get_current_user_optional(request: Request):
    """The signed-in user, or None when there is no valid session.

    For endpoints that must serve a logged-out visitor and a member from the
    same route, such as the Agenda Builder, which works before anyone has an
    account. Returns None instead of raising; a caller that needs a user must
    say so itself rather than assuming this gave them one.
    """
    try:
        return await get_current_user(request)
    except HTTPException:
        return None
