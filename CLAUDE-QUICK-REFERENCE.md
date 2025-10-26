# 🚀 CLAUDE QUICK REFERENCE - WARD OPS CREDOBANK

## 📍 ENVIRONMENT DETAILS

**Production Server:**
- **Hostname:** Flux
- **IP Address:** 10.30.25.46
- **Public Access:** http://10.30.25.46:5001
- **OS:** Ubuntu 24.04 LTS (Noble)
- **Location:** Credobank Data Center, Tbilisi, Georgia (GMT+4)
- **Access:** SSH via JUMP server → then SSH to `wardops@10.30.25.46`

**Project Locations:**
```
Server Path: /home/wardops/ward-flux-credobank
Local Dev: /Users/g.jalabadze/Desktop/WARD OPS/ward-ops-credobank
Git Repo: https://github.com/ward-tech-solutions/ward-flux-credobank.git
Branch: main
```

**Active Docker Containers:**
```
wardops-api-prod              - FastAPI application (port 5001)
wardops-postgres-prod         - PostgreSQL 15 database (port 5433)
wardops-redis-prod            - Redis cache (port 6380)
wardops-victoriametrics-prod  - VictoriaMetrics TSDB (port 8428)
wardops-worker-monitoring-prod - Celery worker (monitoring queue)
wardops-worker-snmp-prod      - Celery worker (SNMP queue)
wardops-worker-alerts-prod    - Celery worker (alerts queue)
wardops-worker-maintenance-prod - Celery worker (maintenance queue)
wardops-beat-prod             - Celery beat scheduler
```

## 🔧 CRITICAL COMMANDS

### Deploy Changes to Production
```bash
# Quick deploy (use this!)
cd /home/wardops/ward-flux-credobank
bash FINAL-PRODUCTION-DEPLOYMENT.sh

# Manual deploy
cd /home/wardops/ward-flux-credobank
git pull origin main
docker-compose -f docker-compose.production-priority-queues.yml build api celery-worker-monitoring
docker stop wardops-api-prod wardops-worker-monitoring-prod
docker rm wardops-api-prod wardops-worker-monitoring-prod
docker-compose -f docker-compose.production-priority-queues.yml up -d api celery-worker-monitoring
```

### Check System Status
```bash
# View running containers
docker ps

# Check API health
curl http://localhost:5001/api/v1/health

# Database connection
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "SELECT COUNT(*) FROM standalone_devices;"

# Redis connection
docker exec wardops-redis-prod redis-cli -a redispass ping
```

### Monitor Logs
```bash
# API logs
docker logs -f wardops-api-prod

# Worker logs (device monitoring)
docker logs -f wardops-worker-monitoring-prod

# Watch for status changes
docker logs -f wardops-worker-monitoring-prod 2>&1 | grep -E "DOWN|RECOVERED|🔔|🗑️"
```

## 🐛 CRITICAL ISSUE FIXED

**Original Problem:** "ZABBIX IS BEATING US - Devices show UP in monitor but are actually DOWN"

**Root Cause:** Multiple API endpoints using stale `PingResult.is_reachable` instead of `device.down_since`

**Solution:** ALL endpoints now use `device.down_since` as single source of truth:
- `NULL` = Device is UP
- `Timestamp` = Device is DOWN since that time

**Fixed Files:**
- `routers/devices.py` - Main device list
- `routers/infrastructure.py` - Infrastructure map
- `routers/websockets.py` - Real-time updates
- `routers/dashboard.py` - Dashboard stats
- `monitoring/tasks_batch.py` - Cache clearing

## 📂 KEY FILES TO KNOW

### Core Device Status Logic
- **`monitoring/tasks_batch.py`** - Pings devices, sets `down_since`, clears cache
- **`routers/devices.py`** - Main API endpoint for device list
- **`routers/devices_standalone.py`** - Standalone device management

### Database Models
- **`monitoring/models.py`** - StandaloneDevice model with `down_since` field
- **`database.py`** - Database connection setup

### Configuration
- **`docker-compose.production-priority-queues.yml`** - Container definitions
- **`.env.production`** - Environment variables (contains passwords)

