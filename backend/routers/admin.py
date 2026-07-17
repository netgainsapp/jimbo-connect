"""/api/admin/* and /api/email-templates* routes. Moved verbatim from
server.py (M13). Route registration order is preserved from the original file."""
import asyncio
import secrets
import string
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends, Response
from bson import ObjectId

from database import (
    users,
    events,
    event_attendees,
    saved_contacts,
    email_templates,
    outreach_leads,
)
import email_send
import outreach
from news.schema import NewsArticleInput
from sales_templates import SalesTemplateInput
from template_seeds import DEFAULT_TEMPLATES, CATEGORIES as TEMPLATE_CATEGORIES
from auth import hash_password, get_current_admin
from models import (
    Profile,
    BulkImportRequest,
    CheckEmailsRequest,
    TemplateUpdateRequest,
    BlogFlagRequest,
    OutreachAddRequest,
)
from core import (
    FRONTEND_URL,
    serialize_template,
    render_email_template,
    body_to_html,
    _hard_delete_user,
)

router = APIRouter()


@router.delete("/api/admin/users/{user_id}")
async def admin_delete_user(
    user_id: str, admin: dict = Depends(get_current_admin)
):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")
    if oid == admin["_id"]:
        raise HTTPException(status_code=400, detail="Use 'delete my account' for self")
    target = await users.find_one({"_id": oid})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    await _hard_delete_user(oid)
    return {"ok": True}


# ---------- Admin ----------

@router.get("/api/admin/users")
async def admin_list_users(_: dict = Depends(get_current_admin)):
    all_users = (
        await users.find({"is_admin": {"$ne": True}})
        .sort("created_at", -1)
        .to_list(None)
    )
    links_by_user: dict = {}
    if all_users:
        async for link in event_attendees.find(
            {"user_id": {"$in": [u["_id"] for u in all_users]}}
        ):
            links_by_user.setdefault(link["user_id"], []).append(
                str(link["event_id"])
            )
    out = []
    for u in all_users:
        event_ids = links_by_user.get(u["_id"], [])
        out.append(
            {
                "id": str(u["_id"]),
                "email": u["email"],
                "profile": Profile(**(u.get("profile") or {})).model_dump(),
                "event_count": len(event_ids),
                "event_ids": event_ids,
                "created_at": u.get("created_at"),
            }
        )
    return out


@router.post("/api/admin/reseed-templates")
async def admin_reseed_templates(_: dict = Depends(get_current_admin)):
    """Force-seed any missing default templates. Idempotent: only inserts
    missing rows. Admin-only, POST-only: a state-changing GET would be
    CSRF-reachable cross-site without a preflight (simple request) since the
    session cookie is SameSite=None."""
    inserted = 0
    for t in DEFAULT_TEMPLATES:
        existing = await email_templates.find_one({"template_id": t["template_id"]})
        if existing:
            continue
        await email_templates.insert_one(
            {**t, "updated_at": datetime.now(timezone.utc)}
        )
        inserted += 1
    return {"inserted": inserted}


@router.get("/api/admin/stats")
async def admin_stats(_: dict = Depends(get_current_admin)):
    total_users = await users.count_documents({"is_admin": {"$ne": True}})
    total_events = await events.count_documents({})
    total_connections = await saved_contacts.count_documents({})
    return {
        "total_users": total_users,
        "total_events": total_events,
        "total_connections": total_connections,
    }


