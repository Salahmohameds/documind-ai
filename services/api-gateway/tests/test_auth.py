"""Authentication endpoint tests.

Covers:
- Successful registration
- Duplicate email registration
- Successful login (seeded admin user)
- Invalid credentials login
- Login response shape matches frontend contract
- Register response shape matches frontend contract
"""

from __future__ import annotations


# ── Registration ─────────────────────────────────────────────────────────


def test_register_success(client):
    """A new user can register and gets the expected response shape."""
    response = client.post(
        "/auth/register",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "org": "TestOrg",
            "password": "securepassword",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["email"] == "test@example.com"
    assert data["verificationSentTo"] == "test@example.com"


def test_register_duplicate_email(client):
    """Registering with an already-taken email returns 409."""
    # The seeded admin user is admin@documind.com
    response = client.post(
        "/auth/register",
        json={
            "name": "Another Admin",
            "email": "admin@documind.com",
            "org": "TestOrg",
            "password": "anotherpassword",
        },
    )
    assert response.status_code == 409
    data = response.json()
    assert data["ok"] is False
    assert data["field"] == "email"


def test_register_short_password(client):
    """Passwords shorter than 8 characters are rejected."""
    response = client.post(
        "/auth/register",
        json={
            "name": "Test",
            "email": "shortpw@example.com",
            "org": "TestOrg",
            "password": "short",
        },
    )
    assert response.status_code == 422
    data = response.json()
    assert data["ok"] is False
    assert data["field"] == "password"


def test_register_short_org(client):
    """Org names shorter than 2 characters are rejected."""
    response = client.post(
        "/auth/register",
        json={
            "name": "Test",
            "email": "orgtest@example.com",
            "org": "X",
            "password": "securepassword",
        },
    )
    assert response.status_code == 422
    data = response.json()
    assert data["ok"] is False
    assert data["field"] == "org"


def test_register_then_login(client):
    """A user who just registered can log in."""
    client.post(
        "/auth/register",
        json={
            "name": "Fresh User",
            "email": "fresh@example.com",
            "org": "FreshOrg",
            "password": "freshpassword123",
        },
    )
    response = client.post(
        "/auth/login",
        json={"email": "fresh@example.com", "password": "freshpassword123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "token" in data
    assert data["session"]["email"] == "fresh@example.com"
    assert data["session"]["name"] == "Fresh User"


# ── Login ────────────────────────────────────────────────────────────────


def test_login_seeded_admin(client):
    """The pre-seeded admin user can log in."""
    response = client.post(
        "/auth/login",
        json={"email": "admin@documind.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "token" in data
    assert isinstance(data["token"], str)
    assert len(data["token"]) > 0

    session = data["session"]
    assert session["email"] == "admin@documind.com"
    assert session["name"] == "Admin User"
    assert session["initials"] == "AU"


def test_login_wrong_password(client):
    """Wrong password returns 401 with the correct error shape."""
    response = client.post(
        "/auth/login",
        json={"email": "admin@documind.com", "password": "wrong"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["ok"] is False
    assert "title" in data
    assert "detail" in data
    assert data["lockedOut"] is False


def test_login_nonexistent_user(client):
    """Logging in with an email that does not exist returns 401."""
    response = client.post(
        "/auth/login",
        json={"email": "nobody@nowhere.com", "password": "whatever"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["ok"] is False


def test_login_case_insensitive_email(client):
    """Email matching is case-insensitive."""
    response = client.post(
        "/auth/login",
        json={"email": "ADMIN@DOCUMIND.COM", "password": "password123"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
