from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Body, Depends
from fastapi.responses import JSONResponse, PlainTextResponse, Response, HTMLResponse
from typing import List, Optional
import os
import uuid
import subprocess

from shared.db.session import SessionLocal, get_db
from sqlalchemy import text as _sql_text, func
from shared.db import models
from shared.db.models import ProcessingStatus
from shared.storage.s3 import Storage
from shared.quality.metrics import estimate_credits
from apps.block0_worker.worker import enqueue_process_document
from structlog import get_logger
from structlog.contextvars import bind_contextvars, clear_contextvars
import time as _t
import redis as redis_lib
from starlette.middleware.base import BaseHTTPMiddleware
import secrets
from prometheus_client import Counter, Histogram, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel, conint, constr
from uuid import UUID
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter

from contextlib import asynccontextmanager


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Skip external IO in test environments
    if not (os.getenv("FIRSTDRAFT_SKIP_STARTUP_CHECKS") or os.getenv("PYTEST_CURRENT_TEST")):
        try:
            Storage().ensure_bucket()
            db = SessionLocal()
            db.close()
        except Exception as e:
            # Don't crash startup; healthz will reflect degraded state
            log = get_logger()
            log.error("lifespan_start_failed", error=str(e))
    yield


app = FastAPI(title="FirstDraft Block 0a API", version="0.1.0", lifespan=_lifespan)
log = get_logger()
templates = Jinja2Templates(directory="apps/block0_api/templates")

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


def _ui_ctx():
    return {
        "enabled": get_env_bool("UI_ENABLED", False),
        "tenant_id": os.getenv("UI_TENANT_ID", "11111111-1111-1111-1111-111111111111"),
        "user_id": int(os.getenv("UI_USER_ID", "1")),
    }


# (Startup handled via lifespan above)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or secrets.token_hex(8)
        try:
            bind_contextvars(request_id=rid, path=str(request.url.path))
            response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            clear_contextvars()


app.add_middleware(RequestIDMiddleware)

# Simple log throttle to avoid spamming identical warnings
_log_throttle: dict[str, float] = {}

def _should_log(key: str, window_sec: float = 60.0) -> bool:
    now = _t.monotonic()
    last = _log_throttle.get(key)
    if last is None or (now - last) >= window_sec:
        _log_throttle[key] = now
        return True
    return False


class HTTPAccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        import time as _t
        start = _t.perf_counter()
        response = await call_next(request)
        try:
            dur_ms = int((_t.perf_counter() - start) * 1000)
            rid = response.headers.get("X-Request-ID") or request.headers.get("X-Request-ID")
            length = response.headers.get("content-length") or response.headers.get("Content-Length")
            log.info(
                "http_access",
                method=request.method,
                path=str(request.url.path),
                status_code=response.status_code,
                duration_ms=dur_ms,
                content_length=int(length) if str(length).isdigit() else None,
                request_id=rid,
            )
        except Exception:
            pass
        return response


app.add_middleware(HTTPAccessLogMiddleware)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only enforce when enabled; skip for health, metrics, UI and version
        if os.getenv('API_AUTH_ENABLED', '0').lower() in {'1','true','yes','on'}:
            path = request.url.path
            if path.startswith('/v0/') and not path.startswith('/v0/version'):
                key = request.headers.get('X-API-Key')
                want = os.getenv('API_KEY')
                if not want or key != want:
                    return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)


app.add_middleware(APIKeyAuthMiddleware)


@app.get("/healthz")
def healthz():
    # DB check
    db_ok = False
    try:
        db = SessionLocal()
        db.execute(_sql_text("SELECT 1"))
        db_ok = True
    except Exception as e:
        if _should_log("db_error"):
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
        if _should_log("redis_error"):
            log.error("health_redis_error", error=str(e))

    # S3/MinIO check
    s3_ok = False
    try:
        s = Storage()
        s3_ok = s.client.bucket_exists(s.bucket)
    except Exception as e:
        if _should_log("s3_error"):
            log.error("health_s3_error", error=str(e))

    ok = db_ok and redis_ok and s3_ok
    payload = {
        "status": "ok" if ok else "degraded",
        "components": {"db": db_ok, "redis": redis_ok, "s3": s3_ok},
    }
    return JSONResponse(payload, status_code=200 if ok else 503)


