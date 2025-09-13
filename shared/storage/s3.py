import hashlib
import hmac
import os
from datetime import datetime, timedelta
from urllib.parse import urlparse, quote, urlencode
from minio import Minio
from urllib.parse import urlparse, urlunparse

try:
    # Optional centralized settings
    from shared.config.settings import settings as _settings
except Exception:  # pragma: no cover - settings optional at import time
    _settings = None


class Storage:
    def __init__(self):
        endpoint_env = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
        endpoint = endpoint_env.replace("http://", "").replace("https://", "")
        secure = os.getenv("S3_SECURE", "false").lower() in {"1", "true", "yes", "on"}
        bucket = os.getenv("S3_BUCKET", "firstdraft-dev")

        if _settings is not None:
            endpoint = _settings.s3_endpoint_url.replace("http://", "").replace("https://", "") or endpoint
            secure = bool(_settings.s3_secure)
            bucket = _settings.s3_bucket or bucket

        self.bucket = bucket
        self.client = Minio(
            endpoint,
            access_key=(getattr(_settings, "s3_access_key", None) or os.getenv("S3_ACCESS_KEY", "minioadmin")),
            secret_key=(getattr(_settings, "s3_secret_key", None) or os.getenv("S3_SECRET_KEY", "minioadmin")),
            secure=secure,
        )

    def ensure_bucket(self):
        found = self.client.bucket_exists(self.bucket)
        if not found:
            self.client.make_bucket(self.bucket)

    def put_object(self, key: str, data: bytes, content_type: str = "application/octet-stream"):
        import io
        self.client.put_object(self.bucket, key, io.BytesIO(data), length=len(data), content_type=content_type)

    def put_file(self, key: str, fileobj, length: int, content_type: str = "application/octet-stream"):
        """Stream an object from a file-like to the bucket without loading into memory."""
        self.client.put_object(self.bucket, key, fileobj, length=length, content_type=content_type)

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

    # Presign helpers
    def presign_put_url(self, key: str, expiry: int = 3600) -> str:
        """Return presigned PUT URL. If S3_PUBLIC_ENDPOINT_URL is set, prefer
        an offline SigV4 presign against that endpoint (no network calls).
        """
        pub = os.getenv("S3_PUBLIC_ENDPOINT_URL")
        if pub:
            try:
                return self._offline_presign("PUT", key, expiry, pub)
            except Exception:
                # Fallback to internal client presign
                pass
        return self.client.presigned_put_object(self.bucket, key, expires=timedelta(seconds=expiry))

    def presign_get_url(self, key: str, expiry: int = 600) -> str:
        """Return presigned GET URL. If S3_PUBLIC_ENDPOINT_URL is set, prefer
        an offline SigV4 presign against that endpoint (no network calls).
        """
        pub = os.getenv("S3_PUBLIC_ENDPOINT_URL")
        if pub:
            try:
                return self._offline_presign("GET", key, expiry, pub)
            except Exception:
                # Fallback to internal client presign
                pass
        return self.client.presigned_get_object(self.bucket, key, expires=timedelta(seconds=expiry))

    def presign_put_url_internal(self, key: str, expiry: int = 3600) -> str:
        """Return presigned PUT URL using internal endpoint (no S3_PUBLIC_ENDPOINT_URL)."""
        return self.client.presigned_put_object(self.bucket, key, expires=timedelta(seconds=expiry))

    def presign_get_url_internal(self, key: str, expiry: int = 600) -> str:
        """Return presigned GET URL using internal endpoint (no S3_PUBLIC_ENDPOINT_URL)."""
        return self.client.presigned_get_object(self.bucket, key, expires=timedelta(seconds=expiry))

    # --- Offline SigV4 presign for public endpoint ---
    def _offline_presign(self, method: str, key: str, expiry: int, public_endpoint: str) -> str:
        # Inputs
        access_key = os.getenv("S3_ACCESS_KEY", "minioadmin")
        secret_key = os.getenv("S3_SECRET_KEY", "minioadmin")
        region = os.getenv("S3_REGION", "us-east-1")
        if not access_key or not secret_key:
            raise RuntimeError("Missing S3 access/secret for signing")

        # Time stamps
        now = datetime.utcnow()
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        # Endpoint and path (path-style)
        tu = urlparse(public_endpoint)
        scheme = tu.scheme or "http"
        host = tu.netloc or tu.path
        canonical_uri = "/" + quote(self.bucket) + "/" + quote(key, safe="/")

        # Credential scope
        credential_scope = f"{date_stamp}/{region}/s3/aws4_request"
        credential = f"{access_key}/{credential_scope}"

        # Query params
        q = {
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Credential": credential,
            "X-Amz-Date": amz_date,
            "X-Amz-Expires": str(int(expiry)),
            "X-Amz-SignedHeaders": "host",
        }

        # Canonical request
        canonical_headers = f"host:{host}\n"
        signed_headers = "host"
        payload_hash = "UNSIGNED-PAYLOAD"
        # Build canonical query with alphabetic order
        from urllib.parse import quote as _quote
        def enc(v: str) -> str:
            return _quote(v, safe="-_.~")
        canonical_query = "&".join(
            f"{enc(k)}={enc(q[k])}" for k in sorted(q.keys())
        )
        canonical_request = "\n".join([
            method,
            canonical_uri,
            canonical_query,
            canonical_headers,
            signed_headers,
            payload_hash,
        ])

        # String to sign
        cr_hash = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = "\n".join([
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            cr_hash,
        ])

        # Signing key
        def _hmac(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

        k_date = _hmac(("AWS4" + secret_key).encode("utf-8"), date_stamp)
        k_region = _hmac(k_date, region)
        k_service = _hmac(k_region, "s3")
        k_signing = _hmac(k_service, "aws4_request")
        signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        # Final URL
        q["X-Amz-Signature"] = signature
        query = urlencode(q)
        return f"{scheme}://{host}{canonical_uri}?{query}"

    def copy_object(self, src_key: str, dst_key: str) -> None:
        """Copy object from src_key to dst_key within the same bucket."""
        from minio.commonconfig import CopySource
        copy_source = CopySource(self.bucket, src_key)
        self.client.copy_object(self.bucket, dst_key, copy_source)

    def remove_object(self, key: str) -> None:
        """Remove object from bucket."""
        self.client.remove_object(self.bucket, key)

    def object_exists(self, key: str) -> bool:
        """Check if object exists."""
        from minio.error import S3Error
        try:
            self.client.stat_object(self.bucket, key)
            return True
        except S3Error:
            return False

    # Listing helpers (used by optional sweepers)
    def list_objects(self, prefix: str = "", recursive: bool = True):
        """Yield MinIO objects for the given prefix."""
        return self.client.list_objects(self.bucket, prefix=prefix, recursive=recursive)

    def remove_objects(self, keys: list[str]) -> None:
        if not keys:
            return
        from minio.deleteobjects import DeleteObject
        errors = self.client.remove_objects(self.bucket, [DeleteObject(k) for k in keys])
        for err in errors:
            # best-effort; log if a logger is available
            try:
                print(f"Failed to delete {err.object_name}: {err.message}")
            except Exception:
                pass
