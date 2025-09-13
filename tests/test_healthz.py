from fastapi.testclient import TestClient


def test_healthz_ok(monkeypatch):
    # Import after patching needed symbols
    import apps.block0_api.main as api

    class DummyDB:
        def execute(self, q):
            return None

        def close(self):
            return None

    class DummyRedis:
        def ping(self):
            return True

    class DummyStorage:
        bucket = "test"

        def __init__(self):
            class _C:
                @staticmethod
                def bucket_exists(_):
                    return True

            self.client = _C()

        def ensure_bucket(self):
            return None

    # Patch dependencies used by /healthz
    monkeypatch.setattr(api, "SessionLocal", lambda: DummyDB())
    monkeypatch.setattr(api.redis_lib, "from_url", lambda url: DummyRedis())
    monkeypatch.setattr(api, "Storage", DummyStorage)

    with TestClient(api.app) as client:
        r = client.get("/healthz")
        assert r.status_code == 200
        j = r.json()
        assert j["status"] == "ok"
        assert j["components"]["db"] is True
        assert j["components"]["redis"] is True
        assert j["components"]["s3"] is True


def test_healthz_degraded(monkeypatch):
    import apps.block0_api.main as api

    class DummyDB:
        def execute(self, q):
            return None

        def close(self):
            return None

    class BadRedis:
        def ping(self):
            raise RuntimeError("boom")

    class BadStorage:
        bucket = "test"

        def __init__(self):
            class _C:
                @staticmethod
                def bucket_exists(_):
                    return False

            self.client = _C()

        def ensure_bucket(self):
            return None

    monkeypatch.setattr(api, "SessionLocal", lambda: DummyDB())
    monkeypatch.setattr(api.redis_lib, "from_url", lambda url: BadRedis())
    monkeypatch.setattr(api, "Storage", BadStorage)

    with TestClient(api.app) as client:
        r = client.get("/healthz")
        assert r.status_code == 503
        j = r.json()
        assert j["status"] == "degraded"
