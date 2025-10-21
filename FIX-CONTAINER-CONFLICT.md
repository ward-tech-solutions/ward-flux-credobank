# Quick Fix: Container Name Conflict & ContainerConfig Error

**Error:** `Cannot create container for service api: Conflict. The container name "/wardops-api-prod" is already in use`

**Error:** `KeyError: 'ContainerConfig'`

---

## The Problem

When you run `docker-compose up -d` after building, it tries to create new containers but:
1. The old containers still exist (even though stopped)
2. Docker Compose 1.29.2 has a bug when trying to recreate containers

---

## Quick Fix (Manual Commands)

Run these commands on the production server:

```bash
cd /home/wardops/ward-flux-credobank

# 1. Stop old containers
docker stop wardops-api-prod wardops-worker-prod

# 2. REMOVE old containers (this is the key step!)
docker rm wardops-api-prod wardops-worker-prod

# 3. Start NEW containers
docker-compose -f docker-compose.production-local.yml up -d api celery-worker

# 4. Verify they're running
docker ps | grep wardops
```

---

## Or Use the Fixed Script

```bash
cd /home/wardops/ward-flux-credobank
./deploy-timezone-fix-v2.sh
```

This script automatically handles:
- Stopping old containers
- Removing old containers (avoids conflict)
- Building new images
- Creating fresh containers

---

## Why This Happens

Docker containers have **two states**:

1. **Stopped** - Container exists but not running
2. **Removed** - Container deleted completely

When you run:
```bash
docker-compose stop api  # Stops the container
docker-compose up -d     # Tries to CREATE a new container
```

This fails because the old container still **exists** (it's just stopped).

**Solution:** You must **remove** (not just stop) the old container:
```bash
docker rm wardops-api-prod  # Deletes the container
```

---

## Complete Deployment Process

```bash
cd /home/wardops/ward-flux-credobank

# Pull latest code
git pull origin main

# Stop containers
docker stop wardops-api-prod wardops-worker-prod

# REMOVE containers (key step!)
docker rm wardops-api-prod wardops-worker-prod

# Rebuild images
docker-compose -f docker-compose.production-local.yml build --no-cache api celery-worker

# Create and start NEW containers
docker-compose -f docker-compose.production-local.yml up -d api celery-worker

# Verify
docker ps | grep wardops
docker logs wardops-api-prod --tail 20
```

---

## Verification

Check that new containers are running:

```bash
docker ps
```

Should show:
```
CONTAINER ID   IMAGE                              CREATED         STATUS
abc123def456   ward-flux-credobank_api:latest    10 seconds ago  Up 8 seconds
```

**Notice "CREATED" is recent** - this proves it's a new container!

---

## Test the Fix

```bash
# Check timezone format in API response
curl http://localhost:5001/api/v1/devices/standalone | jq '.[0].down_since'

# Should show: "2025-10-21T08:34:45.186571+00:00"  ✅
# NOT:         "2025-10-21T08:34:45.186571"        ❌
```

Then open browser and check Monitor page console for correct "Diff hours".

---

## What NOT to Do

### ❌ Don't just restart:
```bash
docker restart wardops-api-prod  # Won't update code!
```

### ❌ Don't stop without removing:
```bash
docker-compose stop api
docker-compose up -d  # ERROR: Container name conflict!
```

### ✅ DO remove before recreating:
```bash
docker stop wardops-api-prod
docker rm wardops-api-prod    # This is the key!
docker-compose up -d api
```

---

## Summary

**Problem:** Old containers blocking new container creation

**Root Cause:** `docker-compose stop` doesn't remove containers

**Solution:** Add `docker rm` before `docker-compose up`

**Quick Command:**
```bash
docker stop wardops-api-prod wardops-worker-prod && \
docker rm wardops-api-prod wardops-worker-prod && \
docker-compose -f docker-compose.production-local.yml up -d api celery-worker
```
