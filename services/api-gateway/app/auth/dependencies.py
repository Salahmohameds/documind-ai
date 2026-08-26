"""FastAPI dependencies for JWT-protected routes.

M2: Extract and validate the Bearer token from the ``Authorization`` header.
Uses the existing ``decode_token()`` from M1.  Returns a dict with ``sub``
and ``role`` so route handlers can access the authenticated user's identity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt_handler import decode_token
from app.config import settings

logger = logging.getLogger(settings.service_name)

# HTTPBearer extracts the Bearer token but we handle errors ourselves
# so auto_error=False lets us return our own 401 shape.
_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    """The identity extracted from a valid JWT — injected into protected routes."""

    email: str   # from ``sub``
    role: str    # from ``role``


class AuthError(Exception):
    """Raised when JWT validation fails.  Caught by the route layer."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


async def require_jwt(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthenticatedUser:
    """FastAPI dependency that enforces JWT authentication.

    Inject this into any route that requires a valid token::

        @router.get("/protected")
        async def protected(user: AuthenticatedUser = Depends(require_jwt)):
            ...

    Raises ``AuthError`` (caught by the exception handler in ``main.py``)
    if the token is missing, malformed, expired, or invalid.
    """
    if credentials is None:
        raise AuthError("Missing or malformed Authorization header")

    token = credentials.credentials

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired")
    except jwt.PyJWTError:
        raise AuthError("Invalid token")

    sub = payload.get("sub")
    role = payload.get("role")

    if not sub or not role:
        raise AuthError("Token missing required claims")

    return AuthenticatedUser(email=sub, role=role)
