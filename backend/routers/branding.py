"""/api/branding* routes: self-serve host branding (Pro), public logo serving,
and the admin kill switch. See docs/HOST-BRANDING-SPEC.md."""
from datetime import datetime, timezone

from bson import Binary, ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile

import billing
import branding
from auth import get_current_admin, get_current_user
from database import users

router = APIRouter()

UPGRADE_MSG = "Host branding is a Pro feature. Upgrade to put your logo and color on your event pages and guest emails."
LOCKED_MSG = "Branding is disabled for this account."


def _require_branding_access(user: dict):
    if user.get("branding_locked"):
        raise HTTPException(status_code=403, detail=LOCKED_MSG)
    if not branding.plan_allows(user):
        raise HTTPException(status_code=403, detail=UPGRADE_MSG)


def _own_status(user: dict) -> dict:
    b = user.get("branding") or {}
    return {
        "allowed": branding.plan_allows(user) and not user.get("branding_locked"),
        "active": branding.branding_active(user),
        "locked": bool(user.get("branding_locked")),
        "plan": billing.plan_of(user),
        "accent": b.get("accent") or "",
        "accent_dark": b.get("accent_dark") or "",
        "has_logo": bool(b.get("logo")),
        "logo_url": branding.logo_url(user),
    }


@router.get("/api/branding")
async def get_branding(user: dict = Depends(get_current_user)):
    return _own_status(user)


@router.put("/api/branding")
async def set_accent(payload: dict, user: dict = Depends(get_current_user)):
    _require_branding_access(user)
    try:
        accent = branding.normalize_accent(payload.get("accent"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    accent_dark = branding.derive_accent_dark(accent)
    await users.update_one(
        {"_id": user["_id"]},
        {"$set": {"branding.accent": accent, "branding.accent_dark": accent_dark}},
    )
    fresh = await users.find_one({"_id": user["_id"]})
    return _own_status(fresh)


@router.post("/api/branding/logo")
async def upload_logo(
    file: UploadFile = File(...), user: dict = Depends(get_current_user)
):
    _require_branding_access(user)
    data = await file.read()
    try:
        clean = branding.process_logo(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "branding.logo": Binary(clean),
                "branding.logo_updated_at": datetime.now(timezone.utc),
            }
        },
    )
    fresh = await users.find_one({"_id": user["_id"]})
    return _own_status(fresh)


@router.delete("/api/branding")
async def reset_branding(user: dict = Depends(get_current_user)):
    await users.update_one({"_id": user["_id"]}, {"$unset": {"branding": ""}})
    fresh = await users.find_one({"_id": user["_id"]})
    return _own_status(fresh)


@router.get("/api/branding/{user_id}/logo.png")
async def serve_logo(user_id: str):
    """Public: guests and email clients load host logos anonymously. Serves
    only while the host's branding is active, so dormant or locked brands
    disappear everywhere at once."""
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    host = await users.find_one({"_id": oid})
    if not host or not branding.branding_active(host):
        raise HTTPException(status_code=404, detail="Not found")
    logo = (host.get("branding") or {}).get("logo")
    if not logo:
        raise HTTPException(status_code=404, detail="Not found")
    return Response(
        content=bytes(logo),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.delete("/api/admin/branding/{user_id}")
async def admin_kill_branding(user_id: str, _: dict = Depends(get_current_admin)):
    """Abuse response, not an approval gate: clears the branding and locks the
    account out of re-adding it until the flag is lifted in the database."""
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")
    result = await users.update_one(
        {"_id": oid},
        {"$unset": {"branding": ""}, "$set": {"branding_locked": True}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True}
