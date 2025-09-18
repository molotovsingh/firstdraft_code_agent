import os
import uuid
from datetime import datetime
import time
from celery import Celery
from structlog import get_logger
from structlog.contextvars import bind_contextvars, clear_contextvars
from prometheus_client import Counter, Histogram, make_wsgi_app
from wsgiref.simple_server import make_server
from threading import Thread
try:
    from shared.config.settings import settings as _settings
except Exception:
    _settings = None

from shared.db.session import SessionLocal
from shared.db import models
from shared.db.models import ProcessingStatus
from shared.quality.metrics import compute_metrics_and_warnings, estimate_actual_credits
from shared.storage.s3 import Storage
from PIL import Image
import io
import pytesseract
import tempfile
import subprocess
from pytesseract import Output
from shared.quality.normalize import deskew_image_bytes
from shared.ocr.adapters.tesseract import TesseractAdapter
from shared.ocr.adapters.ocrmypdf import OCRmyPDFAdapter
from shared.ocr.adapters.base import OCRResult


def _ocr_image_bytes(original_bytes: bytes, lang: str):
    warnings: list[str] = []
    metrics: dict = {}
    used_bytes = original_bytes
    rotated_bytes, applied_deg = deskew_image_bytes(original_bytes)
    if abs(applied_deg) > 0.0:
        warnings.append(f"Auto-deskew applied (~{applied_deg:.1f}°)")
        used_bytes = rotated_bytes
    pil_img = Image.open(io.BytesIO(used_bytes))
    text = pytesseract.image_to_string(pil_img, lang=lang) or ""
    # Confidence (average over valid words)
    try:
        data = pytesseract.image_to_data(pil_img, lang=lang, output_type=Output.DICT)
        confs = [int(c) for c in data.get('conf', []) if c not in ("-1", "-")]
        conf_vals = [c for c in confs if c >= 0]
        if conf_vals:
            avg_conf = sum(conf_vals) / len(conf_vals)
            metrics["ocr_confidence_avg"] = round(float(avg_conf) / 100.0, 3)
    except Exception:
        pass
    return text, used_bytes, metrics, warnings


def _ocr_pdf_bytes(original_bytes: bytes, lang: str):
    warnings: list[str] = []
    text = ""
    with tempfile.TemporaryDirectory() as td:
        in_pdf = f"{td}/in.pdf"
        out_pdf = f"{td}/out.pdf"
        sidecar = f"{td}/out.txt"
        with open(in_pdf, "wb") as f:
            f.write(original_bytes)
        cmd = [
            "ocrmypdf",
            "--language", lang,
            "--sidecar", sidecar,
            "--skip-text",
            in_pdf,
            out_pdf,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=180)
            try:
                with open(sidecar, "r", encoding="utf-8", errors="ignore") as sf:
                    text = sf.read()
            except FileNotFoundError:
                warnings.append("PDF OCR produced no sidecar text")
        except subprocess.CalledProcessError as e:
            warnings.append(f"PDF OCR failed (exit code {e.returncode})")
            # Throttle noisy logs
            if _should_log("ocrmypdf_failed"):
                try:
                    err = e.stderr.decode(errors="ignore") if e.stderr else ""
                except Exception:
                    err = ""
                log.error("ocrmypdf_failed",
                         returncode=e.returncode,
                         stderr=err[:500],  # Truncate very long error messages
                         language=lang,
                         timeout_configured=180)
        except subprocess.TimeoutExpired as e:
            warnings.append(f"PDF OCR timed out after {e.timeout}s")
            if _should_log("ocrmypdf_timeout"):
                log.error("ocrmypdf_timeout",
                         timeout_seconds=e.timeout,
                         language=lang,
                         cmd=" ".join(e.cmd[:3]) if e.cmd else "unknown")
    return text, warnings

log = get_logger()

# Simple log throttle to avoid spamming identical warnings
_log_throttle: dict[str, float] = {}

def _should_log(key: str, window_sec: float = 60.0) -> bool:
    import time as _t
    now = _t.monotonic()
    last = _log_throttle.get(key)
    if last is None or (now - last) >= window_sec:
        _log_throttle[key] = now
        return True
    return False

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://redis:6379/0"))
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

