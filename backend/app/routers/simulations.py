"""Simulation API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.database.neo4j import Neo4jError, ServiceUnavailable, get_neo4j_session
from app.services.attack_path_service import (
    AssetNotFoundError,
    load_graph_snapshot,
    simulate_propagation,
)

router = APIRouter(tags=["simulations"])


class PropagationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    starting_asset: str = Field(min_length=1, max_length=100)
    max_depth: int = Field(default=12, ge=1, le=20)


@router.post("/simulate")
def simulate_compromise(
    payload: PropagationRequest,
    session: Any = Depends(get_neo4j_session),
) -> dict:
    try:
        asset_map, adjacency = load_graph_snapshot(session)
        return simulate_propagation(
            asset_map,
            adjacency,
            payload.starting_asset,
            payload.max_depth,
        )
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ServiceUnavailable, Neo4jError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j database is unavailable",
        ) from exc
