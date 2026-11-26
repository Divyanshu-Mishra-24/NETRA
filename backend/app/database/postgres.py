"""PostgreSQL client configuration (reserved; network twin uses Neo4j)."""

from __future__ import annotations

import os
from typing import Any

try:  # Optional dependency for future relational storage use.
    from sqlalchemy import create_engine
    from sqlalchemy.orm import declarative_base, sessionmaker
except Exception:  # pragma: no cover
    create_engine = None  # type: ignore[assignment]
    declarative_base = None  # type: ignore[assignment]
    sessionmaker = None  # type: ignore[assignment]

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")

Base = declarative_base() if declarative_base is not None else None
engine: Any = None
SessionLocal: Any = None


def init_engine() -> Any:
    """Create a SQLAlchemy engine only when explicitly configured."""
    global engine, SessionLocal
    if not DATABASE_URL:
        return None
    if create_engine is None or sessionmaker is None:
        raise RuntimeError("SQLAlchemy is required for DATABASE_URL/POSTGRES_URL support")
    if engine is None:
        connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
        engine = create_engine(DATABASE_URL, connect_args=connect_args)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine


def create_all_tables() -> None:
    """Create relational tables only when Base/engine are explicitly configured."""
    eng = init_engine()
    if eng is None or Base is None:
        return
    Base.metadata.create_all(bind=eng)
