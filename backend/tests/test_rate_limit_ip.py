"""Unit tests for rate_limit._client_ip trusted-proxy handling.

Regression guard for the finding that the limiter keyed on the leftmost
X-Forwarded-For entry, which a client can forge to rotate to a fresh bucket
on every request. The real client IP must come from the rightmost hop the
trusted proxy (Render) appended.

Run from backend/: python -m pytest tests/test_rate_limit_ip.py
"""
import rate_limit


class _FakeClient:
    def __init__(self, host):
        self.host = host


class _FakeRequest:
    def __init__(self, xff=None, client_host="203.0.113.9"):
        self.headers = {} if xff is None else {"x-forwarded-for": xff}
        self.client = _FakeClient(client_host) if client_host else None


def test_falls_back_to_socket_when_no_xff():
    req = _FakeRequest(xff=None, client_host="203.0.113.9")
    assert rate_limit._client_ip(req) == "203.0.113.9"


def test_single_xff_entry_is_used():
    req = _FakeRequest(xff="198.51.100.7")
    assert rate_limit._client_ip(req) == "198.51.100.7"


def test_spoofed_leftmost_is_ignored_rightmost_hop_wins():
    # Attacker prepends a fake IP; Render appends the real client IP last.
    req = _FakeRequest(xff="1.2.3.4, 198.51.100.7")
    assert rate_limit._client_ip(req) == "198.51.100.7"


def test_client_cannot_rotate_bucket_by_spoofing_xff():
    # Two requests from the same real client with different spoofed prefixes
    # must resolve to the SAME key, so the rate limit actually applies.
    a = _FakeRequest(xff="9.9.9.9, 198.51.100.7")
    b = _FakeRequest(xff="8.8.8.8, 198.51.100.7")
    assert rate_limit._client_ip(a) == rate_limit._client_ip(b) == "198.51.100.7"


def test_missing_client_returns_unknown():
    req = _FakeRequest(xff=None, client_host=None)
    assert rate_limit._client_ip(req) == "unknown"
