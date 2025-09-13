from fastapi.testclient import TestClient
import uuid


def _db_with_doc(doc_id: uuid.UUID):
    """Return a dependency override that yields a minimal DB stub with one document and version."""
    class Doc:
        def __init__(self, id):
            self.id = id
            self.tenant_id = uuid.uuid4()
            self.orig_filename = "file.pdf"
            self.mime = "application/pdf"

    class Ver:
        __tablename__ = "document_versions"

        def __init__(self, document_id, version, storage_uri):
            self.document_id = document_id
            self.version = version
            self.storage_uri = storage_uri

    class Job:
        __tablename__ = "processing_jobs"

        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    class Q:
        def __init__(self, model, rows):
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
            self.vers = [Ver(document_id=doc_id, version=1, storage_uri="t/x/v1/file.pdf")]
            self.jobs = []

        def get(self, model, key):
            from shared.db import models as m
            if model is m.Document and key == doc_id:
                return self.doc
            return None

        def query(self, model):
            from shared.db import models as m
            if model is m.DocumentVersion:
                return Q(model, self.vers)
            return Q(model, [])

        def add(self, obj):
            if getattr(obj, "__tablename__", "") == "document_versions":
                self.vers.append(obj)
            elif getattr(obj, "__tablename__", "") == "processing_jobs":
                self.jobs.append(obj)

        def flush(self):
            return None

        def commit(self):
            return None

        def close(self):
            return None

    def _dep():
        return DB()

    return _dep


def test_reprocess_creates_new_version(monkeypatch):
    import apps.block0_api.main as api

    # Override DB and enqueue
    doc_id = uuid.uuid4()
    api.app.dependency_overrides[api.get_db] = _db_with_doc(doc_id)
    monkeypatch.setattr(api, "enqueue_process_document", lambda job_id: None)

    try:
        with TestClient(api.app) as client:
            r = client.post(f"/v0/documents/{doc_id}/reprocess")
            assert r.status_code == 200
            j = r.json()
            assert j["document_id"] == str(doc_id)
            assert j["new_version"] == 2
            assert isinstance(j["job_id"], str) and len(j["job_id"]) > 10
    finally:
        api.app.dependency_overrides.clear()

