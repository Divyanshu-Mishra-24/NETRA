"""Graph API routes."""

from __future__ import annotations

from typing import Any

import fastapi
from fastapi import APIRouter, Depends, HTTPException, status

from app.database.neo4j import Neo4jError, ServiceUnavailable, get_neo4j_session
from app.models.asset import GraphStats
from app.services.graph_service import get_graph, get_graph_stats
from app.services.attack_path_service import (
    AssetNotFoundError,
    find_paths,
    graph_attack_summary,
    load_graph_snapshot,
    reachable_assets,
)

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


@router.get("/graph/paths")
def read_attack_paths(
    request_from: str = fastapi.Query(alias="from", min_length=1, max_length=100),
    request_to: str = fastapi.Query(alias="to", min_length=1, max_length=100),
    max_depth: int = fastapi.Query(default=6, ge=1, le=12),
    max_paths: int = fastapi.Query(default=20, ge=1, le=100),
    session: Any = Depends(get_neo4j_session),
) -> dict:
    try:
        asset_map, adjacency = load_graph_snapshot(session)
        return find_paths(asset_map, adjacency, request_from, request_to, max_depth, max_paths)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ServiceUnavailable, Neo4jError) as exc:
        raise HTTPException(status_code=503, detail="Neo4j database is unavailable") from exc


@router.get("/graph/shortest-path")
def read_shortest_path(
    request_from: str = fastapi.Query(alias="from", min_length=1, max_length=100),
    request_to: str = fastapi.Query(alias="to", min_length=1, max_length=100),
    max_depth: int = fastapi.Query(default=6, ge=1, le=12),
    session: Any = Depends(get_neo4j_session),
) -> dict:
    try:
        asset_map, adjacency = load_graph_snapshot(session)
        result = find_paths(asset_map, adjacency, request_from, request_to, max_depth, 100)
        if not result["paths"]:
            return result
        shortest_id = result["shortest_path"]
        result["paths"] = [item for item in result["paths"] if item["path_id"] == shortest_id]
        result["path_count"] = len(result["paths"])
        return result
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ServiceUnavailable, Neo4jError) as exc:
        raise HTTPException(status_code=503, detail="Neo4j database is unavailable") from exc


@router.get("/graph/reachable/{asset_id}")
def read_reachable_assets(
    asset_id: str,
    max_depth: int = fastapi.Query(default=12, ge=1, le=20),
    session: Any = Depends(get_neo4j_session),
) -> dict:
    try:
        asset_map, adjacency = load_graph_snapshot(session)
        return reachable_assets(asset_map, adjacency, asset_id, max_depth)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ServiceUnavailable, Neo4jError) as exc:
        raise HTTPException(status_code=503, detail="Neo4j database is unavailable") from exc


@router.get("/graph/attack-summary")
def read_attack_summary(session: Any = Depends(get_neo4j_session)) -> dict:
    try:
        asset_map, adjacency = load_graph_snapshot(session)
        return graph_attack_summary(asset_map, adjacency)
    except (ServiceUnavailable, Neo4jError) as exc:
        raise HTTPException(status_code=503, detail="Neo4j database is unavailable") from exc

