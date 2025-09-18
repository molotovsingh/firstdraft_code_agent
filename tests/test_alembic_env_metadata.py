def test_alembic_env_target_metadata_present():
    import importlib
    import importlib.util
    import pathlib
    import sys

    # Load env.py directly from the migrations directory without relying on package name
    env_path = pathlib.Path('migrations/env.py')
    assert env_path.exists(), "migrations/env.py not found"

    # Ensure the lightweight migrations shim is used when env.py imports `alembic`
    shim_module = importlib.import_module('migrations')
    original_alembic = sys.modules.get('alembic')
    sys.modules['alembic'] = shim_module

    try:
        spec = importlib.util.spec_from_file_location('env', env_path)
        env = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(env)
    finally:
        if original_alembic is not None:
            sys.modules['alembic'] = original_alembic
        else:
            sys.modules.pop('alembic', None)

    assert hasattr(env, 'target_metadata') and env.target_metadata is not None
