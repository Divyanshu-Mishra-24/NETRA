from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.database.neo4j import get_neo4j_session
from app.models.asset import Asset, GraphStats
from app.models.connection import Connection, ConnectionEdge


class FakeSession:
    def run(self, query: str, **params):  # pragma: no cover - simple fake
        raise AssertionError(f"Unexpected query: {query} params={params}")


@contextmanager
def _lifespan_noop(_: Any) -> Iterator[None]:
    yield


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(main_module, "lifespan", _lifespan_noop)

    def override_session():
        yield FakeSession()

    main_module.app.dependency_overrides[get_neo4j_session] = override_session
    with TestClient(main_module.app) as test_client:
        yield test_client
    main_module.app.dependency_overrides.clear()


def test_health_reports_neo4j_status(client, monkeypatch):
    class Driver:
        def verify_connectivity(self):
            return True

    monkeypatch.setattr(main_module.neo4j_db, "get_driver", lambda: Driver())
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "netra-backend"
    assert data["neo4j"] == "connected"
    assert data["status"] == "healthy"


def test_get_assets_returns_list(client, monkeypatch):
    assets = [
        Asset(id="web-01", name="Web", type="web_server", ip="10.0.0.1", os=None, ports=[80], exposure="public", criticality="medium"),
    ]
    monkeypatch.setattr("app.routers.assets.list_assets", lambda session: assets)
    response = client.get("/assets")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body[0]["id"] == "web-01"
    assert body[0]["ports"] == [80]


def test_get_asset_not_found_returns_404(client, monkeypatch):
    from app.services.graph_service import AssetNotFoundError

    def raise_missing(session, asset_id):
        raise AssetNotFoundError("missing")

    monkeypatch.setattr("app.routers.assets.get_asset", raise_missing)
    response = client.get("/assets/unknown")
    assert response.status_code == 404


def test_create_asset_returns_201(client, monkeypatch):
    created = Asset(id="tmp-01", name="Temp", type="server", ip=None, os="Linux", ports=[22], exposure="internal", criticality="low")
    monkeypatch.setattr("app.routers.assets.create_asset", lambda session, payload: created)
    response = client.post(
        "/assets",
        json={"id": "tmp-01", "name": "Temp", "type": "server", "ip": None, "os": "Linux", "ports": [22], "exposure": "internal", "criticality": "low"},
    )
    assert response.status_code == 201
    assert response.json()["id"] == "tmp-01"


def test_update_asset_returns_updated_asset(client, monkeypatch):
    updated = Asset(id="web-01", name="Web Updated", type="web_server", ip="10.0.0.2", os=None, ports=[443], exposure="public", criticality="high")
    monkeypatch.setattr("app.routers.assets.update_asset", lambda session, asset_id, payload: updated)
    response = client.put("/assets/web-01", json={"name": "Web Updated", "ports": [443]})
    assert response.status_code == 200
    assert response.json()["name"] == "Web Updated"
    assert response.json()["ports"] == [443]


def test_delete_asset_returns_204(client, monkeypatch):
    monkeypatch.setattr("app.routers.assets.delete_asset", lambda session, asset_id: None)
    response = client.delete("/assets/web-01")
    assert response.status_code == 204


def test_connect_assets_returns_edge(client, monkeypatch):
    edge = ConnectionEdge(
        id="web-01->api-01",
        source="web-01",
        target="api-01",
        data=Connection(source="web-01", target="api-01", destination="api-01", protocol="tcp", port=8000, allowed=True, evidence="test"),
        label="TCP",
    )
    monkeypatch.setattr("app.routers.assets.create_connection", lambda session, source_id, payload: edge)
    response = client.post("/assets/web-01/connect", json={"target": "api-01", "protocol": "tcp", "port": 8000, "allowed": True, "evidence": "test"})
    assert response.status_code == 201
    body = response.json()
    assert body["source"] == "web-01"
    assert body["target"] == "api-01"
    assert body["data"]["allowed"] is True


def test_get_graph_returns_nodes_and_edges(client, monkeypatch):
    graph = {
        "nodes": [
            {"id": "web-01", "type": "asset", "position": {"x": 0, "y": 0}, "data": {"id": "web-01", "name": "Web", "type": "web_server", "ip": None, "os": None, "ports": [80], "exposure": "public", "criticality": "medium", "source": "network-fixture"}},
        ],
        "edges": [
            {"id": "web-01->api-01", "source": "web-01", "target": "api-01", "type": "connects_to", "label": "TCP", "data": {"source": "web-01", "target": "api-01", "destination": "api-01", "protocol": "tcp", "port": 8000, "allowed": True, "evidence": "test"}},
        ],
    }
    monkeypatch.setattr("app.routers.graph.get_graph", lambda session: graph)
    response = client.get("/graph")
    assert response.status_code == 200
    body = response.json()
    assert "nodes" in body and "edges" in body
    assert body["nodes"][0]["id"] == "web-01"
    assert body["edges"][0]["source"] == "web-01"


def test_get_graph_stats_returns_counts(client, monkeypatch):
    monkeypatch.setattr("app.routers.graph.get_graph_stats", lambda session: GraphStats(asset_count=4, connection_count=3))
    response = client.get("/graph/stats")
    assert response.status_code == 200
    assert response.json() == {"asset_count": 4, "connection_count": 3}
