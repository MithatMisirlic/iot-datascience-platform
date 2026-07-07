# Deployment

## Current Local Runtime

1. Create and activate a Python 3.11+ virtual environment.
2. Install `requirements.txt`.
3. Copy `.env.example` to `.env` and review every value.
4. Start the API with `uvicorn backend.app.main:app --host 127.0.0.1 --port 3000`.
5. Verify `/health`, `/docs`, database creation, and upload-directory permissions.

Application startup validates settings, prepares local SQLite/upload directories, creates missing tables, and configures logging. `PI_ADAPTER_MODE` must remain `noop` without hardware integration.

## Remote Linux Baseline

Use a dedicated unprivileged service account, an application-owned data directory, and environment-specific `DATABASE_URL` and `UPLOAD_DIR` values. Place Uvicorn behind a TLS-terminating reverse proxy and supervise it with the host service manager.

## Remaining Production Gaps

- Alembic migrations and upgrade/rollback procedures.
- PostgreSQL compatibility testing.
- Authentication and authorization.
- Upload size, quota, and media-type enforcement.
- Backup and retention policies for database and artifact files.
- Structured/centralized logs and operational metrics.
- Raspberry Pi transport, credentials, and network failure handling.
- A real processing worker and job queue.