@app.get("/metrics")
def metrics():
    data = generate_latest(registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


# -----------------
# Minimal Dev UI (/ui)
# -----------------
if get_env_bool("UI_ENABLED", False):
    ui = APIRouter()

    @ui.get("/", response_class=HTMLResponse)
    def ui_home(request: Request):
        ctx = _ui_ctx()
        return templates.TemplateResponse(request, "home.html", ctx)

    @ui.get("/docs", response_class=HTMLResponse)
    def ui_docs(request: Request, db=Depends(get_db)):
        ctx = _ui_ctx()
        try:
            tenant = db.get(models.Tenant, UUID(ctx["tenant_id"]))
        except Exception:
            tenant = None
        docs = []
        if tenant:
            q = (
                db.query(models.Document)
                .filter(models.Document.tenant_id == tenant.id)
                .order_by(models.Document.created_at.desc())
                .limit(20)
            )
            for doc in q.all():
                latest = (
                    db.query(models.DocumentVersion)
                    .filter(models.DocumentVersion.document_id == doc.id)
                    .order_by(models.DocumentVersion.version.desc())
                    .first()
                )
                docs.append({
                    "id": str(doc.id),
                    "filename": doc.orig_filename,
                    "mime": doc.mime,
                    "version": latest.version if latest else None,
                })
        return templates.TemplateResponse(request, "docs.html", {**ctx, "docs": docs})

    @ui.get("/docs/{doc_id}", response_class=HTMLResponse)
    def ui_doc_detail(doc_id: str, request: Request, db=Depends(get_db)):
        ctx = _ui_ctx()
        doc = db.get(models.Document, UUID(doc_id))
        if not doc:
            raise HTTPException(status_code=404, detail="not found")
        latest = (
            db.query(models.DocumentVersion)
            .filter(models.DocumentVersion.document_id == doc.id)
            .order_by(models.DocumentVersion.version.desc())
            .first()
        )
        report_md = None
        download_url = None
        if latest:
            # simple Markdown-ish text; reuse report.md content
            lines = [f"# {doc.orig_filename}", f"MIME: {doc.mime}"]
            metrics_map = getattr(latest, "metrics", None) or {}
            for k, v in metrics_map.items():
                lines.append(f"- {k}: {v}")
            report_md = "\n".join(lines)
            if latest.storage_uri:
                from urllib.parse import quote
                download_url = f"/v0/uploads/presign_download?key={quote(latest.storage_uri, safe='')}"
        return templates.TemplateResponse(request, "doc_detail.html", {
            **ctx,
            "doc": doc,
            "doc_id": str(doc.id),
            "version": latest.version if latest else None,
            "report_md": report_md,
            "download_url": download_url,
        })

    @ui.get("/upload", response_class=HTMLResponse)
    def ui_upload(request: Request):
        ctx = _ui_ctx()
        return templates.TemplateResponse(request, "upload.html", ctx)

    @ui.get("/credits", response_class=HTMLResponse)
    def ui_credits(request: Request, db=Depends(get_db)):
        ctx = _ui_ctx()
        bal = {"balance": 0, "count": 0}
        ledger = []
        try:
            tenant = db.get(models.Tenant, UUID(ctx["tenant_id"]))
            if tenant:
                entries = (
                    db.query(models.Credit)
                    .filter(models.Credit.tenant_id == tenant.id)
                    .order_by(models.Credit.created_at.desc())
                    .limit(25)
                    .all()
                )
                bal["balance"] = sum(e.delta for e in entries)
                bal["count"] = len(entries)
                ledger = [
                    {
                        "id": e.id,
                        "user_id": e.user_id,
                        "delta": e.delta,
                        "reason": e.reason,
                        "created_at": e.created_at.isoformat(),
                    }
                    for e in entries
                ]
        except Exception:
            pass
        return templates.TemplateResponse(request, "credits.html", {**ctx, "bal": bal, "ledger": ledger})

    app.include_router(ui, prefix="/ui", tags=["ui"])


# Lightweight version surface for ops/debugging
@app.get("/v0/version")
def version_info():
    git = os.getenv("GIT_SHA")
    if not git:
        try:
            r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=1)
            if r.returncode == 0:
                git = (r.stdout or "").strip() or None
        except Exception:
            git = None
    return {"version": app.version, "git": git}


