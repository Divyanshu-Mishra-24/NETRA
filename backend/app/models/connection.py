"""Connection and graph edge model definitions."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ConnectionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol: Optional[str] = Field(default=None, max_length=50)
    port: Optional[int] = Field(default=None, ge=0, le=65535)
    allowed: Optional[bool] = None
    evidence: Optional[str] = Field(default=None, max_length=500)


class ConnectionCreate(ConnectionBase):
    target: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")


class Connection(ConnectionBase):
    source: str
    target: str
    destination: Optional[str] = None


class ConnectionEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str = "connects_to"
    data: Connection
    label: Optional[str] = None
