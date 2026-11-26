import json
import os
import sys
import time
from pathlib import Path

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

INVENTORY_DIR = Path(os.getenv("INVENTORY_DIR", "/app/inventory"))
MAX_ATTEMPTS = int(os.getenv("NEO4J_CONNECT_ATTEMPTS", "15"))
RETRY_DELAY_SECONDS = float(os.getenv("NEO4J_CONNECT_RETRY_DELAY", "2"))


def load_json(name: str):
    path = INVENTORY_DIR / name
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def connect_with_retry(uri: str, user: str, password: str):
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            driver.verify_connectivity()
            return driver
        except (ServiceUnavailable, OSError, Neo4jError) as exc:
            last_error = exc
            if attempt == MAX_ATTEMPTS:
                break
            print(
                f"Waiting for Neo4j ({attempt}/{MAX_ATTEMPTS}): {exc}",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(RETRY_DELAY_SECONDS)
    raise RuntimeError(f"Unable to connect to Neo4j at {uri}: {last_error}")


def import_inventory(session, assets, connections):
    session.run(
        "CREATE CONSTRAINT asset_id IF NOT EXISTS FOR (asset:Asset) REQUIRE asset.id IS UNIQUE"
    )

    asset_query = """
    MERGE (asset:Asset {id: $id})
    SET asset.name = $name,
        asset.type = $type,
        asset.ip = $ip,
        asset.os = $os,
        asset.ports = $ports,
        asset.exposure = $exposure,
        asset.criticality = $criticality,
        asset.source = 'network-fixture'
    """
    for asset in assets:
        session.run(
            asset_query,
            id=asset["id"],
            name=asset.get("name"),
            type=asset.get("type"),
            ip=asset.get("ip"),
            os=asset.get("os"),
            ports=asset.get("ports", []),
            exposure=asset.get("exposure"),
            criticality=asset.get("criticality"),
        )

    connection_query = """
    MATCH (source:Asset {id: $source})
    MATCH (target:Asset {id: $target})
    MERGE (source)-[link:CONNECTS_TO {source: $source, target: $target}]->(target)
    SET link.source = $source,
        link.destination = $target,
        link.protocol = $protocol,
        link.port = $port,
        link.allowed = $allowed,
        link.evidence = $evidence
    """
    for connection in connections:
        summary = session.run(
            connection_query,
            source=connection["source"],
            target=connection["target"],
            protocol=connection.get("protocol"),
            port=connection.get("port"),
            allowed=connection.get("allowed"),
            evidence=connection.get("evidence"),
        ).consume()
        if summary.counters.nodes_created < 0:
            raise RuntimeError("Unexpected Neo4j write result while importing connections")

    # Verify counts against inventory (idempotent import must include all fixture records)
    asset_ids = [asset["id"] for asset in assets]
    asset_count = session.run(
        "MATCH (asset:Asset) WHERE asset.id IN $asset_ids RETURN count(asset) AS count",
        asset_ids=asset_ids,
    ).single()["count"]
    if asset_count != len(asset_ids):
        raise RuntimeError(
            f"Asset import verification failed: expected {len(asset_ids)} assets, found {asset_count}"
        )

    connection_count = session.run(
        """
        UNWIND $connections AS connection
        MATCH (:Asset {id: connection.source})-[link:CONNECTS_TO {source: connection.source, target: connection.target}]->(:Asset {id: connection.target})
        RETURN count(link) AS count
        """,
        connections=[{"source": c["source"], "target": c["target"]} for c in connections],
    ).single()["count"]
    if connection_count != len(connections):
        raise RuntimeError(
            f"Connection import verification failed: expected {len(connections)} relationships, found {connection_count}"
        )

    return asset_count, connection_count


def main():
    uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "netra_password")

    assets = load_json("assets.json")
    connections = load_json("connections.json")

    driver = None
    try:
        driver = connect_with_retry(uri, user, password)
        with driver.session() as session:
            asset_count, connection_count = session.execute_write(
                import_inventory, assets, connections
            )
        print(
            f"Imported {asset_count} assets and {connection_count} connections from {INVENTORY_DIR}",
            flush=True,
        )
    except Exception as exc:
        print(f"Inventory import failed: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1) from exc
    finally:
        if driver is not None:
            driver.close()


if __name__ == "__main__":
    main()
