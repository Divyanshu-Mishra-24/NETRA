"""Cyber Twin API application."""

from __future__ import annotations

import os
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.neo4j import Neo4jError, ServiceUnavailable, neo4j_db
from app.routers import assets, graph, simulations, vulnerabilities
from app.services.graph_service import ensure_constraints

load_dotenv()
logger = logging.getLogger(__name__)


def _frontend_origins() -> list[str]:
    configured = os.getenv("FRONTEND_ORIGINS")
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        neo4j_db.connect()
        with neo4j_db.session() as session:
            ensure_constraints(session)
    except Exception as exc:
        logger.error("Neo4j startup connectivity failed: %s: %s", type(exc).__name__, exc)
    yield
    neo4j_db.close()


app = FastAPI(
    title="NETRA Cyber Twin API",
    description="FastAPI backend for the NETRA network digital twin backed by Neo4j.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_frontend_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assets.router)
app.include_router(graph.router)
app.include_router(simulations.router)
app.include_router(vulnerabilities.router)


@app.get("/health")
def health() -> dict[str, str]:
    neo4j_status = "unavailable"
    try:
        neo4j_db.get_driver().verify_connectivity()
        neo4j_status = "connected"
    except (ServiceUnavailable, Neo4jError, OSError):
        neo4j_status = "unavailable"
    except Exception:
        neo4j_status = "unavailable"

    overall = "healthy" if neo4j_status == "connected" else "degraded"
    return {"status": overall, "service": "netra-backend", "neo4j": neo4j_status}
