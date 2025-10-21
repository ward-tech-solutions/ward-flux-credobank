# CRITICAL: Why Code Changes Don't Deploy with Just `docker restart`

**Date:** October 21, 2025
**Issue:** Git pull shows "Already up to date" but containers still run old code
**Root Cause:** Dockerfile COPIES code into image at build time

---

## The Problem

When you run:
```bash
cd /home/wardops/ward-flux-credobank
git pull origin main
docker restart wardops-api-prod
```

**The code DOES NOT UPDATE** even though git pull succeeds!

---

## Why This Happens

### How the Dockerfile Works

Looking at [Dockerfile](Dockerfile) lines 68-69 and 77:

```dockerfile
# Line 68-69: Copies ALL application code INTO the image
COPY --chown=ward:ward . .

# Line 77: Copies built frontend INTO the image
COPY --from=frontend-builder --chown=ward:ward /frontend/dist /app/static_new
```

This means:

1. **At build time**: Docker copies the code that exists on the host machine into the image
2. **The image becomes a snapshot** of the code at that moment
3. **The running container uses this snapshot**, not the live files

### What Happens When You Git Pull

```
┌─────────────────────────────────────────────────────────────┐
│  HOST MACHINE: /home/wardops/ward-flux-credobank            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  git pull → Updates these files ✅                    │   │
│  │  - routers/devices.py (NEW CODE)                     │   │
│  │  - monitoring/tasks.py (NEW CODE)                    │   │
│  │  - frontend/src/pages/Monitor.tsx (NEW CODE)         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          ↓
                    docker restart
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  CONTAINER: wardops-api-prod                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Still uses OLD CODE from build time ❌               │   │
│  │  - /app/routers/devices.py (OLD CODE)                │   │
│  │  - /app/monitoring/tasks.py (OLD CODE)               │   │
│  │  - /app/static_new/index-ABC123.js (OLD CODE)        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  Container does NOT see the new files on host!              │
└─────────────────────────────────────────────────────────────┘
```

**The container has its OWN COPY of the code inside it** - it's not reading from the host directory!

---

## The Solution

You **MUST REBUILD** the Docker images to get new code:

```bash
cd /home/wardops/ward-flux-credobank
git pull origin main

# Stop containers
docker-compose -f docker-compose.production-local.yml stop api celery-worker

# Rebuild images with new code
docker-compose -f docker-compose.production-local.yml build --no-cache api celery-worker

# Start containers with new images
docker-compose -f docker-compose.production-local.yml up -d api celery-worker
```

### Why `--no-cache` Is Important

Docker uses layer caching to speed up builds. Without `--no-cache`, it might skip copying the new code:

```bash
# BAD - May use cached copy step:
docker-compose build api

# GOOD - Forces fresh copy of all code:
docker-compose build --no-cache api
```

---

## Quick Deployment Script

Use the automated script:

```bash
cd /home/wardops/ward-flux-credobank
./deploy-timezone-fix.sh
```

This script:
1. Pulls latest code
2. Stops containers
3. Rebuilds images with `--no-cache`
4. Starts containers
5. Verifies deployment

---

## How to Verify New Code Is Active

### 1. Check API Timestamp Format

**OLD CODE (before fix):**
```bash
curl http://localhost:5001/api/v1/devices/standalone | jq '.[0].down_since'
"2025-10-21T08:34:45.186571"  # ❌ No timezone suffix
```

**NEW CODE (after fix):**
```bash
curl http://localhost:5001/api/v1/devices/standalone | jq '.[0].down_since'
"2025-10-21T08:34:45.186571+00:00"  # ✅ Has +00:00 timezone
```

### 2. Check Frontend Build Hash

**OLD CODE:**
```bash
docker exec wardops-api-prod ls -la /app/static_new/assets/
# Shows: index-CWvAtuJb.js (old hash)
```

**NEW CODE:**
```bash
docker exec wardops-api-prod ls -la /app/static_new/assets/
# Shows: index-NEWHASH.js (different hash)
```

### 3. Check Browser Console

Open Monitor page and press F12:

