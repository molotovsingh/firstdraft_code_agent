from fastapi.testclient import TestClient
import os


def test_ui_home_enabled(monkeypatch):
    # Enable UI before import
    monkeypatch.setenv("UI_ENABLED", "1")
    import importlib
    import apps.block0_api.main as api
    importlib.reload(api)
    with TestClient(api.app) as client:
        r = client.get("/ui/")
        assert r.status_code == 200
        assert b"FirstDraft \xe2\x80\x94 Block 0a" in r.content


def test_ui_docs_empty(monkeypatch):
    monkeypatch.setenv("UI_ENABLED", "1")
    import importlib
    import apps.block0_api.main as api

    class DummyDB:
        def get(self, model, key):
            return None  # no tenant

    def _db():
        return DummyDB()

    importlib.reload(api)
    api.app.dependency_overrides[api.get_db] = _db
    try:
        with TestClient(api.app) as client:
            r = client.get("/ui/docs")
            assert r.status_code == 200
            assert b"No documents yet" in r.content
    finally:
        api.app.dependency_overrides.clear()

