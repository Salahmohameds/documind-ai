"""Authentication routes — register and login.

M1 scope:
- ``POST /auth/register`` — creates a user in the in-memory store.
- ``POST /auth/login``    — verifies credentials, returns a JWT.

Request/response shapes match the frontend contract in
``frontend/documind/lib/api.ts``.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.auth.jwt_handler import create_token
from app.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    SessionSchema,
)
from app.auth.store import user_store
from app.config import settings

logger = logging.getLogger(settings.service_name)

router = APIRouter(prefix="/auth", tags=["auth"])


def _initials(name: str) -> str:
    """Derive initials from a display name (e.g. 'Admin User' → 'AU')."""
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    if parts:
        return parts[0][:2].upper()
    return "??"


# ── POST /auth/register ─────────────────────────────────────────────────


@router.post("/register")
def register(body: RegisterRequest):
    """Create a new user in the in-memory store (M1).

    Response shape matches ``SignUpResult`` in the frontend.
    """
    email = body.email.strip().lower()

    # --- validation (mirrors frontend's stub logic) ----------------------
    if not email or "@" not in email:
        return JSONResponse(
            status_code=422,
            content={
                "ok": False,
                "field": "email",
                "title": "Invalid email address",
                "detail": "Please enter a valid email address.",
            },
        )

    if user_store.exists(email):
        return JSONResponse(
            status_code=409,
            content={
                "ok": False,
                "field": "email",
                "title": "That email already has an account",
                "detail": "Sign in instead, or use a different address.",
            },
        )

    if len(body.password) < 8:
        return JSONResponse(
            status_code=422,
            content={
                "ok": False,
                "field": "password",
                "title": "Password too short",
                "detail": "Passwords must be at least 8 characters.",
            },
        )

    if body.org.strip() == "" or len(body.org.strip()) < 2:
        return JSONResponse(
            status_code=422,
            content={
                "ok": False,
                "field": "org",
                "title": "Workspace name is too short",
                "detail": "Use the name your team will recognise — it appears on every exported report.",
            },
        )

    # --- create -----------------------------------------------------------
    user_store.create(
        email=email,
        name=body.name.strip(),
        org=body.org.strip(),
        password=body.password,
        role="user",
    )

    logger.info("user_registered", extra={"email": email})

    return {
        "ok": True,
        "email": email,
        "verificationSentTo": email,
    }


# ── POST /auth/login ────────────────────────────────────────────────────


@router.post("/login")
def login(body: LoginRequest):
    """Verify credentials and issue a JWT.

    Response shape matches the user-specified contract:
    ``{ ok, token, session: { email, name, initials } }``
    """
    user = user_store.verify_password(body.email, body.password)

    if user is None:
        logger.info(
            "login_failed",
            extra={"email": body.email.strip().lower()},
        )
        return JSONResponse(
            status_code=401,
            content={
                "ok": False,
                "title": "Invalid email or password",
                "detail": "Check your credentials and try again.",
                "lockedOut": False,
            },
        )

    token = create_token(email=user.email, role=user.role)

    logger.info("login_success", extra={"email": user.email, "role": user.role})

    return {
        "ok": True,
        "token": token,
        "session": SessionSchema(
            email=user.email,
            name=user.name,
            initials=_initials(user.name),
        ).model_dump(),
    }
