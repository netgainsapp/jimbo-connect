"""Apply LinkedIn result rows to leads. Shared by the results upload and the
Linked Helper webhook so both move a lead forward by exactly the same rule.

Matching is on the normalized profile URL against every lead that has entered
the LinkedIn queue. Nothing here reads or returns an email address.
"""
import event_leads_store as store
import linkedin_results as results


def _index_by_url(leads):
    index = {}
    for lead in leads:
        url = results.normalize_linkedin_url(
            (lead.get("contact") or {}).get("linkedin_url")
        )
        if url:
            index.setdefault(url, []).append(lead)
    return index


async def _apply_one(lead, item, now):
    """Move one lead forward. False when nothing moved, including when a
    concurrent write changed the status since it was read."""
    fields = results.build_update(lead, item, now)
    if fields is None:
        return False
    current = (lead.get("linkedin") or {}).get("status")
    if not await store.update_lead_if(lead["_id"], {"linkedin.status": current}, fields):
        return False
    results.apply_dotted(lead, fields)
    return True


async def import_rows(rows, now):
    """Map and apply result rows. Returns {updated, unchanged, unknown,
    errors}; unknown holds normalized URLs that matched no lead."""
    mapped, errors, idle = results.map_rows(rows)
    index = _index_by_url(await store.list_linkedin_tracked())
    updated, unchanged, unknown = 0, idle, []
    for item in mapped:
        targets = index.get(item["url"])
        if not targets:
            if item["url"] not in unknown:
                unknown.append(item["url"])
            continue
        for lead in targets:
            if await _apply_one(lead, item, now):
                updated += 1
            else:
                unchanged += 1
    return {"updated": updated, "unchanged": unchanged, "unknown": unknown, "errors": errors}
