# FirstDraft v2.0 — Block 0a Scaffold

This repository contains the initial scaffold for Block 0a (Document Pre-processing) and shared modules defined in the PRD (2025-09-07) and ADRs (through 2025-09-10).

What’s included:
- FastAPI service for uploads and reporting (`apps/block0_api`)
- Celery worker for background processing (`apps/block0_worker`)
- Shared libraries for DB, storage, quality metrics, OCR adapters, and LLM router stubs (`shared/*`)
- PostgreSQL, Redis, and MinIO via Docker Compose (`infra/docker-compose.yml`)
- Minimal Alembic migrations to create core tables

Quick start (development):

```bash
# 1) Copy and edit environment variables
cp .env.example .env

# 2) Start services
docker compose -f infra/docker-compose.yml up --build -d

# 3) Apply DB migrations
docker compose -f infra/docker-compose.yml exec api alembic upgrade head

# 4) Try an upload (replace file path)
curl -F "tenant_id=11111111-1111-1111-1111-111111111111" \
     -F "user_id=1" \
     -F "files=@/path/to/your/doc.pdf" \
     http://localhost:8000/v0/documents/upload

# 5) Check job
curl http://localhost:8000/v0/jobs/<job_id>

# 6) Fetch report
curl http://localhost:8000/v0/documents/<document_id>/report.json

# Optional: CI-style smoke test (presign → finalize → worker) inside Docker network
./scripts/ci_smoke.sh
```

Notes:
- Default OCR provider is tesseract. To disable OCR for dev, set `OCR_PROVIDER=stub`. For PDF-focused OCR, set `OCR_PROVIDER=ocrmypdf`.
- Storage is S3-compatible (MinIO locally). Content addressing uses SHA-256 of the original bytes.
- Credits ledger is included with a simple estimation stub and finalization hook.
- If your host cannot resolve `minio`, use the in-network smoke helper `scripts/smoke_in_network.sh` (also used by `ci_smoke.sh`).

## Using uv (faster local setup)
- uv venv .venv
- uv pip install -r requirements.txt
- uv run pytest -q
- uv run ./scripts/ci_smoke.sh

See `API.md` and `RUNBOOK.md` for details.

## Agent Workflow

This repo uses a strict multi‑agent process:

- Code: orchestrates, orders work, reviews, and files bugfix tasks (no coding)
- Claude: implementation and bugfixes
- Gemini: repo reading and suggestions

Start with `AGENTS.md` for roles, invocation patterns, and guardrails.
