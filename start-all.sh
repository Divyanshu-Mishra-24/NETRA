#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$ROOT_DIR/source-infrastructure/network-infra"
FRONTEND_DIR="$ROOT_DIR/frontend"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed or is not on PATH. Start Docker Desktop, then run this script again."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker Desktop is not running. Start it, wait until it is ready, then run this script again."
  exit 1
fi

if command -v npm >/dev/null 2>&1; then
  NPM_COMMAND=(npm)
elif command -v npm.cmd >/dev/null 2>&1; then
  NPM_COMMAND=(npm.cmd)
else
  echo "npm is not installed or is not on PATH."
  exit 1
fi

echo "Starting Network Twin infrastructure..."
(
  cd "$INFRA_DIR"
  docker compose up -d --build
  docker compose --profile tools run --rm twin-importer
)

if ! curl --silent --fail http://127.0.0.1:5173 >/dev/null 2>&1; then
  echo "Starting NETRA dashboard..."
  (
    cd "$FRONTEND_DIR"
    if [[ ! -d node_modules ]]; then
      "${NPM_COMMAND[@]}" install
    fi
    nohup "${NPM_COMMAND[@]}" run dev -- --host 127.0.0.1 --port 5173 --strictPort \
      > "$FRONTEND_DIR/.netra-frontend.log" 2>&1 &
  )

  for _ in {1..20}; do
    if curl --silent --fail http://127.0.0.1:5173 >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

if ! curl --silent --fail http://127.0.0.1:5173 >/dev/null 2>&1; then
  echo "The dashboard did not start. Check frontend/.netra-frontend.log."
  exit 1
fi

echo
echo "NETRA dashboard:       http://localhost:5173"
echo "Network Twin:          http://localhost:5173/#network-twin"
echo "Neo4j Browser gateway: http://localhost:8080"
echo "Source demo:           http://localhost:8080/source/"