@router.get("/api/admin/analytics")
async def admin_analytics(days: int = 30, _: dict = Depends(get_current_admin)):
    """Platform metrics for the dashboard: totals, engagement, plan mix, and a
    daily signups series over the trailing window."""
    from database import messages, db as _db

    days = max(7, min(days, 90))
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    total_users = await users.count_documents({"is_admin": {"$ne": True}})
    total_events = await events.count_documents({})
    total_contacts = await saved_contacts.count_documents({})
    total_messages = await messages.count_documents({})
    total_attendees = await event_attendees.count_documents({})

    # Active hosts: distinct users who have created at least one event.
    host_ids = await events.distinct("created_by")
    active_hosts = len(host_ids)

    avg_attendees = round(total_attendees / total_events, 1) if total_events else 0.0

    # Plan mix (non-admin users). Absent field counts as free.
    plan_mix = {"free": 0, "starter": 0, "pro": 0}
    async for row in users.aggregate(
        [
            {"$match": {"is_admin": {"$ne": True}}},
            {"$group": {"_id": {"$ifNull": ["$plan", "free"]}, "n": {"$sum": 1}}},
        ]
    ):
        key = row["_id"] if row["_id"] in plan_mix else "free"
        plan_mix[key] += row["n"]

    # Daily signups over the window.
    counts = {}
    async for row in users.aggregate(
        [
            {"$match": {"is_admin": {"$ne": True}, "created_at": {"$gte": cutoff}}},
            {
                "$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "n": {"$sum": 1},
                }
            },
        ]
    ):
        counts[row["_id"]] = row["n"]
    series = []
    for i in range(days):
        d = (cutoff + timedelta(days=i + 1)).strftime("%Y-%m-%d")
        series.append({"date": d, "count": counts.get(d, 0)})
    signups_in_window = sum(p["count"] for p in series)

    return {
        "totals": {
            "users": total_users,
            "events": total_events,
            "contacts_saved": total_contacts,
            "messages_sent": total_messages,
            "active_hosts": active_hosts,
            "avg_attendees_per_event": avg_attendees,
        },
        "plan_mix": plan_mix,
        "window_days": days,
        "signups_in_window": signups_in_window,
        "signups_series": series,
    }


@router.post("/api/admin/users/check-emails")
async def admin_check_emails(
    payload: CheckEmailsRequest, _: dict = Depends(get_current_admin)
):
    emails = [str(e).lower().strip() for e in payload.emails if e]
    matches = []
    found_set = set()
    if emails:
        cursor = users.find({"email": {"$in": emails}})
        async for u in cursor:
            profile = u.get("profile") or {}
            matches.append(
                {
                    "id": str(u["_id"]),
                    "email": u["email"],
                    "is_admin": bool(u.get("is_admin")),
                    "profile": {
                        "name": profile.get("name", ""),
                        "role": profile.get("role", ""),
                        "company": profile.get("company", ""),
                        "photo_url": profile.get("photo_url", ""),
                    },
                }
            )
            found_set.add(u["email"])
    not_found = [e for e in emails if e not in found_set]
    return {"matches": matches, "not_found": not_found}


@router.get("/api/email-templates")
async def list_email_templates_api(_: dict = Depends(get_current_admin)):
    out = []
    async for doc in email_templates.find().sort("_id", 1):
        out.append(serialize_template(doc))
    return {"templates": out, "categories": TEMPLATE_CATEGORIES}


