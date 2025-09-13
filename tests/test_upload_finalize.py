from fastapi.testclient import TestClient
import uuid


class DummyStorage:
    bucket = "test"

    def __init__(self):
        self._store = {}

    @staticmethod
    def sha256_hex(data: bytes) -> str:
        import hashlib
        return hashlib.sha256(data).hexdigest()

    def presign_put_url(self, key: str, expiry: int = 3600) -> str:
        return f"https://example.com/put/{key}?exp={expiry}"

    def presign_get_url(self, key: str, expiry: int = 600) -> str:
        return f"https://example.com/get/{key}?exp={expiry}"

    def object_key(self, tenant_id: str, sha256: str, version: int, filename: str) -> str:
        return f"{tenant_id}/{sha256[:2]}/{sha256}/v{version}/{filename}"

    def put_object(self, key: str, data: bytes, content_type: str = "application/octet-stream"):
        self._store[key] = data

    def get_object_bytes(self, key: str) -> bytes:
        if key not in self._store:
            raise FileNotFoundError(key)
        return self._store[key]

    def copy_object(self, src_key: str, dst_key: str) -> None:
        self._store[dst_key] = self._store[src_key]

    def object_exists(self, key: str) -> bool:
        return key in self._store

    def ensure_bucket(self):
        return None


def _override_db_ok(tenant_id: uuid.UUID):
    # Minimal in-memory DB stub that satisfies API usage without real SQLA session
    class Tenant:
        def __init__(self, id):
            self.id = id

    class User:
        def __init__(self, id, tenant_id):
            self.id = id
            self.tenant_id = tenant_id

    class Credit:
        def __init__(self, tenant_id, user_id, delta, reason, job_id, is_estimate):
            self.tenant_id = tenant_id
            self.user_id = user_id
            self.delta = delta
            self.reason = reason
            self.job_id = job_id
            self.is_estimate = is_estimate

    class Q:
        def __init__(self, model, rows):
            self.model = model
            self._rows = rows

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def first(self):
            return None

        def all(self):
            return list(self._rows)

    class DB:
        def __init__(self):
            self.tenant = Tenant(tenant_id)
            self.user = User(1, tenant_id)
            self.credits = []

        def get(self, model, key):
            from shared.db import models as m
            if model is m.Tenant and isinstance(key, uuid.UUID):
                return self.tenant if key == tenant_id else None
            if model is m.User and isinstance(key, int):
                return self.user if key == 1 else None
            return None

        def query(self, model):
            from shared.db import models as m
            if model is m.Credit:
                return Q(model, self.credits)
            return Q(model, [])

        def add(self, obj):
            if hasattr(obj, "id") and getattr(obj, "id") is None:
                obj.id = 1
            if obj.__class__.__name__ == "Credit":
                self.credits.append(obj)

        def flush(self):
            return None

        def commit(self):
            return None

        def rollback(self):
            return None

        def close(self):
            return None

    def _dep():
        return DB()

    return _dep


def test_presign_minimal(monkeypatch):
    import apps.block0_api.main as api
    # Patch Storage
    monkeypatch.setattr(api, "Storage", lambda: DummyStorage())
    with TestClient(api.app) as client:
        r = client.post(
            "/v0/uploads/presign",
            json={
                "tenant_id": "11111111-1111-1111-1111-111111111111",
                "user_id": 1,
                "filename": "file.pdf",
                "mime": "application/pdf",
            },
        )
        assert r.status_code == 200
        j = r.json()
        assert "object_key" in j and j["object_key"].endswith("file.pdf." + j["object_key"].split(".")[-1])
        assert "url" in j and j["url"].startswith("https://")


def test_finalize_missing_object(monkeypatch):
    import apps.block0_api.main as api
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")
    monkeypatch.setattr(api, "Storage", lambda: DummyStorage())
    api.app.dependency_overrides[api.get_db] = _override_db_ok(tenant)
    try:
        with TestClient(api.app) as client:
            r = client.post(
                "/v0/uploads/finalize",
                json={
                    "tenant_id": str(tenant),
                    "user_id": 1,
                    "key": "nonexistent/key",
                    "filename": "file.pdf",
                    "mime": "application/pdf",
                },
            )
            assert r.status_code == 404
    finally:
        api.app.dependency_overrides.clear()

