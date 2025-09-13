from fastapi.testclient import TestClient
import os
import uuid


def _db_with_doc_and_version(doc_id: uuid.UUID):
    class Doc:
        def __init__(self, id):
            self.id = id
            self.orig_filename = "test.pdf"
            self.mime = "application/pdf"

    class Ver:
        def __init__(self, document_id, version, storage_uri):
            self.document_id = document_id
            self.version = version
            self.storage_uri = storage_uri

    class Q:
        def __init__(self, rows):
            self._rows = rows

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def first(self):
            return self._rows[-1] if self._rows else None

    class DB:
        def __init__(self):
            self.doc = Doc(doc_id)
            self.vers = [Ver(doc_id, 1, "tenant/ab/sha/v1/file.pdf")]

        def get(self, model, key):
            from shared.db import models as m
            if model is m.Document and key == doc_id:
                return self.doc
            return None

        def query(self, model):
            from shared.db import models as m
            if model is m.DocumentVersion:
                return Q(self.vers)
            return Q([])

    def _dep():
        return DB()

    return _dep


def test_ui_doc_detail_links(monkeypatch):
    os.environ["UI_ENABLED"] = "1"
    import importlib
    import apps.block0_api.main as api
    importlib.reload(api)

    doc_id = uuid.uuid4()
    api.app.dependency_overrides[api.get_db] = _db_with_doc_and_version(doc_id)
    try:
        with TestClient(api.app) as client:
            r = client.get(f"/ui/docs/{doc_id}")
            assert r.status_code == 200
            html = r.text
            assert f"/v0/documents/{doc_id}/processed.json" in html
            assert f"/v0/documents/{doc_id}/report.md" in html
            assert "/v0/uploads/presign_download?key=" in html
    finally:
        api.app.dependency_overrides.clear()

