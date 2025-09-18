# Gemini Repo Read-through: 2025-09-14

This report summarizes the current state of the repository, highlights risks, and proposes a short plan for stabilization and next steps.

## Ownership & Entrypoints
- **API (`apps/block0_api`)**: FastAPI app (`uvicorn apps.block0_api.main:app`). Uploads, presign/finalize, jobs, credits, minimal Dev UI.
- **Worker (`apps/block0_worker`)**: Celery worker for background processing.
- **Database (`shared/db`, `alembic`)**: SQLAlchemy models; Alembic migrations under `alembic/versions/`.
- **Storage (`shared/storage/s3.py`)**: MinIO/S3 wrapper; supports public/internal presign (Order 006).
- **Infra (`infra/docker-compose.yml`)**: Postgres, Redis, MinIO, API, Worker, Migrator.
- **CI/Smokes (`scripts/ci_smoke.sh`, `scripts/smoke_in_network.sh`)**: Build, migrate, start, verify presign→finalize inside network.
- **Tests (`tests/`)**: Coverage for health, uploads, credits, middleware, Alembic, OCR adapters, UI.

## Recent Orders (validated)
- **006 – Presign (internal network)**: API honors `X-Internal-Network` to presign via internal endpoint; smoke script sets `PRESIGN_INTERNAL=1`.
- **007 – Alembic import + middleware order**: Added `alembic/__init__.py` shim so `import alembic.env` works; reordered `app.add_middleware(...)` to satisfy inspection order expected by tests.
- **008 – Pytest scoping**: Added `pytest.ini` to limit discovery to `tests/`.

## Risks
1. **CI smoke image tag mismatch (High)**
   - `scripts/ci_smoke.sh` mixes `infra-api:latest` and `infra_api:latest`. The underscore tag is wrong and can break the health check container invocation.
2. **No `.gitignore` (Medium)**
   - Root lacks `.gitignore`. Tracked `__pycache__`/`*.pyc` pollute the repo and risk conflicts.
3. **Middleware order test brittleness (Low)**
   - Test asserts `app.user_middleware` order (inspection) rather than behavioral/execution order. Currently passing; improvement is optional.

## Suggested Plan (small, safe increments)
1. **Add comprehensive `.gitignore`** (python, venv, caches, IDE, env files).
2. **Fix image tag in `scripts/ci_smoke.sh`** to consistently use `infra-api:latest`.
3. (Optional) **Harden middleware test** to validate behavior rather than list order.

## Impacted Files
- New: `.gitignore`
- Edit: `scripts/ci_smoke.sh`
- Optional: `tests/test_middleware_order.py`

