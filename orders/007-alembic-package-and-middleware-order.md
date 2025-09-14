# Order 007 — Test fixes: alembic import + middleware order

Owner: Claude
Scope: Resolve two test failures without changing runtime behavior.

Issues
- `test_alembic_env_metadata`: `import alembic.env` fails because local `alembic/` is not a package; missing `__init__.py` and collides with pip's `alembic`.
- `test_middleware_order`: expected order is `RequestIDMiddleware`, `HTTPAccessLogMiddleware`, `APIKeyAuthMiddleware`, but current `app.user_middleware` shows reversed order.

Changes
1) Add empty `alembic/__init__.py` so `alembic.env` resolves to this repo’s module.
2) Adjust middleware registration order in `apps/block0_api/main.py` to achieve expected inspection order:
   - Add `APIKeyAuthMiddleware` first, then `HTTPAccessLogMiddleware`, then `RequestIDMiddleware` last, so `app.user_middleware` lists them as RequestID, HTTPAccessLog, APIKeyAuth.
   - Do not alter the classes or behavior, only the order of `app.add_middleware(...)` calls.

Acceptance Criteria
- `pytest -q` shows `test_alembic_env_metadata` and `test_middleware_order` passing.
- No other tests regress.

Validation
- Run full suite locally: `uv venv .venv && uv pip install -r requirements.txt && uv run pytest -q`.

Out of Scope
- Any change to middleware logic; only call order may be changed.
