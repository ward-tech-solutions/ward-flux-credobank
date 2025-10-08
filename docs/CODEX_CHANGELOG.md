# Codex Session Change Log

This document summarises every change applied during the current Codex session so that future conversations can pick up the full context without re-deriving the work.

---

## 1. Backend Initialisation & Zabbix Persistence

| File | Change |
|------|--------|
| `main.py` | Removed legacy setup wizard and admin UI mounts. Added automatic mounting of `static_new/` assets at import time (with warnings when missing). Added startup logic that lazily instantiates the `ZabbixClient` and reloads Zabbix credentials from the `system_config` table. |
| `main.py` | `/api/v1/settings/zabbix` now reads/writes credentials to `system_config` instead of `.env`. On save the credentials are stored in SQLite, written to `os.environ`, and the in-memory client is reconfigured. |
| `routers/utils.py` | `get_zabbix_client()` was hardened: if `app.state.zabbix` does not exist, create it on demand to avoid `'State' object has no attribute 'zabbix'` during the first request. |

**Result:** Zabbix settings persist in the database and automatically survive restarts (local or Docker). No manual env injection is required after the first configuration.

---

## 2. Frontend Asset Handling

| File | Change |
|------|--------|
| `.dockerignore` | Removed the `static_new/` exclusion. |
| `Dockerfile` | Multi-stage build now copies Vite's `dist/` output into `/app/static_new` so the container serves the React bundle. |
| `README.md` | Documented the GHCR image, copy/paste Docker commands, and clarified default credentials. |

**Result:** The Docker image always contains the React build and the web UI loads correctly (no MIME type errors).

---

## 3. CI/CD

| File | Change |
|------|--------|
| `.github/workflows/docker-image.yml` | Added workflow to build the Docker image and push tags (`main`, SHA, etc.) to GHCR on every push/tag. |

---

## 4. Password & Auth Helpers

* Added scripts/commands (documented in README & this change log) to reset the admin password using `passlib` when needed.

---

## 5. Local Development Runbook

* Updated instructions (and this log) to emphasise:
  - Build the React frontend (`npm --prefix frontend run build`) and copy the assets into `static_new/`.
  - Start Uvicorn with `uvicorn main:app --host 0.0.0.0 --port 5001 --reload`.
  - If the port is busy, run `pkill -f "uvicorn main:app"`.
  - Log in at `http://localhost:5001` (`admin/admin123` by default), configure Zabbix once, and future restarts will reuse those settings.

---

## 6. Docker Deployment Runbook

* Build: `docker build -t ghcr.io/ward-tech-solutions/ward-flux-v2:latest .`
* Push: `docker push ghcr.io/ward-tech-solutions/ward-flux-v2:latest`
* Run (client environment):
  ```bash
  docker run -d \
    --name ward-flux \
    --network host \
    -v ward-flux-data:/data \
    -v ward-flux-logs:/logs \
    ghcr.io/ward-tech-solutions/ward-flux-v2:latest
  ```
* Configure Zabbix via the UI once; the settings are stored in the client’s `/data` volume.

---

## 7. Key Commits (for reference)

* `2a8a572` – Removed setup wizard/admin mounts.
* `7b27f9c` – Included frontend build assets.
* `a3a7b3f` – Persist Zabbix credentials in DB.
* `e6fdaf2` – Lazy Zabbix client creation.
* `dd230bf` – Import-time static asset mounts.

---

## 8. Outstanding Notes

* The SQLite database is local to each environment (`data/ward_ops.db` or Docker volume). Clients maintain their own Zabbix settings and host groups.
* When testing within the container, use:
  ```bash
  docker exec ward-flux python - <<'PY'
  from zabbix_client import ZabbixClient
  print(len(ZabbixClient().get_all_groups()))
  PY
  ```

This file should be kept with the repository so future support sessions begin with the full context already documented.

