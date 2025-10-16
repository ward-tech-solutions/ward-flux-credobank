# Update Existing CredoBank WARD OPS Deployment

> **Guide for updating an already-deployed WARD OPS system to the latest version**

---

## 🎯 Overview

This guide covers updating an existing WARD OPS deployment with:
- ✅ New Alert Rules page with modern UI
- ✅ Database migration for alert trigger tracking
- ✅ 60 Celery workers for 15-second ping intervals
- ✅ Modal scrolling fixes
- ✅ All bug fixes and improvements

**Downtime**: ~2-5 minutes
**Data Loss**: None (preserves all data)

---

## ⚠️ Pre-Update Checklist

Before starting the update:

- [ ] **Backup the database** (critical!)
- [ ] **Note the current version/commit**
- [ ] **Check disk space** (need ~2GB for new images)
- [ ] **Verify you have server access** (SSH + sudo)
- [ ] **Inform users** of brief maintenance window

---

## 📋 Step-by-Step Update Procedure

### Step 1: SSH to CredoBank Server

```bash
# Through jump host
ssh -J jumpuser@jump.credobank.com username@credobank-server

# Or directly if accessible
ssh username@credobank-server
```

---

### Step 2: Backup Current Database (CRITICAL!)

```bash
# Navigate to deployment directory
cd /opt/wardops

# Backup database
sudo docker compose exec postgres pg_dump -U ward_admin ward_ops > backup_$(date +%Y%m%d_%H%M%S).sql

# Verify backup was created
ls -lh backup_*.sql

# Move backup to safe location
sudo mkdir -p /opt/wardops/backups
sudo mv backup_*.sql /opt/wardops/backups/
```

**⚠️ DO NOT SKIP THIS STEP!** This backup lets you rollback if anything goes wrong.

---

### Step 3: Check Current State

```bash
cd /opt/wardops

# Check running containers
sudo docker compose ps

# Check current images
sudo docker images | grep wardops

# Note current version
sudo docker compose exec api python -c "print('Current version')"
```

---

### Step 4: Pull Latest Docker Images

```bash
cd /opt/wardops

# Pull latest images from GitHub Container Registry
# (After CI/CD pipeline completes - wait for green checkmark on GitHub Actions)
sudo docker compose pull

# This will download:
# - ghcr.io/ward-tech-solutions/ward-flux-v2/credobank:latest
# - ghcr.io/ward-tech-solutions/ward-flux-v2/credobank-postgres:latest
```

**Expected output:**
```
Pulling api           ... done
Pulling celery-worker ... done
Pulling postgres      ... done
```

---

### Step 5: Run Database Migration

**Important:** The migration must run BEFORE restarting services.

```bash
cd /opt/wardops

# Run migration in existing database container
sudo docker compose exec postgres psql -U ward_admin -d ward_ops -c "
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS last_triggered_at TIMESTAMP;
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS trigger_count_24h INTEGER DEFAULT 0;
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS trigger_count_7d INTEGER DEFAULT 0;
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS affected_devices_count INTEGER DEFAULT 0;
"

# Verify columns were added
sudo docker compose exec postgres psql -U ward_admin -d ward_ops -c "\d alert_rules"
```

**Expected output:**
```
ALTER TABLE
ALTER TABLE
ALTER TABLE
ALTER TABLE
```

You should see the new columns in the table description.

---

### Step 6: Update Celery Worker Configuration

```bash
cd /opt/wardops

# Edit docker-compose.yml
sudo nano docker-compose.yml
```

**Find this line** (around line 92):
```yaml
command: celery -A celery_app worker --loglevel=info --concurrency=4
```

**Change to:**
```yaml
command: celery -A celery_app worker --loglevel=info --concurrency=60
```

**Save and exit** (Ctrl+X, Y, Enter)

---

### Step 7: Restart Services with New Images

```bash
cd /opt/wardops

# Stop all services
sudo docker compose down

# Start with new images
sudo docker compose up -d

# Wait for services to start (~30 seconds)
sleep 30
```

---

### Step 8: Verify Update Success

```bash
cd /opt/wardops

# Check all containers are running
sudo docker compose ps

# Check API health
curl http://localhost:5001/api/v1/health

# Check logs for errors
sudo docker compose logs api --tail=50

# Check Celery workers
sudo docker compose logs celery-worker --tail=50 | grep "concurrency"
```

**Expected outputs:**

1. **docker compose ps** - All services should show "Up" or "Up (healthy)"
2. **Health check** - Should return `{"status":"healthy",...}`
3. **Celery logs** - Should show `concurrency: 60`

---

### Step 9: Test New Features

**Test in browser:**
1. Open `http://<server-ip>:5001`
2. Login with admin credentials
3. Navigate to **Alert Rules** page
4. Verify:
   - ✅ Modal opens and scrolls properly
   - ✅ Visual Rule Builder appears when selecting "Custom Expression"
   - ✅ Create a test rule works
   - ✅ Bulk operations (select multiple rules) works
   - ✅ Filter persistence (refresh page, filters remain)

**Test device monitoring:**
```bash
# Check that ping intervals are ~15-20 seconds
sudo docker compose logs celery-worker -f

# Watch for ping task executions - should happen every 15-20 seconds
```

