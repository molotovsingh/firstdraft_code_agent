# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FirstDraft v2.0 is a legal AI platform implementing a modular "Lego Blocks" architecture for document pre-processing, entity discovery, and foundational data extraction. The current implementation focuses on Block 0a (Document Pre-processing) with FastAPI, Celery, PostgreSQL, Redis, and MinIO.

## Development Commands

### Environment Setup
```bash
# Copy environment configuration
cp .env.example .env

# Start all services with Docker Compose
docker compose -f infra/docker-compose.yml up --build -d

# Apply database migrations (done automatically via migrator service)
docker compose -f infra/docker-compose.yml exec api alembic upgrade head

# Bootstrap development tenant and users
docker compose -f infra/docker-compose.yml exec api python scripts/bootstrap_dev.py
```

Note: Do not run `sudo` in repository-driven commands. Any privileged setup (e.g., installing Docker or adding your user to the `docker` group) must be performed manually by the operator. See `PRIVILEGE_POLICY.md`.

### Testing and Validation
```bash
# Health checks
docker compose -f infra/docker-compose.yml exec api python scripts/smoke_health.py

# Smoke tests for upload flow
docker compose -f infra/docker-compose.yml exec api python scripts/smoke_presign.py
docker compose -f infra/docker-compose.yml exec api python scripts/smoke_finalize.py

# Credit system testing
docker compose -f infra/docker-compose.yml exec api python scripts/smoke_credits.py <tenant_id>

# Complete CI smoke test (presign → finalize → worker)
./scripts/ci_smoke.sh

# In-network smoke test (if host cannot resolve minio)
./scripts/smoke_in_network.sh
```

### Development Workflow
```bash
# View logs
docker compose -f infra/docker-compose.yml logs -f api
docker compose -f infra/docker-compose.yml logs -f worker

# Open shell in API container
docker compose -f infra/docker-compose.yml exec api bash

# Batch upload documents
docker compose -f infra/docker-compose.yml exec api python scripts/batch_upload.py

# Clean up staging objects
docker compose -f infra/docker-compose.yml exec api python scripts/staging_gc.py --ttl-hours 48 --dry-run
```

### Database Management
```bash
# Create new migration
docker compose -f infra/docker-compose.yml exec api alembic revision --autogenerate -m "description"

# Apply specific migration
docker compose -f infra/docker-compose.yml exec api alembic upgrade <revision>

# Database shell access
docker compose -f infra/docker-compose.yml exec postgres psql -U firstdraft -d firstdraft_system
```

## Architecture Overview

### Modular Block Design
The system implements 7 independent "Lego Blocks":
- **Block 0**: Document Pre-processing (OCR, quality assessment, format standardization)
- **Block 1**: Entity Discovery Engine (planned)
- **Block 2**: Content Storage Engine (content-addressable + deduplication)
- **Block 3**: AI Processing Engine (multi-level AI cascade)
- **Block 4**: Queue Management Engine (enterprise job orchestration)
- **Block 5**: Multi-Tenant Management (client lifecycle + isolation)
- **Block 6**: API Gateway Engine (external interface + routing)

### Current Implementation (Block 0a)
- **FastAPI** (`apps/block0_api/main.py`): HTTP endpoints for upload/status/reporting
- **Celery Worker** (`apps/block0_worker/worker.py`): Background OCR and document processing
- **Shared Libraries** (`shared/*`): Database models, storage, quality metrics, OCR adapters
- **Multi-tenant Database**: PostgreSQL with tenant isolation via tenant_id
- **Object Storage**: S3/MinIO with content-addressable storage using SHA-256
- **Credit System**: Transaction-based billing with estimates and actual charges

### Data Flow
1. **Upload**: Presign → Direct S3 upload → Finalize (creates Document + ProcessingJob)
2. **Processing**: Celery worker performs OCR, quality assessment, stores results
3. **Storage**: Content-addressable with deduplication based on SHA-256
4. **Credits**: Estimate on upload → Reversal + Actual charge on completion

