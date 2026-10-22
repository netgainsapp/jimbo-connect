"""LinkedIn queue export, result import and the Linked Helper webhook.

Auth is the real cookie dependency against a faked users collection; the lead
collection is a small fake that understands dotted equality and $in, so the
queries the store sends are the ones being tested.

Run from backend/: python -m pytest tests/test_linkedin_queue.py
"""
import csv
import io
import json
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

import auth
import event_leads_store
import linkedin_queue as queue
import sales_templates
import server

client = TestClient(server.app)
BASE = "/api/admin/event-leads"
QUEUE = f"{BASE}/linkedin-queue.csv"
RESULTS = f"{BASE}/linkedin-results"
HOOK = f"{BASE}/linkedin-webhook"
ADMIN_ID, MEMBER_ID = ObjectId(), ObjectId()
SECRET = "hook-secret"
HEADER = ["profile_url", "first_name", "last_name", "company", "event_name",
          "event_date", "claim_url", "note", "followup"]
EMAIL = "jane.private@example.com"


def _get(doc, dotted):
    for part in dotted.split("."):
        if not isinstance(doc, dict) or part not in doc:
            return None
        doc = doc[part]
    return doc


def _matches(doc, query):
    for key, want in query.items():
        have = _get(doc, key)
        if isinstance(want, dict) and "$in" in want:
            if have not in want["$in"]:
                return False
        elif have != want:
            return False
    return True


class _Cursor:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self, _length):
        return [dict(r) for r in self.rows]


class _Result:
    def __init__(self, matched):
        self.matched_count = matched


class _Leads:
    def __init__(self):
        self.rows = {}
        self.updates = []

    def add(self, **fields):
        doc = {"_id": ObjectId(), "status": "approved", "contact": {}, **fields}
        self.rows[doc["_id"]] = doc
        return doc["_id"]

    def find(self, query):
        return _Cursor([r for r in self.rows.values() if _matches(r, query)])

    async def update_one(self, query, update):
        row = self.rows.get(query["_id"])
        rest = {k: v for k, v in query.items() if k != "_id"}
        if row is None or not _matches(row, rest):
            return _Result(0)
        self.updates.append((query, update))
        for key, value in update.get("$set", {}).items():
            target = row
            *parents, leaf = key.split(".")
            for part in parents:
                target = target.setdefault(part, {})
            target[leaf] = value
        return _Result(1)


class _Users:
    def __init__(self, rows):
        self.rows = rows

    async def find_one(self, q):
        return self.rows.get(q.get("_id"))


class _Templates:
    def __init__(self, rows=()):
        self.rows = {r["seed_key"]: r for r in rows}

    async def find_one(self, q):
        return self.rows.get(q.get("seed_key"))


@pytest.fixture
def db(monkeypatch):
    leads = _Leads()
    people = _Users({
        ADMIN_ID: {"_id": ADMIN_ID, "is_admin": True},
        MEMBER_ID: {"_id": MEMBER_ID, "is_admin": False},
    })
    monkeypatch.setattr(event_leads_store, "event_leads", leads)
    monkeypatch.setattr(auth, "users", people)
    monkeypatch.setattr(sales_templates, "sales_templates", _Templates())
    monkeypatch.setenv("LINKED_HELPER_WEBHOOK_SECRET", SECRET)
    client.cookies.clear()
    client.cookies.set(auth.COOKIE_NAME, auth.create_access_token(str(ADMIN_ID)))
    yield leads
    client.cookies.clear()


def _lead(leads, handle="jane-doe", linkedin="queued", url=True, **extra):
    fields = {
        "organizer_name": "Denver Devs",
        "anchor": {"title": "Mixer", "start": "2099-01-04T18:00:00-07:00"},
        "contact": {
            "name": "Jane Doe", "email": EMAIL,
            "linkedin_url": f"https://www.linkedin.com/in/{handle}/" if url else "",
        },
        "claim_url": f"https://app.example.com/claim/{handle}",
        "linkedin": {"status": linkedin},
        "funnel": {},
        **extra,
    }
    return leads.add(**fields)


def _rows(response):
    return list(csv.DictReader(io.StringIO(response.text)))


