# 🚀 Deployment Instructions for CredoBank Server

**Server**: 10.30.25.39 (Flux)
**Working Directory on Server**: `/root/ward-ops-credobank` or `/home/wardops/ward-ops-credobank`
**GitHub Repository**: `ward-flux-credobank`

---

## 📋 Prerequisites

- SSH access to CredoBank server (through jump server)
- Git installed on server
- Docker and docker-compose running
- Current directory is `/root/ward-ops-credobank`

---

## 🎯 Quick Deployment (Recommended)

### Option 1: One-Line Command

Copy and paste this **on the CredoBank server**:

```bash
cd /root/ward-ops-credobank && \
git stash && \
git pull origin main && \
docker-compose -f docker-compose.production-local.yml down && \
docker-compose -f docker-compose.production-local.yml build --no-cache && \
docker-compose -f docker-compose.production-local.yml up -d && \
sleep 30 && \
docker-compose -f docker-compose.production-local.yml ps
```

This will:
1. ✅ Stash any local changes
2. ✅ Pull latest code from GitHub
3. ✅ Stop containers
4. ✅ Rebuild images with fixes
5. ✅ Start containers
6. ✅ Show container status

---

### Option 2: Using Deployment Script

**Step 1**: SSH to server
```bash
ssh your-jump-server
ssh root@10.30.25.39
```

**Step 2**: Navigate to directory
```bash
cd /root/ward-ops-credobank
```

**Step 3**: Pull deployment script
```bash
git pull origin main
```

**Step 4**: Run deployment
```bash
./deploy-on-server-simple.sh
```

---

## 📝 Step-by-Step Manual Deployment

If you prefer to do it manually:

### 1. SSH to Server
```bash
# From your machine to jump server
ssh your-jump-server

# From jump server to CredoBank
ssh root@10.30.25.39
```

### 2. Navigate to Project
```bash
cd /root/ward-ops-credobank
# OR
cd /home/wardops/ward-ops-credobank
```

### 3. Check Current Status
```bash
# Check git status
git status
git log -1

# Check containers
docker-compose -f docker-compose.production-local.yml ps
```

### 4. Create Backup (Optional but Recommended)
```bash
# Backup entire directory
cp -r /root/ward-ops-credobank /root/ward-ops-backup-$(date +%Y%m%d-%H%M%S)

# Backup database
docker-compose -f docker-compose.production-local.yml exec -T postgres \
    pg_dump -U ward_admin ward_ops > /root/database-backup-$(date +%Y%m%d-%H%M%S).sql
```

### 5. Pull Latest Code
```bash
# Stash any local changes
git stash save "Backup before deployment $(date)"

# Fetch updates
git fetch origin

# Pull latest from main
git pull origin main

# Verify commit
git log -1
```

### 6. Stop Containers
```bash
docker-compose -f docker-compose.production-local.yml down
```

### 7. Rebuild Docker Images
```bash
# Rebuild with no cache (ensures all fixes are included)
docker-compose -f docker-compose.production-local.yml build --no-cache
```

This will take **3-5 minutes**. You'll see:
- Building api
- Building celery-worker
- Building celery-beat

### 8. Start Containers
```bash
docker-compose -f docker-compose.production-local.yml up -d
```

### 9. Wait for Services
```bash
# Wait 30 seconds for services to initialize
sleep 30
```

### 10. Verify Deployment
```bash
# Check container status
docker-compose -f docker-compose.production-local.yml ps

# All containers should show "Up"
# If any show "Restarting" or "Exit", check logs

# Test API health
curl http://localhost:5001/api/v1/health

# Check recent logs
docker-compose -f docker-compose.production-local.yml logs --tail=50 api
```

---

## ✅ Verification Checklist

After deployment, verify:

- [ ] All containers show "Up" status
- [ ] API responds at `http://localhost:5001/api/v1/health`
- [ ] Web UI accessible at `http://10.30.25.39:5001`
- [ ] Monitor page shows devices: `http://10.30.25.39:5001/monitor`
- [ ] No errors in API logs
- [ ] Database connection working
- [ ] Celery workers running

---

## 🔍 Troubleshooting

### Containers Keep Restarting

**Check logs**:
```bash
docker-compose -f docker-compose.production-local.yml logs api
docker-compose -f docker-compose.production-local.yml logs celery-worker
```

**Common issues**:
- Database not ready: Wait 60 seconds and check again
- Migration errors: Check `logs postgres`
- Port conflicts: Check if ports 5001, 5432, 6379 are free

### API Not Responding

**Check if container is running**:
```bash
docker ps | grep api
```

**Check API logs**:
```bash
docker-compose -f docker-compose.production-local.yml logs --tail=100 api
```

**Restart just API**:
```bash
docker-compose -f docker-compose.production-local.yml restart api
```

### Database Connection Issues

