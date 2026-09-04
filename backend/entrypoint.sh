#!/bin/bash
# Backend container entrypoint.
# 1. Seed demo users (idempotent — skips if users already exist)
# 2. Start the FastAPI application with uvicorn

set -e

echo "=== FinancialEdApp backend starting ==="

echo "--- Seeding demo users (idempotent) ---"
python -m app.seed_users && echo "Seed complete." || echo "Seed skipped or failed (non-fatal)."

echo "--- Starting uvicorn ---"
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${UVICORN_WORKERS:-1}" \
    --log-level "$(echo "${LOG_LEVEL:-info}" | tr '[:upper:]' '[:lower:]')"
