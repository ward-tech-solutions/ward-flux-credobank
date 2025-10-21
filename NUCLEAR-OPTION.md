# NUCLEAR OPTION - Manual Docker Run Commands

**Problem:** Docker Compose 1.29.2 has a ContainerConfig bug that prevents normal deployment.

**Solution:** Bypass docker-compose entirely and use direct docker run commands.

---

## The Problem

Docker Compose `--force-recreate` tries to recreate ALL containers including postgres/redis/victoria, which triggers the ContainerConfig bug. We only want to recreate the API/Worker/Beat containers.

---

## Option 1: Use Surgical Deployment Script

```bash
cd /home/wardops/ward-flux-credobank
git pull origin main
./deploy-surgical.sh
```

This script uses `docker run` commands directly, bypassing docker-compose for container creation.

---

## Option 2: Manual Commands (Copy-Paste)

If you want to do it manually, here are the exact commands:

### Step 1: Clean Up

```bash
cd /home/wardops/ward-flux-credobank

# Stop and remove only our app containers (leave postgres/redis/victoria alone)
docker stop wardops-api-prod wardops-worker-prod wardops-beat-prod
docker rm wardops-api-prod wardops-worker-prod wardops-beat-prod
```

### Step 2: Build Images

```bash
docker-compose -f docker-compose.production-local.yml build --no-cache api celery-worker celery-beat
```

### Step 3: Start API Container

```bash
docker run -d \
  --name wardops-api-prod \
  --network ward-flux-credobank_default \
  -p 5001:5001 \
  -e DATABASE_URL='postgresql://ward_admin:ward_admin_password@postgres:5432/ward_ops' \
  -e REDIS_URL='redis://:redispass@redis:6379/0' \
  -e VICTORIA_URL='http://victoriametrics:8428' \
  -e DEFAULT_ADMIN_PASSWORD='admin123' \
  -e SECRET_KEY='local-prod-test-secret-key-change-me' \
  -e ENVIRONMENT='production' \
  -e MONITORING_MODE='snmp_only' \
  -v /home/wardops/ward-flux-credobank/logs:/app/logs \
  -v api_prod_data:/data \
  --restart unless-stopped \
  ward-flux-credobank_api:latest
```

### Step 4: Start Worker Container

```bash
docker run -d \
  --name wardops-worker-prod \
  --network ward-flux-credobank_default \
  -e DATABASE_URL='postgresql://ward_admin:ward_admin_password@postgres:5432/ward_ops' \
  -e REDIS_URL='redis://:redispass@redis:6379/0' \
  -e VICTORIA_URL='http://victoriametrics:8428' \
  -e SECRET_KEY='local-prod-test-secret-key-change-me' \
  -e ENVIRONMENT='production' \
  -e MONITORING_MODE='snmp_only' \
  -v /home/wardops/ward-flux-credobank/logs:/app/logs \
  -v celery_prod_data:/data \
  --restart unless-stopped \
  ward-flux-credobank_celery-worker:latest \
  celery -A celery_app worker --loglevel=info --concurrency=100
```

### Step 5: Start Beat Container

```bash
docker run -d \
  --name wardops-beat-prod \
  --network ward-flux-credobank_default \
  -e DATABASE_URL='postgresql://ward_admin:ward_admin_password@postgres:5432/ward_ops' \
  -e REDIS_URL='redis://:redispass@redis:6379/0' \
  -e SECRET_KEY='local-prod-test-secret-key-change-me' \
  -e ENVIRONMENT='production' \
  -v /home/wardops/ward-flux-credobank/logs:/app/logs \
  -v beat_prod_data:/data \
  --restart unless-stopped \
  ward-flux-credobank_celery-beat:latest \
  celery -A celery_app beat --loglevel=info
```

### Step 6: Verify

```bash
# Check all containers are running
docker ps | grep wardops

# Test API
curl http://localhost:5001/api/v1/health

# Check timezone fix
curl http://localhost:5001/api/v1/devices/standalone | jq '.[].down_since' | head -3
```

---

## Why This Works

When you use `docker run` directly:
- ✅ No ContainerConfig metadata checks
- ✅ Fresh container creation
- ✅ Full control over what gets recreated
- ✅ Postgres/Redis/Victoria left untouched

When you use `docker-compose up --force-recreate`:
- ❌ Tries to recreate ALL services
- ❌ Reads old container metadata
- ❌ Fails on ContainerConfig key error
- ❌ Can't selectively recreate containers

---

## Network Note

The containers need to be on the same Docker network as postgres/redis/victoria. The network is called `ward-flux-credobank_default` (created by docker-compose).

To verify the network exists:
```bash
docker network ls | grep ward-flux
```

If it doesn't exist, create it:
```bash
docker network create ward-flux-credobank_default
```

---

## Volume Note

The named volumes are already created:
- `api_prod_data`
- `celery_prod_data`
- `beat_prod_data`

You can verify:
```bash
docker volume ls | grep prod_data
```

---

## Future Deployments

Once the containers are created with `docker run`, you can use docker-compose normally for other operations:

```bash
# These work fine:
docker-compose -f docker-compose.production-local.yml stop api
docker-compose -f docker-compose.production-local.yml start api
docker-compose -f docker-compose.production-local.yml logs -f api

# But avoid:
docker-compose -f docker-compose.production-local.yml up -d --force-recreate  # Triggers bug
```

For future code deployments, repeat the process:
1. `docker stop` + `docker rm` the app containers
2. `docker-compose build --no-cache`
3. `docker run` with the new images

Or just use the `deploy-surgical.sh` script!

---

## Troubleshooting

### Problem: "network ward-flux-credobank_default not found"

**Solution:**
```bash
# List networks
docker network ls

# If not found, create it
docker network create ward-flux-credobank_default

# Or start postgres/redis/victoria first to create it
docker-compose -f docker-compose.production-local.yml up -d postgres redis victoriametrics
```

### Problem: "conflict - container name already in use"

**Solution:**
```bash
# Force remove
docker rm -f wardops-api-prod wardops-worker-prod wardops-beat-prod

# Then try docker run again
```

### Problem: API not responding after container starts

**Solution:**
```bash
# Check logs
docker logs wardops-api-prod

# Common issues:
# - Database not ready: Wait 10 seconds and check again
# - Port conflict: Check if something else is using 5001
# - Environment variable typo: Check docker logs for errors
```

---

## Summary

**Docker Compose Bug:** ContainerConfig KeyError when recreating containers

**Workaround:** Use `docker run` directly instead of `docker-compose up`

**Long-term Fix:** Upgrade to Docker Compose v2 (but that's a bigger change)

**Quick Command:**
```bash
./deploy-surgical.sh
```
