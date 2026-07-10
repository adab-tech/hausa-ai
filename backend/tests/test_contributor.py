"""Tests for the anonymous contributor-id helper and per-device rate-limit key."""

from contributor import get_contributor_id
from rate_limit import _rate_limit_key

_VALID = "12345678-1234-4123-8123-123456789abc"


class _FakeRequest:
    """Minimal stand-in with the two attributes get_contributor_id reads."""

    def __init__(self, headers=None, query=None, ip="203.0.113.7"):
        self.headers = headers or {}
        self.query_params = query or {}
        self.client = type("C", (), {"host": ip})()


def test_valid_id_from_header():
    req = _FakeRequest(headers={"X-Contributor-Id": _VALID})
    assert get_contributor_id(req) == _VALID


def test_valid_id_from_query_param():
    req = _FakeRequest(query={"contributor_id": _VALID})
    assert get_contributor_id(req) == _VALID


def test_header_wins_over_query():
    other = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    req = _FakeRequest(headers={"X-Contributor-Id": _VALID}, query={"contributor_id": other})
    assert get_contributor_id(req) == _VALID


def test_id_is_lowercased():
    req = _FakeRequest(headers={"X-Contributor-Id": _VALID.upper()})
    assert get_contributor_id(req) == _VALID


def test_malformed_ids_rejected():
    assert get_contributor_id(_FakeRequest(headers={"X-Contributor-Id": "not-a-uuid"})) is None
    assert get_contributor_id(_FakeRequest(headers={"X-Contributor-Id": "x" * 500})) is None
    assert get_contributor_id(_FakeRequest()) is None


def test_rate_limit_key_prefers_contributor_over_ip():
    req = _FakeRequest(headers={"X-Contributor-Id": _VALID}, ip="203.0.113.7")
    assert _rate_limit_key(req) == f"cid:{_VALID}"


def test_rate_limit_key_falls_back_to_ip():
    # Two users behind one NAT'd IP get distinct keys once they have tokens.
    req = _FakeRequest(ip="203.0.113.7")
    assert _rate_limit_key(req) == "203.0.113.7"
