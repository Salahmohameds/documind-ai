"""Protected routes behind the gateway.

The gateway now proxies to document-service and search-service, so the
JWT middleware finally has something to protect. Until this landed,
every downstream test ran with DISABLE_AUTH=true and the auth path had
never been exercised end to end.

Needs the gateway plus whichever downstream service each route reaches.
"""

import base64
import json
import time

import pytest

PROTECTED_GET = [
    "/documents",
    "/documents/nonexistent/status",
    "/search?question=test&top_k=1",
]


def forge_token(claims):
    """Build a structurally valid JWT with a bogus signature.

    Tests rejection of a token the gateway did not issue. A test must
    never hold the signing secret — if it needs one to pass, the
    boundary it is testing does not exist.
    """
    def b64(obj):
        raw = json.dumps(obj).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    header = b64({"alg": "HS256", "typ": "JWT"})
    payload = b64(claims)
    return f"{header}.{payload}.not-a-real-signature"


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────── unauthenticated access ───────────────────────

@pytest.mark.parametrize("path", PROTECTED_GET)
def test_protected_route_without_a_token_is_401(client, path):
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("path", PROTECTED_GET)
def test_protected_route_with_a_valid_token_is_allowed(client, token, path):
    """Not asserting 200 — a 404 for a missing document is a pass here.

    What matters is that the request reached the downstream service
    rather than being rejected at the gateway.
    """
    r = client.get(path, headers=auth(token))
    assert r.status_code != 401, f"{path} rejected a valid token"
    assert r.status_code < 500, f"{path} returned {r.status_code}"


def test_upload_requires_a_token(client):
    r = client.post("/documents", files={
        "file": ("x.pdf", b"%PDF-1.4\n", "application/pdf"),
    })
    assert r.status_code == 401


# ────────────────────────── malformed tokens ──────────────────────────

def test_garbage_token_is_rejected(client):
    assert client.get("/documents", headers=auth("garbage")).status_code == 401


def test_token_with_a_forged_signature_is_rejected(client):
    """Anyone can mint claims. Only the issuer can sign them.

    If this passes, authentication is decorative — a caller could grant
    themselves any identity or role they like.
    """
    forged = forge_token({
        "sub": "attacker@example.com",
        "role": "admin",
        "exp": int(time.time()) + 3600,
    })
    r = client.get("/documents", headers=auth(forged))
    assert r.status_code == 401, (
        "a token with an invalid signature was accepted — the gateway is "
        "reading claims without verifying them"
    )


def test_expired_token_is_rejected(client):
    forged = forge_token({
        "sub": "someone@example.com",
        "role": "user",
        "exp": int(time.time()) - 3600,
    })
    assert client.get("/documents", headers=auth(forged)).status_code == 401


def test_token_without_the_bearer_scheme_is_rejected(client, token):
    r = client.get("/documents", headers={"Authorization": token})
    assert r.status_code == 401


def test_bearer_without_a_token_is_rejected(client):
    """A scheme with nothing after it is not a credential.

    Note the header is 'Bearer' with no trailing space — httpx refuses
    to send a header value ending in whitespace, so a trailing-space
    version never leaves the client and tests nothing.
    """
    r = client.get("/documents", headers={"Authorization": "Bearer"})
    assert r.status_code == 401


def test_wrong_auth_scheme_is_rejected(client, token):
    r = client.get("/documents", headers={"Authorization": f"Basic {token}"})
    assert r.status_code == 401


# ──────────────────────────── proxy behaviour ────────────────────────────

def test_proxied_response_keeps_its_shape(client, token):
    """The gateway must forward the downstream body, not rewrap it.

    A gateway that reshapes responses becomes a second contract to keep
    in sync, and the frontend ends up coupled to both.
    """
    r = client.get("/documents", headers=auth(token))
    assert r.status_code == 200
    assert "rows" in r.json(), "document list envelope lost in the proxy"


def test_downstream_404_is_preserved(client, token):
    """An unknown document must stay a 404, not become a 500."""
    r = client.get("/documents/definitely_not_a_real_id", headers=auth(token))
    assert r.status_code == 404


def test_search_results_pass_through(client, token):
    r = client.get("/search", params={"question": "payment", "top_k": 5},
                   headers=auth(token))
    assert r.status_code == 200
    assert isinstance(r.json()["results"], list)


def test_request_id_survives_the_proxy_hop(client, token):
    """One id must span gateway and downstream, or correlation breaks."""
    r = client.get("/documents", headers={
        **auth(token), "X-Request-ID": "qa-proxy-trace-001",
    })
    assert r.headers.get("X-Request-ID") == "qa-proxy-trace-001"


# ──────────────────────────── health surface ────────────────────────────

def test_health_probes_remain_unauthenticated(client):
    """Kubernetes cannot present a token.

    If the probes end up behind the same middleware as the proxied
    routes, the kubelet sees 401 and restarts the pod forever.
    """
    for path in ("/liveness", "/readiness"):
        assert client.get(path).status_code == 200

  