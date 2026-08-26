"""SQLAlchemy engine and session factory.

Mirrors ``services/document-service/app/database.py``. Two differences matter
for a worker:

* ``pool_size`` tracks ``concurrency`` rather than a request-handler default —
  each in-flight job holds a session at its stage boundaries, and a pool
  smaller than the concurrency limit turns into silent serialisation.
* Sessions are opened per *unit of work*, not per job. A job spans several
  seconds of HTTP calls to ai-service; holding a transaction open across those
  would pin a Postgres connection for the whole pipeline for no benefit.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

def _engine_options() -> dict:
    """Pool settings, skipped for SQLite.

    SQLite's default pool takes none of these arguments and raises on them, and
    the test suite runs the whole worker against an in-memory database. Guarding
    here keeps one engine definition rather than a second one wired up in
    conftest.
    """
    if settings.database_url.startswith("sqlite"):
        return {}
    return {
        # Recycles connections killed by a Postgres restart or an idle timeout,
        # which a long-lived worker hits far more often than a request handler.
        "pool_pre_ping": True,
        "pool_size": max(5, settings.concurrency + 1),
        "max_overflow": 10,
    }


engine = create_engine(settings.database_url, **_engine_options())

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope around one unit of work."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
