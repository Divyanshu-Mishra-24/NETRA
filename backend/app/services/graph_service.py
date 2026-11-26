"""Infrastructure graph service backed by Neo4j."""

from __future__ import annotations

from typing import Any

from app.models.asset import Asset, AssetCreate, AssetNode, AssetUpdate, GraphStats
from app.models.connection import Connection, ConnectionCreate, ConnectionEdge


class AssetNotFoundError(Exception):
    pass


class AssetAlreadyExistsError(Exception):
    pass


class ConnectionValidationError(Exception):
    pass


def _normalize_ports(value: Any) -> list[int]:
    if value is None:
        return []
    if isinstance(value, list):
        ports: list[int] = []
        for item in value:
            try:
                ports.append(int(item))
            except (TypeError, ValueError):
                continue
        return ports
    return []


def _asset_from_node(node: dict[str, Any]) -> Asset:
    return Asset(
        id=str(node.get("id")),
        name=node.get("name") or "",
        type=node.get("type") or "unknown",
        ip=node.get("ip"),
        os=node.get("os"),
        ports=_normalize_ports(node.get("ports")),
        exposure=node.get("exposure"),
        criticality=node.get("criticality"),
        source=node.get("source"),
    )


def _connection_from_rel(source_id: str, target_id: str, rel: dict[str, Any]) -> Connection:
    return Connection(
        source=source_id,
        target=target_id,
        destination=rel.get("destination") or target_id,
        protocol=rel.get("protocol"),
        port=rel.get("port"),
        allowed=rel.get("allowed"),
        evidence=rel.get("evidence"),
    )


def ensure_constraints(session: Any) -> None:
    session.run(
        "CREATE CONSTRAINT asset_id IF NOT EXISTS FOR (asset:Asset) REQUIRE asset.id IS UNIQUE"
    )


def list_assets(session: Any) -> list[Asset]:
    records = session.run(
        """
        MATCH (asset:Asset)
        RETURN asset
        ORDER BY asset.name, asset.id
        """
    )
    return [_asset_from_node(dict(record["asset"])) for record in records]


def get_asset(session: Any, asset_id: str) -> Asset:
    record = session.run(
        "MATCH (asset:Asset {id: $id}) RETURN asset",
        id=asset_id,
    ).single()
    if record is None:
        raise AssetNotFoundError(f"Asset '{asset_id}' not found")
    return _asset_from_node(dict(record["asset"]))


def create_asset(session: Any, payload: AssetCreate) -> Asset:
    existing = session.run(
        "MATCH (asset:Asset {id: $id}) RETURN asset.id AS id",
        id=payload.id,
    ).single()
    if existing is not None:
        raise AssetAlreadyExistsError(f"Asset '{payload.id}' already exists")

    data = payload.model_dump()
    record = session.run(
        """
        CREATE (asset:Asset {id: $id})
        SET asset.name = $name,
            asset.type = $type,
            asset.ip = $ip,
            asset.os = $os,
            asset.ports = $ports,
            asset.exposure = $exposure,
            asset.criticality = $criticality,
            asset.source = 'api'
        RETURN asset
        """,
        **data,
    ).single()
    if record is None:
        raise RuntimeError("Failed to create asset")
    return _asset_from_node(dict(record["asset"]))


def update_asset(session: Any, asset_id: str, payload: AssetUpdate) -> Asset:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return get_asset(session, asset_id)

    params: dict[str, Any] = {"id": asset_id}
    set_clauses = []
    for key, value in updates.items():
        params[key] = value
        set_clauses.append(f"asset.{key} = ${key}")

    query = f"""
    MATCH (asset:Asset {{id: $id}})
    SET {', '.join(set_clauses)}
    RETURN asset
    """
    record = session.run(query, **params).single()
    if record is None:
        raise AssetNotFoundError(f"Asset '{asset_id}' not found")
    return _asset_from_node(dict(record["asset"]))


def delete_asset(session: Any, asset_id: str) -> None:
    record = session.run(
        """
        MATCH (asset:Asset {id: $id})
        WITH asset, asset.id AS id
        DETACH DELETE asset
        RETURN id
        """,
        id=asset_id,
    ).single()
    if record is None:
        raise AssetNotFoundError(f"Asset '{asset_id}' not found")


def create_connection(session: Any, source_id: str, payload: ConnectionCreate) -> ConnectionEdge:
    if source_id == payload.target:
        raise ConnectionValidationError("Source and target assets must be different")

    exists = session.run(
        """
        MATCH (source:Asset {id: $source_id})
        MATCH (target:Asset {id: $target_id})
        RETURN source.id AS source, target.id AS target
        """,
        source_id=source_id,
        target_id=payload.target,
    ).single()
    if exists is None:
        raise AssetNotFoundError("Source or target asset not found")

    record = session.run(
        """
        MATCH (source:Asset {id: $source_id})
        MATCH (target:Asset {id: $target_id})
        MERGE (source)-[link:CONNECTS_TO {source: $source_id, target: $target_id}]->(target)
        SET link.source = $source_id,
            link.destination = $target_id,
            link.protocol = $protocol,
            link.port = $port,
            link.allowed = $allowed,
            link.evidence = $evidence
        RETURN source.id AS source, target.id AS target, link
        """,
        source_id=source_id,
        target_id=payload.target,
        protocol=payload.protocol,
        port=payload.port,
        allowed=payload.allowed,
        evidence=payload.evidence,
    ).single()
    if record is None:
        raise RuntimeError("Failed to create connection")

    rel = dict(record["link"])
    connection = _connection_from_rel(record["source"], record["target"], rel)
    edge_id = f"{connection.source}->{connection.target}"
    label = connection.protocol.upper() if connection.protocol else "CONNECTS_TO"
    return ConnectionEdge(id=edge_id, source=connection.source, target=connection.target, data=connection, label=label)


def get_graph(session: Any) -> dict[str, list[dict[str, Any]]]:
    assets = list_assets(session)
    nodes: list[AssetNode] = []
    for index, asset in enumerate(assets):
        col = index % 4
        row = index // 4
        nodes.append(
            AssetNode(
                id=asset.id,
                position={"x": float(col * 280), "y": float(row * 180)},
                data=asset,
            )
        )

    records = session.run(
        """
        MATCH (source:Asset)-[link:CONNECTS_TO]->(target:Asset)
        RETURN source.id AS source, target.id AS target, link
        ORDER BY source.id, target.id
        """
    )
    edges: list[ConnectionEdge] = []
    for record in records:
        source_id = record["source"]
        target_id = record["target"]
        rel = dict(record["link"])
        connection = _connection_from_rel(source_id, target_id, rel)
        edges.append(
            ConnectionEdge(
                id=f"{source_id}->{target_id}",
                source=source_id,
                target=target_id,
                data=connection,
                label=(connection.protocol.upper() if connection.protocol else "CONNECTS_TO"),
            )
        )

    return {
        "nodes": [node.model_dump() for node in nodes],
        "edges": [edge.model_dump() for edge in edges],
    }


def get_graph_stats(session: Any) -> GraphStats:
    record = session.run(
        """
        CALL {
          MATCH (asset:Asset)
          RETURN count(asset) AS asset_count
        }
        CALL {
          MATCH (:Asset)-[link:CONNECTS_TO]->(:Asset)
          RETURN count(link) AS connection_count
        }
        RETURN asset_count, connection_count
        """
    ).single()
    if record is None:
        return GraphStats(asset_count=0, connection_count=0)
    return GraphStats(
        asset_count=int(record["asset_count"] or 0),
        connection_count=int(record["connection_count"] or 0),
    )