## 🔄 TYPICAL WORKFLOW

1. **Make changes locally:**
   ```bash
   cd /Users/g.jalabadze/Desktop/WARD\ OPS/ward-ops-credobank
   # Edit files
   git add .
   git commit -m "Fix: description"
   git push origin main
   ```

2. **Deploy to production:**
   ```bash
   ssh wardops@10.30.25.46
   cd /home/wardops/ward-flux-credobank
   bash FINAL-PRODUCTION-DEPLOYMENT.sh
   ```

3. **Verify fix:**
   - Open browser: http://10.30.25.46:5001
   - Hard refresh: Ctrl+F5
   - Check device status matches reality

## ⚠️ IMPORTANT NOTES

### What's NOT Used Anymore
- ❌ SQLite database (`data/ward_ops.db`) - deprecated
- ❌ Zabbix integration - removed
- ❌ PostgreSQL `ping_results` table - stale after Phase 2
- ❌ Flapping detector - broken, uses old PingResult table

### What IS Used
- ✅ PostgreSQL `standalone_devices` table
- ✅ `device.down_since` field (source of truth)
- ✅ VictoriaMetrics for time-series data
- ✅ Redis for API response caching
- ✅ Celery Beat for scheduling

### Database Credentials
```python
Database: PostgreSQL
Host: wardops-postgres-prod (container)
Port: 5433 (exposed), 5432 (internal)
User: ward_admin
Password: ward_admin_password
Database: ward_ops
```

### Redis Credentials
```python
Host: wardops-redis-prod (container)
Port: 6380 (exposed), 6379 (internal)
Password: redispass
```

## 🎯 QUICK FIXES

### If devices show wrong status:
1. Check `down_since` in database:
   ```bash
   docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops \
     -c "SELECT name, ip, down_since FROM standalone_devices WHERE ip = '10.195.110.51';"
   ```

2. Force cache clear:
   ```bash
   docker exec wardops-redis-prod redis-cli -a redispass FLUSHALL
   ```

3. Restart monitoring worker:
   ```bash
   docker restart wardops-worker-monitoring-prod
   ```

### If deployment fails:
1. Check docker-compose syntax:
   ```bash
   docker-compose -f docker-compose.production-priority-queues.yml config
   ```

2. Remove stuck containers:
   ```bash
   docker ps -a | grep Exited
   docker rm [container_id]
   ```

3. Rebuild from scratch:
   ```bash
   docker-compose -f docker-compose.production-priority-queues.yml build --no-cache api
   ```

## 📊 MONITORING INTERVALS

- **Device Ping:** Every 10 seconds (batched)
- **SNMP Poll:** Every 60 seconds
- **Cache TTL:** 30 seconds (but clears on status change)
- **WebSocket Heartbeat:** Every 15 seconds
- **Alert Evaluation:** Every 30 seconds

## 🔍 DEBUGGING CHECKLIST

When debugging device status issues:

1. [ ] Check database `down_since` value
2. [ ] Verify monitoring worker is running
3. [ ] Check for cache keys in Redis
4. [ ] Look for status change logs in worker
5. [ ] Verify API returns correct status
6. [ ] Hard refresh browser
7. [ ] Check browser console for JS errors

## 📝 DEPLOYMENT SCRIPTS AVAILABLE

- **`FINAL-PRODUCTION-DEPLOYMENT.sh`** - Complete deployment with all fixes
- **`DEPLOY-COMPLETE-FIX.sh`** - Deploy status fix only
- **`deploy-diagnostic-logging.sh`** - Deploy with extra logging
- **`deploy-critical-status-fix.sh`** - Initial status fix deployment

## 💡 PRO TIPS

1. **Always hard refresh** browser after deployment (Ctrl+F5)
2. **Monitor worker logs** during deployment for errors
3. **Check database first** when debugging - it's the source of truth
4. **Use grep with emojis** to find important logs: `grep "🔔\|🗑️\|✅\|❌"`
5. **Don't trust browser cache** - use incognito mode for testing

---

**Last Updated:** October 26, 2025
**System Version:** WARD OPS v2.0 - Banking Edition
**Maintainer:** WARD Tech Solutions