#!/usr/bin/env bash
set -euo pipefail

# Auto-generate security secrets if they are not provided
if [[ -z "${SECRET_KEY:-}" ]]; then
  SECRET_KEY="$(python - <<'PY'
import secrets, base64
print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
PY
)"
  export SECRET_KEY
  echo "[entrypoint] Generated SECRET_KEY"
fi

if [[ -z "${ENCRYPTION_KEY:-}" ]]; then
  ENCRYPTION_KEY="$(python - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
)"
  export ENCRYPTION_KEY
  echo "[entrypoint] Generated ENCRYPTION_KEY"
fi

# Provide a default admin bootstrap password if none supplied
if [[ -z "${DEFAULT_ADMIN_PASSWORD:-}" ]]; then
  export DEFAULT_ADMIN_PASSWORD="admin123"
  echo "[entrypoint] DEFAULT_ADMIN_PASSWORD not provided, using default 'admin123'"
fi

# Ensure database schema and baseline data exist before the API starts.
cd /app
DATABASE_URL=${DATABASE_URL:-"sqlite:////data/ward_flux.db"}
echo "[entrypoint] Seeding database at ${DATABASE_URL}"

# Run SQL migrations first (creates tables like georgian_regions, georgian_cities, etc.)
if [[ "${DATABASE_URL}" == postgresql://* ]] || [[ "${DATABASE_URL}" == postgres://* ]]; then
  echo "[entrypoint] Running PostgreSQL migrations..."
  PYTHONPATH=/app python3 /app/scripts/run_sql_migrations.py
fi

# Seed core data (users, system config, monitoring profiles)
PYTHONPATH=/app python3 /app/scripts/seed_core.py --database-url "${DATABASE_URL}" --seeds-dir "seeds/core"

# Seed CredoBank data (875 devices, 128 branches, alert rules, Georgian regions/cities)
if [[ -d "/app/seeds/credobank" ]]; then
  echo "[entrypoint] Seeding CredoBank data (875 devices, 128 branches, alerts, Georgian regions/cities)"
  PYTHONPATH=/app python3 /app/scripts/seed_credobank.py --database-url "${DATABASE_URL}" --seeds-dir "seeds/credobank"
fi

exec "$@"
