from app.services.attack_path_service import (
    AssetNotFoundError,
    build_snapshot,
    find_paths,
    simulate_propagation,
)


def asset(asset_id, risk=50, exposure="internal", criticality="medium"):
    return {
        "id": asset_id,
        "name": asset_id.upper(),
        "exposure": exposure,
        "criticality": criticality,
        "risk_score": risk,
    }


def edge(source, target, allowed=True):
    return {
        "id": f"{source}->{target}",
        "source": source,
        "target": target,
        "allowed": allowed,
        "protocol": "tcp",
        "port": 443,
        "evidence": "fixture",
    }


def test_single_direct_path():
    assets, adjacency = build_snapshot([asset("a"), asset("b")], [edge("a", "b")])
    result = find_paths(assets, adjacency, "a", "b")
    assert result["path_count"] == 1
    assert result["paths"][0]["assets"] == ["a", "b"]
    assert result["paths"][0]["hop_count"] == 1


def test_multiple_paths_stable_ranking():
    records = [asset("a"), asset("b"), asset("c"), asset("d")]
    assets, adjacency = build_snapshot(records, [edge("a", "b"), edge("b", "d"), edge("a", "c"), edge("c", "d")])
    result = find_paths(assets, adjacency, "a", "d")
    assert result["path_count"] == 2
    assert result["paths"][0]["hop_count"] == 2
    assert result["shortest_path"] == "path-001"


def test_directed_reverse_path_and_blocked_edge():
    assets, adjacency = build_snapshot([asset("a"), asset("b")], [edge("a", "b", True), edge("b", "a", False)])
    assert find_paths(assets, adjacency, "a", "b")["path_count"] == 1
    assert find_paths(assets, adjacency, "b", "a")["path_count"] == 0


def test_missing_allowed_is_blocked():
    assets, adjacency = build_snapshot([asset("a"), asset("b")], [{
        "id": "a->b",
        "source": "a",
        "target": "b",
        "allowed": None,
        "protocol": "tcp",
        "port": 443,
    }])
    assert find_paths(assets, adjacency, "a", "b")["path_count"] == 0


def test_cycle_and_max_depth():
    assets, adjacency = build_snapshot(
        [asset("a"), asset("b"), asset("c")],
        [edge("a", "b"), edge("b", "c"), edge("c", "b"), edge("b", "a")],
    )
    result = find_paths(assets, adjacency, "a", "c", max_depth=2)
    assert result["path_count"] == 1
    assert find_paths(assets, adjacency, "a", "c", max_depth=1)["path_count"] == 0


def test_same_asset_and_missing_asset():
    assets, adjacency = build_snapshot([asset("a")], [])
    same = find_paths(assets, adjacency, "a", "a")
    assert same["paths"][0]["hop_count"] == 0
    try:
        find_paths(assets, adjacency, "missing", "a")
        assert False
    except AssetNotFoundError:
        pass


def test_duplicate_edges_and_disconnected_graph():
    assets, adjacency = build_snapshot(
        [asset("a"), asset("b"), asset("c")],
        [edge("a", "b"), edge("a", "b"), edge("b", "c", False)],
    )
    result = find_paths(assets, adjacency, "a", "c")
    assert result["path_count"] == 0
    assert len(adjacency["a"]) == 1


def test_path_risk_and_missing_risk():
    assets, adjacency = build_snapshot(
        [asset("a", None), asset("b", 100, "public", "critical")],
        [edge("a", "b")],
    )
    result = find_paths(assets, adjacency, "a", "b")
    assert 0 <= result["paths"][0]["path_risk"] <= 100


def test_propagation_linear_branch_cycle():
    assets, adjacency = build_snapshot(
        [asset("a", 20), asset("b", 40), asset("c", 80), asset("d", 60)],
        [edge("a", "b"), edge("a", "c"), edge("b", "d"), edge("d", "b"), edge("c", "d")],
    )
    result = simulate_propagation(assets, adjacency, "a")
    assert result["propagation_order"] == ["a", "b", "c", "d"]
    assert len(set(result["affected_asset_ids"])) == 4
    assert result["aggregate_risk"] == 50.0
    assert result["highest_risk_asset"] == "c"


def test_propagation_blocked_and_missing_start():
    assets, adjacency = build_snapshot([asset("a"), asset("b")], [edge("a", "b", False)])
    result = simulate_propagation(assets, adjacency, "a")
    assert result["affected_asset_ids"] == ["a"]
    try:
        simulate_propagation(assets, adjacency, "missing")
        assert False
    except AssetNotFoundError:
        pass


def test_50_node_performance_shape():
    records = [asset(f"n{i}", i % 101) for i in range(50)]
    edges = [edge(f"n{i}", f"n{i + 1}") for i in range(49)]
    assets, adjacency = build_snapshot(records, edges)
    result = find_paths(assets, adjacency, "n0", "n10", max_depth=12)
    assert result["path_count"] == 1
