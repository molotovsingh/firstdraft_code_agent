from fastapi.testclient import TestClient
import os


def test_auth_disabled_by_default(monkeypatch):
    # Ensure disabled
    monkeypatch.delenv('API_AUTH_ENABLED', raising=False)
    monkeypatch.delenv('API_KEY', raising=False)
    import importlib
    import apps.block0_api.main as api
    importlib.reload(api)
    with TestClient(api.app) as client:
        r = client.get('/v0/version')
        assert r.status_code == 200


def test_auth_enabled_blocks_without_key(monkeypatch):
    monkeypatch.setenv('API_AUTH_ENABLED', '1')
    monkeypatch.setenv('API_KEY', 'secret')
    import importlib
    import apps.block0_api.main as api
    importlib.reload(api)
    with TestClient(api.app) as client:
        r = client.get('/v0/version')
        # version is excluded, should be allowed
        assert r.status_code == 200
        r2 = client.get('/v0/credits/summary', params={'tenant_id': '00000000-0000-0000-0000-000000000000'})
        assert r2.status_code == 401


def test_auth_enabled_allows_with_key(monkeypatch):
    monkeypatch.setenv('API_AUTH_ENABLED', '1')
    monkeypatch.setenv('API_KEY', 'secret')
    import importlib
    import apps.block0_api.main as api
    importlib.reload(api)
    with TestClient(api.app) as client:
        r = client.get('/v0/credits/summary', params={'tenant_id': '00000000-0000-0000-0000-000000000000'}, headers={'X-API-Key': 'secret'})
        # Will 400 on invalid tenant, which is fine; key was accepted
        assert r.status_code in (200, 400, 404, 422)

