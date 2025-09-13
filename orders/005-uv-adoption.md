# Order 005 — Adopt `uv` for env + installs (incremental)

Owner: Claude
Scope: Introduce `uv` as the primary package/deps tool with minimal risk. Keep `requirements.txt` as the single source of truth for now. No behavior changes to app code.

Why
- ADR-0007 selects `uv` (fast, lockable, reproducible). Builds and local setup are currently pip/venv, which are slower on CI.

Acceptance Criteria
- Dev docs: Add a short "Using `uv`" section to `README.md` and `RUNBOOK.md` with:
  - `uv venv .venv`
  - `uv pip install -r requirements.txt`
  - `uv run pytest -q`, `uv run ./scripts/ci_smoke.sh`
- Dockerfiles: Install `uv` and use it to install deps:
  - `infra/dockerfiles/Dockerfile.api` and `infra/dockerfiles/Dockerfile.worker` install `uv` (official installer) and run `uv pip install -r requirements.txt`.
  - Preserve existing runtime user, env, and image size considerations (no extra layers beyond necessity).
- CI: If `.github/workflows/ci.yml` runs tests outside Docker, add a lightweight `uv` setup step (skip if entirely Docker-based). Ensure cache friendliness; otherwise leave as-is.
- No removal of `requirements.txt` yet; no `pyproject.toml` added in this order.

Validation
- Local: fresh clone → follow `uv` steps → `uv run pytest -q` passes (or current expected status) and `uv run ./scripts/ci_smoke.sh` runs when Docker is available.
- Docker: `docker compose -f infra/docker-compose.yml build` succeeds and build time is acceptable; containers start normally.
- CI: Workflow still passes (or unchanged if Docker-only).

Out of Scope
- Converting to `pyproject.toml`/`uv.lock` ownership. That can be a follow-up order once we’re stable.
- Changing production deployment strategy.

Change Log (to include in PR)
- Add `uv` usage docs; switch Dockerfiles to `uv pip install -r requirements.txt`; keep `requirements.txt` as the source of truth.
