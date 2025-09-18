"""
Project-local Alembic shim for tests.

Why: The repository includes `migrations/env.py` and migration scripts under
`migrations/versions/`. Tests import migration modules directly, but we
do not need the full Alembic runtime. Importing the real `alembic` package
under the same top-level name is fragile in local execution, so we expose the
minimal surface needed at import time:

- Migration files import `from alembic import op` which should succeed (functions are not
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


# --- Minimal no-op `context` API used by migrations/env.py at import time ---
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


# Note: This shim is kept for compatibility but tests now load env.py directly
# from the migrations directory without relying on package imports.
