# Credo Server Deployment Commands Reference

**Server:** 10.30.25.46 (Flux)
**Docker Version:** Docker Compose V2
**Important:** Use `docker compose` (with space), NOT `docker-compose` (with hyphen)

---

## ⚠️ Common Error

```bash
# ❌ WRONG (will fail on Credo server):
docker-compose -f docker-compose.production-priority-queues.yml up -d

# Error: unknown shorthand flag: 'f' in -f
```

```bash
# ✅ CORRECT (use space, not hyphen):
docker compose -f docker-compose.production-priority-queues.yml up -d
```

**Why:** Credo server has Docker Compose V2, which uses `docker compose` as a subcommand.

---

## 🚀 Standard Deployment Commands

### Full Deployment (API + Frontend)
```bash
cd /home/wardops/ward-flux-credobank
git pull origin main

# Stop, remove, rebuild, and restart API
docker compose -f docker-compose.production-priority-queues.yml stop api && \
docker compose -f docker-compose.production-priority-queues.yml rm -f api && \
docker compose -f docker-compose.production-priority-queues.yml build --no-cache api && \
docker compose -f docker-compose.production-priority-queues.yml up -d api && \
sleep 15 && \
docker logs wardops-api-prod --tail 20
```

### Deploy Worker Changes
```bash
cd /home/wardops/ward-flux-credobank
git pull origin main

# Example: Deploy monitoring worker
docker compose -f docker-compose.production-priority-queues.yml stop celery-worker-monitoring && \
docker compose -f docker-compose.production-priority-queues.yml rm -f celery-worker-monitoring && \
docker compose -f docker-compose.production-priority-queues.yml build --no-cache celery-worker-monitoring && \
docker compose -f docker-compose.production-priority-queues.yml up -d celery-worker-monitoring && \
sleep 5 && \
docker logs wardops-worker-monitoring-prod --tail 20
```

### Deploy Celery Beat (Scheduler)
```bash
cd /home/wardops/ward-flux-credobank
git pull origin main

docker compose -f docker-compose.production-priority-queues.yml stop celery-beat && \
docker compose -f docker-compose.production-priority-queues.yml rm -f celery-beat && \
docker compose -f docker-compose.production-priority-queues.yml build --no-cache celery-beat && \
docker compose -f docker-compose.production-priority-queues.yml up -d celery-beat && \
sleep 5 && \
docker logs wardops-celery-beat-prod --tail 20
```

---

## 📦 Service Names Reference

### Container Name → Service Name Mapping

| Container Name | Service Name | Purpose |
|---|---|---|
| `wardops-api-prod` | `api` | FastAPI web server + React frontend |
| `wardops-worker-monitoring-prod` | `celery-worker-monitoring` | Ping monitoring (10s interval) |
| `wardops-worker-alerts-prod` | `celery-worker-alerts` | Alert evaluation (10s interval) |
| `wardops-worker-snmp-prod` | `celery-worker-snmp` | SNMP polling |
| `wardops-celery-beat-prod` | `celery-beat` | Task scheduler |
| `wardops-worker-maintenance-prod` | `celery-worker-maintenance` | Cleanup tasks |
| `wardops-postgres-prod` | `postgres` | PostgreSQL database |
| `wardops-redis-prod` | `redis` | Redis task queue |
| `wardops-victoriametrics-prod` | `victoriametrics` | Metrics storage |

**Important:** Use the **Service Name** in docker compose commands, not the container name!

---

## 🔍 Common Operations

### View Logs
```bash
# API logs
docker logs wardops-api-prod --tail 50 -f

# Worker logs
docker logs wardops-worker-monitoring-prod --tail 50 -f

# All container status
docker ps | grep wardops
```

### Check Container Health
```bash
# List all containers
docker compose -f docker-compose.production-priority-queues.yml ps

# Check specific service status
docker compose -f docker-compose.production-priority-queues.yml ps api
```

### Restart Service (Quick)
```bash
# Quick restart without rebuild
docker compose -f docker-compose.production-priority-queues.yml restart api

# View logs after restart
docker logs wardops-api-prod --tail 20
```

