"""
Project-local Alembic shim for tests.

Why: The repository includes `alembic/env.py` and migration scripts under
`alembic/versions/`. Tests import `alembic.env` and migration modules, but we
do not need the full Alembic runtime. Importing the real `alembic` package
under the same top-level name is fragile in local execution, so we expose the
minimal surface needed at import time:

- `alembic.env` should import and expose `target_metadata`.
- `from alembic import op` in migration files should succeed (functions are not
  executed by tests, they only check presence of upgrade/downgrade callables).

This shim intentionally provides no-op `context` and `op` objects that satisfy
imports without performing any side effects.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from types import SimpleNamespace
from contextlib import contextmanager


# --- Minimal no-op `context` API used by alembic/env.py at import time ---
@contextmanager
def _noop_txn():
    yield


class _ContextNoop:
    # env.py expects `config` with attribute `config_file_name`
    config = SimpleNamespace(config_file_name=None)

    @staticmethod
    def is_offline_mode() -> bool:
        # Prefer offline path (safe, no DB calls)
        return True

    @staticmethod
    def configure(*args, **kwargs) -> None:  # pragma: no cover - no-op
        return None

    @staticmethod
    def begin_transaction():  # pragma: no cover - no-op
        return _noop_txn()

    @staticmethod
    def run_migrations() -> None:  # pragma: no cover - no-op
        return None


context = _ContextNoop()


# --- Minimal no-op `op` API referenced by migration modules at import time ---
class _OpNoop:
    def __getattr__(self, name):  # pragma: no cover - generic sink
        # Return a no-op callable for any attribute lookup (create_table, execute, ...)
        def _fn(*args, **kwargs):
            return None

        return _fn


op = _OpNoop()


# --- Load local alembic.env as submodule `alembic.env` ---
def _load_local_env() -> None:
    env_path = os.path.join(os.path.dirname(__file__), "env.py")
    spec = importlib.util.spec_from_file_location("alembic.env", env_path)
    assert spec and spec.loader, "failed to create spec for alembic.env"
    mod = importlib.util.module_from_spec(spec)
    sys.modules["alembic.env"] = mod
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]


if "alembic.env" not in sys.modules:
    _load_local_env()
