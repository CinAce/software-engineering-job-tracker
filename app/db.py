"""Database session management.

One place, imported everywhere. The previous version of this course imported
`app.database` thirteen times and created it in a different module's project,
which meant no application in that module started at all. It is created here,
once, before anything imports it.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.ports.config import get_settings

settings = get_settings()

# SQLite needs check_same_thread=False under a threaded server; Postgres does
# not accept the argument at all. One conditional, stated once.
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
