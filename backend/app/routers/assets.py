"""Assets API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.database.neo4j import Neo4jError, ServiceUnavailable, get_neo4j_session
from app.models.asset import Asset, AssetCreate, AssetUpdate
from app.models.connection import ConnectionCreate, ConnectionEdge
from app.services.graph_service import (
    AssetAlreadyExistsError,
    AssetNotFoundError,
    ConnectionValidationError,
    create_asset,
    create_connection,
    delete_asset,
    get_asset,
    list_assets,
    update_asset,
)

router = APIRouter(tags=["assets"])


@router.get("/assets", response_model=list[Asset])
def read_assets(session: Any = Depends(get_neo4j_session)) -> list[Asset]:
    try:
        return list_assets(session)
    except (ServiceUnavailable, Neo4jError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j database is unavailable",
        ) from exc


@router.get("/assets/{asset_id}", response_model=Asset)
def read_asset(asset_id: str, session: Any = Depends(get_neo4j_session)) -> Asset:
    try:
        return get_asset(session, asset_id)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ServiceUnavailable, Neo4jError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j database is unavailable",
        ) from exc


@router.post("/assets", response_model=Asset, status_code=status.HTTP_201_CREATED)
def create_asset_endpoint(payload: AssetCreate, session: Any = Depends(get_neo4j_session)) -> Asset:
    try:
        return create_asset(session, payload)
    except AssetAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (ServiceUnavailable, Neo4jError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j database is unavailable",
        ) from exc


@router.put("/assets/{asset_id}", response_model=Asset)
def update_asset_endpoint(
    asset_id: str, payload: AssetUpdate, session: Any = Depends(get_neo4j_session)
) -> Asset:
    try:
        return update_asset(session, asset_id, payload)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ServiceUnavailable, Neo4jError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j database is unavailable",
        ) from exc


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_asset_endpoint(asset_id: str, session: Any = Depends(get_neo4j_session)) -> Response:
    try:
        delete_asset(session, asset_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ServiceUnavailable, Neo4jError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j database is unavailable",
        ) from exc


@router.post(
    "/assets/{asset_id}/connect",
    response_model=ConnectionEdge,
    status_code=status.HTTP_201_CREATED,
)
def connect_asset_endpoint(
    asset_id: str, payload: ConnectionCreate, session: Any = Depends(get_neo4j_session)
) -> ConnectionEdge:
    try:
        return create_connection(session, asset_id, payload)
    except ConnectionValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ServiceUnavailable, Neo4jError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j database is unavailable",
        ) from exc

