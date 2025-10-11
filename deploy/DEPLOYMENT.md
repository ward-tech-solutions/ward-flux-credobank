# Ward OPS – CredoBank Deployment Guide

This document walks through deploying the Ward OPS stack (API, Celery, React frontend, PostgreSQL with seed data, Redis) on a single Linux host.

## 1. Prerequisites

- Ubuntu 22.04 (or equivalent modern Linux)
- Docker Engine + Compose plugin (install with `apt` or from Docker’s repo)
- Access to the private registry that hosts the Ward OPS images

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER
```

Log out/in after the `usermod` command so you can run docker without `sudo`.

## 2. Files Required

Copy the following into `/opt/wardops/` on the target server:

```
deploy/docker-compose.yml        -> /opt/wardops/docker-compose.yml
deploy/.env.prod.example         -> /opt/wardops/.env.prod   (update secrets)
```

Update `.env.prod` before deployment:

- `DATABASE_URL`/`REDIS_URL` – use the internal service names (`db`, `redis`) from the compose file
- `SECRET_KEY`, `ENCRYPTION_KEY` – generate secure random values (32+ characters)
- `DEFAULT_ADMIN_PASSWORD` – this is the initial UI password for the `admin` user; change it immediately after login
- `REDIS_PASSWORD` – update if you want a different Redis auth key

## 3. Pull Images

```bash
docker login registry.example.com
docker pull ward_flux/wardops-app:credobank-latest
docker pull ward_flux/wardops-postgres-seeded:credobank-latest
```

## 4. Launch the Stack

```bash
cd /opt/wardops
docker compose run --rm api ./scripts/run_sql_migrations.py   # records applied migrations
docker compose up -d
```

- API: `http://<server-ip>:5001/api/v1/health`
- Frontend: `http://<server-ip>:3000`

Default credentials:

- UI admin: `admin / admin123` (change after first login)
- PostgreSQL: `fluxdb / FluxDB` (used by the compose file internally)

## 5. Optional: systemd service

Create `/etc/systemd/system/wardops.service`:

```ini
[Unit]
Description=Ward OPS Compose Stack
Requires=docker.service
After=docker.service

[Service]
WorkingDirectory=/opt/wardops
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
Restart=always
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable wardops
sudo systemctl start wardops
```

## 6. Monitoring & Maintenance

- Logs: `docker compose logs -f api worker beat`
- Nightly retention/alert evaluation happens via `celery-beat`
- Quick validation (optional):
  ```bash
  docker compose run --rm api ./scripts/celery_smoke_test.py
  ```
- To update the stack:
  ```bash
  docker pull registry.example.com/wardops/app:credobank-latest
  docker pull registry.example.com/wardops/postgres-seeded:credobank-latest
  docker compose up -d
  ```

## 7. Data Backups

- PostgreSQL runs with a persistent Docker volume (`db-data`). Use `pg_dump` inside the `db` container or schedule regular snapshots.
- Redis is ephemeral by default; enable persistence if you rely on long-running task results.

## 8. Support

For environment-specific issues (networking, TLS termination, VM sizing) coordinate with the CredoBank infrastructure team. For application bugs or feature requests, escalate through Ward OPS support.
