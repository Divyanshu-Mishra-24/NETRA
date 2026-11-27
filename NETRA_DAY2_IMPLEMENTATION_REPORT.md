# NETRA Day 2 Implementation Report

## 1. Implementation Summary

Day 2 adds an integrated vulnerability and risk-scoring module to the existing Cyber/Network Twin. The implementation provides NVD CVE lookup and candidate search, Neo4j vulnerability storage and asset associations, exposure assessment, deterministic four-factor risk scoring, FastAPI endpoints, and Network Twin UI controls. Potential matches remain separate from confirmed/applicable matches.

## 2. Existing Code Reused

- Existing Neo4j Asset, CONNECTS_TO, graph, FastAPI, React graph, asset panel, and inventory importer components.
- Existing Docker network infrastructure: Nginx, FastAPI API, PostgreSQL, Neo4j, and twin-net/proxy configuration.
- Existing frontend navigation, theme, graph interactions, and asset/connection forms.
- Existing test client, health route, graph routes, and Neo4j integration-test structure.
- The Cloud Twin was not modified.

## 3. Files Modified or Created

- `backend/app/models/asset.py`
- `backend/app/models/vulnerability.py`
- `backend/app/routers/vulnerabilities.py`
- `backend/app/services/nvd_service.py`
- `backend/app/services/vulnerability_service.py`
- `backend/app/services/risk_service.py`
- `backend/app/services/graph_service.py`
- `backend/app/main.py`
- `backend/tests/test_vulnerability_engine.py`
- `frontend/src/services/api.ts`
- `frontend/src/components/AssetPanel.tsx`
- `frontend/src/components/InfrastructureGraph.tsx`
- `frontend/src/pages/NetworkTwin.tsx`
- `frontend/src/styles.css`
- `source-infrastructure/network-infra/inventory/assets.json`
- `source-infrastructure/network-infra/twin/import_twin.py`
- `source-infrastructure/network-infra/compose.yaml`
- `NETRA_DAY2_IMPLEMENTATION_REPORT.md`

## 4. Vulnerability Engine

The NVD client calls `https://services.nvd.nist.gov/rest/json/cves/2.0`, supports `keywordSearch`, `cveId`, pagination parameters, optional `apiKey` authentication, in-memory caching, 15-second default timeout, and three bounded retries with exponential backoff. Permanent 403 and 429 responses are not retried. CVSS v4.0, v3.1, v3.0, and v2.0 are parsed with missing-CVSS and rejected-CVE handling.

Neo4j stores global `Vulnerability` nodes keyed by unique `cve_id`. Asset relationships use `HAS_VULNERABILITY` and relationship metadata: `match_type`, `confidence`, `status`, `matched_product`, `matched_version`, `evidence`, and `added_at`.

Candidate keyword search is always presented as potential until a user or later applicability logic marks it confirmed/applicable. Manual attachment and status updates preserve one asset-only association. Removing a relationship does not delete the shared vulnerability node.

## 5. Risk Scoring Methodology

Formula:

`Risk = 0.40 × V + 0.30 × E + 0.15 × C + 0.15 × A`

- Vulnerability: accepted, confirmed, or applicable CVSS associations only. The highest CVSS score is used and the second/third highest add smaller normalization bonuses. Potential, resolved, rejected, and missing-CVSS associations do not create a vulnerability factor.
- Exposure: public 100, internal 60, restricted 20, unknown 30.
- Connectivity: normalized allowed graph degree, `min(100, degree / 5 × 100)`.
- Criticality: low 20, medium 50, high 75, critical 100; unknown 30.
- Bands: 0–39 low, 40–69 medium, 70–100 high.
- Formula version: `netra-risk-v1`.

Overall infrastructure risk is the average asset risk score, using the same bands.

## 6. API Endpoints

- `GET /vulnerabilities/search?keyword=<text>&start_index=0&results_per_page=20`
- `GET /vulnerabilities/{cve_id}`
- `GET /assets/{id}/vulnerabilities`
- `POST /assets/{id}/vulnerabilities`
- `PATCH /assets/{id}/vulnerabilities/{cve_id}`
- `DELETE /assets/{id}/vulnerabilities/{cve_id}`
- `POST /assets/{id}/vulnerabilities/refresh`
- `GET /assets/{id}/exposure`
- `GET /assets/{id}/risk`
- `POST /assets/{id}/risk/recalculate`
- `GET /risk/summary`
- `POST /risk/recalculate-all`

Attach example:

```json
{
  "cve_id": "CVE-2021-44228",
  "evidence": "Manually reviewed candidate",
  "match_type": "potential",
  "status": "potential",
  "matched_product": "log4j",
  "matched_version": "2.14.1"
}
```

## 7. Test Results

| Test | Expected Result | Actual Result | Status |
|---|---|---|---|
| Neo4j connection | Connected | Docker Neo4j container healthy; backend reported connected through `/health` | PASS |
| NVD lookup | CVE details | Live lookup returned `CVE-2021-44228` | PASS |
| Backend unit/API suite | Tests pass without live NVD dependency | 15 passed, 1 Neo4j integration test skipped | PASS |
| Manual CVE association | Saved | Implemented Neo4j relationship logic; no destructive live association test performed | NOT EXECUTED |
| Risk calculation | 0–100 score | Formula tests passed; live risk summary returned valid unknown/zero state | PASS |
| Graph risk coloring | Updated | Implemented from backend `risk_level` and `risk_score`; browser visual verification not available | NOT EXECUTED |
| Frontend build | Successful | `tsc --noEmit && vite build` completed successfully | PASS |
| Docker stack | Existing infrastructure operational | Docker services remained operational; updated backend container rebuilt and healthy | PASS |

## 8. Startup Commands

### Windows PowerShell

```powershell
docker compose -f D:\Netra\source-infrastructure\network-infra\compose.yaml up -d --build
docker compose -f D:\Netra\source-infrastructure\network-infra\compose.yaml --profile tools run --rm twin-importer
cd D:\Netra\frontend
npm install
npm run dev
```

### WSL/Linux

```bash
cd /mnt/d/Netra/source-infrastructure/network-infra
docker compose up -d --build
docker compose --profile tools run --rm twin-importer
cd /mnt/d/Netra/frontend
npm install
npm run dev
```

### Backend and tests

```bash
cd backend
python -m pytest -q
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Frontend build

```bash
cd frontend
npm run build
```

### NVD verification

```bash
cd backend
python -c "from app.services.nvd_service import nvd_client; print(nvd_client.get_cve('CVE-2021-44228')['cve_id'])"
```

### Risk verification

```bash
curl -s http://127.0.0.1:8080/netra/api/risk/summary
curl -s http://127.0.0.1:8080/netra/api/assets/web-01/risk
```

## 9. Known Limitations

- Exact package versions are not inferred from ambiguous image tags or container names.
- Docker host-bind/public-internet reachability is not proven by published ports alone.
- NVD CPE applicability is modeled conservatively; keyword candidates are potential until manually or semantically confirmed.
- The in-memory NVD cache is process-local.
- Relationship status and match type remain the source of truth for risk eligibility.
- Graph risk color behavior was not automated in a browser test.

## 10. Day 3 Readiness

The Asset nodes now retain `risk_score`, `risk_level`, and `risk_calculated_at`, while CVE associations are available through Neo4j relationships and explainable risk-factor output. These structures can be consumed by a future attack-path engine without changing the Cloud Twin or deleting existing graph data.
