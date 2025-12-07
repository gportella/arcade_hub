"""Database engine and session management."""

from contextlib import contextmanager
from typing import Generator, Iterator

from sqlmodel import Session, SQLModel, create_engine

from .config import get_settings

_engine = None


def get_engine():
    """Return a singleton SQLModel engine."""

    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = (
            {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
        )
        _engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)
    return _engine


def init_db() -> None:
    """Create database tables if they do not yet exist."""

    engine = get_engine()
    SQLModel.metadata.create_all(engine)


@contextmanager
def session_context() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""

    session = Session(get_engine())
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency to yield a session."""

    with session_context() as session:
        yield session
