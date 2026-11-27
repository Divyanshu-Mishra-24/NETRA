"""Deterministic attack reachability and compromise propagation analysis."""

from __future__ import annotations

import os
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Iterable


class AssetNotFoundError(Exception):
    pass


def _limit(value: int, default: int, minimum: int, maximum: int) -> int:
    if value is None:
        return default
    return min(max(int(value), minimum), maximum)


def criticality_score(value: str | None) -> float:
    return {
        "low": 20.0,
        "medium": 50.0,
        "high": 75.0,
        "critical": 100.0,
    }.get(str(value or "").lower(), 30.0)


def exposure_score(value: str | None) -> float:
    normalized = str(value or "").lower()
    if normalized in {"public", "external", "internet-facing"}:
        return 100.0
    if normalized in {"internal", "internally accessible"}:
        return 60.0
    if normalized in {"private", "restricted", "isolated"}:
        return 20.0
    return 30.0


def normalize_asset(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(record["id"]),
        "name": str(record.get("name") or record["id"]),
        "type": str(record.get("type") or "unknown"),
        "exposure": record.get("exposure"),
        "criticality": record.get("criticality"),
        "risk_score": float(record["risk_score"]) if record.get("risk_score") is not None else None,
    }


def normalize_edge(record: dict[str, Any]) -> dict[str, Any]:
    source = str(record["source"])
    target = str(record["target"])
    allowed = record.get("allowed")
    edge_id = str(record.get("id") or f"{source}->{target}")
    missing_allowed = allowed is None
    return {
        "id": edge_id,
        "source": source,
        "target": target,
        "allowed": False if missing_allowed else bool(allowed),
        "missing_allowed": missing_allowed,
        "protocol": record.get("protocol"),
        "port": record.get("port"),
        "evidence": record.get("evidence"),
    }


