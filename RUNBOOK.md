# Runbook — Block 0a Dev

## Services
- `api` (FastAPI): HTTP endpoints for upload/status/report
- `worker` (Celery): Background processing for normalization/OCR
- `postgres`: Metadata store
- `redis`: Broker/result backend
- `minio`: S3-compatible object store

## Common Commands
```bash
# Start stack
docker compose -f infra/docker-compose.yml up --build -d

# Logs
docker compose -f infra/docker-compose.yml logs -f api

docker compose -f infra/docker-compose.yml logs -f worker

# Run migrations (after containers are up)
docker compose -f infra/docker-compose.yml exec api alembic upgrade head

# Bootstrap dev tenant and users
docker compose -f infra/docker-compose.yml exec api python scripts/bootstrap_dev.py

# Open shell in api container
docker compose -f infra/docker-compose.yml exec api bash
```

## Data Locations
- Objects: `s3://firstdraft-dev/{tenant}/{sha256[:2]}/{sha256}/v{n}/...`
- Database: Postgres `firstdraft_system` (dev), see `DATABASE_URL`

## Feature Flags
- `OCR_PROVIDER=stub|tesseract|ocrmypdf` (stub by default)
- `QUALITY_MODE=recommended|budget` (default in `.env`)
- `OCR_LANG=eng|eng+hin` (default `eng+hin`)
- `METRICS_PORT` (worker only): if set (e.g., `9300`), worker exposes Prometheus metrics on that port

## Troubleshooting
- MinIO bucket missing: API creates on startup; restart `api` if MinIO came up late.
- DB connection errors: Ensure `alembic upgrade head` executed and Postgres is healthy.
- Large uploads: Increase `client_max_body_size` or proxy limits if fronted by a gateway.
- Worker metrics: set `METRICS_PORT=9300` in `.env` and rebuild/restart worker to scrape metrics at `http://localhost:9300/`
