"""Graph API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.database.neo4j import Neo4jError, ServiceUnavailable, get_neo4j_session
from app.models.asset import GraphStats
from app.services.graph_service import get_graph, get_graph_stats

router = APIRouter(tags=["graph"])


@router.get("/graph")
def read_graph(session: Any = Depends(get_neo4j_session)) -> dict:
    try:
        return get_graph(session)
    except (ServiceUnavailable, Neo4jError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j database is unavailable",
        ) from exc


@router.get("/graph/stats", response_model=GraphStats)
def read_graph_stats(session: Any = Depends(get_neo4j_session)) -> GraphStats:
    try:
        return get_graph_stats(session)
    except (ServiceUnavailable, Neo4jError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j database is unavailable",
        ) from exc

