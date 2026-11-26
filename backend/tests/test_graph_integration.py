import os
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _neo4j_config():
    return (
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        os.getenv("NEO4J_USER", "neo4j"),
        os.getenv("NEO4J_PASSWORD", "netra_password"),
    )


@pytest.fixture(scope="module")
def integration_client():
    try:
        from neo4j import GraphDatabase
    except Exception as exc:
        pytest.skip(f"Neo4j Python driver not installed for integration test: {exc}")

    uri, user, password = _neo4j_config()
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        driver.close()
    except Exception as exc:
        pytest.skip(f"Neo4j not available for integration test: {exc}")

    with TestClient(app) as client:
        yield client


def test_graph_crud_with_temporary_asset(integration_client):
    client = integration_client
    asset_id = f"tmp-test-{uuid.uuid4().hex[:8]}"
    target_id = "internet"
    payload = {
        "id": asset_id,
        "name": "Temporary Test Asset",
        "type": "test_server",
        "ip": "10.255.255.10",
        "os": "TestOS",
        "ports": [65000],
        "exposure": "internal",
        "criticality": "low",
    }

    try:
        create_resp = client.post("/assets", json=payload)
        assert create_resp.status_code == 201
        assert create_resp.json()["id"] == asset_id

        get_resp = client.get(f"/assets/{asset_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == payload["name"]
        assert get_resp.json()["ports"] == payload["ports"]

        update_resp = client.put(f"/assets/{asset_id}", json={"name": "Temporary Test Asset Updated", "criticality": "medium"})
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "Temporary Test Asset Updated"
        assert update_resp.json()["criticality"] == "medium"

        # Connect temp asset to existing 'internet' node if present; otherwise create a temporary target and clean both.
        target_check = client.get(f"/assets/{target_id}")
        cleanup_target = False
        if target_check.status_code != 200:
            target_id = f"tmp-target-{uuid.uuid4().hex[:8]}"
            cleanup_target = True
            target_payload = {**payload, "id": target_id, "name": "Temporary Target"}
            assert client.post("/assets", json=target_payload).status_code == 201

        connect_resp = client.post(
            f"/assets/{asset_id}/connect",
            json={"target": target_id, "protocol": "tcp", "port": 65000, "allowed": True, "evidence": "pytest-temp-connection"},
        )
        assert connect_resp.status_code == 201
        edge = connect_resp.json()
        assert edge["source"] == asset_id
        assert edge["target"] == target_id

        graph_resp = client.get("/graph")
        assert graph_resp.status_code == 200
        graph = graph_resp.json()
        assert any(node["id"] == asset_id for node in graph.get("nodes", []))
        assert any(e["source"] == asset_id and e["target"] == target_id for e in graph.get("edges", []))

        stats_resp = client.get("/graph/stats")
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        assert "asset_count" in stats and "connection_count" in stats

    finally:
        # Clean up only temporary test data
        client.delete(f"/assets/{asset_id}")
        if 'cleanup_target' in locals() and locals().get('cleanup_target'):
            client.delete(f"/assets/{target_id}")
