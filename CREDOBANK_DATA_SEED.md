# CredoBank Data Seeding

This document explains how the CredoBank device data is automatically loaded into the Docker image.

## Overview

The WARD FLUX Docker image now includes **1,100 records** of CredoBank production data that is automatically seeded when the container starts:

- **875 standalone devices** (routers, switches, firewalls, etc.)
- **128 branches** (CredoBank branch locations)
- **4 alert rules** (monitoring thresholds and notifications)
- **11 Georgian regions** (geographic reference data)
- **82 Georgian cities** (geographic reference data)

**Runtime data is NOT seeded** - the following tables start empty:
- ping_results
- alert_history
- discovery_jobs
- discovery_results
- mtr_results
- traceroute_results
- network_topology

## How It Works

### 1. Data Export (Local Development)

The `scripts/export_credobank_data.py` script exports data from your local PostgreSQL database to JSON files:

```bash
./venv/bin/python scripts/export_credobank_data.py
```

This creates JSON files in `seeds/credobank/`:
- `devices.json` (875 devices, 1MB)
- `branches.json` (128 branches)
- `alert_rules.json` (4 rules)
- `georgian_regions.json` (11 regions)
- `georgian_cities.json` (82 cities)

### 2. Docker Image Build (CI/CD)

When you push to the `client/credo-bank` branch:

1. GitHub Actions builds the Docker image
2. The `Dockerfile` copies all files including `seeds/credobank/`
3. The image is pushed to `ghcr.io/ward-tech-solutions/ward-flux-v2/credobank:latest`

**Important:** The seed files are included in the Docker image (~1.1MB total).

### 3. Container Startup (Production Server)

The `docker-entrypoint.sh` script runs when the container starts:

```bash
# Seed core data (users, system config, monitoring profiles)
PYTHONPATH=/app python3 /app/scripts/seed_core.py --database-url "${DATABASE_URL}" --seeds-dir "seeds/core"

# Seed CredoBank data (875 devices, 128 branches, alerts, Georgian regions/cities)
if [[ -d "/app/seeds/credobank" ]]; then
  echo "[entrypoint] Seeding CredoBank data (875 devices, 128 branches, alerts, Georgian regions/cities)"
  PYTHONPATH=/app python3 /app/scripts/seed_credobank.py --database-url "${DATABASE_URL}" --seeds-dir "seeds/credobank"
fi
```

The seeding process:
- Checks if each record already exists (idempotent)
- Skips records that are already present
- Only inserts new records

### 4. Celery Workers Start Polling

After seeding completes:
- The API server starts (`uvicorn main:app`)
- Celery workers start polling devices
- Ping results, alerts, and topology data begin populating

## Updating CredoBank Data

To update the device data:

1. **Export from local database:**
   ```bash
   ./venv/bin/python scripts/export_credobank_data.py
   ```

2. **Commit the changes:**
   ```bash
   git add seeds/credobank/
   git commit -m "Update CredoBank device data"
   git push origin client/credo-bank
   ```

3. **Wait for CI/CD (~15 minutes):**
   - GitHub Actions builds new image
   - Image is pushed to GHCR

4. **Redeploy on server:**
   ```bash
   cd /opt/wardops
   docker compose pull
   docker compose down
   docker volume rm wardops_db-data  # Clear old data
   docker compose up -d
   ```

## Files Involved

- `docker-entrypoint.sh` - Container startup script
- `scripts/seed_credobank.py` - Seeding script for CredoBank data
- `scripts/export_credobank_data.py` - Export script for local database
- `seeds/credobank/*.json` - JSON seed files (included in Docker image)

## Database Schema

The seed script populates these tables:
- `georgian_regions` (raw SQL, no model)
- `georgian_cities` (raw SQL, no model)
- `branches` (Branch model)
- `standalone_devices` (StandaloneDevice model)
- `alert_rules` (AlertRule model)

## Verification

After deployment, verify the data was seeded:

```bash
# Check container logs
docker logs wardops-api

# Should see:
# [entrypoint] Seeding CredoBank data (875 devices, 128 branches, alerts, Georgian regions/cities)
# INFO seed_credobank: Seeded 11 Georgian regions
# INFO seed_credobank: Seeded 82 Georgian cities
# INFO seed_credobank: Seeded 128 branches
# INFO seed_credobank: Seeded 875 standalone devices
# INFO seed_credobank: Seeded 4 alert rules
```

Check the dashboard:
- Navigate to http://your-server:5001
- Dashboard should show **875 devices**
- Map should show **128 branch locations**

## Troubleshooting

**Problem:** Dashboard shows 0 devices after deployment

**Solution:** Check container logs for seeding errors:
```bash
docker logs wardops-api | grep -i seed
```

**Problem:** Seeding takes too long

**Solution:** The 875 devices should seed in < 30 seconds. If it takes longer, check database performance.

**Problem:** Duplicate devices after redeployment

**Solution:** The seed script is idempotent. If you see duplicates, the database volume was not cleared before redeployment. Run:
```bash
docker compose down
docker volume rm wardops_db-data
docker compose up -d
```
