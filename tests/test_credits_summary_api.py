from fastapi.testclient import TestClient
import uuid


def _db_with_credits(tenant_id: uuid.UUID):
    class Credit:
        def __init__(self, tenant_id, delta, is_estimate, reason):
            self.tenant_id = tenant_id
            self.user_id = 1
            self.delta = delta
            self.is_estimate = is_estimate
            self.reason = reason

    class Tenant:
        def __init__(self, id):
            self.id = id

    class Q:
        def __init__(self, rows):
            self._rows = rows

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def group_by(self, *args, **kwargs):
            return self

        def all(self):
            return list(self._rows)

        def scalar(self):
            # Not used in fallback path; trigger exception to force fallback branch
            raise RuntimeError("no db agg in stub")

        def one(self):
            raise RuntimeError("no db agg in stub")

    class DB:
        def __init__(self):
            # Mix of estimate (pending) and finalized rows
            self.rows = [
                Credit(tenant_id, -100, False, "actual"),
                Credit(tenant_id, -50, False, "actual"),
                Credit(tenant_id, 75, False, "estimate_reversal"),
                Credit(tenant_id, -200, True, "estimate"),
                Credit(tenant_id, -150, True, "estimate"),
            ]

        def get(self, model, key):
            from shared.db import models as m
            if model is m.Tenant and isinstance(key, uuid.UUID):
                return Tenant(tenant_id) if key == tenant_id else None
            return None

        def query(self, model):
            return Q(self.rows)

    def _dep():
        return DB()

    return _dep


def test_credits_summary_fallback_agg(monkeypatch):
    import apps.block0_api.main as api

    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    api.app.dependency_overrides[api.get_db] = _db_with_credits(tenant_id)
    try:
        with TestClient(api.app) as client:
            r = client.get("/v0/credits/summary", params={"tenant_id": str(tenant_id)})
            assert r.status_code == 200
            j = r.json()
            # Totals: (-100) + (-50) + 75 + (-200) + (-150) = -425
            assert j["total"] == -425
            assert j["pending_estimates"]["count"] == 2
            assert j["pending_estimates"]["sum"] == -350
            # by_reason presence
            assert "actual" in j["by_reason"]
    finally:
        api.app.dependency_overrides.clear()

