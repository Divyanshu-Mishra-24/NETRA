"""Asset and graph node model definitions."""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AssetBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=200)
    type: str = Field(..., min_length=1, max_length=100)
    ip: Optional[str] = Field(default=None, max_length=100)
    os: Optional[str] = Field(default=None, max_length=100)
    ports: List[int] = Field(default_factory=list)
    exposure: Optional[str] = Field(default=None, max_length=50)
    criticality: Optional[str] = Field(default=None, max_length=50)
    software: List[dict[str, Any]] = Field(default_factory=list)
    risk_score: Optional[float] = Field(default=None, ge=0, le=100)
    risk_level: Optional[str] = Field(default=None, max_length=20)
    risk_calculated_at: Optional[str] = None


class AssetCreate(AssetBase):
    id: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")


class AssetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    type: Optional[str] = Field(default=None, min_length=1, max_length=100)
    ip: Optional[str] = Field(default=None, max_length=100)
    os: Optional[str] = Field(default=None, max_length=100)
    ports: Optional[List[int]] = None
    exposure: Optional[str] = Field(default=None, max_length=50)
    criticality: Optional[str] = Field(default=None, max_length=50)
    software: Optional[List[dict[str, Any]]] = None


class Asset(AssetBase):
    id: str
    source: Optional[str] = None


class AssetNode(BaseModel):
    id: str
    type: str = "asset"
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    data: Asset


class HealthResponse(BaseModel):
    status: str
    service: str = "netra-backend"
    neo4j: str
    detail: Optional[str] = None


class GraphStats(BaseModel):
    asset_count: int
    connection_count: int


class MessageResponse(BaseModel):
    message: str
    id: Optional[str] = None
    details: Optional[dict[str, Any]] = None