### Key Design Patterns
- **Never Reject Documents**: All documents processed with quality warnings instead of rejection
- **Quality-First**: Extensive quality assessment and metrics collection
- **Credit Transparency**: Upfront cost estimates with user control over quality/cost tradeoffs
- **Extensible Schema**: Database designed for future feature additions without migrations

## Configuration

### Environment Variables
Key settings in `.env`:
- `OCR_PROVIDER`: stub|tesseract|ocrmypdf (default: tesseract)
- `QUALITY_MODE`: recommended|budget (affects OCR processing speed/quality)
- `OCR_LANG`: eng|eng+hin|hin (language support)
- `UI_ENABLED`: Enable development UI at /ui
- `API_AUTH_ENABLED`: Require X-API-Key header for API access
- `DELETE_STAGING_ON_FINALIZE`: Clean up presigned staging objects

### Feature Flags
- OCR providers can be swapped without code changes
- Budget mode reduces processing time with quality tradeoffs
- Multi-language support for Hindi/English documents

## Database Schema

### Core Tables
- **tenants**: Multi-tenant isolation (UUID primary keys)
- **users**: Integer-based user management within tenants
- **documents**: Immutable document records with SHA-256 content addressing
- **document_versions**: Versioned processing results and artifacts
- **processing_jobs**: Async job tracking with status and error handling
- **credits**: Transaction ledger for billing with estimates and actuals

### Key Relationships
- Documents belong to tenants and users
- Versions link to documents with artifact URIs
- Jobs process specific document versions
- Credits track tenant-level transaction history

## API Design

### Upload Flow (Recommended)
1. `POST /v0/uploads/presign` → Get presigned PUT URL
2. PUT file directly to S3/MinIO using presigned URL
3. `POST /v0/uploads/finalize` → Create document records and enqueue processing

### Legacy Upload
- `POST /v0/documents/upload` → Direct multipart upload (less efficient)

### Status and Reports
- `GET /v0/jobs/{id}` → Processing status
- `GET /v0/documents/{id}/report.json` → Metadata and warnings
- `GET /v0/documents/{id}/processed.json` → Machine-readable output for downstream blocks

### Credits API
- `GET /v0/credits/balance` → Current tenant balance
- `GET /v0/credits/ledger` → Transaction history
- `GET /v0/credits/summary` → Aggregate view by transaction type

## Quality Strategy

### OCR Processing
- **Images**: Tesseract with automatic deskewing and confidence scoring
- **PDFs**: OCRmyPDF with configurable timeout and language support
- **Quality Modes**: Budget (faster, single language) vs Recommended (full quality)

### Metrics Collection
- OCR confidence scores and text quality assessment
- Image quality metrics (blur detection, skew correction)
- Document completeness and language detection
- Processing duration and resource usage

### Warning System
- Quality warnings for low OCR confidence
- Format issues and enhancement notifications
- Language detection mismatches
- Processing timeout or failure alerts

## Development Guidelines

### Code Organization
- Shared libraries in `shared/` for cross-block functionality
- Application-specific code in `apps/block0_*`
- Infrastructure configuration in `infra/`
- Development scripts in `scripts/`

### Testing Strategy
- Smoke tests for critical user flows
- Health checks for service dependencies
- End-to-end testing via CI smoke scripts
- Unit tests should focus on shared library functions

### Database Migrations
- Use Alembic for schema changes
- Design for forward compatibility
- Include placeholder columns for future features
- Test migrations on development data

### Monitoring
- Prometheus metrics for API and worker processes
- Structured logging with request correlation
- Health endpoints for service monitoring
- Credit usage tracking for billing insights

## Deployment

### Docker Compose Development
All services run via `docker-compose.yml` with:
- Automatic dependency management
- Health checks and startup ordering
- Volume persistence for PostgreSQL and MinIO
- Environment variable configuration

### Production Considerations
- Multi-tenant database isolation strategy
- S3-compatible storage for object persistence
- Redis for job queuing and caching
- Kubernetes-ready containerization

### Service Dependencies
- PostgreSQL: Primary data store
- Redis: Message broker and cache
- MinIO/S3: Object storage
- Python services: API and worker processes