def _linkedin(leads, oid):
    return leads.rows[oid]["linkedin"]


# ---------- queue export ----------

def test_queue_holds_only_approved_leads_with_a_url_still_queued(db):
    _lead(db, "wanted")
    _lead(db, "not-approved", status="new")
    _lead(db, "no-url", url=False)
    _lead(db, "already-exported", linkedin="exported")
    _lead(db, "never-queued", linkedin="none")

    response = client.get(QUEUE)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    rows = _rows(response)
    assert [r["profile_url"] for r in rows] == ["https://www.linkedin.com/in/wanted/"]


def test_queue_columns_and_rendered_messages_carry_the_claim_link(db):
    _lead(db)

    response = client.get(QUEUE)

    assert next(csv.reader(io.StringIO(response.text))) == HEADER
    row = _rows(response)[0]
    assert (row["first_name"], row["last_name"]) == ("Jane", "Doe")
    assert row["company"] == "Denver Devs" and row["event_name"] == "Mixer"
    assert row["event_date"] == "Sunday, January 4"
    assert row["claim_url"] == "https://app.example.com/claim/jane-doe"
    assert len(row["note"]) <= 300 and "Jane" in row["note"]
    assert "https://app.example.com/claim/jane-doe" in row["followup"]


def test_queue_uses_the_admin_edited_template_text(db, monkeypatch):
    monkeypatch.setattr(sales_templates, "sales_templates", _Templates([
        {"seed_key": "ic-linkedin-note", "body": "Edited note for {first_name}"},
        {"seed_key": "ic-linkedin-followup", "body": "Edited follow up {claim_url}"},
    ]))
    _lead(db)

    row = _rows(client.get(QUEUE))[0]

    assert row["note"] == "Edited note for Jane"
    assert row["followup"] == "Edited follow up https://app.example.com/claim/jane-doe"


def test_queue_never_carries_the_email_address(db):
    _lead(db)

    response = client.get(QUEUE)

    assert EMAIL not in response.text
    assert "email" not in response.text.splitlines()[0]


def test_queue_cells_are_safe_from_formula_injection(db):
    _lead(db, organizer_name='=HYPERLINK("http://evil")',
          contact={"name": "@cmd Doe", "email": EMAIL,
                   "linkedin_url": "https://www.linkedin.com/in/x/"})

    row = _rows(client.get(QUEUE))[0]

    assert row["company"].startswith("'=")
    assert row["first_name"].startswith("'@")


def test_export_marks_leads_exported_and_a_second_export_is_empty(db):
    oid = _lead(db)

    response = client.get(QUEUE)

    disposition = response.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="linkedin-queue-')
    assert disposition.endswith('.csv"')
    state = _linkedin(db, oid)
    assert state["status"] == "exported"
    assert state["exported_at"] == state["updated_at"]
    again = client.get(QUEUE)
    assert again.text.strip().split(",") == HEADER
    assert _rows(again) == []


def test_empty_queue_is_a_header_only_csv(db):
    response = client.get(QUEUE)

    assert response.status_code == 200
    assert response.text.strip().split(",") == HEADER


def test_dry_run_returns_the_csv_without_marking(db):
    oid = _lead(db)

    response = client.get(QUEUE, params={"dry_run": "true"})

    assert len(_rows(response)) == 1
    assert _linkedin(db, oid) == {"status": "queued"}
    assert db.updates == []


def test_lead_taken_by_another_export_is_not_listed_twice(db, monkeypatch):
    _lead(db)
    real = event_leads_store.update_lead_if

    async def lose_the_race(lead_oid, condition, fields):
        db.rows[lead_oid]["linkedin"]["status"] = "exported"
        return await real(lead_oid, condition, fields)

    monkeypatch.setattr(event_leads_store, "update_lead_if", lose_the_race)

    assert _rows(client.get(QUEUE)) == []


