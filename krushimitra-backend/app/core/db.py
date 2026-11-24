"""Database engine + session. SQLAlchemy 2.0 style.

The engine is created lazily (no connection at import), so the app boots and mock endpoints work
even with no database running. DB-backed endpoints open a session via the `get_db` dependency.
"""
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# SQLite + FastAPI: requests are served on a threadpool, so the default same-thread check
# would reject every session opened outside the creating thread.
_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)
if settings.database_url.startswith("sqlite"):
    _path = settings.database_url.split("///", 1)[-1]
    if _path and _path != ":memory:":
        Path(_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url, pool_pre_ping=True, future=True, connect_args=_connect_args
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all() -> None:
    """Create any missing tables. Called at startup.

    Deliberately not Alembic yet: the schema is still moving daily and there is no production
    data to migrate. Swap to Alembic before the first real farmer's data exists.
    """
    from app import models  # noqa: F401  - registers every model on Base.metadata

    Base.metadata.create_all(bind=engine)
