
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$ROOT_DIR/source-infrastructure/network-infra"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

PYTHON_CMD=""
if command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v py >/dev/null 2>&1; then
  PYTHON_CMD="py -3"
fi

NPM_CMD=""
if command -v npm >/dev/null 2>&1; then
  NPM_CMD="npm"
elif command -v npm.cmd >/dev/null 2>&1; then
  NPM_CMD="npm.cmd"
fi

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd docker
require_cmd curl
if [[ -z "$PYTHON_CMD" ]]; then
  echo "Python 3 is required to run the NETRA backend (python/python3/py)." >&2
  exit 1
fi
if [[ -z "$NPM_CMD" ]]; then
  echo "npm is required to run the NETRA frontend." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Start Docker Desktop/daemon and try again." >&2
  exit 1
fi

echo "[1/5] Starting network infrastructure (Docker)..."
(
  cd "$INFRA_DIR"
  docker compose up -d --build
)

echo "[2/5] Importing infrastructure inventory into Neo4j..."
(
  cd "$INFRA_DIR"
  docker compose --profile tools run --rm twin-importer
)

echo "[3/5] Verifying NETRA backend..."
for _ in {1..30}; do
  if curl --silent --fail http://127.0.0.1:8080/netra/api/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if curl --silent --fail http://127.0.0.1:8080/netra/api/health >/dev/null 2>&1; then
  echo "[4/5] NETRA backend is healthy through the infrastructure proxy."
else
  echo "[4/5] NETRA backend is unavailable. Check Docker logs with: docker logs netra-backend" >&2
fi

if ! curl --silent --fail http://127.0.0.1:5173 >/dev/null 2>&1; then
  echo "[5/5] Starting NETRA frontend on http://127.0.0.1:5173 ..."
  (
    cd "$FRONTEND_DIR"
    if [[ ! -d node_modules ]]; then
      $NPM_CMD install
    fi
    nohup $NPM_CMD run dev -- --host 127.0.0.1 --port 5173 --strictPort > "$ROOT_DIR/.netra-frontend.log" 2>&1 &
  )
  for _ in {1..40}; do
    if curl --silent --fail http://127.0.0.1:5173 >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
else
  echo "[5/5] NETRA frontend already running."
fi

echo
echo "NETRA services:"
echo "  Frontend:            http://localhost:5173"
echo "  Network Twin UI:     http://localhost:5173/#network-twin"
echo "  Backend API:         http://localhost:8080/netra/api"
echo "  Backend health:      http://localhost:8080/netra/api/health"
echo "  Swagger docs:        http://localhost:8000/docs"
echo "  Neo4j Browser proxy: http://localhost:8080"
echo "  Source demo app:     http://localhost:8080/source/"
echo
echo "Logs:"
echo "  Backend:  $ROOT_DIR/.netra-backend.log"
echo "  Frontend: $ROOT_DIR/.netra-frontend.log"
echo
if ! curl --silent --fail http://127.0.0.1:8080/netra/api/health >/dev/null 2>&1; then
  echo "Warning: backend health check did not pass. Check docker logs netra-backend." >&2
fi
if ! curl --silent --fail http://127.0.0.1:5173 >/dev/null 2>&1; then
  echo "Warning: frontend did not become ready. Check .netra-frontend.log." >&2
fi
