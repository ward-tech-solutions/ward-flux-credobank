# Deploy WARD OPS on CredoBank Server

## Quick Deploy (From Server)

Since you're already SSH'd into the CredoBank server via jump host, run this **ON THE SERVER**:

```bash
cd /root/ward-ops-credobank
./deploy-on-server.sh
```

That's it! The script will handle everything automatically.

## What the Script Does

1. ✅ Creates automatic backup at `/root/ward-ops-backup-[timestamp]`
2. ✅ Pulls latest code from GitHub (ward-flux-credobank)
3. ✅ Stops running containers
4. ✅ Builds new Docker images with cache busting
5. ✅ Starts containers with optimizations (50 workers)
6. ✅ Verifies API health
7. ✅ Shows deployment summary

## What Gets Deployed

Latest version includes:
- ✅ **Monitor page fix**: Devices show correct UP/DOWN status immediately
- ✅ **Zabbix removed**: 30% less code (643 lines removed)
- ✅ **SNMP GETBULK**: 60% faster polling for SNMPv2c/v3
- ✅ **Worker optimization**: 50 workers (down from 100) = 50% less RAM

## Manual Steps (If Script Fails)

If you need to deploy manually:

```bash
# 1. SSH to server (you're already there)
cd /root/ward-ops-credobank

# 2. Backup
cp -r /root/ward-ops-credobank /root/ward-ops-backup-$(date +%Y%m%d-%H%M%S)

# 3. Pull latest code
git fetch origin
git reset --hard origin/main

# 4. Stop containers
docker-compose -f docker-compose.production-local.yml stop

# 5. Rebuild images
CACHE_BUST=$(date +%s)
docker-compose -f docker-compose.production-local.yml build \
    --no-cache \
    --build-arg CACHE_BUST="${CACHE_BUST}" \
    api celery-worker celery-beat

# 6. Start containers
docker-compose -f docker-compose.production-local.yml up -d

# 7. Check status
docker-compose -f docker-compose.production-local.yml ps
curl http://localhost:5001/api/v1/health
```

## After Deployment - Verify

### 1. Check Monitor Page
- Open: http://10.30.25.39:5001
- Go to Monitor page
- Devices should show correct status based on latest ping
- UP devices should NOT show "Down Xm" anymore

### 2. Watch Live State Transitions
```bash
# See devices going UP (✅) and DOWN (❌) in real-time
docker-compose -f docker-compose.production-local.yml logs -f celery-worker | grep -E '✅|❌'
```

You'll see logs like:
```
✅ Device Khulo-881 (10.195.53.250) RECOVERED - was DOWN for 0:06:00
❌ Device Khulo-881 (10.195.53.250) went DOWN
Clearing down_since for Khulo-881 (10.195.53.250) - device is UP
```

### 3. Verify API Health
```bash
curl http://localhost:5001/api/v1/health
```

Should return:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "components": {
    "database": "healthy",
    "api": "healthy"
  }
}
```

### 4. Check Worker Status
```bash
docker-compose -f docker-compose.production-local.yml exec celery-worker \
    celery -A celery_app inspect stats | grep concurrency
```

Should show: `"concurrency": 50`

## Rollback (If Needed)

If something goes wrong:

```bash
# Find latest backup
ls -lt /root/ward-ops-backup-* | head -1

# Stop current deployment
cd /root/ward-ops-credobank
docker-compose -f docker-compose.production-local.yml down

# Restore from backup
BACKUP_PATH="/root/ward-ops-backup-YYYYMMDD-HHMMSS"  # Use actual path
cd "${BACKUP_PATH}"
docker-compose -f docker-compose.production-local.yml up -d
```

## Troubleshooting

### Issue: Script not found
```bash
# Make sure you're in the right directory
cd /root/ward-ops-credobank

# Make script executable
chmod +x deploy-on-server.sh

# Run script
./deploy-on-server.sh
```

### Issue: Git pull fails
```bash
# Check current changes
git status

# Stash local changes
git stash

# Pull again
git pull origin main
```

### Issue: Containers won't start
```bash
# Check logs
docker-compose -f docker-compose.production-local.yml logs

# Check disk space
df -h

# Clean up old containers/images
docker system prune -a
```

### Issue: API not responding
```bash
# Check API logs
docker-compose -f docker-compose.production-local.yml logs api | tail -100

# Restart API
docker-compose -f docker-compose.production-local.yml restart api
```

## Expected Behavior After Fix

| Scenario | Old Behavior | New Behavior |
|----------|-------------|--------------|
| Device pings successfully | Sometimes shows "Down Xm" | Immediately shows UP |
| Device ping times out | Shows DOWN | Shows DOWN ✅ |
| Device recovers | Shows DOWN for minutes after recovery | Immediately shows UP ✅ |
| Zabbix resolves in 6m | WARD OPS still shows DOWN after 16m | WARD OPS shows UP after 6m ✅ |

## Support

If you encounter any issues:
1. Check logs: `docker-compose -f docker-compose.production-local.yml logs -f`
2. Verify containers: `docker-compose -f docker-compose.production-local.yml ps`
3. Check GitHub: https://github.com/ward-tech-solutions/ward-flux-credobank
