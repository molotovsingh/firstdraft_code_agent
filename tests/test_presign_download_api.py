from fastapi.testclient import TestClient


class DummyStorage:
    bucket = "test"

    def __init__(self):
        pass

    def presign_get_url(self, key: str, expiry: int = 600) -> str:
        return f"https://example.com/get/{key}?exp={expiry}"


def test_presign_download_ok(monkeypatch):
    import apps.block0_api.main as api

    # Patch Storage to avoid MinIO
    monkeypatch.setattr(api, "Storage", lambda: DummyStorage())

    with TestClient(api.app) as client:
        r = client.get("/v0/uploads/presign_download", params={"key": "abc/def", "expiry": 900})
        assert r.status_code == 200
        j = r.json()
        assert j["url"].startswith("https://example.com/get/")
        assert j["expiry"] == 900