def build_snapshot(
    assets: Iterable[dict[str, Any]],
    edges: Iterable[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    asset_map: dict[str, dict[str, Any]] = {}
    adjacency: dict[str, list[dict[str, Any]]] = {}
    for record in assets:
        asset = normalize_asset(record)
        asset_map[asset["id"]] = asset
        adjacency.setdefault(asset["id"], [])

    seen: set[tuple[str, str, str, str]] = set()
    for record in edges:
        edge = normalize_edge(record)
        if edge["source"] not in asset_map or edge["target"] not in asset_map:
            continue
        key = (
            edge["source"],
            edge["target"],
            str(edge.get("protocol") or ""),
            str(edge.get("port") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        if edge["allowed"]:
            adjacency.setdefault(edge["source"], []).append(edge)
    for source in adjacency:
        adjacency[source].sort(key=lambda item: (item["target"], item["id"]))
    return asset_map, adjacency


def path_risk(asset_ids: list[str], asset_map: dict[str, dict[str, Any]]) -> float:
    assets = [asset_map[item] for item in asset_ids]
    known_risk = [item["risk_score"] for item in assets if item["risk_score"] is not None]
    mean_risk = sum(known_risk) / len(known_risk) if known_risk else 0.0
    avg_criticality = sum(criticality_score(item["criticality"]) for item in assets) / len(assets)
    entry_exposure = exposure_score(assets[0]["exposure"])
    hop_penalty = max(0.0, 100.0 - (len(asset_ids) - 1) * 4.0)
    score = (
        0.65 * mean_risk
        + 0.20 * avg_criticality
        + 0.10 * entry_exposure
        + 0.05 * hop_penalty
    )
    return round(min(100.0, max(0.0, score)), 2)


def find_paths(
    asset_map: dict[str, dict[str, Any]],
    adjacency: dict[str, list[dict[str, Any]]],
    entry: str,
    target: str,
    max_depth: int = 6,
    max_paths: int = 20,
) -> dict[str, Any]:
    if entry not in asset_map:
        raise AssetNotFoundError(f"Asset '{entry}' not found")
    if target not in asset_map:
        raise AssetNotFoundError(f"Asset '{target}' not found")

    max_depth = _limit(max_depth, 6, 1, 12)
    max_paths = _limit(max_paths, 20, 1, 100)

    if entry == target:
        risk = path_risk([entry], asset_map)
        return {
            "entry_asset": entry,
            "target_asset": target,
            "path_count": 1,
            "paths": [{
                "path_id": "path-001",
                "assets": [entry],
                "asset_names": [asset_map[entry]["name"]],
                "edge_ids": [],
                "edges": [],
                "hop_count": 0,
                "path_risk": risk,
                "ranking_method": "heuristic",
                "explanation": "The entry and target assets are the same; no traversal is required.",
                "traversal_assumptions": ["Missing allowed values are treated as blocked."],
            }],
            "truncated": False,
            "shortest_path": "path-001",
        }

    queue: deque[tuple[str, list[str], list[dict[str, Any]], set[str]]] = deque()
    queue.append((entry, [entry], [], {entry}))
    paths: list[dict[str, Any]] = []
    truncated = False

    while queue:
        node, node_path, edge_path, visited = queue.popleft()
        if len(node_path) - 1 >= max_depth:
            continue
        for edge in adjacency.get(node, []):
            target_id = edge["target"]
            if target_id in visited:
                continue
            next_nodes = node_path + [target_id]
            next_edges = edge_path + [edge]
            if target_id == target:
                risk = path_risk(next_nodes, asset_map)
                paths.append({
                    "nodes": next_nodes,
                    "edges": next_edges,
                    "risk": risk,
                })
                if len(paths) >= max_paths:
                    truncated = True
                    queue.clear()
                    break
            elif len(next_nodes) - 1 < max_depth:
                queue.append((target_id, next_nodes, next_edges, visited | {target_id}))

    def ranking_key(path: dict[str, Any]) -> tuple:
        nodes = path["nodes"]
        return (
            -path["risk"],
            len(nodes) - 1,
            tuple(nodes),
            tuple(edge["id"] for edge in path["edges"]),
        )

    paths.sort(key=ranking_key)
    result_paths: list[dict[str, Any]] = []
    for index, path in enumerate(paths, start=1):
        nodes = path["nodes"]
        edges = path["edges"]
        used_missing_allowed = any(edge["missing_allowed"] for edge in edges)
        assumptions = ["Missing allowed values are treated as blocked."]
        result_paths.append({
            "path_id": f"path-{index:03d}",
            "assets": nodes,
            "asset_names": [asset_map[item]["name"] for item in nodes],
            "edge_ids": [edge["id"] for edge in edges],
            "edges": [
                {
                    "id": edge["id"],
                    "source": edge["source"],
                    "target": edge["target"],
                    "protocol": edge["protocol"],
                    "port": edge["port"],
                    "allowed": True,
                    "evidence": edge["evidence"],
                }
                for edge in edges
            ],
            "hop_count": len(nodes) - 1,
            "path_risk": path["risk"],
            "ranking_method": "heuristic",
            "explanation": (
                f"The path follows {len(nodes) - 1} permitted directed connection(s). "
                "Reachability does not confirm exploitation."
            ),
            "traversal_assumptions": assumptions,
        })

    shortest = min(result_paths, key=lambda item: (item["hop_count"], item["assets"]))["path_id"] if result_paths else None
    return {
        "entry_asset": entry,
        "target_asset": target,
        "path_count": len(result_paths),
        "paths": result_paths,
        "truncated": truncated,
        "shortest_path": shortest,
    }


def simulate_propagation(
    asset_map: dict[str, dict[str, Any]],
    adjacency: dict[str, list[dict[str, Any]]],
    starting_asset: str,
    max_depth: int = 12,
) -> dict[str, Any]:
    if starting_asset not in asset_map:
        raise AssetNotFoundError(f"Asset '{starting_asset}' not found")
    max_depth = _limit(max_depth, 12, 1, 20)

    queue: deque[tuple[str, int]] = deque([(starting_asset, 0)])
    visited = {starting_asset}
    predecessor: dict[str, str] = {}
    propagation_order = [starting_asset]
    traversed: list[dict[str, Any]] = []
    depths: dict[str, int] = {starting_asset: 0}

    while queue:
        current, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for edge in adjacency.get(current, []):
            target = edge["target"]
            if target in visited:
                continue
            visited.add(target)
            predecessor[target] = current
            depths[target] = depth + 1
            propagation_order.append(target)
            traversed.append({
                "source": current,
                "target": target,
                "edge_id": edge["id"],
                "protocol": edge["protocol"],
                "port": edge["port"],
                "depth": depth + 1,
                "predecessor": current,
            })
            queue.append((target, depth + 1))

    affected = [asset_map[item] for item in propagation_order]
    known_risk = [item["risk_score"] for item in affected if item["risk_score"] is not None]
    mean_risk = round(sum(known_risk) / len(known_risk), 2) if known_risk else 0.0
    criticality_impact = sum(criticality_score(item["criticality"]) for item in affected)
    impact_indicator = round(min(100.0, criticality_impact / max(1, len(asset_map)) * 100.0), 2)
    highest = max(
        affected,
        key=lambda item: (
            item["risk_score"] if item["risk_score"] is not None else -1.0,
            item["id"],
        ),
    )
    return {
        "scenario_id": f"scenario-{uuid.uuid5(uuid.NAMESPACE_URL, starting_asset + str(depths)).hex[:12]}",
        "starting_asset": starting_asset,
        "affected_asset_ids": propagation_order,
        "affected_asset_names": [asset_map[item]["name"] for item in propagation_order],
        "propagation_order": propagation_order,
        "propagation_depth": max(depths.values(), default=0),
        "traversed_connections": traversed,
        "total_affected_assets": len(propagation_order),
        "aggregate_risk": mean_risk,
        "impact_indicator": impact_indicator,
        "highest_risk_asset": highest["id"],
        "highest_risk_asset_name": highest["name"],
        "assumptions": [
            "This is a reachability-based hypothetical simulation, not a confirmed exploit.",
            "Only allowed directed CONNECTS_TO edges are eligible.",
            "Missing allowed values are treated as blocked.",
            "No real network action or exploitation is performed.",
        ],
        "explanation": "Breadth-first traversal follows permitted directed connections and avoids repeated or cyclic processing.",
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }


def load_graph_snapshot(session: Any) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    assets = session.run(
        """
        MATCH (a:Asset)
        RETURN a.id AS id, a.name AS name, a.type AS type,
               a.exposure AS exposure, a.criticality AS criticality,
               a.risk_score AS risk_score
        ORDER BY a.id
        """
    )
    edges = session.run(
        """
        MATCH (source:Asset)-[r:CONNECTS_TO]->(target:Asset)
        RETURN source.id AS source, target.id AS target, r.allowed AS allowed,
               r.protocol AS protocol, r.port AS port, r.evidence AS evidence,
               source.id + '->' + target.id AS id
        ORDER BY source.id, target.id, r.protocol, r.port
        """
    )
    asset_records = [dict(record) for record in assets]
    edge_records = [dict(record) for record in edges]
    return build_snapshot(asset_records, edge_records)


def reachable_assets(
    asset_map: dict[str, dict[str, Any]],
    adjacency: dict[str, list[dict[str, Any]]],
    starting_asset: str,
    max_depth: int = 12,
) -> dict[str, Any]:
    simulation = simulate_propagation(asset_map, adjacency, starting_asset, max_depth)
    return {
        "starting_asset": starting_asset,
        "reachable_asset_ids": simulation["affected_asset_ids"],
        "reachable_asset_names": simulation["affected_asset_names"],
        "traversed_connections": simulation["traversed_connections"],
        "maximum_depth": simulation["propagation_depth"],
        "aggregate_risk": simulation["aggregate_risk"],
        "assumptions": simulation["assumptions"],
    }


def graph_attack_summary(
    asset_map: dict[str, dict[str, Any]],
    adjacency: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    known = [item["risk_score"] for item in asset_map.values() if item["risk_score"] is not None]
    mean = round(sum(known) / len(known), 2) if known else 0.0
    blocked_edges = 0
    eligible_edges = 0
    for edges in adjacency.values():
        eligible_edges += len(edges)
    all_asset_count = len(asset_map)
    highest = max(
        asset_map.values(),
        key=lambda item: (item["risk_score"] if item["risk_score"] is not None else -1.0, item["id"]),
        default=None,
    )
    return {
        "asset_count": all_asset_count,
        "eligible_directed_connections": eligible_edges,
        "blocked_or_unknown_connections": blocked_edges,
        "mean_asset_risk": mean,
        "highest_risk_asset": highest["id"] if highest else None,
        "methodology": "Graph security summary of current assets and allowed directed reachability.",
    }
