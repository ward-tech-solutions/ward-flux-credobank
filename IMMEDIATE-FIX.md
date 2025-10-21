# IMMEDIATE FIX - Manual Commands

**Current Status:** API container created successfully, but worker container has ContainerConfig error

---

## Quick Fix - Run These Commands NOW

```bash
cd /home/wardops/ward-flux-credobank

# 1. Find and remove ALL wardops containers (including ghost containers)
docker ps -a | grep wardops

# 2. Force remove all wardops containers
docker rm -f $(docker ps -aq --filter "name=wardops") 2>/dev/null || true

# 3. Create and start containers with --force-recreate flag
docker-compose -f docker-compose.production-local.yml up -d --force-recreate api celery-worker celery-beat

# 4. Verify they're running
docker ps | grep wardops
```

---

## Alternative: Use Automated Script

```bash
cd /home/wardops/ward-flux-credobank
git pull origin main
./deploy-timezone-fix-v3.sh
```

---

## What's Happening

The error shows:
```
Creating wardops-api-prod ... done  ✅ (This worked!)
ERROR: for d0210381887e_wardops-worker-prod  'ContainerConfig'  ❌ (This failed!)
```

There's a ghost container `d0210381887e_wardops-worker-prod` that's interfering.

---

## The Nuclear Option (If Above Doesn't Work)

If the worker container keeps failing, manually remove everything:

```bash
cd /home/wardops/ward-flux-credobank

# Stop ALL containers
docker stop $(docker ps -aq --filter "name=wardops")

# Remove ALL containers
docker rm $(docker ps -aq --filter "name=wardops")

# List any remaining containers
docker ps -a | grep wardops

# If you see any containers with weird names like d0210381887e, remove by ID:
docker rm -f d0210381887e

# Now rebuild everything from scratch
docker-compose -f docker-compose.production-local.yml build --no-cache

# Start fresh
docker-compose -f docker-compose.production-local.yml up -d
```

---

## Verify Deployment

After containers are running:

```bash
# 1. Check all containers are up
docker ps --filter "name=wardops"

# Should show:
# wardops-api-prod      Up X seconds
# wardops-worker-prod   Up X seconds
# wardops-beat-prod     Up X seconds

# 2. Check API health
curl http://localhost:5001/api/v1/health

# 3. Verify timezone fix
curl http://localhost:5001/api/v1/devices/standalone | jq '.[0].down_since'

# Should show: "2025-10-21T08:34:45.186571+00:00"  ✅
# NOT:         "2025-10-21T08:34:45.186571"        ❌
```

---

## Why ContainerConfig Error Happens

Docker Compose 1.29.2 has a bug where:
1. It tries to "recreate" containers
2. It reads metadata from old containers
3. The old container's image config is missing the 'ContainerConfig' key
4. It crashes with KeyError

**Solution:** Don't recreate - remove old containers completely and create fresh ones.

---

## Current Status of API Container

The good news: **wardops-api-prod was created successfully!**

You can verify the timezone fix is already working:

```bash
# Check if API is responding
curl http://localhost:5001/api/v1/health

# Check timezone in response
curl http://localhost:5001/api/v1/devices/standalone | jq '.[].down_since' | head -3
```

If you see timestamps with `+00:00` suffix, the **API fix is already live!**

You just need to get the worker container running.

---

## Quick Test While Worker is Down

Even with the worker container failing, you can test:

1. **API timezone fix** - Should be working since API container is up
2. **Delete button** - Should work since it only uses the API
3. **Toast notifications** - Should work (frontend feature)

What WON'T work without the worker:
- Background ping tasks
- State transition detection (UP→DOWN, DOWN→UP)
- New down_since timestamps being set

But you can verify the timezone fix with existing down devices!

---

## Summary

**Status:**
- ✅ API container: Running with new code
- ❌ Worker container: ContainerConfig error
- ✅ Timezone fix: Should be active in API responses

**Next Step:**
Remove the ghost worker container and recreate it fresh.

**Command:**
```bash
docker rm -f $(docker ps -aq --filter "name=wardops-worker") && \
docker-compose -f docker-compose.production-local.yml up -d celery-worker
```
