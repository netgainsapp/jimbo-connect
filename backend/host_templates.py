"""Per-host email template overrides.

The admin templates in email_templates are one global set: Jim's wording, used
for every host. This module lets a host replace the wording of the emails that
go out in THEIR name, without touching anyone else's.

The design is an allowlist plus a resolution order:

HOST_EDITABLE names the only templates a host may override. password-reset is
excluded because it is the platform speaking, not a host, and a host-authored
reset email is a phishing kit. The outreach templates are excluded because
they are sales material aimed AT hosts, not mail sent FOR them. The allowlist
gates reads as well as writes, so even a row smuggled into the collection for
an uneditable template is never resolved.

Resolution: host override > admin-edited global > seed default. A host who
never touches anything gets exactly what they got before this existed, which
is what makes the feature safe to ship: customizing is opt in, per template,
per host, and reset is a delete rather than a copy of the default, so a later
improvement to the default reaches everyone who never customized.
"""
from __future__ import annotations

from datetime import datetime, timezone

from database import host_email_templates
from core import get_email_template, merge_vars, serialize_template

#: The only templates a host may override. Order is display order.
HOST_EDITABLE = (
    "invitation",
    "save-the-date",
    "youre-in",
    "day-of",
    "post-event",
    "reconnect",
)

# Mirrors the admin caps in models.TemplateUpdateRequest.
MAX_SUBJECT = 300
MAX_BODY = 20000


class TemplateError(Exception):
    """Bad input, with a message intended for the person who typed it."""


def _require_editable(template_id: str) -> None:
    if template_id not in HOST_EDITABLE:
        # Opaque on purpose: "not editable" and "does not exist" answer the
        # same, so the route cannot be used to probe which system templates
        # exist.
        raise TemplateError("That template cannot be customized.")


async def resolve(template_id: str, host_id=None) -> dict | None:
    """The template as this host's guests would receive it.

    Only subject and body come from the override; title, blurb and category
    stay with the base template, because the host edits words, not identity.
    """
    base = await get_email_template(template_id)
    if base is None:
        return None
    if host_id is None or template_id not in HOST_EDITABLE:
        return base
    row = await host_email_templates.find_one(
        {"host_id": host_id, "template_id": template_id}
    )
    if not row:
        return base
    return {**base, "subject": row["subject"], "body": row["body"]}


async def render_for_host(template_id: str, ctx: dict, host_id=None) -> dict | None:
    """render_email_template, but host aware. Call sites that send on a host's
    behalf use this; platform sends keep using core.render_email_template."""
    t = await resolve(template_id, host_id)
    if not t:
        return None
    return {
        "subject": merge_vars(t["subject"], ctx),
        "body": merge_vars(t["body"], ctx),
    }


async def list_for(host_id) -> list:
    """Every editable template, resolved for this host, in display order."""
    out = []
    for template_id in HOST_EDITABLE:
        t = await resolve(template_id, host_id)
        if not t:
            continue
        row = await host_email_templates.find_one(
            {"host_id": host_id, "template_id": template_id}
        )
        serialized = serialize_template(t)
        serialized["customized"] = row is not None
        out.append(serialized)
    return out


async def upsert(host_id, template_id: str, subject, body) -> dict:
    _require_editable(template_id)
    subject = str(subject or "").strip()[:MAX_SUBJECT]
    body = str(body or "").strip()[:MAX_BODY]
    if not subject or not body:
        raise TemplateError("A template needs both a subject and a body.")
    await host_email_templates.update_one(
        {"host_id": host_id, "template_id": template_id},
        {"$set": {
            "host_id": host_id,
            "template_id": template_id,
            "subject": subject,
            "body": body,
            "updated_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
    resolved = await resolve(template_id, host_id)
    serialized = serialize_template(resolved)
    serialized["customized"] = True
    return serialized


async def reset(host_id, template_id: str) -> dict:
    """Back to the default. A no-op when nothing was customized: the state the
    host asked for is the state they get."""
    _require_editable(template_id)
    await host_email_templates.delete_one(
        {"host_id": host_id, "template_id": template_id}
    )
    resolved = await resolve(template_id, host_id)
    serialized = serialize_template(resolved)
    serialized["customized"] = False
    return serialized
