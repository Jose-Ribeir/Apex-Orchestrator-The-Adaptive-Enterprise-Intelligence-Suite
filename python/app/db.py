"""
PostgreSQL connection via SQLAlchemy (DATABASE_URL).
"""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine | None:
    """Return SQLAlchemy engine, or None if database not configured."""
    global _engine
    settings = get_settings()
    if not settings.database_configured:
        return None
    if _engine is None:
        _engine = create_engine(
            settings.get_database_url(),
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            connect_args={"connect_timeout": 10},
        )
    return _engine


def get_session_factory() -> sessionmaker[Session] | None:
    """Return session factory for Cloud SQL, or None if not configured."""
    global _SessionLocal
    engine = get_engine()
    if engine is None:
        return None
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _SessionLocal


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager for a DB session. Raises RuntimeError if Cloud SQL is not configured."""
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("Database is not configured. Set DATABASE_URL in .env")
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_connection() -> bool:
    """Return True if Cloud SQL is configured and a test query succeeds."""
    engine = get_engine()
    if engine is None:
        return False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
