"""Shared spreadsheet import: turn rows of people into accounts and put them on
an event.

There are two callers with deliberately different powers:

* the admin import (`/api/admin/users/bulk-import`), which may run without an
  event and may hand back plaintext credentials when email is not configured;
* the host import (`/api/events/{id}/attendees/import`), which may not do
  either.

That difference is the whole reason this module exists rather than the host
route calling the admin one. A host is importing people whose email addresses
they do not control. If they could choose the password, or read back the
generated one, importing `someone@example.com` would hand them a working login
for that person's account. So for hosts the password is random, never returned,
and never chosen: the invitation email is the only way in, and anyone else can
use password reset. See `disclose_credentials` / `default_password` below.

The capacity check lives here too, so both paths fill to the cap and report the
overflow per row rather than failing the whole import.
"""
import asyncio
import secrets
import string
from datetime import datetime, timezone

import branding
import email_send
from auth import hash_password
from core import APP_URL, attendee_room
import host_templates
from database import event_attendees, users
from send_report import tally_failure


def _random_password() -> str:
    return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))


async def import_rows(
    *,
    actor: dict,
    rows: list,
    event_doc: dict | None,
    event_oid=None,
    default_password: str | None = None,
    disclose_credentials: bool = False,
    source: str = "manual",
) -> dict:
    """Import `rows`, optionally adding each person to `event_doc`.

    `default_password` and `disclose_credentials` are admin-only powers; the
    host path passes neither. Returns the same summary shape for both callers.

    `source` records which tool the list came out of, on the event membership
    rather than on the person: someone can arrive at one event from an
    Audience Republic export and at the next by signing up themselves, and
    both facts are true. Stored only on rows this import creates, so existing
    memberships keep whatever they already said.
    """
    now = datetime.now(timezone.utc)
    created = 0
    skipped = 0
    added_to_event = 0
    emailed = 0
    email_failures: dict = {}
    accounts: list = []
    errors: list = []

    # Cap read once and tracked locally rather than re-counted per row. An
    # import that would overflow fills to the cap and reports the rest instead
    # of failing outright: a 400 row spreadsheet against a 250 cap should still
    # get 250 people in, not zero.
    attendee_limit, attendee_count = (None, 0)
    if event_oid is not None and event_doc:
        attendee_limit, attendee_count = await attendee_room(event_doc)

    for row in rows:
        email = row.email.lower().strip()
        try:
            existing = await users.find_one({"email": email})
            if existing:
                skipped += 1
                user_id = existing["_id"]
            else:
                temp_password = default_password or _random_password()
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

                # Plaintext goes to ONE channel and never to a host. For an
                # admin it is the invitation email, or the response as an
                # explicit fallback when email is not configured. Never both.
                if disclose_credentials and not email_send.is_configured():
                    accounts.append({"email": email, "password": temp_password})

                if email_send.is_configured():
                    actor_profile = actor.get("profile") or {}
                    # Host aware: the invitation goes out in the acting
                    # host's name, so their override applies. Admin imports
                    # send the admin's own wording by the same rule.
                    rendered = await host_templates.render_for_host(
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
                            "host_name": actor_profile.get("name") or "Jim",
                            "site_url": APP_URL,
                        },
                        host_id=actor["_id"],
                    )
                    # The account exists whether or not the invitation lands,
                    # so the two outcomes are counted separately. Reporting
                    # only "created" is how an import that emailed nobody read
                    # exactly like one that worked.
                    if rendered:
                        send_result = await email_send.send_template_branded(
                            to=email,
                            rendered=rendered,
                            button_label="Open your directory",
                            button_url=APP_URL,
                            brand=branding.email_brand(actor),
                        )
                        if send_result.get("sent"):
                            emailed += 1
                        else:
                            tally_failure(email_failures, send_result.get("reason"))
                    else:
                        # No template means no mail at all, which is the one
                        # failure mode that leaves no trace anywhere else.
                        tally_failure(email_failures, "invitation template unavailable")

            if event_oid is not None:
                already = await event_attendees.find_one(
                    {"event_id": event_oid, "user_id": user_id}
                )
                if not already:
                    if attendee_limit is not None and attendee_count >= attendee_limit:
                        # The account still exists, they are simply not on this
                        # event. Reported per row so it is obvious who missed
                        # out rather than the numbers quietly not adding up.
                        errors.append({
                            "email": email,
                            "error": (
                                f"Event is at its limit of {attendee_limit} "
                                "attendees. Upgrade to add more."
                            ),
                        })
                    else:
                        await event_attendees.insert_one(
                            {
                                "event_id": event_oid,
                                "user_id": user_id,
                                "joined_at": now,
                                "source": source,
                                "imported_at": now,
                            }
                        )
                        added_to_event += 1
                        attendee_count += 1
        except Exception as e:
            errors.append({"email": email, "error": str(e)})

    return {
        "created": created,
        "skipped": skipped,
        "added_to_event": added_to_event,
        # Only new accounts are emailed, so `emailed` is never the row count.
        "emailed": emailed,
        "email_failures": email_failures,
        "errors": errors,
        "accounts": accounts,
    }