class PresignRequest(BaseModel):
    tenant_id: UUID
    user_id: conint(ge=1)
    filename: constr(min_length=1)
    mime: Optional[constr(min_length=1)] = None


@app.post("/v0/uploads/presign")
def presign_upload(payload: PresignRequest, request: Request):
    """
    Create a presigned PUT URL for direct upload to S3/MinIO.
    No DB writes here. Returns object_key and URL.
    """
    tenant_id = str(payload.tenant_id)
    # user_id is accepted but unused here; model validation enforces shape
    filename = payload.filename
    mime = payload.mime or "application/octet-stream"

    # Random sha-like path id and short suffix to avoid collisions
    rand_sha = secrets.token_hex(32)  # 64 hex chars
    suffix = secrets.token_hex(4)     # 8 hex chars
    object_key = f"{tenant_id}/{rand_sha[:2]}/{rand_sha}/v1/orig/{filename}.{suffix}"

    storage = Storage()
    # Check X-Internal-Network header to decide presign method
    if request.headers.get("X-Internal-Network"):
        url = storage.presign_put_url_internal(object_key, expiry=3600)
    else:
        url = storage.presign_put_url(object_key, expiry=3600)
    log.info("presign_created", tenant_id=tenant_id, user_id=int(payload.user_id), object_key=object_key)
    return JSONResponse({"object_key": object_key, "url": url, "expiry": 3600, "mime": mime})


@app.get("/v0/uploads/presign_download")
def presign_download(key: str, expiry: int = 600):
    """
    Generate a temporary presigned GET URL for QA download checks.
    """
    if not key:
        raise HTTPException(status_code=400, detail="key is required")
    storage = Storage()
    expiry = max(1, min(expiry, 24 * 3600))
    url = storage.presign_get_url(key, expiry=expiry)
    log.info("presign_download", key=key, expiry=expiry)
    return {"url": url, "expiry": expiry}