def test_a_lead_whose_row_fails_stays_queued_and_the_rest_are_marked(db, monkeypatch, capsys):
    good = _lead(db, "good")
    bad = _lead(db, "bad", organizer_name="Boom")
    real = queue.queue_row

    def explode_for_boom(lead, *args):
        if lead["organizer_name"] == "Boom":
            raise ValueError("bad date")
        return real(lead, *args)

    monkeypatch.setattr(queue, "queue_row", explode_for_boom)

    response = client.get(QUEUE)

    assert response.status_code == 200
    assert [r["profile_url"] for r in _rows(response)] == ["https://www.linkedin.com/in/good/"]
    assert response.headers["x-linkedin-skipped"] == "1"
    assert _linkedin(db, good)["status"] == "exported"
    assert _linkedin(db, bad) == {"status": "queued"}
    logged = capsys.readouterr().err
    assert "ValueError" in logged and str(bad) in logged and EMAIL not in logged


def test_a_lead_that_cannot_be_marked_is_left_out_and_stays_queued(db, monkeypatch):
    good = _lead(db, "good")
    stuck = _lead(db, "stuck", organizer_name="Stuck")
    real = event_leads_store.update_lead_if

    async def fail_for_stuck(oid, condition, fields):
        if oid == stuck:
            raise RuntimeError("write failed")
        return await real(oid, condition, fields)

    monkeypatch.setattr(event_leads_store, "update_lead_if", fail_for_stuck)

    response = client.get(QUEUE)

    assert [r["company"] for r in _rows(response)] == ["Denver Devs"]
    assert response.headers["x-linkedin-skipped"] == "1"
    assert _linkedin(db, good)["status"] == "exported"
    assert _linkedin(db, stuck) == {"status": "queued"}


def test_nothing_is_marked_before_every_row_is_built(db, monkeypatch):
    _lead(db, "a")
    _lead(db, "b", organizer_name="Boom")
    marks_when_building = []
    real = queue.queue_row

    def spy(lead, *args):
        marks_when_building.append(len(db.updates))
        return real(lead, *args)

    monkeypatch.setattr(queue, "queue_row", spy)
    client.get(QUEUE)

    assert marks_when_building == [0, 0]


def test_include_exported_lists_exported_leads_without_re_marking(db):
    queued = _lead(db, "queued")
    exported = _lead(db, "exported", linkedin="exported")
    _lead(db, "invited", linkedin="invited")
    db.rows[exported]["linkedin"]["exported_at"] = "first"

    response = client.get(QUEUE, params={"include_exported": "true"})

    urls = sorted(r["profile_url"] for r in _rows(response))
    assert urls == ["https://www.linkedin.com/in/exported/",
                    "https://www.linkedin.com/in/queued/"]
    assert _linkedin(db, exported)["exported_at"] == "first"
    assert _linkedin(db, queued)["status"] == "exported"
    assert [q["_id"] for q, _ in db.updates] == [queued]


def test_exported_leads_are_not_listed_without_include_exported(db):
    _lead(db, "exported", linkedin="exported")

    assert _rows(client.get(QUEUE)) == []


def test_linkedin_routes_need_an_admin(db):
    client.cookies.clear()
    assert client.get(QUEUE).status_code == 401
    assert client.post(RESULTS, json={"rows": []}).status_code == 401

    client.cookies.set(auth.COOKIE_NAME, auth.create_access_token(str(MEMBER_ID)))
    assert client.get(QUEUE).status_code == 403
    assert client.post(RESULTS, json={"rows": []}).status_code == 403


# ---------- results import ----------

def _post_rows(rows):
    return client.post(RESULTS, json={"rows": rows})


def test_results_map_connected_replied_and_failed(db):
    a = _lead(db, "a", linkedin="invited")
    b = _lead(db, "b", linkedin="connected")
    c = _lead(db, "c", linkedin="exported")

    body = _post_rows([
        {"linkedin_url": "https://www.linkedin.com/in/a/", "status": "connected",
         "at": "2026-11-01T10:00:00Z"},
        {"linkedin_url": "https://linkedin.com/in/B", "status": "replied", "at": ""},
        {"linkedin_url": "linkedin.com/in/c?x=1", "status": "failed", "at": ""},
    ]).json()

    assert body["ok"] is True and body["updated"] == 3
    assert body["unchanged"] == 0 and body["unknown"] == [] and body["errors"] == []
    assert _linkedin(db, a)["status"] == "connected"
    assert _linkedin(db, a)["connected_at"].isoformat().startswith("2026-11-01T10:00")
    assert _linkedin(db, b)["status"] == "replied" and "replied_at" in _linkedin(db, b)
    assert db.rows[b]["funnel"]["linkedin_replied_at"] == _linkedin(db, b)["replied_at"]
    assert _linkedin(db, c)["status"] == "failed" and "failed_at" in _linkedin(db, c)
    assert "updated_at" in _linkedin(db, c)


