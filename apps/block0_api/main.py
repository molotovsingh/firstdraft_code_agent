from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from typing import List, Optional
import os
import uuid

from shared.db.session import SessionLocal
from shared.db import models
from shared.db.models import ProcessingStatus
from shared.storage.s3 import Storage
from shared.quality.metrics import estimate_credits
from apps.block0_worker.worker import enqueue_process_document
from structlog import get_logger
import redis as redis_lib
from starlette.middleware.base import BaseHTTPMiddleware
import secrets
from prometheus_client import Counter, Histogram, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI(title="FirstDraft Block 0a API", version="0.1.0")
log = get_logger()

# Prometheus metrics (API process only)
registry = CollectorRegistry()
UPLOAD_FILES_TOTAL = Counter(
    "upload_files_total",
    "Number of files uploaded",
    ["tenant_id", "mime"],
    registry=registry,
)
UPLOAD_BYTES_TOTAL = Counter(
    "upload_bytes_total",
    "Total bytes uploaded",
    ["tenant_id"],
    registry=registry,
)
JOBS_QUEUED_TOTAL = Counter(
    "jobs_queued_total",
    "Total jobs enqueued",
    ["tenant_id"],
    registry=registry,
)
UPLOAD_HANDLE_SECONDS = Histogram(
    "upload_handle_seconds",
    "Latency for handling upload endpoint",
    registry=registry,
)


def get_env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in {"1", "true", "yes", "on"}


@app.on_event("startup")
def startup() -> None:
    # Create bucket if not exists
    Storage().ensure_bucket()
    # Ensure DB reachable by opening and closing a session
    db = SessionLocal()
    db.close()


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or secrets.token_hex(8)
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response


app.add_middleware(RequestIDMiddleware)


@app.get("/healthz")
def healthz():
    # DB check
    db_ok = False
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db_ok = True
    except Exception as e:
        log.error("health_db_error", error=str(e))
    finally:
        try:
            db.close()
        except Exception:
            pass

    # Redis check
    redis_ok = False
    try:
        r = redis_lib.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
        redis_ok = bool(r.ping())
    except Exception as e:
        log.error("health_redis_error", error=str(e))

    # S3/MinIO check
    s3_ok = False
    try:
        s = Storage()
        s3_ok = s.client.bucket_exists(s.bucket)
    except Exception as e:
        log.error("health_s3_error", error=str(e))

    ok = db_ok and redis_ok and s3_ok
    return {
        "status": "ok" if ok else "degraded",
        "components": {"db": db_ok, "redis": redis_ok, "s3": s3_ok},
    }