### Stop All Services
```bash
docker compose -f docker-compose.production-priority-queues.yml stop
```

### Start All Services
```bash
docker compose -f docker-compose.production-priority-queues.yml up -d
```

---

## 🗄️ Database Operations

### Connect to PostgreSQL
```bash
# Interactive psql shell
docker exec -it wardops-postgres-prod psql -U ward_admin -d ward_ops

# Run single query
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "SELECT COUNT(*) FROM standalone_devices;"
```

### Common Database Queries
```bash
# Check device count
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT COUNT(*) as total_devices FROM standalone_devices;
"

# Check ISP interfaces
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT COUNT(*) as total_isp_interfaces
FROM device_interfaces
WHERE interface_type = 'isp';
"

# Check active alerts
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT severity, COUNT(*)
FROM alert_history
WHERE resolved_at IS NULL
GROUP BY severity;
"
```

---

## 🐛 Troubleshooting

### Problem: Container Won't Start
```bash
# Check logs
docker logs wardops-api-prod --tail 100

# Check if port is in use
netstat -tulpn | grep 5001

# Force remove and recreate
docker compose -f docker-compose.production-priority-queues.yml down api
docker compose -f docker-compose.production-priority-queues.yml up -d api
```

### Problem: Frontend Not Updating
```bash
# Full rebuild with no cache
docker compose -f docker-compose.production-priority-queues.yml build --no-cache api
docker compose -f docker-compose.production-priority-queues.yml up -d api

# Clear browser cache or hard refresh (Ctrl+F5)
```

### Problem: Worker Crash Loop
```bash
# Check worker logs
docker logs wardops-worker-monitoring-prod --tail 100

# Check if Celery can connect to Redis
docker exec wardops-redis-prod redis-cli ping

# Restart worker
docker compose -f docker-compose.production-priority-queues.yml restart celery-worker-monitoring
```

### Problem: Database Connection Issues
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Test connection
docker exec wardops-postgres-prod pg_isready -U ward_admin

# Check logs
docker logs wardops-postgres-prod --tail 50
```

---

## 📝 Deployment Checklist

Before deploying:
- [ ] Code committed to main branch
- [ ] Tested locally (if possible)
- [ ] Know which service needs updating
- [ ] Have backup plan (know how to rollback)

After deploying:
- [ ] Check container status: `docker ps | grep wardops`
- [ ] View logs for errors: `docker logs <container> --tail 20`
- [ ] Test functionality in browser
- [ ] Check metrics in VictoriaMetrics
- [ ] Verify no new alerts fired

---

## 🔄 Rollback Procedure

```bash
# 1. Check what commit is currently deployed
cd /home/wardops/ward-flux-credobank
git log --oneline -1

# 2. Rollback to previous commit
git reset --hard HEAD~1

# 3. Rebuild and restart
docker compose -f docker-compose.production-priority-queues.yml stop <service>
docker compose -f docker-compose.production-priority-queues.yml rm -f <service>
docker compose -f docker-compose.production-priority-queues.yml build --no-cache <service>
docker compose -f docker-compose.production-priority-queues.yml up -d <service>

# 4. Verify rollback worked
docker logs <container> --tail 20
```

---

## ⚡ Quick Reference

```bash
# Pull latest code
cd /home/wardops/ward-flux-credobank && git pull origin main

# Rebuild API (frontend + backend)
docker compose -f docker-compose.production-priority-queues.yml stop api && \
docker compose -f docker-compose.production-priority-queues.yml rm -f api && \
docker compose -f docker-compose.production-priority-queues.yml build --no-cache api && \
docker compose -f docker-compose.production-priority-queues.yml up -d api

# View logs
docker logs wardops-api-prod --tail 20 -f

# Check status
docker ps | grep wardops

# Database query
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "SELECT COUNT(*) FROM standalone_devices;"
```

---

**Remember:** Always use `docker compose` (space) not `docker-compose` (hyphen) on Credo server!

**Last Updated:** 2025-10-27
