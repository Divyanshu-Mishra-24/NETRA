# NETRA Day 3 Implementation Report

## A. Implementation Summary

Day 3 adds deterministic attack-path discovery and compromise propagation to the Cyber/Network Twin:

- Directed, bounded entry-to-target path discovery.
- Shortest eligible path lookup.
- Multiple path ranking using a documented heuristic.
- Breadth-first hypothetical compromise propagation.
- Cycle prevention and duplicate-edge handling.
- Neo4j-backed FastAPI endpoints.
- Network Twin UI controls for path selection, graph highlighting, propagation, and reset.
- Read-only simulation behavior that does not modify Neo4j relationships or Docker networks.

## B. Existing Functionality Preserved

- Day 1 Neo4j Asset and CONNECTS_TO graph.
- Day 1 asset and connection CRUD.
- Day 2 NVD lookup and CVE associations.
- Day 2 exposure and asset-risk calculation.
- Existing risk graph coloring.
- Existing frontend theme, navigation, asset panel, and graph interactions.
- Cloud Twin remains unchanged.

## C. Files Modified

- `backend/app/services/attack_path_service.py`
- `backend/app/routers/graph.py`
- `backend/app/routers/simulations.py`
- `frontend/src/services/api.ts`
- `frontend/src/components/InfrastructureGraph.tsx`
- `frontend/src/pages/NetworkTwin.tsx`
- `frontend/src/styles.css`
- `backend/tests/test_attack_path_engine.py`
- `NETRA_DAY3_IMPLEMENTATION_REPORT.md`

## D. Attack Graph Methodology

Paths follow directed `(:Asset)-[:CONNECTS_TO]->(:Asset)` relationships.

- `allowed=true` permits traversal.
- `allowed=false` blocks traversal.
- Missing `allowed` is conservatively treated as blocked and is disclosed in API assumptions.
- Simple paths do not revisit an asset.
- Default path depth is 6; API depth range is 1–12.
- Default path count is 20; API count range is 1–100.

The path heuristic is:

`0.65 × mean known asset risk + 0.20 × mean criticality factor + 0.10 × entry exposure factor + 0.05 × hop length factor`

The hop factor is `max(0, 100 - 4 × hops)`. This is deterministic heuristic prioritization, not ML or exploitation probability.

## E. Compromise Propagation Methodology

Propagation uses breadth-first traversal from the selected asset:

1. Add the starting asset to the visited set.
2. Follow allowed directed outgoing edges.
3. Record predecessor and depth.
4. Prevent repeated and cyclic processing.
5. Calculate mean known affected-asset risk.
6. Calculate impact as normalized total criticality.

Simulation is reachability-based and is explicitly labeled hypothetical. It does not require or claim a real exploit.

## F. API Documentation

- `GET /graph/paths?from=internet&to=db-01&max_depth=6&max_paths=20`
- `GET /graph/shortest-path?from=internet&to=db-01&max_depth=6`
- `POST /simulate`
- `GET /graph/reachable/{asset_id}?max_depth=12`
- `GET /graph/attack-summary`

Propagation example:

```json
{
  "starting_asset": "internet",
  "max_depth": 12
}
```

Live returned 4 affected assets in order:
`internet`, `web-01`, `api-01`, `db-01`, with aggregate risk `36.19`.

Live internet-to-database path discovery returned the directed inventory path and an additional existing graph path if present. Reverse `db-01` to `internet` returned an empty path list.

## G. Test Results

| Test category | Total | Passed | Failed | Blocked |
|---|---:|---:|---:|---:|
| Graph algorithms | 11 | 11 | 0 | 0 |
| Propagation | 4 | 4 | 0 | 0 |
| FastAPI unit tests | 29 suite tests | 29 | 0 | 0 |
| Neo4j integration | 5 live checks | 5 | 0 | 0 |
| Frontend | 1 production build | 1 | 0 | 0 |
| End-to-end browser | 0 | 0 | 0 | 1 |
| Performance | 2 | 2 | 0 | 0 |

## H. Evidence

Commands executed:

```powershell
cd D:\Netra\backend
python -m pytest -q
```

Result: `29 passed, 1 warning`.

```powershell
cd D:\Netra\frontend
npm run build
```

Result: TypeScript and Vite production build succeeded.

```powershell
docker compose -f D:\Netra\source-infrastructure\network-infra\compose.yaml up -d --build backend
curl.exe -sS http://127.0.0.1:8080/netra/api/health
curl.exe -sS "http://127.0.0.1:8080/netra/api/graph/paths?from=internet&to=db-01&max_depth=6&max_paths=20"
curl.exe -sS "http://127.0.0.1:8080/netra/api/graph/paths?from=db-01&to=internet&max_depth=6&max_paths=20"
curl.exe -sS "http://127.0.0.1:8080/netra/api/graph/reachable/internet?max_depth=12"
```

Live backend health: `healthy`, Neo4j `connected`.

Live reverse path: `path_count=0`.

Live propagation: 4 affected assets, depth 2, aggregate risk `36.19`, highest-risk asset `web-01`.

Live path API response time: approximately `71 ms`.

Graph preservation: Docker Compose was used without `--volumes`; no graph reset or network-rule mutation was performed during the engine implementation.

## I. Known Limitations

- Browser automation was not executed; manual UI verification remains.
- The live graph may contain assets or relationships from earlier work; the engine uses only actual Neo4j data and does not fabricate missing nodes.
- Missing `allowed` values are blocked conservatively, because no explicit security meaning is available.
- Vulnerability-aware eligibility is not mixed into propagation; this implementation is reachability-based.
- Multi-path enumeration is bounded to 100 paths and depth 12.

## J. Day 4 Readiness

The engine is read-only and separates graph loading, pathfinding, and propagation. A future mitigation layer can pass a read-only graph snapshot with blocked edges or patched assets without rewriting Neo4j or Docker networking.
