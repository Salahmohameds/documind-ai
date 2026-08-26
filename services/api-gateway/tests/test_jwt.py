"""JWT generation and validation tests.

Covers:
- Token contains the correct claims (sub, exp, role)
- Token does NOT contain iss or aud
- Token is valid and decodable
- Expired tokens are rejected
- Invalid tokens are rejected
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

from app.auth.jwt_handler import create_token, decode_token
from app.config import settings


def test_token_contains_required_claims():
    """The token must contain sub, exp, and role — nothing else per M1 spec."""
    token = create_token(email="test@example.com", role="user")
    payload = decode_token(token)

    assert payload["sub"] == "test@example.com"
    assert payload["role"] == "user"
    assert "exp" in payload


def test_token_does_not_contain_iss_or_aud():
    """M1 decision: no iss or aud claims."""
    token = create_token(email="test@example.com", role="admin")
    payload = decode_token(token)

    assert "iss" not in payload
    assert "aud" not in payload


def test_token_role_is_admin():
    """Admin role is correctly encoded."""
    token = create_token(email="admin@documind.com", role="admin")
    payload = decode_token(token)
    assert payload["role"] == "admin"


def test_token_role_is_user():
    """User role is correctly encoded."""
    token = create_token(email="user@example.com", role="user")
    payload = decode_token(token)
    assert payload["role"] == "user"


def test_token_expiration_is_24_hours():
    """Token exp claim should be approximately 24 hours from now."""
    before = datetime.now(UTC)
    token = create_token(email="test@example.com", role="user")
    after = datetime.now(UTC)

    payload = decode_token(token)
    exp = datetime.fromtimestamp(payload["exp"], tz=UTC)

    # The expiration should be within 24h ± a few seconds of token creation.
    expected_min = before + timedelta(hours=24) - timedelta(seconds=5)
    expected_max = after + timedelta(hours=24) + timedelta(seconds=5)
    assert expected_min <= exp <= expected_max


def test_token_uses_hs256():
    """Token header indicates HS256."""
    token = create_token(email="test@example.com", role="user")
    header = jwt.get_unverified_header(token)
    assert header["alg"] == "HS256"


def test_expired_token_is_rejected():
    """An expired token raises ExpiredSignatureError."""
    payload = {
        "sub": "test@example.com",
        "exp": datetime.now(UTC) - timedelta(hours=1),
        "role": "user",
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    try:
        decode_token(token)
        assert False, "Should have raised"
    except jwt.ExpiredSignatureError:
        pass  # Expected.


def test_invalid_signature_is_rejected():
    """A token signed with the wrong secret is rejected."""
    token = jwt.encode(
        {"sub": "test@example.com", "exp": datetime.now(UTC) + timedelta(hours=1), "role": "user"},
        "wrong-secret",
        algorithm="HS256",
    )

    try:
        decode_token(token)
        assert False, "Should have raised"
    except jwt.InvalidSignatureError:
        pass  # Expected.


def test_malformed_token_is_rejected():
    """A completely invalid token string is rejected."""
    try:
        decode_token("not.a.valid.token")
        assert False, "Should have raised"
    except jwt.PyJWTError:
        pass  # Expected.


def test_login_returns_decodable_jwt(client):
    """End-to-end: the JWT returned by login is valid and contains correct claims."""
    response = client.post(
        "/auth/login",
        json={"email": "admin@documind.com", "password": "password123"},
    )
    data = response.json()
    token = data["token"]
    payload = decode_token(token)

    assert payload["sub"] == "admin@documind.com"
    assert payload["role"] == "admin"
    assert "exp" in payload
    assert "iss" not in payload
    assert "aud" not in payload
