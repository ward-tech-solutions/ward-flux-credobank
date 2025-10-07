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

exec "$@"
