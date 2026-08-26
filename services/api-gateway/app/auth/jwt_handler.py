"""JWT creation and validation helpers.

M1 specification (blocker resolution):
- Algorithm: HS256
- Secret: ``JWT_SECRET`` environment variable
- Claims: ``sub`` (email), ``exp`` (24 h), ``role`` (user | admin)
- No ``iss``, ``aud``, or additional claims.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

from app.config import settings


def create_token(*, email: str, role: str) -> str:
    """Issue a signed JWT with the M1 claim set."""
    now = datetime.now(UTC)
    payload = {
        "sub": email,
        "exp": now + timedelta(hours=settings.jwt_expiration_hours),
        "role": role,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT.  Raises ``jwt.PyJWTError`` on failure."""
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
