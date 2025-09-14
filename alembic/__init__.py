"""
Project-local Alembic shim.

Goals:
- Allow tests to import `alembic.env` from this repository (alembic/env.py)
- Preserve access to the real Alembic package symbols like `op` and `context`

Implementation: temporarily remove this directory from sys.path, import the
installed Alembic package, then restore sys.path. Re-export `op` and `context`.
Also register `alembic.env` pointing at our local env.py.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from types import ModuleType


def _import_real_alembic() -> ModuleType:
    here = os.path.dirname(__file__)
    removed = False
    try:
        if here in sys.path:
            sys.path.remove(here)
            removed = True
        # Now import the installed Alembic package
        return importlib.import_module("alembic")
    finally:
        if removed:
            # Restore our package path at the front for local imports
            sys.path.insert(0, here)


_real = _import_real_alembic()

# Re-export common Alembic modules used by migration scripts
_context_mod = importlib.import_module("alembic.context")
_op_mod = importlib.import_module("alembic.op")
context = _context_mod
op = _op_mod


def _load_local_env() -> ModuleType:
    env_path = os.path.join(os.path.dirname(__file__), "env.py")
    spec = importlib.util.spec_from_file_location("alembic.env", env_path)
    assert spec and spec.loader, "failed to create spec for alembic.env"
    mod = importlib.util.module_from_spec(spec)
    sys.modules["alembic.env"] = mod
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


# Preload local alembic.env into sys.modules so `import alembic.env` resolves here.
if "alembic.env" not in sys.modules:
    _load_local_env()
