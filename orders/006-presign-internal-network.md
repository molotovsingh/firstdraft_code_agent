# Order 006 — Make CI smoke presign work in-network

Owner: Claude
Scope: Ensure the presign → upload → finalize smoke works when executed inside the Docker network (where `localhost:9000` is invalid and `minio:9000` must be used).

Problem
- The API presigns using `S3_PUBLIC_ENDPOINT_URL` (default `http://localhost:9000`).
- In-network smoke runs a throwaway container on the Docker network; `localhost:9000` points to itself, not MinIO, so the PUT fails.

Solution (minimal, safe)
- API: `/v0/uploads/presign` should accept an opt-in “internal network” hint via header `X-Internal-Network: 1`.
  - When present, return a presigned PUT URL using the internal MinIO endpoint (i.e., via the MinIO client’s `presigned_put_object`, which yields `http://minio:9000/...`).
  - Otherwise, keep current behavior (offline presign using `S3_PUBLIC_ENDPOINT_URL` if set).
- Storage helper: add `presign_put_url_internal(key, expiry)` that calls the client presign directly (no offline signing), mirroring `presign_put_url` signature.
- Smoke tooling:
  - `scripts/smoke_finalize.py`: if env `PRESIGN_INTERNAL=1`, include header `X-Internal-Network: 1` in the presign request.
  - `scripts/smoke_in_network.sh`: set `PRESIGN_INTERNAL=1` for the container running the smoke.

Acceptance Criteria
- In-network smoke (`scripts/ci_smoke.sh`) completes successfully on a fresh stack.
- When `PRESIGN_INTERNAL=1`, the presign response URL host is `minio:9000`.
- When not set, behavior remains unchanged (host/dev flow still returns `localhost:9000` by default).

Validation
- Build + run: `./scripts/ci_smoke.sh` → succeeds.
- Manual: `docker run --rm --network firstdraft_net -e API_BASE=http://api:8000 -e PRESIGN_INTERNAL=1 infra_api:latest python scripts/smoke_finalize.py` → succeeds.

Out of Scope
- Changing defaults in `.env` or compose.
- Adding complex autodetection beyond the explicit header.