**OLD CODE:**
```
[Device] down_since: 2025-10-21T08:34:45.186571
Date: 2025-10-21T04:34:45.186Z  # ❌ Wrong time (6 hour offset)
Diff hours: 6.07
```

**NEW CODE:**
```
[Device] down_since: 2025-10-21T08:34:45.186571+00:00
Date: 2025-10-21T08:34:45.186Z  # ✅ Correct time
Diff hours: 0.05
```

---

## Why Docker Compose Volumes Don't Help Here

You might notice in [docker-compose.production-local.yml](docker-compose.production-local.yml) lines 76-78:

```yaml
volumes:
  - ./logs:/app/logs        # ✅ This works - logs are shared
  - api_prod_data:/data     # ✅ This works - data persists
```

**Notice what's MISSING:**
```yaml
# This is NOT present:
  - .:/app  # ❌ Would mount source code (not safe for production)
```

In production deployments, you **don't want** to mount the source code directory because:
- Risk of accidental code changes affecting running containers
- Permission issues between host and container
- Security concerns

Instead, the code is **copied into the image** at build time, making the container self-contained and immutable.

---

## Development vs Production

### Development Setup (not used here)

```yaml
# Development would have:
volumes:
  - .:/app  # Live code mounting
```

**Benefit:** Code changes immediately visible (just restart)
**Used for:** Local development with hot-reload

### Production Setup (current)

```dockerfile
# Production has:
COPY --chown=ward:ward . .  # Code copied into image
```

**Benefit:** Immutable, reproducible deployments
**Used for:** Production servers
**Trade-off:** Must rebuild to update code

---

## Common Mistakes

### ❌ WRONG: Just restart after git pull

```bash
git pull origin main
docker restart wardops-api-prod  # ❌ Container still has old code!
```

### ❌ WRONG: Build without --no-cache

```bash
docker-compose build api  # ❌ May use cached layers!
```

### ✅ CORRECT: Rebuild with --no-cache

```bash
git pull origin main
docker-compose -f docker-compose.production-local.yml build --no-cache api celery-worker
docker-compose -f docker-compose.production-local.yml up -d api celery-worker
```

---

## Deployment Checklist

- [ ] Git pull latest code
- [ ] Stop affected containers
- [ ] Build with `--no-cache` flag
- [ ] Start containers
- [ ] Verify new code is active (check API response format)
- [ ] Verify frontend assets updated (check browser console)
- [ ] Test functionality

---

## Time Estimates

| Step | Time | Why |
|------|------|-----|
| Git pull | 5 sec | Downloads latest code |
| Stop containers | 10 sec | Graceful shutdown |
| Build --no-cache | **2-3 min** | Rebuilds frontend + backend |
| Start containers | 15 sec | Container startup |
| Health checks | 30 sec | Wait for ready state |
| **Total** | **~4 minutes** | Full deployment cycle |

---

## Troubleshooting

### Problem: Build takes too long (> 5 minutes)

**Cause:** Network issues downloading npm packages or Python packages

**Solution:**
```bash
# Check if intermediate containers exist
docker ps -a | grep frontend-builder

# Clean up and retry
docker system prune -f
docker-compose build --no-cache api
```

### Problem: "Already up to date" but code still old

**Cause:** You're in the wrong directory or wrong branch

**Check:**
```bash
pwd  # Should show: /home/wardops/ward-flux-credobank
git branch  # Should show: * main
git log --oneline -1  # Should show latest commit hash
```

### Problem: Build fails with "ContainerConfig" error

**Cause:** Old containers interfering with new build

**Solution:**
```bash
docker stop wardops-api-prod wardops-worker-prod
docker rm wardops-api-prod wardops-worker-prod
docker-compose -f docker-compose.production-local.yml up -d --build
```

---

## Summary

**Key Insight:** Docker containers run **copied code**, not live code.

**Golden Rule:** After `git pull`, you **MUST rebuild** to deploy changes.

**Quick Command:**
```bash
./deploy-timezone-fix.sh
```

---

**Next Steps:**

1. Run deployment script
2. Verify timezone fix is active
3. Test delete button and toast notifications
4. Monitor for 24 hours to ensure stability