@router.put("/api/email-templates/{template_id}")
async def update_email_template_api(
    template_id: str,
    payload: TemplateUpdateRequest,
    _: dict = Depends(get_current_admin),
):
    updates = {}
    if payload.subject is not None:
        updates["subject"] = payload.subject
    if payload.body is not None:
        updates["body"] = payload.body
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")
    updates["updated_at"] = datetime.now(timezone.utc)
    result = await email_templates.update_one(
        {"template_id": template_id}, {"$set": updates}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    doc = await email_templates.find_one({"template_id": template_id})
    return serialize_template(doc)


@router.post("/api/email-templates/{template_id}/reset")
async def reset_email_template_api(
    template_id: str, _: dict = Depends(get_current_admin)
):
    default = next(
        (t for t in DEFAULT_TEMPLATES if t["template_id"] == template_id), None
    )
    if not default:
        raise HTTPException(status_code=404, detail="No default for this template")
    await email_templates.update_one(
        {"template_id": template_id},
        {"$set": {**default, "updated_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    doc = await email_templates.find_one({"template_id": template_id})
    return serialize_template(doc)


@router.post("/api/admin/users/bulk-import")
async def admin_bulk_import(
    payload: BulkImportRequest, admin: dict = Depends(get_current_admin)
):
    event_oid = None
    event_doc = None
    if payload.event_id:
        try:
            event_oid = ObjectId(payload.event_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid event id")
        event_doc = await events.find_one({"_id": event_oid})
        if not event_doc:
            raise HTTPException(status_code=404, detail="Event not found")

    now = datetime.now(timezone.utc)
    created = 0
    skipped = 0
    added_to_event = 0
    accounts: list = []
    errors: list = []

    for row in payload.rows:
        email = row.email.lower().strip()
        try:
            existing = await users.find_one({"email": email})
            if existing:
                skipped += 1
                user_id = existing["_id"]
            else:
                temp_password = (
                    payload.default_password
                    or "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
                )
                profile = {
                    "name": row.name or "",
                    "role": row.role or "",
                    "company": row.company or "",
                    "industry": row.industry or "",
                    "bio": row.bio or "",
                    "looking_for": row.looking_for or "",
                    "phone": row.phone or "",
                    "linkedin": row.linkedin or "",
                    "photo_url": "",
                }
                doc = {
                    "email": email,
                    # Off the event loop: 500 rows of bcrypt would otherwise
                    # freeze the API for the whole import.
                    "password_hash": await asyncio.to_thread(
                        hash_password, temp_password
                    ),
                    "is_admin": False,
                    "created_at": now,
                    "profile": profile,
                    "email_verified": False,
                }
                result = await users.insert_one(doc)
                user_id = result.inserted_id
                created += 1
                # Plaintext credentials go to ONE channel: the invitation email
                # when Resend is configured, or the API response as an explicit
                # fallback so the admin can distribute them by hand. Never both.
                if not email_send.is_configured():
                    accounts.append({"email": email, "password": temp_password})

                # Send invitation email if Resend is configured (send_email
                # itself skips hard-bounced addresses).
                if email_send.is_configured():
                    admin_profile = admin.get("profile") or {}
                    rendered = await render_email_template(
                        "invitation",
                        {
                            "attendee_name": row.name or "",
                            "attendee_email": email,
                            "temp_password": temp_password,
                            "event_name": event_doc["name"] if event_doc else "",
                            "event_date": event_doc["date"].strftime("%B %d, %Y")
                            if event_doc
                            else "",
                            "event_location": event_doc.get("location", "")
                            if event_doc
                            else "",
                            "host_name": admin_profile.get("name") or "Jim",
                            "site_url": FRONTEND_URL,
                        },
                    )
                    if rendered:
                        await email_send.send_email(
                            to=email,
                            subject=rendered["subject"],
                            html=body_to_html(rendered["body"]),
                            text=rendered["body"],
                        )

            if event_oid:
                already = await event_attendees.find_one(
                    {"event_id": event_oid, "user_id": user_id}
                )
                if not already:
                    await event_attendees.insert_one(
                        {
                            "event_id": event_oid,
                            "user_id": user_id,
                            "joined_at": now,
                        }
                    )
                    added_to_event += 1
        except Exception as e:
            errors.append({"email": email, "error": str(e)})

    return {
        "created": created,
        "skipped": skipped,
        "added_to_event": added_to_event,
        "errors": errors,
        "accounts": accounts,
    }


# ---------- Outreach cockpit (stages host-acquisition leads, hands off to
# signal-scout for sending). Admin only. ----------

def _serialize_lead(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "email": doc.get("email", ""),
        "name": doc.get("name", ""),
        "company": doc.get("company", ""),
        "role": doc.get("role", ""),
        "source": doc.get("source", ""),
        "status": doc.get("status", "new"),
        "created_at": doc.get("created_at"),
        "pushed_at": doc.get("pushed_at"),
    }


@router.get("/api/admin/outreach/status")
async def outreach_status(_: dict = Depends(get_current_admin)):
    total = await outreach_leads.count_documents({})
    pushed = await outreach_leads.count_documents({"status": "pushed"})
    return {
        "configured": outreach.is_configured(),
        "signal_scout_url": outreach.SIGNAL_SCOUT_URL or None,
        "total": total,
        "pushed": pushed,
        "new": total - pushed,
    }


@router.get("/api/admin/outreach/leads")
async def outreach_list(_: dict = Depends(get_current_admin)):
    docs = await outreach_leads.find({}).sort("created_at", -1).to_list(1000)
    return [_serialize_lead(d) for d in docs]


@router.post("/api/admin/outreach/leads")
async def outreach_add(
    payload: OutreachAddRequest, _: dict = Depends(get_current_admin)
):
    now = datetime.now(timezone.utc)
    added = 0
    for lead in payload.leads:
        email = str(lead.email).lower().strip()
        res = await outreach_leads.update_one(
            {"email": email},
            {
                "$setOnInsert": {
                    "email": email,
                    "name": lead.name or "",
                    "company": lead.company or "",
                    "role": lead.role or "",
                    "source": lead.source or "",
                    "status": "new",
                    "created_at": now,
                }
            },
            upsert=True,
        )
        if res.upserted_id is not None:
            added += 1
    return {"added": added, "received": len(payload.leads)}


@router.delete("/api/admin/outreach/leads/{lead_id}")
async def outreach_remove(lead_id: str, _: dict = Depends(get_current_admin)):
    try:
        oid = ObjectId(lead_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    res = await outreach_leads.delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"ok": True}


@router.get("/api/admin/outreach/leads.csv")
async def outreach_csv(_: dict = Depends(get_current_admin)):
    docs = await outreach_leads.find({}).sort("created_at", -1).to_list(None)
    return Response(
        content=outreach.to_csv(docs),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=intro-connect-leads.csv"
        },
    )


@router.post("/api/admin/outreach/push")
async def outreach_push(_: dict = Depends(get_current_admin)):
    docs = await outreach_leads.find({"status": {"$ne": "pushed"}}).to_list(None)
    if not docs:
        return {"ok": False, "skipped": "no_new_leads"}
    result = await outreach.push_to_signal_scout(docs)
    if result.get("ok"):
        now = datetime.now(timezone.utc)
        await outreach_leads.update_many(
            {"_id": {"$in": [d["_id"] for d in docs]}},
            {"$set": {"status": "pushed", "pushed_at": now}},
        )
    return result


def _serialize_blog_post(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "slug": doc.get("slug", ""),
        "title": doc.get("title", ""),
        "summary": doc.get("summary", ""),
        "status": doc.get("status", "draft"),
        "guardrail_reasons": doc.get("guardrail_reasons", []),
        "topic_id": doc.get("topic_id"),
        "created_at": doc.get("created_at"),
        "published_at": doc.get("published_at"),
    }


@router.post("/api/admin/blog/run")
async def admin_blog_run(_: dict = Depends(get_current_admin)):
    from blog.generate import run_once

    return await run_once()


@router.get("/api/admin/blog/flags")
async def admin_blog_flags(_: dict = Depends(get_current_admin)):
    from blog.flags import get_flags

    return await get_flags()


@router.put("/api/admin/blog/flags")
async def admin_blog_set_flag(
    payload: BlogFlagRequest, _: dict = Depends(get_current_admin)
):
    from blog.flags import set_flag, get_flags

    try:
        await set_flag(payload.name, payload.value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Unknown flag")
    return await get_flags()


@router.get("/api/admin/blog/posts")
async def admin_blog_posts(_: dict = Depends(get_current_admin)):
    from blog.store import list_all

    posts = await list_all()
    return [_serialize_blog_post(p) for p in posts]


@router.post("/api/admin/blog/posts/{post_id}/publish")
async def admin_blog_publish(post_id: str, _: dict = Depends(get_current_admin)):
    from blog.store import publish_post

    res = await publish_post(post_id)
    if res is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if res.get("error"):
        raise HTTPException(
            status_code=400,
            detail={"error": res["error"], "reasons": res.get("reasons", [])},
        )
    return _serialize_blog_post(res)


@router.post("/api/admin/blog/posts/{post_id}/unpublish")
async def admin_blog_unpublish(post_id: str, _: dict = Depends(get_current_admin)):
    from blog.store import unpublish_post

    res = await unpublish_post(post_id)
    if res is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return _serialize_blog_post(res)


# ---------- Admin: news (human-authored, source-attributed) ----------

def _serialize_news(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "slug": doc.get("slug", ""),
        "headline": doc.get("headline", ""),
        "summary": doc.get("summary", ""),
        "source_url": doc.get("source_url", ""),
        "sources": doc.get("sources", []),
        "event_date": doc.get("event_date"),
        "status": doc.get("status", "draft"),
        "created_at": doc.get("created_at"),
        "published_at": doc.get("published_at"),
    }


@router.get("/api/admin/news")
async def admin_news_list(_: dict = Depends(get_current_admin)):
    from news.store import list_all

    return [_serialize_news(a) for a in await list_all()]


@router.post("/api/admin/news")
async def admin_news_create(
    payload: NewsArticleInput, _: dict = Depends(get_current_admin)
):
    from news.store import create_article

    doc = await create_article(payload)
    return _serialize_news(doc)


@router.put("/api/admin/news/{article_id}")
async def admin_news_update(
    article_id: str, payload: NewsArticleInput, _: dict = Depends(get_current_admin)
):
    from news.store import update_article

    doc = await update_article(article_id, payload)
    if doc is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return _serialize_news(doc)


@router.delete("/api/admin/news/{article_id}")
async def admin_news_delete(article_id: str, _: dict = Depends(get_current_admin)):
    from news.store import delete_article

    if not await delete_article(article_id):
        raise HTTPException(status_code=404, detail="Article not found")
    return {"ok": True}


@router.post("/api/admin/news/{article_id}/publish")
async def admin_news_publish(article_id: str, _: dict = Depends(get_current_admin)):
    from news.store import publish_article

    res = await publish_article(article_id)
    if res is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return _serialize_news(res)


@router.post("/api/admin/news/{article_id}/unpublish")
async def admin_news_unpublish(article_id: str, _: dict = Depends(get_current_admin)):
    from news.store import unpublish_article

    res = await unpublish_article(article_id)
    if res is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return _serialize_news(res)


# ---------- Admin: sales / outreach template library (copy-paste) ----------

@router.get("/api/admin/sales-templates")
async def admin_sales_list(_: dict = Depends(get_current_admin)):
    import sales_templates

    return await sales_templates.list_all()


@router.post("/api/admin/sales-templates")
async def admin_sales_create(
    payload: SalesTemplateInput, _: dict = Depends(get_current_admin)
):
    import sales_templates

    return await sales_templates.create(payload)


@router.put("/api/admin/sales-templates/{tid}")
async def admin_sales_update(
    tid: str, payload: SalesTemplateInput, _: dict = Depends(get_current_admin)
):
    import sales_templates

    out = await sales_templates.update(tid, payload)
    if out is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return out


@router.post("/api/admin/sales-templates/{tid}/duplicate")
async def admin_sales_duplicate(tid: str, _: dict = Depends(get_current_admin)):
    import sales_templates

    out = await sales_templates.duplicate(tid)
    if out is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return out


@router.delete("/api/admin/sales-templates/{tid}")
async def admin_sales_delete(tid: str, _: dict = Depends(get_current_admin)):
    import sales_templates

    if not await sales_templates.delete(tid):
        raise HTTPException(status_code=404, detail="Template not found")
    return {"ok": True}