def test_unknown_urls_are_reported_not_fatal(db):
    known = _lead(db, "known", linkedin="exported")

    body = _post_rows([
        {"linkedin_url": "https://www.linkedin.com/in/stranger/", "status": "invited"},
        {"linkedin_url": "https://www.linkedin.com/in/known/", "status": "invited"},
    ]).json()

    assert body["unknown"] == ["linkedin.com/in/stranger"]
    assert body["updated"] == 1
    assert _linkedin(db, known)["status"] == "invited"


def test_status_never_moves_backward_and_failed_is_not_applied_before_export(db):
    replied = _lead(db, "r", linkedin="replied")
    queued = _lead(db, "q", linkedin="queued")

    body = _post_rows([
        {"linkedin_url": "linkedin.com/in/r", "status": "invited"},
        {"linkedin_url": "linkedin.com/in/q", "status": "failed"},
    ]).json()

    assert body["updated"] == 0 and body["unchanged"] == 2
    assert _linkedin(db, replied)["status"] == "replied"
    assert _linkedin(db, queued)["status"] == "queued"


def test_a_leads_reply_time_in_the_funnel_is_not_overwritten(db):
    oid = _lead(db, "r", linkedin="connected",
                funnel={"linkedin_replied_at": "first-time"})

    _post_rows([{"linkedin_url": "linkedin.com/in/r", "status": "replied"}])

    assert db.rows[oid]["funnel"]["linkedin_replied_at"] == "first-time"


def test_rows_for_one_lead_apply_in_order_and_never_regress(db):
    oid = _lead(db, "a", linkedin="exported")

    body = _post_rows([
        {"linkedin_url": "linkedin.com/in/a", "status": "invited"},
        {"linkedin_url": "linkedin.com/in/a", "status": "connected"},
        {"linkedin_url": "linkedin.com/in/a", "status": "invited"},
    ]).json()

    assert (body["updated"], body["unchanged"]) == (2, 1)
    assert _linkedin(db, oid)["status"] == "connected"


def test_bad_rows_are_reported_with_their_row_number(db):
    _lead(db, "a", linkedin="exported")

    body = _post_rows([
        {"linkedin_url": "linkedin.com/in/a", "status": "invited"},
        {"status": "invited"},
        {"linkedin_url": "linkedin.com/in/a", "status": "ghosted"},
        "not an object",
    ]).json()

    assert body["updated"] == 1
    assert [e["row"] for e in body["errors"]] == [2, 3, 4]
    assert all(e["reason"] for e in body["errors"])


def test_csv_upload_in_the_minimal_format(db):
    oid = _lead(db, "a", linkedin="exported")
    text = ("linkedin_url,status,at\n"
            "https://www.linkedin.com/in/a/,connected,2026-11-01T10:00:00Z\n")

    response = client.post(RESULTS, files={"file": ("results.csv", text, "text/csv")})

    assert response.status_code == 200 and response.json()["updated"] == 1
    assert _linkedin(db, oid)["status"] == "connected"


def test_csv_upload_in_the_linked_helper_format(db):
    a = _lead(db, "a", linkedin="exported")
    b = _lead(db, "b", linkedin="exported")
    c = _lead(db, "c", linkedin="exported")
    text = (
        "﻿profile_url,invited_date_iso,connected_at,replied_message_1_text,campaign_name\n"
        "https://www.linkedin.com/in/a/,2026-10-28T09:00:00Z,,,Events\n"
        "https://www.linkedin.com/in/b/,2026-10-28T09:00:00Z,2026-10-29T09:00:00Z,,Events\n"
        "https://www.linkedin.com/in/c/,2026-10-28T09:00:00Z,2026-10-29T09:00:00Z,Yes please,Events\n"
    )

    body = client.post(RESULTS, files={"file": ("lh.csv", text.encode("utf-8"), "text/csv")}).json()

    assert body["updated"] == 3
    assert [_linkedin(db, x)["status"] for x in (a, b, c)] == ["invited", "connected", "replied"]


