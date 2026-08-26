"""In-memory user store — M1 only.

This is a deliberate temporary solution for Milestone 1.  No database, no
users table.  A production implementation would store users in PostgreSQL
(requires a ``users`` table approved by Role 6 / Data Engineer).

The store is pre-seeded with the test user specified in the M1 blockers
resolution: ``admin@documind.com / password123``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from passlib.hash import bcrypt

from app.config import settings

logger = logging.getLogger(settings.service_name)


@dataclass
class User:
    """Minimal user record for M1."""

    email: str
    name: str
    org: str
    password_hash: str
    role: str = "user"


class InMemoryUserStore:
    """Thread-safe (GIL-protected) dictionary-backed store.

    Production replacement: PostgreSQL ``users`` table behind a repository
    interface with the same ``get`` / ``create`` contract.
    """

    def __init__(self) -> None:
        self._users: dict[str, User] = {}
        self._seed()

    def _seed(self) -> None:
        """Pre-populate the test user required for M1 validation."""
        self.create(
            email="admin@documind.com",
            name="Admin User",
            org="DocuMind",
            password="password123",
            role="admin",
        )
        logger.info(
            "user_store_seeded",
            extra={"seeded_users": ["admin@documind.com"]},
        )

    def get(self, email: str) -> User | None:
        """Look up a user by email (case-insensitive)."""
        return self._users.get(email.strip().lower())

    def exists(self, email: str) -> bool:
        return email.strip().lower() in self._users

    def create(
        self,
        *,
        email: str,
        name: str,
        org: str,
        password: str,
        role: str = "user",
    ) -> User:
        """Hash the password and store the user.  Returns the new ``User``."""
        normalised = email.strip().lower()
        user = User(
            email=normalised,
            name=name,
            org=org,
            password_hash=bcrypt.hash(password),
            role=role,
        )
        self._users[normalised] = user
        return user

    def verify_password(self, email: str, password: str) -> User | None:
        """Return the ``User`` if the password matches, else ``None``."""
        user = self.get(email)
        if user is None:
            return None
        if not bcrypt.verify(password, user.password_hash):
            return None
        return user


# Module-level singleton.
user_store = InMemoryUserStore()