@app.get("/metrics")
def metrics():
    data = generate_latest(registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


@app.post("/v0/documents/upload")
@UPLOAD_HANDLE_SECONDS.time()
async def upload_documents(
    tenant_id: str = Form(...),
    user_id: int = Form(...),
    case_ref: Optional[str] = Form(None),
    quality_mode: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
):
    if quality_mode not in {None, "recommended", "budget"}:
        raise HTTPException(status_code=400, detail="Invalid quality_mode")

    db = SessionLocal()
    storage = Storage()
    out = []
    try:
        # Basic existence checks for tenant/user (best-effort for now)
        tenant = db.get(models.Tenant, uuid.UUID(tenant_id))
        if tenant is None:
            raise HTTPException(status_code=400, detail="Unknown tenant_id")
        user = db.get(models.User, user_id)
        if user is None or str(user.tenant_id) != tenant_id:
            raise HTTPException(status_code=400, detail="Invalid user for tenant")

        total_bytes = 0
        for f in files:
            content = await f.read()
            total_bytes += len(content)
            sha256 = Storage.sha256_hex(content)
            # Create document
            doc = models.Document(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                user_id=user.id,
                case_ref=case_ref,
                orig_filename=f.filename,
                mime=f.content_type or "application/octet-stream",
                bytes_sha256=sha256,
            )
            db.add(doc)
            db.flush()

            # Store original
            orig_key = storage.object_key(tenant_id=str(tenant.id), sha256=sha256, version=1, filename=f.filename)
            storage.put_object(orig_key, content, content_type=doc.mime)

            # Create version with placeholder paths
            ver = models.DocumentVersion(
                document_id=doc.id,
                version=1,
                storage_uri=orig_key,
            )
            db.add(ver)
            db.flush()

            # Create job
            job = models.ProcessingJob(
                id=uuid.uuid4(),
                document_id=doc.id,
                status=ProcessingStatus.queued,
            )
            db.add(job)

            # Credit estimate (stub)
            estimate = estimate_credits(doc.mime, len(content))
            credit = models.Credit(
                tenant_id=tenant.id,
                user_id=user.id,
                delta=-estimate,
                reason="estimate",
                job_id=job.id,
                is_estimate=True,
            )
            db.add(credit)
            db.commit()

            # Enqueue background processing
            enqueue_process_document(str(job.id))
            # Metrics
            UPLOAD_FILES_TOTAL.labels(tenant_id=str(tenant.id), mime=doc.mime).inc()
            JOBS_QUEUED_TOTAL.labels(tenant_id=str(tenant.id)).inc()

            out.append({
                "document_id": str(doc.id),
                "job_id": str(job.id),
                "credit_estimate": estimate,
            })

        # Record bytes once per request
        UPLOAD_BYTES_TOTAL.labels(tenant_id=str(tenant.id)).inc(total_bytes)
        return JSONResponse({"documents": out})
    finally:
        db.close()


@app.get("/v0/jobs/{job_id}")
def get_job(job_id: str):
    db = SessionLocal()
    try:
        job = db.get(models.ProcessingJob, uuid.UUID(job_id))
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return {
            "id": str(job.id),
            "document_id": str(job.document_id),
            "status": job.status.value,
            "steps": job.steps,
            "error": job.error,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        }
    finally:
        db.close()


@app.get("/v0/documents")
def list_documents(tenant_id: str, limit: int = 20):
    """List recent documents for a tenant with their latest version."""
    db = SessionLocal()
    try:
        tenant = db.get(models.Tenant, uuid.UUID(tenant_id))
        if tenant is None:
            raise HTTPException(status_code=400, detail="Unknown tenant_id")
        q = (
            db.query(models.Document)
            .filter(models.Document.tenant_id == tenant.id)
            .order_by(models.Document.created_at.desc())
            .limit(max(1, min(limit, 200)))
        )
        items = []
        for doc in q.all():
            latest = (
                db.query(models.DocumentVersion)
                .filter(models.DocumentVersion.document_id == doc.id)
                .order_by(models.DocumentVersion.version.desc())
                .first()
            )
            items.append({
                "id": str(doc.id),
                "orig_filename": doc.orig_filename,
                "mime": doc.mime,
                "created_at": doc.created_at.isoformat(),
                "latest_version": latest.version if latest else None,
            })
        return {"documents": items}
    finally:
        db.close()


@app.post("/v0/documents/{document_id}/reprocess")
def reprocess_document(document_id: str):
    """Create a new version and job to reprocess the document using the latest pipeline."""
    db = SessionLocal()
    storage = Storage()
    try:
        doc = db.get(models.Document, uuid.UUID(document_id))
        if doc is None:
            raise HTTPException(status_code=404, detail="document not found")
        latest = (
            db.query(models.DocumentVersion)
            .filter(models.DocumentVersion.document_id == doc.id)
            .order_by(models.DocumentVersion.version.desc())
            .first()
        )
        if latest is None:
            raise HTTPException(status_code=409, detail="no prior version; upload first")
        new_version = latest.version + 1
        # New version points to the same original storage URI
        new_ver = models.DocumentVersion(
            document_id=doc.id,
            version=new_version,
            storage_uri=latest.storage_uri,
        )
        db.add(new_ver)
        db.flush()

        job = models.ProcessingJob(
            id=uuid.uuid4(),
            document_id=doc.id,
            status=ProcessingStatus.queued,
        )
        db.add(job)
        db.commit()

        enqueue_process_document(str(job.id))
        return {"document_id": str(doc.id), "new_version": new_version, "job_id": str(job.id)}
    finally:
        db.close()

@app.get("/v0/documents/{document_id}/report.json")
def report_json(document_id: str):
    db = SessionLocal()
    try:
        doc = db.get(models.Document, uuid.UUID(document_id))
        if doc is None:
            raise HTTPException(status_code=404, detail="document not found")
        latest = (
            db.query(models.DocumentVersion)
            .filter(models.DocumentVersion.document_id == doc.id)
            .order_by(models.DocumentVersion.version.desc())
            .first()
        )
        return {
            "document_id": str(doc.id),
            "orig_filename": doc.orig_filename,
            "mime": doc.mime,
            "version": latest.version if latest else None,
            "metrics": latest.metrics if latest else None,
            "warnings": latest.warnings if latest else None,
        }
    finally:
        db.close()


@app.get("/v0/documents/{document_id}/report.md")
def report_md(document_id: str):
    db = SessionLocal()
    try:
        doc = db.get(models.Document, uuid.UUID(document_id))
        if doc is None:
            raise HTTPException(status_code=404, detail="document not found")
        latest = (
            db.query(models.DocumentVersion)
            .filter(models.DocumentVersion.document_id == doc.id)
            .order_by(models.DocumentVersion.version.desc())
            .first()
        )
        lines = [f"# Document Report", f"- Document ID: {doc.id}", f"- Filename: {doc.orig_filename}", f"- MIME: {doc.mime}"]
        if latest:
            lines.append(f"- Version: {latest.version}")
            lines.append("\n## Warnings")
            for w in (latest.warnings or []):
                lines.append(f"- {w}")
            lines.append("\n## Metrics")
            for k, v in (latest.metrics or {}).items():
                lines.append(f"- {k}: {v}")
        return PlainTextResponse("\n".join(lines))
    finally:
        db.close()


@app.get("/v0/documents/{document_id}/processed.json")
def processed_json(document_id: str):
    db = SessionLocal()
    try:
        doc = db.get(models.Document, uuid.UUID(document_id))
        if doc is None:
            raise HTTPException(status_code=404, detail="document not found")
        latest = (
            db.query(models.DocumentVersion)
            .filter(models.DocumentVersion.document_id == doc.id)
            .order_by(models.DocumentVersion.version.desc())
            .first()
        )
        if latest is None:
            raise HTTPException(status_code=404, detail="no versions for document")
        return {
            "schema_version": 1,
            "document_id": str(doc.id),
            "version": latest.version,
            "filename": doc.orig_filename,
            "mime": doc.mime,
            "artifacts": {
                "original_uri": latest.storage_uri,
                "ocr_text_uri": latest.ocr_text_uri,
            },
            "metrics": latest.metrics or {},
            "warnings": latest.warnings or [],
        }
    finally:
        db.close()
