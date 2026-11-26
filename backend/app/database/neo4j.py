"""Neo4j client configuration and FastAPI dependencies."""

from __future__ import annotations

import os
import logging
from contextlib import contextmanager
from typing import Any, Generator, TYPE_CHECKING

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

try:  # pragma: no cover - exercised in environments with neo4j installed
    from neo4j import GraphDatabase
    from neo4j.exceptions import Neo4jError, ServiceUnavailable
except Exception:  # pragma: no cover
    GraphDatabase = None  # type: ignore[assignment]

    class Neo4jError(Exception):
        """Fallback Neo4j error when the neo4j driver package is unavailable."""

    class ServiceUnavailable(Exception):
        """Fallback Neo4j service unavailable error when the driver package is unavailable."""

if TYPE_CHECKING:  # pragma: no cover
    from neo4j import Driver, Session


class Neo4jDatabase:
    def __init__(self) -> None:
        self._driver: Any = None

    @property
    def uri(self) -> str:
        return os.getenv("NEO4J_URI", "bolt://localhost:7687")

    @property
    def user(self) -> str:
        return os.getenv("NEO4J_USER", "neo4j")

    @property
    def password(self) -> str:
        return os.getenv("NEO4J_PASSWORD", "netra_password")

    def connect(self) -> None:
        if self._driver is None:
            if GraphDatabase is None:
                raise ServiceUnavailable(
                    "Neo4j Python driver is not installed. Install backend dependencies from requirements.txt."
                )
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def get_driver(self) -> Any:
        if self._driver is None:
            self.connect()
        assert self._driver is not None
        return self._driver

    def verify_connectivity(self) -> bool:
        try:
            self.get_driver().verify_connectivity()
            return True
        except Exception as exc:
            logger.error("Neo4j connectivity check failed: %s: %s", type(exc).__name__, exc)
            return False

    @contextmanager
    def session(self) -> Generator[Any, None, None]:
        session = self.get_driver().session()
        try:
            yield session
        finally:
            session.close()


neo4j_db = Neo4jDatabase()


def get_neo4j_session() -> Generator[Any, None, None]:
    with neo4j_db.session() as session:
        yield session


__all__ = ["neo4j_db", "get_neo4j_session", "Neo4jError", "ServiceUnavailable"]