**Check PostgreSQL**:
```bash
docker-compose -f docker-compose.production-local.yml logs postgres

# Test connection
docker-compose -f docker-compose.production-local.yml exec postgres \
    psql -U ward_admin -d ward_ops -c "SELECT COUNT(*) FROM standalone_devices;"
```

### Git Pull Fails

**Reset to clean state**:
```bash
# Save your changes
git stash

# Or discard all local changes
git reset --hard HEAD

# Then pull
git pull origin main
```

---

## 🔄 Rollback Procedure

If something goes wrong, rollback to previous version:

### Using Backup Directory

```bash
# Go to backup
cd /root/ward-ops-backup-YYYYMMDD-HHMMSS

# Start containers from backup
docker-compose -f docker-compose.production-local.yml down
docker-compose -f docker-compose.production-local.yml up -d
```

### Using Git

```bash
cd /root/ward-ops-credobank

# Find previous commit
git log --oneline -5

# Reset to previous commit
git reset --hard <commit-hash>

# Rebuild and restart
docker-compose -f docker-compose.production-local.yml down
docker-compose -f docker-compose.production-local.yml build --no-cache
docker-compose -f docker-compose.production-local.yml up -d
```

---

## 📊 Useful Commands

### View Logs
```bash
# All services
docker-compose -f docker-compose.production-local.yml logs -f

# Specific service
docker-compose -f docker-compose.production-local.yml logs -f api
docker-compose -f docker-compose.production-local.yml logs -f celery-worker
docker-compose -f docker-compose.production-local.yml logs -f postgres

# Last 100 lines
docker-compose -f docker-compose.production-local.yml logs --tail=100 api
```

### Container Management
```bash
# List containers
docker-compose -f docker-compose.production-local.yml ps

# Restart specific service
docker-compose -f docker-compose.production-local.yml restart api

# Stop all
docker-compose -f docker-compose.production-local.yml stop

# Start all
docker-compose -f docker-compose.production-local.yml start

# Remove all (dangerous!)
docker-compose -f docker-compose.production-local.yml down -v
```

### Database Operations
```bash
# Database shell
docker-compose -f docker-compose.production-local.yml exec postgres \
    psql -U ward_admin -d ward_ops

# Run SQL query
docker-compose -f docker-compose.production-local.yml exec postgres \
    psql -U ward_admin -d ward_ops -c "SELECT COUNT(*) FROM standalone_devices;"

# Backup database
docker-compose -f docker-compose.production-local.yml exec -T postgres \
    pg_dump -U ward_admin ward_ops > backup.sql

# Restore database
cat backup.sql | docker-compose -f docker-compose.production-local.yml exec -T postgres \
    psql -U ward_admin -d ward_ops
```

### Check Resource Usage
```bash
# Container stats
docker stats

# Disk usage
docker system df

# Clean up unused images
docker system prune -a
```

---

## 🎯 What's Being Deployed

**Phase 1 (7 Critical Fixes)**:
- ✅ Fixed bare exception handlers → specific exceptions
- ✅ Fixed undefined variable crashes → proper error handling
- ✅ Added database rollback → 13 endpoints with transaction management
- ✅ Added VictoriaMetrics timeouts → 5 HTTP call sites
- ✅ Fixed wildcard imports → explicit imports
- ✅ Made singletons thread-safe → 3 singleton classes
- ✅ Fixed asyncio event loop leaks → proper lifecycle

**Phase 2 (4 Reliability Fixes)**:
- ✅ WebSocket JSON error handling → logged errors + client feedback
- ✅ Null checks for device.ip → prevents crashes
- ✅ Global HTTP timeout (30s) → prevents worker hangs
- ✅ Database rollback in template import → data consistency

**Impact**:
- 🚫 No crashes from invalid input
- 📝 Better error visibility and logging
- 💾 Database consistency guaranteed
- ⏱️ Workers protected from hangs
- 🔒 Thread-safe operations
- 🎯 Zero configuration changes needed

---

## 📞 Support

If you encounter issues:

1. **Check logs** first
2. **Verify** all containers are running
3. **Wait** 60 seconds (services may be starting)
4. **Rollback** if needed
5. **Contact** support with log output

---

## 📌 Quick Reference

| What | Command |
|------|---------|
| SSH to server | `ssh root@10.30.25.39` |
| Project directory | `cd /root/ward-ops-credobank` |
| Pull code | `git pull origin main` |
| Rebuild | `docker-compose -f docker-compose.production-local.yml build --no-cache` |
| Restart | `docker-compose -f docker-compose.production-local.yml up -d` |
| Check status | `docker-compose -f docker-compose.production-local.yml ps` |
| View logs | `docker-compose -f docker-compose.production-local.yml logs -f api` |
| Web UI | http://10.30.25.39:5001 |
| API Health | http://10.30.25.39:5001/api/v1/health |

---

**Last Updated**: 2025-10-22
**Version**: Phase 1 & 2
**Status**: Production Ready ✅
