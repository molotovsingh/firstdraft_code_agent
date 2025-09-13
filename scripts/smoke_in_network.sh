#!/usr/bin/env bash
set -euo pipefail

# Runs the presign->finalize smoke inside the Docker network so 'minio' host resolves.
# Prereqs: `docker-compose -f infra/docker-compose.yml up -d postgres redis minio create-bucket`

NETWORK=${NETWORK:-firstdraft_net}
IMAGE=${IMAGE:-infra_api:latest}

echo "Running smoke inside network: $NETWORK using image: $IMAGE"
docker run --rm --network "$NETWORK" \
  --env API_BASE='http://api:8000' \
  --env TENANT_ID='11111111-1111-1111-1111-111111111111' \
  --env USER_ID='1' \
  "$IMAGE" python scripts/smoke_finalize.py

