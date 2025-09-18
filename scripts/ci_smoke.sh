#!/usr/bin/env bash
set -euo pipefail

# CI-friendly smoke: build images, start core services, run migrations,
# start api+worker, and run the in-network presign→finalize smoke.

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
COMPOSE_FILE="$ROOT_DIR/infra/docker-compose.yml"
NETWORK_NAME="firstdraft_net"

echo "[ci_smoke] Preflight: checking Docker daemon access..."
if ! docker info >/dev/null 2>&1; then
  echo "[ci_smoke] ERROR: Docker is not accessible by the current user." >&2
  echo "[ci_smoke] Ensure Docker is installed, running, and that your user has permission (e.g., user is in the 'docker' group)." >&2
  echo "[ci_smoke] See PRIVILEGE_POLICY.md and get-docker.README.md for operator setup steps." >&2
  exit 2
fi

dc() {
  if docker compose version >/dev/null 2>&1; then
    docker compose -f "$COMPOSE_FILE" "$@"
  else
    echo "[ci_smoke] ERROR: docker compose v2 not found. Please install Docker Compose v2 (\"docker compose\") as v1 has known issues (KeyError: 'ContainerConfig')." >&2
    exit 2
  fi
}

echo "[ci_smoke] Building images..."
dc build

echo "[ci_smoke] Starting core services (postgres/redis/minio/create-bucket)..."
dc up -d postgres redis minio create-bucket

echo "[ci_smoke] Running DB migrations via migrator container..."
dc run --rm migrator

echo "[ci_smoke] Bootstrapping dev fixtures (tenant/users)..."
dc run --rm -e PYTHONPATH=/app api python scripts/bootstrap_dev.py

echo "[ci_smoke] Starting api and worker..."
dc up -d api worker

echo "[ci_smoke] Waiting for API health..."
ATTEMPTS=0
MAX_ATTEMPTS=24 # ~120s @ 5s interval
until docker run --rm --network "$NETWORK_NAME" infra-api:latest curl -fsS http://api:8000/healthz >/dev/null 2>&1; do
  ATTEMPTS=$((ATTEMPTS+1))
  if [ "$ATTEMPTS" -ge "$MAX_ATTEMPTS" ]; then
    echo "[ci_smoke] API did not become healthy in time" >&2
    dc logs --no-color api | tail -n 200 || true
    exit 1
  fi
  sleep 5
done

echo "[ci_smoke] Running in-network smoke..."
NETWORK="$NETWORK_NAME" IMAGE=infra-api:latest "$ROOT_DIR/scripts/smoke_in_network.sh"

echo "[ci_smoke] OK"