celery_app = Celery("block0")
celery_app.conf.broker_url = CELERY_BROKER_URL
celery_app.conf.result_backend = CELERY_RESULT_BACKEND

# Optional Prometheus metrics server (disabled unless METRICS_PORT is set)
def _start_metrics_and_health_http(port: int):
    """Start a lightweight HTTP server exposing /metrics and /health on given port."""
    metrics_app = make_wsgi_app()

    def app(environ, start_response):
        path = environ.get('PATH_INFO') or '/'
        if path == '/metrics':
            return metrics_app(environ, start_response)
        if path == '/health':
            start_response('200 OK', [('Content-Type', 'text/plain; charset=utf-8')])
            return [b'ok']
        start_response('404 Not Found', [('Content-Type', 'text/plain; charset=utf-8')])
        return [b'not found']

    def _serve():
        with make_server('0.0.0.0', port, app) as httpd:
            log.info("worker_http_server_started", port=httpd.server_port)
            httpd.serve_forever()

    th = Thread(target=_serve, daemon=True)
    th.start()

try:
    _metrics_port = os.getenv("METRICS_PORT") or (str(_settings.metrics_port) if _settings and _settings.metrics_port else None)
    if _metrics_port:
        _start_metrics_and_health_http(int(_metrics_port))
except Exception:
    log.exception("worker_metrics_server_failed")

# Worker metrics
OCR_DURATION_SECONDS = Histogram(
    "worker_ocr_duration_seconds",
    "Time spent performing OCR per document",
    labelnames=["mime"],
)
JOBS_PROCESSED_TOTAL = Counter(
    "worker_jobs_processed_total",
    "Jobs processed by worker",
    labelnames=["status"],
)
PAGES_PROCESSED_TOTAL = Counter(
    "worker_pages_processed_total",
    "Pages processed (approx; images count as 1)",
    labelnames=["mime"],
)


def enqueue_process_document(job_id: str) -> None:
    process_document.delay(job_id)


