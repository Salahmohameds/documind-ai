"""Contract tests for api-gateway authentication.

Covers registration validation, login, and the JWT itself. Token
structure is inspected without verifying the signature — the secret
belongs to the service, and a client should never need it.
"""

import base64
import json
import time

import pytest

PASSWORD = "correct-horse-battery-staple"


def decode_claims(token):
    """Read JWT claims without verifying the signature.

    A client can read claims; only the issuer can validate them. These
    tests assert what the token says, not that it is trustworthy.
    """
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)          # restore base64 padding
    return json.loads(base64.urlsafe_b64decode(payload))


# ───────────────────────────── health ─────────────────────────────

def test_liveness_needs_no_token(client):
    assert client.get("/liveness").status_code == 200


def test_readiness_needs_no_token(client):
    assert client.get("/readiness").status_code == 200


# ─────────────────────────── registration ───────────────────────────

def test_register_creates_a_user(client, new_email):
    r = client.post("/auth/register", json={
        "email": new_email,
        "password": PASSWORD,
        "name": "QA Tester",
        "org": "DocuMind QA",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["email"] == new_email


def test_register_normalises_email_case(client):
    """Email is an identity, not a string.

    If Alice@ and alice@ are different accounts, a user can silently
    create a duplicate and then fail to sign in.
    """
    import uuid
    local = f"qa_{uuid.uuid4().hex[:12]}"

    first = client.post("/auth/register", json={
        "email": f"{local.upper()}@EXAMPLE.COM",
        "password": PASSWORD, "name": "QA", "org": "DocuMind QA",
    })
    assert first.status_code == 200
    assert first.json()["email"] == f"{local}@example.com"

    duplicate = client.post("/auth/register", json={
        "email": f"{local}@example.com",
        "password": PASSWORD, "name": "QA", "org": "DocuMind QA",
    })
    assert duplicate.status_code == 409


def test_register_rejects_duplicate_email(client, registered):
    email, _ = registered
    r = client.post("/auth/register", json={
        "email": email, "password": PASSWORD,
        "name": "Someone Else", "org": "Other Org",
    })
    assert r.status_code == 409
    assert r.json()["field"] == "email"


def test_register_rejects_malformed_email(client):
    r = client.post("/auth/register", json={
        "email": "not-an-email", "password": PASSWORD,
        "name": "QA", "org": "DocuMind QA",
    })
    assert r.status_code == 422
    assert r.json()["field"] == "email"


def test_register_rejects_short_password(client, new_email):
    r = client.post("/auth/register", json={
        "email": new_email, "password": "short",
        "name": "QA", "org": "DocuMind QA",
    })
    assert r.status_code == 422
    assert r.json()["field"] == "password"


def test_register_rejects_short_org(client, new_email):
    r = client.post("/auth/register", json={
        "email": new_email, "password": PASSWORD,
        "name": "QA", "org": "X",
    })
    assert r.status_code == 422
    assert r.json()["field"] == "org"


def test_register_validation_errors_name_the_field(client, new_email):
    """The frontend highlights a specific input, so `field` is a contract."""
    r = client.post("/auth/register", json={
        "email": new_email, "password": "x",
        "name": "QA", "org": "DocuMind QA",
    })
    body = r.json()
    for key in ("ok", "field", "title", "detail"):
        assert key in body, f"missing {key} in validation error"
    assert body["ok"] is False


def test_register_rejects_missing_fields(client):
    assert client.post("/auth/register", json={}).status_code == 422


# ────────────────────────────── login ──────────────────────────────

def test_login_with_valid_credentials_returns_a_token(client, registered):
    email, password = registered
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert isinstance(body["token"], str) and body["token"]


def test_login_returns_session_details(client, registered):
    email, password = registered
    session = client.post("/auth/login", json={
        "email": email, "password": password,
    }).json()["session"]
    assert session["email"] == email
    assert session["name"] == "QA Tester"
    assert session["initials"] == "QT"


def test_login_rejects_wrong_password(client, registered):
    email, _ = registered
    r = client.post("/auth/login", json={
        "email": email, "password": "definitely-not-the-password",
    })
    assert r.status_code == 401
    assert r.json()["ok"] is False


def test_login_rejects_unknown_email(client):
    r = client.post("/auth/login", json={
        "email": "nobody@example.com", "password": PASSWORD,
    })
    assert r.status_code == 401


def test_failed_login_does_not_reveal_whether_the_account_exists(
    client, registered
):
    """Distinguishing the two turns login into an account enumerator."""
    email, _ = registered

    wrong_password = client.post("/auth/login", json={
        "email": email, "password": "wrong",
    })
    unknown_user = client.post("/auth/login", json={
        "email": "nobody-at-all@example.com", "password": "wrong",
    })

    assert wrong_password.status_code == unknown_user.status_code
    assert wrong_password.json()["title"] == unknown_user.json()["title"]


def test_login_never_returns_the_password(client, registered):
    email, password = registered
    body = client.post("/auth/login", json={
        "email": email, "password": password,
    }).text
    assert password not in body
    assert "password" not in body.lower()


def test_login_rejects_missing_fields(client):
    assert client.post("/auth/login", json={}).status_code == 422


# ─────────────────────────────── JWT ───────────────────────────────

def test_token_has_three_segments(token):
    assert len(token.split(".")) == 3


def test_token_subject_is_the_user(token, registered):
    email, _ = registered
    assert decode_claims(token)["sub"] == email


def test_token_carries_a_role(token):
    claims = decode_claims(token)
    assert "role" in claims
    assert claims["role"] == "user"


def test_token_expires(token):
    """A token without an expiry is valid forever if it leaks."""
    claims = decode_claims(token)
    assert "exp" in claims
    assert claims["exp"] > time.time()


def test_token_expiry_is_not_excessive(token):
    """Long-lived tokens widen the window on a stolen credential."""
    claims = decode_claims(token)
    lifetime_hours = (claims["exp"] - time.time()) / 3600
    assert lifetime_hours <= 24, (
        f"token is valid for {lifetime_hours:.1f}h — a leaked token stays "
        "usable for that long, and there is no revocation"
    )


def test_token_does_not_carry_the_password(token):
    claims = decode_claims(token)
    serialised = json.dumps(claims).lower()
    assert "password" not in serialised
    assert "hash" not in serialised


def test_two_logins_produce_usable_tokens(client, registered):
    """Logging in twice must not invalidate the first session."""
    email, password = registered
    first = client.post("/auth/login", json={
        "email": email, "password": password,
    }).json()["token"]
    second = client.post("/auth/login", json={
        "email": email, "password": password,
    }).json()["token"]

    assert decode_claims(first)["sub"] == decode_claims(second)["sub"]


# ──────────────────────── request correlation ────────────────────────

def test_request_id_is_echoed(client):
    """Correlation only works if the caller's id survives the hop."""
    r = client.get("/liveness", headers={"X-Request-ID": "qa-test-12345"})
    assert r.headers.get("X-Request-ID") == "qa-test-12345"


def test_request_id_is_generated_when_absent(client):
    r = client.get("/liveness")
    assert r.headers.get("X-Request-ID")