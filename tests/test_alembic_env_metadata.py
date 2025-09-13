def test_alembic_env_target_metadata_present():
    import importlib
    env = importlib.import_module('alembic.env')
    assert hasattr(env, 'target_metadata') and env.target_metadata is not None

