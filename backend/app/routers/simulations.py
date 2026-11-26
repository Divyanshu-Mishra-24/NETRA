"""Simulation API routes."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.get("")
def list_simulations() -> list[dict]:
    """Placeholder simulations endpoint (network twin Day 1 scope does not modify simulations)."""
    return []
