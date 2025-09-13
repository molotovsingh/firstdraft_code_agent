from pydantic import BaseSettings, AnyUrl
import logging
import structlog


class Settings(BaseSettings):
    app_env: str = "dev"
    log_level: str = "INFO"

    # Database
    database_url: str

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    # S3/MinIO
    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_region: str = "us-east-1"
    s3_bucket: str = "firstdraft-dev"
    s3_secure: bool = False

    # Features
    ocr_lang: str = "eng+hin"
    quality_mode: str = "recommended"
    metrics_port: int | None = None
    # Optional OCR tuning
    ocr_oem: int | None = None
    ocr_psm: int | None = None
    ocr_tesseract_extra: str | None = None
    ocr_ocrmypdf_extra: str | None = None
    ocr_ocrmypdf_recommended: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Configure structlog once at import time
_level_name = (settings.log_level or "INFO").upper()
_level = getattr(logging, _level_name, logging.INFO)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(_level),
    cache_logger_on_first_use=True,
)
