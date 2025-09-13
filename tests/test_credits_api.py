from fastapi.testclient import TestClient


def test_credits_balance_invalid_tenant(monkeypatch):
    import apps.block0_api.main as api

    with TestClient(api.app) as client:
        r = client.get("/v0/credits/balance", params={"tenant_id": "not-a-uuid"})
        assert r.status_code == 400


def test_credits_ledger_tenant_not_found(monkeypatch):
    import apps.block0_api.main as api

    class DummyDB:
        def get(self, model, key):
            # Simulate valid UUID but unknown tenant
            return None

    # Override dependency to supply DummyDB
    def _override_db():
        return DummyDB()

    api.app.dependency_overrides[api.get_db] = _override_db
    try:
        with TestClient(api.app) as client:
            # Use a valid UUID to reach tenant-not-found path
            r = client.get("/v0/credits/ledger", params={"tenant_id": "00000000-0000-0000-0000-000000000000"})
            assert r.status_code == 404
    finally:
        api.app.dependency_overrides.clear()


def test_credits_balance_ok(monkeypatch):
    import apps.block0_api.main as api
    from types import SimpleNamespace
    import uuid

    tid = uuid.uuid4()

    class DummyTenant:
        id = tid

    class DummyCredit:
        def __init__(self, delta):
            self.delta = delta

    class Q:
        def __init__(self, items):
            self._items = items

        def filter(self, *args, **kwargs):
            return self

        def all(self):
            return self._items

    class DummyDB:
        def get(self, model, key):
            # Return a tenant for the provided UUID
            return DummyTenant() if isinstance(key, uuid.UUID) else None

        def query(self, model):
            # Return three credit entries summing to -10
            return Q([DummyCredit(-20), DummyCredit(+5), DummyCredit(+5)])

    def _override_db():
        return DummyDB()

    api.app.dependency_overrides[api.get_db] = _override_db
    try:
        with TestClient(api.app) as client:
            r = client.get("/v0/credits/balance", params={"tenant_id": str(tid)})
            assert r.status_code == 200
            j = r.json()
            assert j["tenant_id"] == str(tid)
            assert j["balance"] == -10
            assert j["count"] == 3
    finally:
        api.app.dependency_overrides.clear()