@celery_app.task(name="process_document")
def process_document(job_id: str):
    db = SessionLocal()
    try:
        job = db.get(models.ProcessingJob, uuid.UUID(job_id))
        if job is None:
            log.error("job_not_found", job_id=job_id)
            return
        bind_contextvars(job_id=str(job.id))
        job.status = ProcessingStatus.running
        job.started_at = datetime.utcnow()
        job.steps = ["normalize", "ocr", "quality", "finalize"]
        db.commit()

        # Load document/version
        ver = (
            db.query(models.DocumentVersion)
            .filter(models.DocumentVersion.document_id == job.document_id)
            .order_by(models.DocumentVersion.version.desc())
            .first()
        )
        if not ver:
            raise RuntimeError("document_version_missing")

        # Minimal OCR implementation: images only (ENG). PDFs get a placeholder warning.
        doc = db.get(models.Document, job.document_id)
        if doc:
            bind_contextvars(document_id=str(doc.id), tenant_id=str(doc.tenant_id))
        storage = Storage()
        ocr_text = ""
        metrics = {}
        warnings = []

        try:
            original_bytes = storage.get_object_bytes(ver.storage_uri)
            t0 = time.perf_counter()
            # Determine provider and languages
            provider = (os.getenv("OCR_PROVIDER", "tesseract") or "tesseract").strip().lower()
            lang_cfg = getattr(_settings, "ocr_lang", None) or os.getenv("OCR_LANG", "eng")
            # Accept comma or plus separated lists
            languages = [p.strip() for p in lang_cfg.replace("+", ",").split(",") if p.strip()]

            quality_mode = (os.getenv("QUALITY_MODE", "recommended") or "recommended").strip().lower()
            if provider == "stub":
                warnings = (warnings or []) + ["OCR disabled (stub provider)"]
                ocr_text = ""
            else:
                if doc.mime and doc.mime.lower().startswith("image/"):
                    # Deskew for recommended mode only
                    if quality_mode != "budget":
                        rotated_bytes, applied_deg = deskew_image_bytes(original_bytes)
                        if abs(applied_deg) > 0.0:
                            warnings.append(f"Auto-deskew applied (~{applied_deg:.1f}°)")
                            original_bytes = rotated_bytes
                    # Budget mode: restrict to first language for speed
                    if quality_mode == "budget" and languages:
                        languages = [languages[0]]
                    # Optional speed knobs via settings/env
                    oem_env = os.getenv("OCR_OEM")
                    psm_env = os.getenv("OCR_PSM")
                    oem = int(oem_env) if oem_env and oem_env.isdigit() else getattr(_settings, "ocr_oem", None)
                    psm = int(psm_env) if psm_env and psm_env.isdigit() else getattr(_settings, "ocr_psm", None)
                    extra = os.getenv("OCR_TESSERACT_EXTRA") or getattr(_settings, "ocr_tesseract_extra", None)
                    # If budget mode and no explicit values, choose lighter defaults
                    if quality_mode == "budget":
                        oem = oem if oem is not None else 1  # LSTM only
                        psm = psm if psm is not None else 6  # Assume a single uniform block of text
                    t = TesseractAdapter(oem=oem, psm=psm, extra_config=extra)
                    res: OCRResult = t.process(original_bytes, doc.mime or "image/unknown", languages=languages)
                    ocr_text = res.combined_text
                    # Confidence metric if available will be recomputed by metrics module as well
                elif (doc.mime or "").lower() == "application/pdf":
                    # Budget mode: restrict to first language and shorter timeout
                    if quality_mode == "budget" and languages:
                        languages = [languages[0]]
                    # Optional extra flags for ocrmypdf
                    extra_pdf: list[str] = []
                    # Always consider OCR_OCRMYPDF_EXTRA
                    extra_env = os.getenv("OCR_OCRMYPDF_EXTRA") or getattr(_settings, "ocr_ocrmypdf_extra", None)
                    if extra_env:
                        try:
                            extra_pdf += [p for p in extra_env.split(' ') if p]
                        except Exception:
                            pass
                    # Add recommended-only extras if not in budget mode
                    if quality_mode != "budget":
                        extra_reco = os.getenv("OCR_OCRMYPDF_RECOMMENDED") or getattr(_settings, "ocr_ocrmypdf_recommended", None)
                        if extra_reco:
                            try:
                                extra_pdf += [p for p in extra_reco.split(' ') if p]
                            except Exception:
                                pass
                    p = OCRmyPDFAdapter(
                        timeout_seconds=(90 if quality_mode == "budget" else 180),
                        fast_mode=(quality_mode == "budget"),
                        tesseract_timeout=(60 if quality_mode == "budget" else None),
                        extra_args=extra_pdf,
                    )
                    res: OCRResult = p.process(original_bytes, "application/pdf", languages=languages)
                    ocr_text = res.combined_text
                else:
                    warnings = (warnings or []) + [f"Unsupported MIME for OCR at this stage: {doc.mime}"]
                    ocr_text = ""
            # Observe duration
            OCR_DURATION_SECONDS.labels(mime=(doc.mime or "unknown").lower()).observe(time.perf_counter() - t0)
        except Exception as e:
            error_type = type(e).__name__
            warnings = (warnings or []) + [f"OCR processing failed ({error_type}): {str(e)[:100]}"]
            if _should_log("ocr_failed"):
                log.exception("ocr_failed",
                             job_id=job_id,
                             document_id=str(doc.id) if doc else "unknown",
                             mime_type=doc.mime if doc else "unknown",
                             file_size_bytes=len(original_bytes) if 'original_bytes' in locals() else 0,
                             provider=provider,
                             quality_mode=quality_mode,
                             languages=languages,
                             error_type=error_type)

        # Store OCR text as object for consistency
        tenant_id = str(doc.tenant_id)
        sha = doc.bytes_sha256
        ocr_key = f"{tenant_id}/{sha[:2]}/{sha}/v{ver.version}/ocr/combined.txt"
        storage.put_object(ocr_key, ocr_text.encode("utf-8"), content_type="text/plain; charset=utf-8")

        # Update version
        # For images, set page_count=1 if not present
        if doc.mime and doc.mime.lower().startswith("image/"):
            metrics = metrics or {}
            metrics.setdefault("page_count", 1)
        # Compute metrics & warnings (image blur/skew, language, density)
        m2, w2 = compute_metrics_and_warnings(doc.mime, original_bytes, ocr_text)
        metrics.update(m2 or {})
        warnings = (warnings or []) + (w2 or [])
        ver.metrics = metrics
        ver.warnings = warnings
        ver.ocr_text_uri = ocr_key
        db.commit()

        # Finalize credits: compensate estimate and record actual
        estimate_credit = (
            db.query(models.Credit)
            .filter(models.Credit.job_id == job.id, models.Credit.is_estimate == True)
            .first()
        )
        if estimate_credit:
            try:
                # Compute a simple actual cost for now (same heuristic as estimate)
                # Inputs available: mime, bytes length (from storage), metrics (page_count, density)
                actual = estimate_actual_credits(doc.mime or "application/octet-stream", len(original_bytes or b""), metrics)

                # 1) Reverse the earlier estimate (credit back)
                reversal = models.Credit(
                    tenant_id=estimate_credit.tenant_id,
                    user_id=estimate_credit.user_id,
                    delta=+abs(estimate_credit.delta),
                    reason="estimate_reversal",
                    job_id=job.id,
                    is_estimate=False,
                )
                db.add(reversal)

                # 2) Charge actual
                actual_row = models.Credit(
                    tenant_id=estimate_credit.tenant_id,
                    user_id=estimate_credit.user_id,
                    delta=-abs(int(actual)),
                    reason="actual",
                    job_id=job.id,
                    is_estimate=False,
                )
                db.add(actual_row)

                # Mark the original estimate row closed
                estimate_credit.is_estimate = False
                db.commit()
            except Exception:
                log.exception("credit_finalization_failed", job_id=job_id)

        job.status = ProcessingStatus.succeeded
        job.finished_at = datetime.utcnow()
        db.commit()
        # Metrics: jobs + pages
        JOBS_PROCESSED_TOTAL.labels(status="succeeded").inc()
        page_count = metrics.get("page_count") if isinstance(metrics, dict) else None
        if isinstance(page_count, int) and page_count > 0:
            PAGES_PROCESSED_TOTAL.labels(mime=(doc.mime or "unknown").lower()).inc(page_count)
        log.info("job_succeeded", job_id=job_id)
    except Exception as e:
        if _should_log("job_failed"):
            doc_info = {}
            if 'doc' in locals() and doc:
                doc_info = {
                    "document_id": str(doc.id),
                    "tenant_id": str(doc.tenant_id),
                    "mime_type": doc.mime,
                    "filename": doc.orig_filename,
                }
            log.exception("job_failed",
                         job_id=job_id,
                         error_type=type(e).__name__,
                         **doc_info)
        job = db.get(models.ProcessingJob, uuid.UUID(job_id)) if 'job' in locals() else None
        if job:
            job.status = ProcessingStatus.failed
            job.error = str(e)
            job.finished_at = datetime.utcnow()
            db.commit()
        JOBS_PROCESSED_TOTAL.labels(status="failed").inc()
        # Compensate estimated credits on failure (refund)
        try:
            if job:
                estimate_credit = (
                    db.query(models.Credit)
                    .filter(models.Credit.job_id == job.id, models.Credit.is_estimate == True)
                    .first()
                )
                if estimate_credit:
                    refund = models.Credit(
                        tenant_id=estimate_credit.tenant_id,
                        user_id=estimate_credit.user_id,
                        delta=+abs(estimate_credit.delta),
                        reason="refund_failure",
                        job_id=job.id,
                        is_estimate=False,
                    )
                    db.add(refund)
                    estimate_credit.is_estimate = False
                    db.commit()
        except Exception:
            if _should_log("credit_refund_failed"):
                log.exception("credit_refund_failed",
                             job_id=job_id,
                             tenant_id=str(estimate_credit.tenant_id) if 'estimate_credit' in locals() and estimate_credit else "unknown")
    finally:
        try:
            clear_contextvars()
        except Exception:
            pass
        db.close()