@app.post("/v0/documents/upload")
@UPLOAD_HANDLE_SECONDS.time()
async def upload_documents(
    tenant_id: str = Form(...),
    user_id: int = Form(...),
    case_ref: Optional[str] = Form(None),
    quality_mode: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
    db=Depends(get_db),
):
    if quality_mode not in {None, "recommended", "budget"}:
        raise HTTPException(status_code=400, detail="Invalid quality_mode")

    storage = Storage()
    out = []
    # Basic existence checks for tenant/user (best-effort for now)
    try:
        tenant = db.get(models.Tenant, uuid.UUID(tenant_id))
        if tenant is None:
            raise HTTPException(status_code=400, detail="Unknown tenant_id")
        user = db.get(models.User, user_id)
        if user is None or str(user.tenant_id) != tenant_id:
            raise HTTPException(status_code=400, detail="Invalid user for tenant")

        total_bytes = 0
        for f in files:
            # Stream to temp file and compute sha256 incrementally to avoid large memory usage
            mime = f.content_type or "application/octet-stream"
            hasher = hashlib.sha256()
            size_bytes = 0
            with tempfile.NamedTemporaryFile(delete=False) as tf:
                try:
                    while True:
                        chunk = await f.read(1024 * 1024)
                        if not chunk:
                            break
                        size_bytes += len(chunk)
                        hasher.update(chunk)
                        tf.write(chunk)
                    temp_path = tf.name
                finally:
                    tf.flush()
            total_bytes += size_bytes
            sha256 = hasher.hexdigest()
            # Create document
            doc = models.Document(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                user_id=user.id,
                case_ref=case_ref,
                orig_filename=f.filename,
                mime=mime,
                bytes_sha256=sha256,
            )
            db.add(doc)
            db.flush()

            # Store original
            orig_key = storage.object_key(tenant_id=str(tenant.id), sha256=sha256, version=1, filename=f.filename)
            with open(temp_path, "rb") as rf:
                storage.put_file(orig_key, rf, length=size_bytes, content_type=mime)

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

            # Credit estimate (stub) based on size
            estimate = estimate_credits(mime, size_bytes)
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
            log.info("job_enqueued", job_id=str(job.id), document_id=str(doc.id), tenant_id=str(tenant.id), user_id=user.id)
            # Metrics
            UPLOAD_FILES_TOTAL.labels(tenant_id=str(tenant.id), mime=doc.mime).inc()
            JOBS_QUEUED_TOTAL.labels(tenant_id=str(tenant.id)).inc()

            # Compute current tenant balance after estimate
            bal = sum(e.delta for e in db.query(models.Credit).filter(models.Credit.tenant_id == tenant.id).all())

            out.append({
                "document_id": str(doc.id),
                "job_id": str(job.id),
                "credit_estimate": estimate,
                "tenant_balance": int(bal),
            })
            # Cleanup temp file
            try:
                os.unlink(temp_path)
            except Exception:
                pass
        # Record bytes once per request
        UPLOAD_BYTES_TOTAL.labels(tenant_id=str(tenant.id)).inc(total_bytes)
        log.info("upload_completed", tenant_id=str(tenant.id), files=len(files), total_bytes=total_bytes)
        return JSONResponse({"documents": out})
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        log.error("upload_documents_error", error=str(e))
        raise HTTPException(status_code=500, detail="internal error")


@app.get("/v0/jobs/{job_id}")
def get_job(job_id: str, db=Depends(get_db)):
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


@app.get("/v0/documents")
def list_documents(tenant_id: str, limit: int = 20, db=Depends(get_db)):
    """List recent documents for a tenant with their latest version."""
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


@app.post("/v0/documents/{document_id}/reprocess")
def reprocess_document(document_id: str, db=Depends(get_db)):
    """Create a new version and job to reprocess the document using the latest pipeline."""
    storage = Storage()
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
    db.flush()  # ensure job row exists before FK references (credits)
    db.commit()

    enqueue_process_document(str(job.id))
    return {"document_id": str(doc.id), "new_version": new_version, "job_id": str(job.id)}

@app.get("/v0/documents/{document_id}/report.json")
def report_json(document_id: str, db=Depends(get_db)):
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


@app.get("/v0/documents/{document_id}/report.md")
def report_md(document_id: str, db=Depends(get_db)):
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


@app.get("/v0/documents/{document_id}/processed.json")
def processed_json(document_id: str, db=Depends(get_db)):
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


# --- Credits APIs (read-only surfaces for Block 0) ---

@app.get("/v0/credits/balance")
def credits_balance(tenant_id: str, user_id: Optional[int] = None, db=Depends(get_db)):
    """
    Return summed credits for a tenant (and optionally a specific user).
    Positive deltas are refunds/top-ups; negative deltas are spends.
    """
    try:
        tenant = db.get(models.Tenant, uuid.UUID(tenant_id))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid tenant_id")
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant not found")

    # Prefer DB aggregation; fallback to in-Python sum if unavailable (e.g., unit tests with dummy DB)
    try:
        q = db.query(func.coalesce(func.sum(models.Credit.delta), 0), func.count(models.Credit.id)) \
              .filter(models.Credit.tenant_id == tenant.id)
        if user_id is not None:
            q = q.filter(models.Credit.user_id == user_id)
        total, count = q.one()
        return {"tenant_id": str(tenant.id), "user_id": user_id, "balance": int(total or 0), "count": int(count or 0)}
    except Exception:
        q = db.query(models.Credit).filter(models.Credit.tenant_id == tenant.id)
        if user_id is not None:
            q = q.filter(models.Credit.user_id == user_id)
        entries = q.all()
        balance = sum(getattr(e, 'delta', 0) for e in entries)
        return {"tenant_id": str(tenant.id), "user_id": user_id, "balance": int(balance), "count": len(entries)}


