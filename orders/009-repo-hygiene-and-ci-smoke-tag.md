# Order 009 — Repo hygiene + CI smoke tag fix

Owner: Claude
Scope: Improve repository hygiene and stabilize CI smoke script; no behavior changes to app/services.

Problems
- `.gitignore` missing → tracked `__pycache__/` and `*.pyc` artifacts; noisy `git status` and risk of conflicts.
- `scripts/ci_smoke.sh` uses inconsistent image tags (`infra-api:latest` vs `infra_api:latest`) causing potential CI failures.

Changes
1) Add a standard Python `.gitignore` at repo root covering:
   - `__pycache__/`, `*.py[cod]`, `*.pyo`, `*.pyd`, `*.so`
   - `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.coverage`, `htmlcov/`
   - `.venv/`, `venv/`, `ENV/`
   - `.DS_Store`, `.idea/`, `.vscode/`
   - `.env`, `*.env`
2) Update `scripts/ci_smoke.sh` to use `infra-api:latest` consistently (replace any `infra_api:latest`).
3) Untrack currently committed artifacts (one-time cleanup): remove `apps/block0_api/__pycache__/main.cpython-313.pyc` and any other accidentally tracked caches from Git index (keep on disk).

Acceptance Criteria
- `git status` shows a clean tree (no tracked `__pycache__`/`*.pyc`).
- `scripts/ci_smoke.sh` references only `infra-api:latest`; smoke passes in environments with Docker Compose v2 available.
- Unit tests still pass (`pytest -q`) and no behavior changes to runtime code.

Validation
- Run: `pytest -q`.
- Inspect: `grep -R "infra_api:latest" -n scripts || true` → no matches.
- Optional (if Docker available): `./scripts/ci_smoke.sh` completes with `[ci_smoke] OK`.

Constraints
- No unrelated refactors.
- Do not change public APIs or DB schemas.
- Keep edits minimal and focused.

Out of Scope
- Middleware test refactor; only if needed in a future order.

Change Log
- Add `.gitignore`; fix image tag; untrack cache artifacts.

