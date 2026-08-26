"""Pydantic schemas for the auth endpoints.

Request/response shapes match the frontend contract in
``frontend/documind/lib/api.ts`` — specifically ``SignUpInput``,
``SignUpResult``, ``SignInResult``, and ``Session``.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    """``POST /auth/login`` request body."""

    email: str
    password: str


class SessionSchema(BaseModel):
    """Matches ``Session`` in ``frontend/documind/lib/types.ts``."""

    email: str
    name: str
    initials: str


class LoginSuccessResponse(BaseModel):
    """Successful login — includes JWT token + session."""

    ok: bool = True
    token: str
    session: SessionSchema


class LoginFailureResponse(BaseModel):
    """Failed login — matches the frontend's error branch."""

    ok: bool = False
    title: str
    detail: str
    locked_out: bool = False


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """``POST /auth/register`` request body.

    Fields match ``SignUpInput`` in ``frontend/documind/lib/api.ts``:
    ``name``, ``email``, ``org``, ``password``.
    """

    name: str
    email: str
    org: str
    password: str


class RegisterSuccessResponse(BaseModel):
    """Matches ``{ ok: true, email, verificationSentTo }`` from the frontend."""

    ok: bool = True
    email: str
    verification_sent_to: str

    class Config:
        populate_by_name = True


class RegisterFailureResponse(BaseModel):
    """Matches ``{ ok: false, field, title, detail }`` from the frontend."""

    ok: bool = False
    field: str | None = None
    title: str
    detail: str