@app.get("/v0/credits/ledger")
def credits_ledger(tenant_id: str, limit: int = 50, db=Depends(get_db)):
    """Return recent credit ledger rows for a tenant (descending by created_at)."""
    try:
        tenant = db.get(models.Tenant, uuid.UUID(tenant_id))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid tenant_id")
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant not found")
    q = (
        db.query(models.Credit)
        .filter(models.Credit.tenant_id == tenant.id)
        .order_by(models.Credit.created_at.desc())
        .limit(max(1, min(200, limit)))
    )
    rows = []
    for e in q.all():
        rows.append({
            "id": e.id,
            "user_id": e.user_id,
            "delta": e.delta,
            "reason": e.reason,
            "job_id": str(e.job_id) if e.job_id else None,
            "is_estimate": bool(e.is_estimate),
            "created_at": e.created_at.isoformat(),
        })
    return {"tenant_id": str(tenant.id), "items": rows}


@app.get("/v0/credits/summary")
def credits_summary(tenant_id: str, db=Depends(get_db)):
    """Return aggregate view for a tenant's credits."""
    try:
        tenant = db.get(models.Tenant, uuid.UUID(tenant_id))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid tenant_id")
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant not found")

    try:
        # Total
        total = db.query(func.coalesce(func.sum(models.Credit.delta), 0)) \
                 .filter(models.Credit.tenant_id == tenant.id).scalar()
        # By reason
        rows = db.query(models.Credit.reason, func.coalesce(func.sum(models.Credit.delta), 0)) \
                 .filter(models.Credit.tenant_id == tenant.id) \
                 .group_by(models.Credit.reason).all()
        by_reason = {r: int(v or 0) for r, v in rows}
        # Pending estimates
        pe_count, pe_sum = db.query(func.count(models.Credit.id), func.coalesce(func.sum(models.Credit.delta), 0)) \
                             .filter(models.Credit.tenant_id == tenant.id, models.Credit.is_estimate == True).one()
        return {
            "tenant_id": str(tenant.id),
            "total": int(total or 0),
            "by_reason": by_reason,
            "pending_estimates": {"count": int(pe_count or 0), "sum": int(pe_sum or 0)},
        }
    except Exception:
        entries = db.query(models.Credit).filter(models.Credit.tenant_id == tenant.id).all()
        total = sum(getattr(e, 'delta', 0) for e in entries)
        by_reason = {}
        pending_estimates = {"count": 0, "sum": 0}
        for e in entries:
            reason = getattr(e, 'reason', 'unknown')
            by_reason[reason] = int(by_reason.get(reason, 0) + getattr(e, 'delta', 0))
            if getattr(e, 'is_estimate', False):
                pending_estimates["count"] += 1
                pending_estimates["sum"] += getattr(e, 'delta', 0)
        return {
            "tenant_id": str(tenant.id),
            "total": int(total),
            "by_reason": by_reason,
            "pending_estimates": {"count": int(pending_estimates["count"]), "sum": int(pending_estimates["sum"])},
        }


class FinalizeRequest(BaseModel):
    tenant_id: UUID
    user_id: conint(ge=1)
    key: constr(min_length=1)
    filename: Optional[constr(min_length=1)] = None
    mime: Optional[constr(min_length=1)] = None


