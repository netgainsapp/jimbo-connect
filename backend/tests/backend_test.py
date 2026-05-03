"""
Jimbo Connect backend API tests.
Covers auth, profile, events (admin), event directory, contact save/note flows.
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://netgains-app.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@jimboconnect.com"
ADMIN_PASSWORD = "admin123"


# --------- fixtures ---------

@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="session")
def user_session():
    s = requests.Session()
    email = f"test_user_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "StrongPass123!", "name": "Test User"})
    assert r.status_code == 200, f"Register failed: {r.status_code} {r.text}"
    s._email = email
    s._user_id = r.json()["id"]
    return s


@pytest.fixture(scope="session")
def user_session_2():
    s = requests.Session()
    email = f"test_user2_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "StrongPass123!", "name": "Test User Two"})
    assert r.status_code == 200
    s._email = email
    s._user_id = r.json()["id"]
    return s


# --------- health ---------

def test_root():
    r = requests.get(f"{API}/")
    assert r.status_code == 200
    assert "message" in r.json()


# --------- auth ---------

class TestAuth:
    def test_admin_login(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200
        data = r.json()
        assert data["role"] == "admin"
        assert data["email"] == ADMIN_EMAIL
        # httpOnly cookie
        assert "access_token" in s.cookies.get_dict()

    def test_invalid_login(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
        assert r.status_code in (401, 429)

    def test_register_and_me(self):
        s = requests.Session()
        email = f"test_me_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register", json={"email": email, "password": "StrongPass123!", "name": "ME Test"})
        assert r.status_code == 200
        me = s.get(f"{API}/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == email

    def test_duplicate_register(self, user_session):
        r = requests.post(f"{API}/auth/register", json={
            "email": user_session._email, "password": "abcABC123!", "name": "Dup"
        })
        assert r.status_code == 400

    def test_me_unauthenticated(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_logout(self):
        s = requests.Session()
        s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        r = s.post(f"{API}/auth/logout")
        assert r.status_code == 200
        me = s.get(f"{API}/auth/me")
        assert me.status_code == 401


# --------- profile ---------

class TestProfile:
    def test_get_profile(self, user_session):
        r = user_session.get(f"{API}/profile")
        assert r.status_code == 200
        assert r.json()["email"] == user_session._email

    def test_update_profile_and_persist(self, user_session):
        payload = {
            "name": "Updated Name",
            "role_title": "Engineer",
            "company": "Acme",
            "bio": "Hello",
            "industry": "Technology",
            "interests": ["AI", "Startups"],
            "table_cohort": "Cohort A",
        }
        r = user_session.put(f"{API}/profile", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Updated Name"
        assert data["role_title"] == "Engineer"
        assert data["interests"] == ["AI", "Startups"]
        # Verify persistence
        g = user_session.get(f"{API}/profile")
        assert g.json()["company"] == "Acme"
        assert g.json()["table_cohort"] == "Cohort A"


# --------- events (admin) ---------

@pytest.fixture(scope="session")
def event_id(admin_session):
    payload = {
        "name": "TEST_Event_Networking",
        "description": "Test event",
        "date": "2026-02-15",
        "location": "NYC",
        "industries": ["Technology", "Finance"],
    }
    r = admin_session.post(f"{API}/events", json=payload)
    assert r.status_code == 200, f"Create event failed: {r.text}"
    data = r.json()
    assert data["name"] == payload["name"]
    assert "code" in data and data["code"]
    assert "id" in data
    return data["id"]


@pytest.fixture(scope="session")
def event_code(admin_session, event_id):
    r = admin_session.get(f"{API}/events/{event_id}")
    assert r.status_code == 200
    return r.json()["code"]


class TestEvents:
    def test_list_events_admin(self, admin_session, event_id):
        r = admin_session.get(f"{API}/events")
        assert r.status_code == 200
        ids = [e["id"] for e in r.json()]
        assert event_id in ids

    def test_list_events_forbidden_for_user(self, user_session):
        r = user_session.get(f"{API}/events")
        assert r.status_code == 403

    def test_update_event(self, admin_session, event_id):
        r = admin_session.put(f"{API}/events/{event_id}", json={"location": "San Francisco"})
        assert r.status_code == 200
        assert r.json()["location"] == "San Francisco"

    def test_get_event(self, user_session, event_id):
        r = user_session.get(f"{API}/events/{event_id}")
        assert r.status_code == 200
        assert r.json()["id"] == event_id

    def test_non_admin_cannot_create_event(self, user_session):
        r = user_session.post(f"{API}/events", json={"name": "X", "date": "2026-01-01"})
        assert r.status_code == 403


# --------- join & attendees ---------

class TestJoinAndDirectory:
    def test_user_joins_event(self, user_session, event_code, event_id):
        r = user_session.post(f"{API}/events/join/{event_code}")
        assert r.status_code == 200
        assert r.json()["event_id"] == event_id
        # My events should include the event
        me = user_session.get(f"{API}/my-events")
        assert me.status_code == 200
        assert any(e["id"] == event_id for e in me.json())

    def test_user2_joins_event(self, user_session_2, event_code):
        r = user_session_2.post(f"{API}/events/join/{event_code}")
        assert r.status_code == 200

    def test_get_attendees(self, user_session, event_id, user_session_2):
        r = user_session.get(f"{API}/events/{event_id}/attendees")
        assert r.status_code == 200
        attendees = r.json()
        ids = [a["id"] for a in attendees]
        assert user_session._user_id in ids
        assert user_session_2._user_id in ids
        # password hash not exposed
        for a in attendees:
            assert "password_hash" not in a

    def test_search_filter_by_industry(self, user_session, event_id):
        # user_session has industry Technology set in profile test
        r = user_session.get(f"{API}/events/{event_id}/attendees", params={"industry": "Technology"})
        assert r.status_code == 200
        ids = [a["id"] for a in r.json()]
        assert user_session._user_id in ids

    def test_search_by_name(self, user_session, event_id):
        r = user_session.get(f"{API}/events/{event_id}/attendees", params={"search": "Updated"})
        assert r.status_code == 200
        ids = [a["id"] for a in r.json()]
        assert user_session._user_id in ids

    def test_filter_by_interests(self, user_session, event_id):
        r = user_session.get(f"{API}/events/{event_id}/attendees", params={"interests": "AI"})
        assert r.status_code == 200
        ids = [a["id"] for a in r.json()]
        assert user_session._user_id in ids


# --------- contacts ---------

class TestContacts:
    def test_save_and_list_contact(self, user_session, user_session_2):
        target_id = user_session_2._user_id
        r = user_session.post(f"{API}/contacts/save", json={"contact_user_id": target_id})
        assert r.status_code == 200
        # Duplicate should fail
        r2 = user_session.post(f"{API}/contacts/save", json={"contact_user_id": target_id})
        assert r2.status_code == 400
        # List should include
        lst = user_session.get(f"{API}/contacts")
        assert lst.status_code == 200
        assert any(c["id"] == target_id for c in lst.json())

    def test_is_saved(self, user_session, user_session_2):
        r = user_session.get(f"{API}/contacts/{user_session_2._user_id}/is-saved")
        assert r.status_code == 200
        assert r.json()["is_saved"] is True

    def test_update_note(self, user_session, user_session_2):
        r = user_session.put(f"{API}/contacts/{user_session_2._user_id}/note", json={"note": "Great chat"})
        assert r.status_code == 200
        lst = user_session.get(f"{API}/contacts").json()
        target = next(c for c in lst if c["id"] == user_session_2._user_id)
        assert target["note"] == "Great chat"

    def test_remove_contact(self, user_session, user_session_2):
        r = user_session.delete(f"{API}/contacts/{user_session_2._user_id}")
        assert r.status_code == 200
        lst = user_session.get(f"{API}/contacts").json()
        assert not any(c["id"] == user_session_2._user_id for c in lst)


# --------- admin stats ---------

class TestAdminStats:
    def test_admin_stats(self, admin_session):
        r = admin_session.get(f"{API}/admin/stats")
        assert r.status_code == 200
        data = r.json()
        for key in ["total_users", "total_events", "active_events", "total_connections"]:
            assert key in data
            assert isinstance(data[key], int)

    def test_non_admin_stats_forbidden(self, user_session):
        r = user_session.get(f"{API}/admin/stats")
        assert r.status_code == 403
