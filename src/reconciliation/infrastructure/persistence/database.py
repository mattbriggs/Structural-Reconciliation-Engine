"""Database bootstrap for the SQLite persistence adapter (REQ-224).

Provides an engine and session factory. SQLite is suitable for local/single
-node deployments; production database selection remains an infrastructure
decision (the repositories depend only on a session factory).
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from reconciliation.infrastructure.persistence.models import Base


class Database:
    """Owns a SQLAlchemy engine and session factory.

    :param url: SQLAlchemy database URL; defaults to an in-memory SQLite db.
    """

    def __init__(self, url: str = "sqlite+pysqlite:///:memory:") -> None:
        # ``check_same_thread`` is relaxed only for in-memory/dev SQLite use.
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        engine_kwargs: dict[str, object] = {"future": True, "connect_args": connect_args}
        # An in-memory SQLite database is per-connection; a StaticPool shares one
        # connection so tables created once are visible across request threads.
        if url.startswith("sqlite") and ":memory:" in url:
            engine_kwargs["poolclass"] = StaticPool
        self._engine: Engine = create_engine(url, **engine_kwargs)
        self._session_factory = sessionmaker(bind=self._engine, future=True)

    def create_all(self) -> None:
        """Create all tables. Idempotent."""
        Base.metadata.create_all(self._engine)

    @property
    def session_factory(self) -> Callable[[], Session]:
        """Return the session factory for repositories."""
        return self._session_factory

    def dispose(self) -> None:
        """Dispose of the engine's connection pool."""
        self._engine.dispose()