@app.post("/v0/uploads/finalize")
def finalize_upload(payload: FinalizeRequest, db=Depends(get_db)):
    """
    Finalize a presigned upload by moving it to permanent storage and creating DB records.
    """
    tenant_id = str(payload.tenant_id)
    user_id = int(payload.user_id)
    key = payload.key
    filename = payload.filename
    mime = payload.mime or "application/octet-stream"

    storage = Storage()
    # Validate tenant and user
    tenant = db.get(models.Tenant, uuid.UUID(tenant_id))
    if tenant is None:
        raise HTTPException(status_code=400, detail="Unknown tenant_id")
    user = db.get(models.User, user_id)
    if user is None or str(user.tenant_id) != tenant_id:
        raise HTTPException(status_code=400, detail="Invalid user for tenant")

    # Fetch object bytes from staging location
    try:
        content = storage.get_object_bytes(key)
    except Exception as e:
        log.error("finalize_fetch_error", key=key, error=str(e))
        raise HTTPException(status_code=404, detail="Object not found at key")

    # Compute SHA256
    sha256 = Storage.sha256_hex(content)

    # Derive final storage key
    if not filename:
        import os as _os
        filename = _os.path.basename(key)
        # If a random 8-hex suffix exists at the end, strip it (e.g., file.pdf.ab12cd34)
        parts = filename.split(".")
        if len(parts) >= 3 and len(parts[-1]) == 8 and all(c in "0123456789abcdef" for c in parts[-1]):
            filename = ".".join(parts[:-1])

    final_key = storage.object_key(tenant_id=str(tenant.id), sha256=sha256, version=1, filename=filename)

    # Idempotency guard: if a document with same SHA already exists for this tenant, reuse it
    existing_doc = (
        db.query(models.Document)
        .filter(models.Document.tenant_id == tenant.id, models.Document.bytes_sha256 == sha256)
        .first()
    )
    if existing_doc:
        doc = existing_doc
        # Prefer existing version's storage_uri if present; avoid duplicate copy
        existing_ver = (
            db.query(models.DocumentVersion)
            .filter(models.DocumentVersion.document_id == doc.id)
            .order_by(models.DocumentVersion.version.desc())
            .first()
        )
        if not existing_ver:
            # Create an initial version pointing to final_key (copy if missing)
            if not storage.object_exists(final_key):
                storage.copy_object(key, final_key)
            ver = models.DocumentVersion(document_id=doc.id, version=1, storage_uri=final_key)
            db.add(ver)
            db.flush()
    else:
        # New document path: copy from staging to final and create records
        if not storage.object_exists(final_key):
            storage.copy_object(key, final_key)
        doc = models.Document(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            user_id=user.id,
            case_ref=None,
            orig_filename=filename,
            mime=mime,
            bytes_sha256=sha256,
        )
        db.add(doc)
        db.flush()
        ver = models.DocumentVersion(
            document_id=doc.id,
            version=1,
            storage_uri=final_key,
        )
        db.add(ver)
        db.flush()

    # Optional cleanup of staging object
    if os.getenv("DELETE_STAGING_ON_FINALIZE", "false").lower() in {"1", "true", "yes", "on"}:
        try:
            storage.remove_object(key)
        except Exception:
            log.error("staging_delete_failed", key=key)

    # Create ProcessingJob
    job = models.ProcessingJob(
        id=uuid.uuid4(),
        document_id=doc.id,
        status=ProcessingStatus.queued,
    )
    db.add(job)
    db.flush()  # ensure job id persisted before creating credit

    # Estimate credits
    estimate = estimate_credits(mime, len(content))
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

    # Enqueue for processing
    enqueue_process_document(str(job.id))
    log.info("job_enqueued", job_id=str(job.id), document_id=str(doc.id), tenant_id=str(tenant.id), user_id=user.id)

    # Compute fresh balance including just-inserted estimate
    bal = sum(e.delta for e in db.query(models.Credit).filter(models.Credit.tenant_id == tenant.id).all())
    log.info("finalize_ok", document_id=str(doc.id), job_id=str(job.id), version=1)
    return JSONResponse({
        "document_id": str(doc.id),
        "job_id": str(job.id),
        "version": 1,
        "storage_uri": final_key,
        "credit_estimate": estimate,
        "tenant_balance": int(bal),
    })
