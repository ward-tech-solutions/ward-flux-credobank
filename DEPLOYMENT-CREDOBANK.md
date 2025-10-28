# WARD FLUX - Credobank Server Deployment Guide

**Server**: Credobank Production Server (Flux)
**Location**: `/home/wardops/ward-flux-credobank`
**Docker Compose**: `docker-compose.production-priority-queues.yml`

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Standard Deployment](#standard-deployment)
3. [Emergency Rollback](#emergency-rollback)
4. [Interface Discovery](#interface-discovery)
5. [Monitoring & Logs](#monitoring--logs)
6. [Troubleshooting](#troubleshooting)
7. [Database Operations](#database-operations)

---

## Prerequisites

### Required Access
- SSH access to Credobank server
- Root or sudo privileges
- Git access to repository

### Running Services
```bash
# Check current running containers
docker-compose -f docker-compose.production-priority-queues.yml ps
```

Expected containers:
- `wardops-postgres-prod` - PostgreSQL database
- `wardops-redis-prod` - Redis cache
- `wardops-victoriametrics-prod` - Metrics storage
- `wardops-api-prod` - API + Frontend
- `wardops-beat-prod` - Celery Beat scheduler
- `wardops-worker-alerts-prod` - Alert worker
- `wardops-worker-monitoring-prod` - Monitoring worker
- `wardops-worker-snmp-prod` - SNMP worker
- `wardops-worker-maintenance-prod` - Maintenance worker

---

## Standard Deployment

### Step 1: Navigate to Project Directory
```bash
cd /home/wardops/ward-flux-credobank
```

### Step 2: Backup Current State (Optional but Recommended)
```bash
# Note current commit
git log --oneline -1 > /tmp/deployment-backup-$(date +%Y%m%d-%H%M%S).txt

# Backup database (if needed)
docker exec wardops-postgres-prod pg_dump -U ward_admin ward_ops > /tmp/ward_ops_backup_$(date +%Y%m%d-%H%M%S).sql
```

### Step 3: Pull Latest Changes
```bash
# Fetch latest from GitHub
git fetch origin

# Pull changes
git pull origin main
```

### Step 4: Check What Changed
```bash
# Show files that changed
git diff HEAD@{1} --name-only

# If backend changed (Python files)
git diff HEAD@{1} --name-only | grep -E "\.py$|requirements\.txt"

# If frontend changed (TypeScript/React files)
git diff HEAD@{1} --name-only | grep -E "frontend/src/"

# If database migrations changed
git diff HEAD@{1} --name-only | grep -E "migrations/"
```

### Step 5: Deploy Based on Changes

#### Option A: Only Frontend Changed (Fast - 30 seconds)
```bash
# Just restart API (frontend is built inside API container on startup)
docker-compose -f docker-compose.production-priority-queues.yml restart api

# Check API logs
docker-compose -f docker-compose.production-priority-queues.yml logs --tail=50 api
```

#### Option B: Backend Changed (Medium - 2-3 minutes)
```bash
# Rebuild and restart API + workers
docker-compose -f docker-compose.production-priority-queues.yml up -d --build api celery-worker-snmp celery-worker-monitoring celery-worker-alerts

# Check logs
docker-compose -f docker-compose.production-priority-queues.yml logs --tail=50 api
```

#### Option C: Major Changes or Complete Rebuild (Slow - 5-10 minutes)
```bash
# Stop all services
docker-compose -f docker-compose.production-priority-queues.yml down

# Rebuild everything from scratch (no cache)
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache

# Start all services
docker-compose -f docker-compose.production-priority-queues.yml up -d

# Check all containers started
docker-compose -f docker-compose.production-priority-queues.yml ps
```

### Step 6: Verify Deployment
```bash
# Check API health
curl -f http://localhost:5001/api/v1/health

# Check API logs for errors
docker-compose -f docker-compose.production-priority-queues.yml logs --tail=100 api | grep -i error

# Check worker status
docker-compose -f docker-compose.production-priority-queues.yml ps | grep -E "worker|beat"
```

### Step 7: Clear Browser Cache
**Important**: After deployment, users must:
1. Clear browser cache (Ctrl+Shift+Delete → Clear all)
2. Hard refresh (Ctrl+Shift+R)
3. Or open in incognito/private mode

---

## Emergency Rollback

### Quick Rollback to Previous Commit
```bash
cd /home/wardops/ward-flux-credobank

# Check current commit
git log --oneline -1

# View recent commits to find stable version
git log --oneline -10

# Rollback to specific commit (replace COMMIT_HASH)
git reset --hard COMMIT_HASH

# Force push to GitHub (if needed)
# git push origin main --force

# Rebuild and restart
docker-compose -f docker-compose.production-priority-queues.yml down
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache
docker-compose -f docker-compose.production-priority-queues.yml up -d
```

### Rollback to Last Working State
```bash
# View reflog to see previous HEAD positions
git reflog

# Reset to previous state (1 commit back)
git reset --hard HEAD@{1}

# Or reset to 5 commits back
git reset --hard HEAD~5

# Rebuild
docker-compose -f docker-compose.production-priority-queues.yml down
docker-compose -f docker-compose.production-priority-queues.yml up -d --build
```

### Known Stable Commits
| Commit | Date | Description | Status |
|--------|------|-------------|--------|
| `972d85b` | 2024-10-XX | WARD colors + dark mode | ✅ Stable |
| `6bda097` | 2024-10-XX | Modern topology design | ✅ Stable |

To rollback to known stable commit:
```bash
git reset --hard 972d85b
docker-compose -f docker-compose.production-priority-queues.yml down
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache
docker-compose -f docker-compose.production-priority-queues.yml up -d
```

---

## Interface Discovery

Interface discovery finds and stores network interfaces for devices.

### Check Discovery Status
```bash
# Check how many interfaces discovered
docker exec -it wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT COUNT(*) as total_interfaces FROM device_interfaces WHERE enabled = true;
"

# Check devices with interfaces
docker exec -it wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    COUNT(DISTINCT device_id) as devices_with_interfaces,
    COUNT(*) as total_interfaces
FROM device_interfaces
WHERE enabled = true;
"
```

### Trigger Discovery for One Device
```bash
# Discover interfaces for specific IP
docker exec -it wardops-api-prod python3 trigger_discovery.py 10.195.57.5

# Example output:
# ✅ Found device: 10.195.57.5 (ID: xxx)
# ✅ SNMP credentials: version=2c
# Success: True
# Interfaces found: 21
# Interfaces saved: 20
# 🎯 ISP Interfaces (3):
#    - Fa3: magti
#    - Fa4: silknet
```

### Trigger Discovery for All Devices
```bash
# Queue discovery task for all 93 ISP routers (takes 10-15 minutes)
docker exec -it wardops-api-prod python3 -c "
from celery_app_v2_priority_queues import app
result = app.send_task('monitoring.tasks.discover_all_interfaces')
print(f'✅ Discovery task queued: {result.id}')
"

# Monitor progress
docker logs -f wardops-worker-snmp-prod
```

### Automatic Discovery Schedule
Discovery runs automatically:
- **Time**: Daily at 2:30 AM
- **Task**: `discover-all-interfaces`
- **Queue**: `snmp`
- **Worker**: `wardops-worker-snmp-prod`

---

## Monitoring & Logs

### View Container Logs
```bash
# API logs (frontend + backend)
docker-compose -f docker-compose.production-priority-queues.yml logs -f api

# All workers
docker-compose -f docker-compose.production-priority-queues.yml logs -f celery-worker-snmp celery-worker-monitoring celery-worker-alerts

# Specific worker
docker logs -f wardops-worker-snmp-prod

# Beat scheduler
docker logs -f wardops-beat-prod

# Last 100 lines
docker-compose -f docker-compose.production-priority-queues.yml logs --tail=100 api
```

### Check Container Health
```bash
# All containers status
docker-compose -f docker-compose.production-priority-queues.yml ps

# Container resource usage
docker stats --no-stream

# Specific container details
docker inspect wardops-api-prod

# Check container restart count
docker inspect wardops-api-prod | grep -A 5 RestartCount
```

### Check Service Health Endpoints
```bash
# API health
curl http://localhost:5001/api/v1/health

# VictoriaMetrics health
curl http://localhost:8428/health

# Redis
docker exec wardops-redis-prod redis-cli -a redispass PING

# PostgreSQL
docker exec wardops-postgres-prod pg_isready -U ward_admin
```

### Monitor Celery Workers
```bash
# Check worker status
docker exec -it wardops-worker-snmp-prod celery -A celery_app_v2_priority_queues inspect active

# Check registered tasks
docker exec -it wardops-worker-snmp-prod celery -A celery_app_v2_priority_queues inspect registered

# Check worker stats
docker exec -it wardops-worker-snmp-prod celery -A celery_app_v2_priority_queues inspect stats
```

---

## Troubleshooting

### API Not Responding
```bash
# Check if container is running
docker-compose -f docker-compose.production-priority-queues.yml ps api

# Check logs for errors
docker-compose -f docker-compose.production-priority-queues.yml logs --tail=200 api | grep -i error

# Restart API
docker-compose -f docker-compose.production-priority-queues.yml restart api

# If still not working, rebuild
docker-compose -f docker-compose.production-priority-queues.yml up -d --build api
```

### Frontend Not Loading / Showing Old Version
```bash
# Check if frontend was built
docker-compose -f docker-compose.production-priority-queues.yml logs api | grep -i "frontend\|build"

# Force rebuild API (includes frontend)
docker-compose -f docker-compose.production-priority-queues.yml up -d --build --no-deps api

# Clear browser cache and hard refresh (Ctrl+Shift+R)
```

### Database Connection Errors
```bash
# Check PostgreSQL is running
docker-compose -f docker-compose.production-priority-queues.yml ps postgres

# Check PostgreSQL logs
docker logs wardops-postgres-prod --tail=100

# Test connection
docker exec -it wardops-postgres-prod psql -U ward_admin -d ward_ops -c "SELECT 1;"

# Restart PostgreSQL
docker-compose -f docker-compose.production-priority-queues.yml restart postgres
```

### Redis Connection Errors
```bash
# Check Redis is running
docker-compose -f docker-compose.production-priority-queues.yml ps redis

# Test Redis
docker exec wardops-redis-prod redis-cli -a redispass PING

# Check Redis memory
docker exec wardops-redis-prod redis-cli -a redispass INFO memory

# Restart Redis
docker-compose -f docker-compose.production-priority-queues.yml restart redis
```

### Workers Not Processing Tasks
```bash
# Check worker status
docker-compose -f docker-compose.production-priority-queues.yml ps | grep worker

# Check worker logs
docker logs -f wardops-worker-snmp-prod

# Restart workers
docker-compose -f docker-compose.production-priority-queues.yml restart celery-worker-snmp celery-worker-monitoring celery-worker-alerts

# Check Celery Beat scheduler
docker logs -f wardops-beat-prod
```

### Disk Space Issues
```bash
# Check disk usage
df -h

# Check Docker disk usage
docker system df

# Clean up old images/containers (be careful!)
docker system prune -a

# Clean old logs
docker-compose -f docker-compose.production-priority-queues.yml logs --tail=0 api
```

### Memory Issues
```bash
# Check container memory usage
docker stats --no-stream

# Check system memory
free -h

# Restart memory-heavy workers
docker-compose -f docker-compose.production-priority-queues.yml restart celery-worker-snmp
```

---

## Database Operations

### Connect to Database
```bash
# Connect to PostgreSQL
docker exec -it wardops-postgres-prod psql -U ward_admin -d ward_ops
```

### Useful Database Queries
```sql
-- Check device count
SELECT COUNT(*) FROM standalone_devices;

-- Check .5 devices (ISP routers)
SELECT COUNT(*) FROM standalone_devices WHERE ip LIKE '%.5';

-- Check interface count
SELECT COUNT(*) FROM device_interfaces WHERE enabled = true;

-- Check devices with interfaces
SELECT
    d.ip,
    d.name,
    COUNT(i.id) as interface_count
FROM standalone_devices d
LEFT JOIN device_interfaces i ON i.device_id = d.id AND i.enabled = true
WHERE d.ip LIKE '%.5'
GROUP BY d.ip, d.name
ORDER BY interface_count DESC
LIMIT 20;

-- Check recent alerts
SELECT * FROM alerts ORDER BY created_at DESC LIMIT 10;

-- Check metrics count
SELECT
    date_trunc('day', timestamp) as day,
    COUNT(*) as metric_count
FROM interface_metrics
GROUP BY day
ORDER BY day DESC
LIMIT 7;
```

### Database Backup
```bash
# Full backup
docker exec wardops-postgres-prod pg_dump -U ward_admin ward_ops > /tmp/ward_ops_backup_$(date +%Y%m%d-%H%M%S).sql

# Compressed backup
docker exec wardops-postgres-prod pg_dump -U ward_admin ward_ops | gzip > /tmp/ward_ops_backup_$(date +%Y%m%d-%H%M%S).sql.gz

# Backup specific tables
docker exec wardops-postgres-prod pg_dump -U ward_admin -t standalone_devices -t device_interfaces ward_ops > /tmp/ward_ops_devices_backup.sql
```

### Database Restore
```bash
# Restore from backup
docker exec -i wardops-postgres-prod psql -U ward_admin ward_ops < /tmp/ward_ops_backup.sql

# Restore compressed backup
gunzip -c /tmp/ward_ops_backup.sql.gz | docker exec -i wardops-postgres-prod psql -U ward_admin ward_ops
```

---

## Quick Reference Commands

### Most Common Operations

```bash
# Standard deployment (frontend/backend changes)
cd /home/wardops/ward-flux-credobank
git pull origin main
docker-compose -f docker-compose.production-priority-queues.yml restart api

# Complete rebuild (major changes)
cd /home/wardops/ward-flux-credobank
git pull origin main
docker-compose -f docker-compose.production-priority-queues.yml down
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache
docker-compose -f docker-compose.production-priority-queues.yml up -d

# Check everything is running
docker-compose -f docker-compose.production-priority-queues.yml ps
curl http://localhost:5001/api/v1/health

# View logs
docker-compose -f docker-compose.production-priority-queues.yml logs -f api

# Rollback to stable version
git reset --hard 972d85b
docker-compose -f docker-compose.production-priority-queues.yml down
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache
docker-compose -f docker-compose.production-priority-queues.yml up -d
```

---

## Environment Variables

Key environment variables (set in docker-compose file):
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection
- `VICTORIA_URL` - VictoriaMetrics URL
- `SECRET_KEY` - JWT secret
- `WARD_ENCRYPTION_KEY` - Encryption key for credentials
- `ENVIRONMENT` - `production`
- `MONITORING_MODE` - `snmp_only`

To check environment:
```bash
docker exec wardops-api-prod env | grep -E "DATABASE_URL|REDIS_URL|VICTORIA_URL|ENVIRONMENT"
```

---

## Support

**Issues or Questions:**
- GitHub Issues: https://github.com/ward-tech-solutions/ward-flux-credobank/issues
- Check logs first: `docker-compose -f docker-compose.production-priority-queues.yml logs`
- Try rollback to last known stable commit

**Last Updated:** October 28, 2025
**Version:** v2.0 (Priority Queue Architecture)
