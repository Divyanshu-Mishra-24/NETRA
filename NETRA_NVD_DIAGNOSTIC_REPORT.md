# NETRA NVD Integration Diagnostic Report

## 1. Root Cause

Confirmed root cause: the NETRA backend Docker container could not reach `services.nvd.nist.gov`.

The original backend container on `twin_net` was on a Docker network configured as `internal: true`. This prevented outbound HTTPS and DNS/NVD connectivity. Reproduced symptoms:

- Backend keyword/direct lookup returned HTTP 503 `NVD is temporarily unavailable`.
- Container DNS lookup for `services.nvd.nist.gov` failed with `Temporary failure in name resolution`.
- Direct host-machine requests to NVD returned HTTP 200.

The frontend and NVD URL/query mapping were not the root cause. The fixed request path is now React -> FastAPI `/vulnerabilities/search` -> NVD HTTP client -> official NVD endpoint.

## 2. Findings

| Component | Problem Found | Fix Applied | Verification |
|---|---|---|---|
| NVD connectivity | Backend Docker network blocked outbound HTTPS/DNS | Changed `twin_net` from `internal: true` to external-capable network; kept app/data networks internal | Container DNS resolved, direct container HTTP lookup returned 200 |
| API configuration | NVD variables were not consistently included in compose/runtime configuration | Added NVD environment variables to compose/root/backend configuration | Container received base URL and timeout configuration; missing API key remains supported |
| HTTP client | Internal DNS failure was hidden as generic 503 | Added status handling for 400, 403, 404, 429, 5xx, timeout, invalid JSON and unexpected schema | Live direct and keyword searches returned 200; unit mocked status tests passed |
| Response parsing | Potentially assumed all CVE metrics contain CVSS | Existing parser retains CVSS v4/v3.1/v3.0/v2 handling and gracefully handles missing metrics/rejected text | Live CVE parsed with CVSS 3.1 score 10.0; v2 keyword records parsed |
| FastAPI router | Search and direct routes existed, but failure responses were too generic | Added meaningful 400/404/429/502/503 classifications | Direct and keyword endpoints returned real 200 JSON |
| Frontend search | No design issue found; request chain used the correct backend URL and parameter | Preserved existing UI and existing search flow | Frontend production build passed |
| Neo4j integration | No permanent association was present, and relationship warnings were visible only when empty | Temporary association test verified relationship persistence and cleanup | Association returned successfully; temporary asset returned 404 after cleanup |
| Risk recalculation | Risk remains based only on accepted/confirmed non-rejected associations | No change to this conservative rule | Temporary potential association did not alter confirmed risk rule |

## 3. Files Modified

- `backend/app/services/nvd_service.py` - improved HTTP status, JSON, timeout and retry handling.
- `backend/app/routers/vulnerabilities.py` - corrected NVD error mapping.
- `source-infrastructure/network-infra/compose.yaml` - made `twin_net` capable of outbound NVD access and passed NVD configuration.
- `.env` - added NVD configuration placeholders.
- `backend/.env.example` - added NVD configuration placeholders.
- `backend/tests/test_vulnerability_engine.py` - added mocked empty-result and 403/429 tests.

No Cloud Twin files were modified. Neo4j and Docker volumes were not deleted.

## 4. Commands Executed

```powershell
curl.exe -sS -i "http://127.0.0.1:8080/netra/api/vulnerabilities/search?keyword=nginx&results_per_page=20"
```

Before the fix: exit code 0, HTTP 503 `NVD is temporarily unavailable`.

```powershell
docker exec netra-backend python -c "...httpx lookup..."
```

Before the fix: `Temporary failure in name resolution`.

```powershell
docker compose down
docker compose up -d --build
```

Exit code 0. Services restarted while Docker volumes remained present.

```powershell
curl.exe -sS -i "http://127.0.0.1:8080/netra/api/vulnerabilities/CVE-2021-44228"
```

Exit code 0, HTTP 200. Returned CVSS 3.1 10.0 and the official CVE description.

```powershell
curl.exe -sS -i "http://127.0.0.1:8080/netra/api/vulnerabilities/search?keyword=nginx&results_per_page=5"
```

Exit code 0, HTTP 200. Returned 491 total candidate matches and 5 parsed items.

```powershell
python -m pytest -q
```

Exit code 0: `18 passed, 1 warning`.

```powershell
npm run build
```

Exit code 0: TypeScript and Vite production build succeeded.

## 5. Test Results

| Test | Result |
|---|---|
| Direct NVD lookup | PASS |
| NVD keyword search | PASS |
| Container DNS/NVD HTTPS connectivity | PASS |
| Missing API key support | PASS (live requests succeeded without a key) |
| 403 mocked response | PASS |
| 429 mocked response | PASS |
| Empty NVD result | PASS |
| CVSS v3.1 parsing | PASS |
| CVSS v2 parsing through live keyword search | PASS |
| Rejected/missing CVSS handling | PASS |
| Temporary Neo4j association | PASS |
| Association cleanup | PASS |
| Frontend build | PASS |
| Browser visual test | NOT EXECUTED |

## 6. Remaining Issues

- Live NVD rate limits may still return HTTP 429. The backend reports this distinctly and does not retry 429.
- An NVD API key is optional for current no-key test operation but higher-volume use is recommended.
- Browser-level NVD UI verification was not performed automatically.
- Keyword matches remain candidate/potential matches; applicability is not inferred automatically.
- The NVD cache is process-local and resets on backend restart.

## 7. Startup and Verification Commands

### PowerShell

```powershell
cd D:\Netra\source-infrastructure\network-infra
docker compose up -d --build

curl.exe -sS http://127.0.0.1:8080/netra/api/health
curl.exe -sS "http://127.0.0.1:8080/netra/api/vulnerabilities/search?keyword=nginx&results_per_page=5"
curl.exe -sS "http://127.0.0.1:8080/netra/api/vulnerabilities/CVE-2021-44228"

cd D:\Netra\frontend
npm run dev
```

### Bash/WSL

```bash
cd /mnt/d/Netra/source-infrastructure/network-infra
docker compose up -d --build

curl -sS http://127.0.0.1:8080/netra/api/health
curl -sS 'http://127.0.0.1:8080/netra/api/vulnerabilities/search?keyword=nginx&results_per_page=5'
curl -sS 'http://127.0.0.1:8080/netra/api/vulnerabilities/CVE-2021-44228'
```

### Automated tests

```powershell
cd D:\Netra\backend
python -m pytest -q

cd D:\Netra\frontend
npm run build
```
