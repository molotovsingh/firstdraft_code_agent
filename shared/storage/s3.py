import hashlib
import os
from minio import Minio


class Storage:
    def __init__(self):
        endpoint = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000").replace("http://", "").replace("https://", "")
        secure = os.getenv("S3_SECURE", "false").lower() in {"1", "true", "yes", "on"}
        self.bucket = os.getenv("S3_BUCKET", "firstdraft-dev")
        self.client = Minio(
            endpoint,
            access_key=os.getenv("S3_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("S3_SECRET_KEY", "minioadmin"),
            secure=secure,
        )

    def ensure_bucket(self):
        found = self.client.bucket_exists(self.bucket)
        if not found:
            self.client.make_bucket(self.bucket)

    def put_object(self, key: str, data: bytes, content_type: str = "application/octet-stream"):
        import io
        self.client.put_object(self.bucket, key, io.BytesIO(data), length=len(data), content_type=content_type)

    def object_key(self, tenant_id: str, sha256: str, version: int, filename: str) -> str:
        prefix = f"{tenant_id}/{sha256[:2]}/{sha256}/v{version}"
        return f"{prefix}/{filename}"

    @staticmethod
    def sha256_hex(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def get_object_bytes(self, key: str) -> bytes:
        resp = self.client.get_object(self.bucket, key)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()