def test_json_content_type_is_matched_case_insensitively(db):
    oid = _lead(db, "a", linkedin="exported")
    body = json.dumps({"rows": [{"linkedin_url": "linkedin.com/in/a", "status": "invited"}]})

    response = client.post(RESULTS, content=body,
                           headers={"Content-Type": "Application/JSON; charset=utf-8"})

    assert response.status_code == 200 and response.json()["updated"] == 1
    assert _linkedin(db, oid)["status"] == "invited"


def test_a_profile_subpage_url_in_a_result_matches_the_lead(db):
    oid = _lead(db, "a", linkedin="exported")

    body = _post_rows([{"linkedin_url": "https://www.linkedin.com/in/a/details/experience/",
                        "status": "invited"}]).json()

    assert body["updated"] == 1 and body["unknown"] == []
    assert _linkedin(db, oid)["status"] == "invited"


def test_failed_does_not_overwrite_a_connected_or_replied_lead(db):
    connected = _lead(db, "c", linkedin="connected")
    replied = _lead(db, "r", linkedin="replied")
    invited = _lead(db, "i", linkedin="invited")

    body = _post_rows([
        {"linkedin_url": "linkedin.com/in/c", "status": "failed"},
        {"linkedin_url": "linkedin.com/in/r", "status": "failed"},
        {"linkedin_url": "linkedin.com/in/i", "status": "failed"},
    ]).json()

    assert (body["updated"], body["unchanged"]) == (1, 2)
    assert _linkedin(db, connected)["status"] == "connected"
    assert _linkedin(db, replied)["status"] == "replied"
    assert _linkedin(db, invited)["status"] == "failed"


def test_results_need_a_file_or_rows(db):
    assert client.post(RESULTS, json={"nope": 1}).status_code == 400
    assert client.post(RESULTS, data={"x": "y"}).status_code == 400


# ---------- webhook ----------

def _hook(body, secret=SECRET):
    params = {} if secret is None else {"secret": secret}
    return client.post(HOOK, params=params, json=body)


def test_webhook_fails_closed_without_a_secret_or_with_a_wrong_one(db, monkeypatch):
    assert _hook({}, secret=None).status_code == 401
    assert _hook({}, secret="wrong").status_code == 401
    monkeypatch.delenv("LINKED_HELPER_WEBHOOK_SECRET")
    assert _hook({}, secret="").status_code == 401
    assert _hook({}, secret=SECRET).status_code == 401
    assert db.updates == []


def test_webhook_applies_one_camel_case_payload(db):
    oid = _lead(db, "a", linkedin="exported")

    response = _hook({
        "profileUrl": "https://www.linkedin.com/in/a/",
        "invitedDateIso": "2026-10-28T09:00:00Z",
        "connectedAtIso": "2026-10-29T09:00:00Z",
        "repliedMessageText": "",
    })

    assert response.status_code == 200
    assert response.json() == {"ok": True, "updated": 1, "unchanged": 0, "unknown": []}
    assert _linkedin(db, oid)["status"] == "connected"


def test_webhook_accepts_a_list_and_reports_unknown_and_unchanged(db):
    done = _lead(db, "done", linkedin="replied")
    body = _hook([
        {"profileUrl": "https://www.linkedin.com/in/done/",
         "invitedDateIso": "2026-10-28T09:00:00Z"},
        {"profileUrl": "https://www.linkedin.com/in/ghost/",
         "invitedDateIso": "2026-10-28T09:00:00Z"},
        {"profileUrl": "https://www.linkedin.com/in/done/"},
    ]).json()

    assert body == {"ok": True, "updated": 0, "unchanged": 2,
                    "unknown": ["linkedin.com/in/ghost"]}
    assert _linkedin(db, done)["status"] == "replied"


def test_webhook_rejects_a_body_that_is_not_json_objects(db):
    assert _hook("just a string").status_code == 400
    assert client.post(HOOK, params={"secret": SECRET}, content=b"{nope").status_code == 400