---

## ✅ Post-Update Verification Checklist

- [ ] All Docker containers running and healthy
- [ ] API health check returns success
- [ ] Can login to web interface
- [ ] Alert Rules page loads and functions
- [ ] Dashboard shows all 873 devices
- [ ] Active Alerts section displays properly
- [ ] Ping monitoring working (check logs)
- [ ] Celery running with 60 workers
- [ ] Database migration columns exist

---

## 🔄 Rollback Procedure (If Something Goes Wrong)

### Quick Rollback

```bash
cd /opt/wardops

# Stop current version
sudo docker compose down

# Restore database backup
sudo docker compose up -d postgres
sleep 10
cat /opt/wardops/backups/backup_YYYYMMDD_HHMMSS.sql | sudo docker compose exec -T postgres psql -U ward_admin ward_ops

# Revert docker-compose.yml changes
sudo nano docker-compose.yml
# Change concurrency back to 4

# Pull previous image version (if you noted the tag)
# Edit docker-compose.yml to use specific image tag instead of :latest
# image: ghcr.io/ward-tech-solutions/ward-flux-v2/credobank:PREVIOUS_TAG

# Restart with old version
sudo docker compose up -d
```

---

## 📊 What's New in This Update

### Frontend Changes
- **Alert Rules Page**: Complete redesign with modern UI
- **Modal Scrolling**: Fixed overflow and scrolling issues
- **Visual Rule Builder**: Build expressions without code
- **Filter Persistence**: Filters saved across page reloads
- **Bulk Operations**: Enable/disable/delete multiple rules
- **Expandable Analytics**: Click to see rule statistics

### Backend Changes
- **Database Schema**: 4 new columns for alert tracking
- **Celery Scaling**: 4→60 workers for better performance
- **Ping Intervals**: Now 15-20 seconds (was 3-4 minutes)

### Bug Fixes
- Fixed WebSocket infinite reconnection
- Fixed multi-region user filtering
- Fixed device count display (873 devices now visible)
- Fixed TypeScript compilation errors

---

## 🐛 Troubleshooting

### Issue: Containers won't start after update

**Solution:**
```bash
# Check logs
sudo docker compose logs

# Check disk space
df -h

# Try pulling images again
sudo docker compose pull
sudo docker compose up -d
```

---

### Issue: Database migration fails

**Solution:**
```bash
# Check if columns already exist
sudo docker compose exec postgres psql -U ward_admin -d ward_ops -c "\d alert_rules"

# If migration partially completed, it's safe to re-run
# The IF NOT EXISTS clause prevents errors
```

---

### Issue: Old images taking up space

**Solution:**
```bash
# List all images
sudo docker images

# Remove old/unused images
sudo docker image prune -a

# Remove specific old image
sudo docker rmi <IMAGE_ID>
```

---

### Issue: Celery workers not starting with concurrency=60

**Solution:**
```bash
# Check resource limits
free -h
top

# If insufficient RAM, reduce to 40-50 workers
sudo nano docker-compose.yml
# Change concurrency=60 to concurrency=40
sudo docker compose restart celery-worker
```

---

### Issue: Alert Rules page not loading

**Solution:**
```bash
# Check frontend build
sudo docker compose logs api | grep -i vite

# Force rebuild if needed
sudo docker compose build --no-cache api
sudo docker compose up -d api
```

---

## 📞 Support

**If you encounter issues:**

1. **Check logs**: `sudo docker compose logs -f`
2. **Check GitHub Issues**: https://github.com/ward-tech-solutions/ward-flux-v2/issues
3. **Restore backup**: Follow rollback procedure above
4. **Contact support**: Provide logs and error messages

---

## 🎯 Quick Command Reference

```bash
# Update procedure (short version)
cd /opt/wardops
sudo docker compose exec postgres pg_dump -U ward_admin ward_ops > backup.sql
sudo docker compose pull
sudo docker compose exec postgres psql -U ward_admin -d ward_ops -c "ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS last_triggered_at TIMESTAMP, ADD COLUMN IF NOT EXISTS trigger_count_24h INTEGER DEFAULT 0, ADD COLUMN IF NOT EXISTS trigger_count_7d INTEGER DEFAULT 0, ADD COLUMN IF NOT EXISTS affected_devices_count INTEGER DEFAULT 0;"
sudo nano docker-compose.yml  # Change concurrency to 60
sudo docker compose down
sudo docker compose up -d
sudo docker compose ps
curl http://localhost:5001/api/v1/health

# Rollback (if needed)
cd /opt/wardops
sudo docker compose down
sudo docker compose up -d postgres
cat backup.sql | sudo docker compose exec -T postgres psql -U ward_admin ward_ops
sudo nano docker-compose.yml  # Revert concurrency to 4
sudo docker compose up -d
```

---

## ✨ Summary

This update brings significant improvements to the Alert Rules page, fixes critical bugs, and dramatically improves monitoring performance with 60 Celery workers. The update is **safe** and **reversible** if you follow the backup steps.

**Total time**: 5-10 minutes
**Downtime**: 2-5 minutes
**Risk**: Low (if backup is taken)

**Ready to update? Follow the steps above carefully!** 🚀
