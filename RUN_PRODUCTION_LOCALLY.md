# 🏭 Run Production CredoBank Setup Locally

This guide shows you how to run the **exact production setup** from the CredoBank server (10.30.25.39) on your local MacBook.

---

## Why Run Production Locally?

✅ Test changes with **real production data**
✅ Debug issues in a **production-like environment**
✅ Verify fixes before deploying to production
✅ Safe testing without affecting live users

---

## Quick Start (3 Steps)

### Step 1: Build the Production Docker Image

```bash
cd "/Users/g.jalabadze/Desktop/WARD OPS/CredoBranches"

# Build the exact same Docker image as production
docker build --no-cache -t wardops-credobank:local .
```

### Step 2: Get Production Database

**Option A: Latest from CI/CD (Recommended)**

The CI/CD pipeline builds and pushes images with seeded database. Pull it:

```bash
# Login to GitHub Container Registry
echo "YOUR_GITHUB_TOKEN" | docker login ghcr.io -u ward-tech-solutions --password-stdin

# Pull the seeded PostgreSQL image
docker pull ghcr.io/ward-tech-solutions/ward-flux-v2/credobank-postgres:latest

# Tag it for local use
docker tag ghcr.io/ward-tech-solutions/ward-flux-v2/credobank-postgres:latest postgres-seeded:local
```

**Option B: Export from Production Server**

```bash
# SSH to production and export database
ssh root@10.30.25.39

# On production server
cd /opt/wardops
docker compose exec postgres pg_dump -U ward_admin -Fc ward_ops > /tmp/prod_backup.dump
exit

# Back on your Mac - download the dump
scp root@10.30.25.39:/tmp/prod_backup.dump ./backups/
```

### Step 3: Start Services

**If using seeded PostgreSQL image from CI/CD:**

```bash
# Create a docker-compose.production-local.yml (see below)
docker-compose -f docker-compose.production-local.yml up -d
```

**If using exported database dump:**

```bash
# Start postgres first
docker-compose up -d postgres redis

# Wait for postgres to be ready
sleep 10

# Import database
cat backups/prod_backup.dump | docker-compose exec -T postgres pg_restore -U ward_admin -d ward_ops -c --if-exists

# Start all services
docker-compose up -d
```

---

## Configuration Files

### 1. Create `.env.production`

```bash
cp .env.production.local .env.production
```

Edit and fill in:

```env
# From production server
POSTGRES_PASSWORD=ward_admin_password
REDIS_PASSWORD=redispass
SECRET_KEY=your-production-secret-key
ENCRYPTION_KEY=your-production-encryption-key

# Others
DEFAULT_ADMIN_PASSWORD=admin123
DATABASE_URL=postgresql://ward_admin:ward_admin_password@postgres:5432/ward_ops
REDIS_URL=redis://:redispass@redis:6379/0
MONITORING_MODE=snmp_only
ENVIRONMENT=production
```

### 2. Create `docker-compose.production-local.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: postgres-seeded:local  # Or postgres:15-alpine if importing dump manually
    container_name: wardops-postgres-prod-local
    environment:
      POSTGRES_USER: ward_admin
      POSTGRES_PASSWORD: ward_admin_password
      POSTGRES_DB: ward_ops
    ports:
      - "5432:5432"  # Same port as production
    volumes:
      - postgres_data_prod:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ward_admin"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: wardops-redis-prod-local
    command: redis-server --requirepass redispass
    ports:
      - "6379:6379"  # Same port as production
    volumes:
      - redis_data_prod:/data
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    image: wardops-credobank:local
    container_name: wardops-api-prod-local
    environment:
      DATABASE_URL: postgresql://ward_admin:ward_admin_password@postgres:5432/ward_ops
      REDIS_URL: redis://:redispass@redis:6379/0
      DEFAULT_ADMIN_PASSWORD: admin123
      SECRET_KEY: local-prod-test-secret-key
      ENVIRONMENT: production
    ports:
      - "5001:8000"  # Same port as production (5001)
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs

  celery-worker:
    image: wardops-credobank:local
    container_name: wardops-worker-prod-local
    environment:
      DATABASE_URL: postgresql://ward_admin:ward_admin_password@postgres:5432/ward_ops
      REDIS_URL: redis://:redispass@redis:6379/0
      SECRET_KEY: local-prod-test-secret-key
      ENVIRONMENT: production
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
    command: celery -A celery_app worker --loglevel=info --concurrency=60

  celery-beat:
    image: wardops-credobank:local
    container_name: wardops-beat-prod-local
    environment:
      DATABASE_URL: postgresql://ward_admin:ward_admin_password@postgres:5432/ward_ops
      REDIS_URL: redis://:redispass@redis:6379/0
      SECRET_KEY: local-prod-test-secret-key
      ENVIRONMENT: production
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
    command: celery -A celery_app beat --loglevel=info

volumes:
  postgres_data_prod:
  redis_data_prod:
```

---

## Complete Setup Procedure

### Method 1: Using CI/CD Seeded Database (Fastest)

```bash
# 1. Build local image
docker build --no-cache -t wardops-credobank:local .

# 2. Pull seeded database from GitHub
docker pull ghcr.io/ward-tech-solutions/ward-flux-v2/credobank-postgres:latest
docker tag ghcr.io/ward-tech-solutions/ward-flux-v2/credobank-postgres:latest postgres-seeded:local

# 3. Start everything
docker-compose -f docker-compose.production-local.yml up -d

# 4. Check status
docker-compose -f docker-compose.production-local.yml ps

