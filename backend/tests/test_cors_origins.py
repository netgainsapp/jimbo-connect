import re
from server import CORS_ORIGIN_REGEX

pat = re.compile(CORS_ORIGIN_REGEX)

def test_allows_app_subdomain():
    assert pat.match("https://app.intro-connect.com")

def test_allows_apex():
    assert pat.match("https://intro-connect.com")

def test_allows_own_render_service():
    assert pat.match("https://jimbo-connect-web-huph.onrender.com")

def test_rejects_foreign_origin():
    assert not pat.match("https://evil.example.com")

def test_rejects_other_render_tenant():
    assert not pat.match("https://someone-else.onrender.com")
