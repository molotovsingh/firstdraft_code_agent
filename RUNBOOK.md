# Runbook — Block 0a Dev

## Services
- `api` (FastAPI): HTTP endpoints for upload/status/report
- `worker` (Celery): Background processing for normalization/OCR
- `postgres`: Metadata store
- `redis`: Broker/result backend
- `minio`: S3-compatible object store
- `migrator`: One-shot service that runs `alembic upgrade head` on startup

## Common Commands
```bash
# Start stack
# Prefer Docker Compose v2 (`docker compose`). If you only have v1, `docker-compose` works but consider upgrading.
docker compose -f infra/docker-compose.yml up --build -d

# Logs
docker compose -f infra/docker-compose.yml logs -f api

docker compose -f infra/docker-compose.yml logs -f worker

# Migrations
# A one‑shot `migrator` service runs `alembic upgrade head` automatically.
# For ad-hoc needs, you can still run this manually:
docker compose -f infra/docker-compose.yml exec api alembic upgrade head

# Bootstrap dev tenant and users
docker compose -f infra/docker-compose.yml exec api python scripts/bootstrap_dev.py

# Quick smoke checks
docker compose -f infra/docker-compose.yml exec api python scripts/smoke_health.py
docker compose -f infra/docker-compose.yml exec api python scripts/smoke_presign.py
docker compose -f infra/docker-compose.yml exec api python scripts/smoke_finalize.py
# Open shell in api container
docker compose -f infra/docker-compose.yml exec api bash
```

### Using uv locally
- uv venv .venv
- uv pip install -r requirements.txt
- uv run pytest -q

## First-Time Setup (Dev)
- Copy env: `cp .env.example .env` and review values.
- Start core stack: `docker compose -f infra/docker-compose.yml up --build -d`.
- Verify health: `docker compose -f infra/docker-compose.yml logs -f api` until `/healthz` is ok.
- Run smokes: use the three `scripts/smoke_*.py` commands above via `exec api ...`.
- Optional: one-shot CI/dev flow: run `scripts/ci_smoke.sh` from the repo root.

## Data Locations
- Objects: `s3://firstdraft-dev/{tenant}/{sha256[:2]}/{sha256}/v{n}/...`
- Database: Postgres `firstdraft_system` (dev), see `DATABASE_URL`
- Persistence: Docker named volumes `pgdata` (Postgres) and `minio_data` (MinIO) retain data across restarts.

## Feature Flags
- `OCR_PROVIDER=stub|tesseract|ocrmypdf` (tesseract by default; comment out for code default)
- `QUALITY_MODE=recommended|budget` (default in `.env`)
- `OCR_LANG=eng|eng+hin` (default `eng+hin`)
- `METRICS_PORT` (worker only): if set (e.g., `9300`), worker exposes Prometheus metrics on that port
- `DELETE_STAGING_ON_FINALIZE` (api): if `true`, staging object is deleted after copy
- `S3_PUBLIC_ENDPOINT_URL` (api): external endpoint for presigned URLs (e.g., `http://localhost:9000`)

### OCR Tuning (Advanced)
- Images (Tesseract):
  - `OCR_OEM` and `OCR_PSM` to control engine and page segmentation mode.
  - `OCR_TESSERACT_EXTRA` to pass extra flags (e.g., `--dpi 200`).
- PDFs (ocrmypdf):
  - `OCR_OCRMYPDF_EXTRA` to pass additional flags.
  - Budget mode is optimized automatically (reduced cleanup, shorter timeouts).

### API Auth (Optional)
- Set `API_AUTH_ENABLED=1` and `API_KEY=<value>` to require `X-API-Key` for `/v0/*` endpoints (except `/v0/version`).

## Presigned Upload Flow (Recommended)
1. `POST /v0/uploads/presign` → get `object_key` + presigned PUT URL
2. PUT file bytes to URL (client → S3/MinIO)
3. `POST /v0/uploads/finalize` with `tenant_id`, `user_id`, and `key=object_key`
4. Poll `/v0/jobs/{id}`; fetch `/v0/documents/{id}/processed.json`

Helper scripts:
- `scripts/batch_upload.py` (uses presigned by default; add `--legacy` for old path)
- `scripts/smoke_presign.py`, `scripts/smoke_finalize.py`
- `scripts/smoke_credits.py <tenant_id>` prints balance and recent ledger
- `scripts/staging_gc.py --ttl-hours 48 --dry-run` to sweep orphaned presign staging objects
- `scripts/smoke_in_network.sh` runs the finalize smoke inside Docker network so the `minio` hostname resolves (useful if host cannot reach `minio`)

Note: External scripts should work directly with the default configuration. If you encounter hostname resolution errors with presigned URLs, ensure `S3_PUBLIC_ENDPOINT_URL=http://localhost:9000` is set in `.env` and restart the stack.

For legacy Docker Compose v1 compatibility, you can run smoke tests inside the network:
```bash
docker-compose -f infra/docker-compose.yml up -d postgres redis minio create-bucket api worker
./scripts/smoke_in_network.sh
```

## Credits (Dev Notes)
- Estimate on upload/finalize inserts `credits` row: `delta=-estimate`, `reason=estimate`, `is_estimate=true`.
- On job success, worker posts:
  - `estimate_reversal` with `+estimate`
  - `actual` with `-actual` (simple heuristic; uses `page_count` if available)
  - marks original estimate `is_estimate=false`.
- On job failure, worker posts `refund_failure` with `+estimate` and closes the estimate.
- Inspect via:
  - `GET /v0/credits/balance?tenant_id=...`
  - `GET /v0/credits/ledger?tenant_id=...&limit=50`

### Refund Demo
To simulate a failure and observe a refund:

```bash
docker compose -f infra/docker-compose.yml exec api python scripts/demo_refund_failure.py
```

This creates a document version with a non-existent storage key, causing the worker to fail fetching bytes. The job transitions to `failed`, a `refund_failure` credit is added, and the original estimate is closed.

## Troubleshooting
- MinIO bucket missing: API creates on startup; restart `api` if MinIO came up late.
- DB connection errors: Ensure `alembic upgrade head` executed and Postgres is healthy.
- Large uploads: Increase `client_max_body_size` or proxy limits if fronted by a gateway.
- Worker metrics: set `METRICS_PORT=9300` in `.env` and rebuild/restart worker to scrape metrics at `http://localhost:9300/`. The same port serves `GET /health`.
  
  In docker-compose, you can map the port (uncomment):
  
  ```yaml
  worker:
    # environment:
    #   - METRICS_PORT=9300
    # ports:
    #   - "9300:9300"
  ```
- Tests hang at API startup: set env `FIRSTDRAFT_SKIP_STARTUP_CHECKS=1` (auto-detected under `pytest`) to skip S3/DB checks during app startup.
- docker-compose v1 error: If you see `KeyError: 'ContainerConfig'` during `up`, upgrade to Docker Compose v2 (`docker compose`) or prune old containers/images (`docker system prune -a`) and retry.
- API healthcheck failing: check `/healthz` logs; ensure migrator ran successfully and that Postgres is reachable.

## Dev UI Tips
- From Documents list or detail, quick links are available:
  - Processed JSON `/v0/documents/{id}/processed.json`
  - Report Markdown `/v0/documents/{id}/report.md`
  - Temporary presigned download of original via `/v0/uploads/presign_download?key=...`