# 5. View logs
docker-compose -f docker-compose.production-local.yml logs -f
```

### Method 2: Using Production Database Dump

```bash
# 1. Build local image
docker build --no-cache -t wardops-credobank:local .

# 2. Export from production
mkdir -p backups
ssh root@10.30.25.39 "cd /opt/wardops && docker compose exec -T postgres pg_dump -U ward_admin -Fc ward_ops" > backups/prod_$(date +%Y%m%d).dump

# 3. Start postgres and redis
docker-compose -f docker-compose.production-local.yml up -d postgres redis

# 4. Wait for postgres
sleep 10

# 5. Import database
cat backups/prod_$(date +%Y%m%d).dump | docker-compose -f docker-compose.production-local.yml exec -T postgres pg_restore -U ward_admin -d ward_ops -c --if-exists

# 6. Start all services
docker-compose -f docker-compose.production-local.yml up -d

# 7. Check status
docker-compose -f docker-compose.production-local.yml ps
```

---

## Access the Application

Once started, access at:

🌐 **http://localhost:5001** (same port as production!)

**Login Credentials:**
- Username: `admin` (or your production admin username)
- Password: `admin123` (or your production admin password)

**API Documentation:**
📚 http://localhost:5001/docs

---

## Verification Checklist

Make sure everything matches production:

```bash
# 1. Check container status
docker-compose -f docker-compose.production-local.yml ps
# All containers should be "Up" and "healthy"

# 2. Check database has data
docker-compose -f docker-compose.production-local.yml exec postgres psql -U ward_admin -d ward_ops -c "SELECT COUNT(*) FROM devices;"
# Should show 873 devices (or your current count)

# 3. Check frontend file hash
docker-compose -f docker-compose.production-local.yml exec api ls -la /app/static_new/assets/ | grep "index-"
# Should show the latest file hash (e.g., index-BujfsJWt.js)

# 4. Check API health
curl http://localhost:5001/api/v1/health
# Should return {"status":"healthy"}

# 5. Check Celery workers
docker-compose -f docker-compose.production-local.yml logs celery-worker | grep "celery@"
# Should show 60 workers registered
```

---

## Common Tasks

### View Logs

```bash
# All services
docker-compose -f docker-compose.production-local.yml logs -f

# Specific service
docker-compose -f docker-compose.production-local.yml logs -f api
docker-compose -f docker-compose.production-local.yml logs -f celery-worker
```

### Shell into Containers

```bash
# API container
docker-compose -f docker-compose.production-local.yml exec api bash

# Database
docker-compose -f docker-compose.production-local.yml exec postgres psql -U ward_admin -d ward_ops
```

### Restart Services

```bash
# Restart specific service
docker-compose -f docker-compose.production-local.yml restart api

# Restart all
docker-compose -f docker-compose.production-local.yml restart
```

### Stop Everything

```bash
docker-compose -f docker-compose.production-local.yml down
```

### Clean Restart

```bash
# Remove all data and start fresh
docker-compose -f docker-compose.production-local.yml down -v
docker-compose -f docker-compose.production-local.yml up -d
```

---

## Troubleshooting

### Database Import Warnings

You might see warnings like:
```
WARNING: errors ignored on restore: 12
```

This is **normal** and happens because `pg_restore` tries to drop tables that don't exist yet. The database will import correctly.

### Port Already in Use

```bash
# Check what's using port 5001
lsof -i :5001

# Kill the process
kill -9 <PID>
```

### Containers Exit Immediately

```bash
# Check logs for errors
docker-compose -f docker-compose.production-local.yml logs api

# Common issues:
# 1. Database not ready - wait longer and restart
# 2. Missing environment variables - check .env.production
```

### "Connection Refused" to Database

```bash
# Make sure postgres is healthy
docker-compose -f docker-compose.production-local.yml ps postgres

# Wait for health check to pass
docker-compose -f docker-compose.production-local.yml logs postgres

# Restart if needed
docker-compose -f docker-compose.production-local.yml restart postgres
```

---

## Differences from Production

| Aspect | Production | Local |
|--------|-----------|-------|
| **Server** | 10.30.25.39 | localhost |
| **Database** | Production data | Copy of production |
| **Network** | Real devices accessible | Local network only (ping will fail for remote devices) |
| **Scale** | 60 workers | 60 workers (can reduce if needed) |
| **Data Changes** | Affects real system | Isolated, safe to test |

**Important**: Changes you make locally **do not** affect production! This is a completely isolated copy.

---

## Testing Workflow

1. **Run production locally** with this guide
2. **Test your changes** safely with real data
3. **Verify fixes work** as expected
4. **Commit changes** to git
5. **Wait for CI/CD** to build
6. **Deploy to production** with confidence

---

## Resource Usage

The production setup locally will use:

- **CPU**: 4-6 cores (for 60 workers)
- **Memory**: 6-8 GB
- **Disk**: ~5 GB (database + images)

Make sure Docker Desktop has these resources allocated:
Docker Desktop → Settings → Resources

---

## Quick Commands Reference

```bash
# Start
docker-compose -f docker-compose.production-local.yml up -d

# Stop
docker-compose -f docker-compose.production-local.yml down

# Logs
docker-compose -f docker-compose.production-local.yml logs -f

# Status
docker-compose -f docker-compose.production-local.yml ps

# Rebuild
docker build --no-cache -t wardops-credobank:local .
docker-compose -f docker-compose.production-local.yml up -d --build

# Clean restart
docker-compose -f docker-compose.production-local.yml down -v
docker-compose -f docker-compose.production-local.yml up -d
```

---

**You're now running production locally! 🎉**

Test all your changes safely before deploying to the real server.
