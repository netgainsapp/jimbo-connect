"""Tests for the SSRF guard on the sponsor OG fetch: public-IP validation and
IP pinning (DNS-rebind defense). The fetch itself connects to the exact IP
that passed validation; these tests cover the resolve + pin helpers.

Run from backend/: python -m pytest tests/test_ssrf.py
"""
import os

import pytest

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import server


def _fake_resolver(mapping):
    def fake_getaddrinfo(host, port, *args, **kwargs):
        ips = mapping.get(host)
        if not ips:
            raise OSError("name not known")
        return [(2, 1, 6, "", (ip, 0)) for ip in ips]

    return fake_getaddrinfo


def _wire(monkeypatch, mapping):
    monkeypatch.setattr(server.socket, "getaddrinfo", _fake_resolver(mapping))


# ---- _resolve_public_ip ----

def test_public_host_resolves(monkeypatch):
    _wire(monkeypatch, {"example.com": ["93.184.216.34"]})
    assert server._resolve_public_ip("https://example.com/x") == "93.184.216.34"


@pytest.mark.parametrize(
    "bad_ip",
    ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "0.0.0.0", "::1"],
)
def test_non_public_addresses_blocked(monkeypatch, bad_ip):
    _wire(monkeypatch, {"evil.test": [bad_ip]})
    with pytest.raises(ValueError):
        server._resolve_public_ip("https://evil.test/")


def test_any_private_answer_poisons_the_set(monkeypatch):
    # A rebinding resolver that mixes one public and one private answer must
    # be rejected outright, not just have the private answer skipped.
    _wire(monkeypatch, {"mixed.test": ["93.184.216.34", "10.0.0.5"]})
    with pytest.raises(ValueError):
        server._resolve_public_ip("https://mixed.test/")


def test_prefers_ipv4_when_both(monkeypatch):
    _wire(monkeypatch, {"dual.test": ["2606:2800:220:1:248:1893:25c8:1946", "93.184.216.34"]})
    assert server._resolve_public_ip("https://dual.test/") == "93.184.216.34"


def test_bad_scheme_and_missing_host_rejected(monkeypatch):
    _wire(monkeypatch, {})
    with pytest.raises(ValueError):
        server._resolve_public_ip("ftp://example.com/")
    with pytest.raises(ValueError):
        server._resolve_public_ip("https:///nohost")


# ---- _pin_url ----

def test_pin_swaps_host_for_ip_and_keeps_path():
    pinned, host = server._pin_url("https://example.com/a/b?c=d", "93.184.216.34")
    assert pinned == "https://93.184.216.34/a/b?c=d"
    assert host == "example.com"


def test_pin_preserves_explicit_port():
    pinned, host = server._pin_url("http://example.com:8080/x", "93.184.216.34")
    assert pinned == "http://93.184.216.34:8080/x"
    assert host == "example.com"


def test_pin_brackets_ipv6():
    pinned, _ = server._pin_url("https://example.com/", "2606:2800::1946")
    assert pinned.startswith("https://[2606:2800::1946]/")


def test_pin_drops_userinfo():
    # Credentials in the URL must not survive into the pinned request.
    pinned, host = server._pin_url("https://u:p@example.com/x", "93.184.216.34")
    assert "u:p@" not in pinned
    assert host == "example.com"
