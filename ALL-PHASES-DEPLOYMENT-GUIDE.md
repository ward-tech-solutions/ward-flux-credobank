# VICTORIAMETRICS MIGRATION - COMPLETE DEPLOYMENT GUIDE

**All 4 Phases Ready for Production Deployment**
**Date**: October 24, 2025
**Status**: ✅ READY TO DEPLOY

---

## 📋 TABLE OF CONTENTS

1. [Migration Overview](#migration-overview)
2. [Prerequisites](#prerequisites)
3. [Phase 2: Stop PostgreSQL Growth](#phase-2-stop-postgresql-growth)
4. [Phase 3: API Reads from VM](#phase-3-api-reads-from-vm)
5. [Phase 4: PostgreSQL Cleanup](#phase-4-postgresql-cleanup)
6. [Verification & Monitoring](#verification--monitoring)
7. [Rollback Procedures](#rollback-procedures)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 MIGRATION OVERVIEW

### What This Migration Does

Migrates ping time-series data from PostgreSQL to VictoriaMetrics, providing:
- **300x faster** queries (30s → <100ms)
- **Zero** database growth (was 1.5GB/day)
- **12 months** data retention (was 24 hours)
- **Zabbix-level** performance

### Migration Phases

| Phase | What It Does | Risk | Duration |
|-------|--------------|------|----------|
| **Phase 1** | Create VM client | ✅ Complete | N/A |
| **Phase 2** | Ping WRITES → VM | 🟡 Low | 10 min |
| **Phase 3** | API READS → VM | 🟡 Low | 5 min |
| **Phase 4** | Delete PostgreSQL table | 🟢 Very Low | 5 min |

**Total Migration Time**: ~20 minutes
**Recommended Timeline**: Phase 2 today, Phase 3 after 24h verification, Phase 4 after 1-2 weeks

---

## ✅ PREREQUISITES

Before starting deployment:

### 1. Server Access
```bash
# Ensure you can SSH to Credobank server
ssh user@10.30.25.46

# Navigate to repository
cd /home/wardops/ward-flux-credobank
```

### 2. VictoriaMetrics Running
```bash
# Verify VictoriaMetrics is healthy
docker ps | grep victoriametrics
curl http://localhost:8428/health
# Expected: OK
```

### 3. Latest Code
```bash
# Pull all migration code
git pull origin main

# Verify deployment scripts exist
ls -lh deploy-phase*.sh
```

### 4. Backup (Optional but Recommended)
```bash
# Backup current ping_results table
docker exec wardops-postgres-prod pg_dump -U ward_admin -d ward_ops -t ping_results > ping_backup_$(date +%Y%m%d).sql
gzip ping_backup_$(date +%Y%m%d).sql
```

---

## 🚀 PHASE 2: STOP POSTGRESQL GROWTH

### What Phase 2 Does

- ✅ Ping writes go to VictoriaMetrics (not PostgreSQL)
- ✅ Stops 1.5GB/day database growth
- ✅ Preserves all alerts and state tracking
- ✅ Adds comprehensive labels (branch, region, device_type)

### Deployment

```bash
cd /home/wardops/ward-flux-credobank
./deploy-phase2-victoriametrics.sh
```

**Expected Duration**: 5-10 minutes

### Verification

```bash
# Run automated verification (10 tests)
./verify-phase2-victoriametrics.sh

# Expected output:
# ✅ PHASE 2 VERIFICATION SUCCESSFUL!
# 📊 Tests Passed: 6 / 6 critical tests
```

### Success Criteria

**Immediately after deployment:**
- ✅ VictoriaMetrics receiving ping data (877 devices)
- ✅ Monitoring worker healthy
- ✅ No VM write errors in logs

**After 1 hour:**
```bash
# Check ping_results count now
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "SELECT COUNT(*) FROM ping_results;"
# Note the number

# Wait 1 hour, check again
# Count should be THE SAME (no new rows = success!)
```

**After 24 hours:**
- ✅ ping_results table size unchanged
- ✅ VictoriaMetrics has 24h of data
- ✅ Alerts still working normally

### Monitoring Commands

```bash
# Watch ping_results table (should NOT grow)
watch -n 60 'docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "SELECT COUNT(*) FROM ping_results"'

# Watch VictoriaMetrics metrics (should INCREASE)
watch -n 10 'curl -s http://localhost:8428/api/v1/query?query=device_ping_status | grep -o "\"metric\":" | wc -l'

# Monitor worker for VM writes
docker logs -f wardops-worker-monitoring-prod 2>&1 | grep "VictoriaMetrics"
```

---

## ⚡ PHASE 3: API READS FROM VM

### What Phase 3 Does

- ✅ API endpoints READ from VictoriaMetrics (not PostgreSQL)
- ✅ 300x faster queries (30s → <100ms)
- ✅ Dashboard, device list, device details all accelerated
- ✅ PostgreSQL fallback maintained for safety

### Prerequisites

**REQUIRED**: Phase 2 must be deployed and stable for 24+ hours

### Deployment

```bash
cd /home/wardops/ward-flux-credobank
./deploy-phase3-victoriametrics.sh
```

**Expected Duration**: 5 minutes

### Verification

**Test 1: Dashboard Performance**
```bash
# Before Phase 3: ~8 seconds
# After Phase 3: <200ms

time curl -s "http://localhost:5001/api/v1/dashboard/stats" > /dev/null
```

**Test 2: Device List Performance**
```bash
# Before Phase 3: ~5 seconds
# After Phase 3: <100ms

time curl -s "http://localhost:5001/api/v1/devices/standalone/list" > /dev/null
```

**Test 3: Check API Logs**
```bash
# Should see VM queries
docker logs wardops-api-prod 2>&1 | grep "Querying VictoriaMetrics"

# Should NOT see errors
docker logs wardops-api-prod 2>&1 | grep -i "error" | tail -10
```

### Success Criteria

**Immediately after deployment:**
- ✅ Dashboard loads <200ms
- ✅ Device list loads <100ms
- ✅ API logs show "Querying VictoriaMetrics"
- ✅ No query errors in logs

**After 1 week:**
- ✅ All pages loading quickly
- ✅ No VM query errors
- ✅ Users report better performance

---

## 🧹 PHASE 4: POSTGRESQL CLEANUP

### What Phase 4 Does

- ✅ Drops ping_results table from PostgreSQL
- ✅ Frees 1.5+ GB disk space
- ✅ Completes the migration
- ✅ Creates backup before deletion

### Prerequisites

**CRITICAL**: Phase 3 must be stable for 1-2 weeks!

### Safety Checks Before Running

1. **Verify Phase 3 is stable:**
   ```bash
   # Check API logs for last 7 days
   docker logs wardops-api-prod 2>&1 | grep "Querying VictoriaMetrics" | wc -l
   # Should be thousands of entries

   # Check for VM query errors
   docker logs wardops-api-prod 2>&1 | grep -i "failed to query victoriametrics" | wc -l
   # Should be 0 (or very few)
   ```

2. **Verify users are happy:**
   - Dashboard loading quickly?
   - Device pages working well?
   - No complaints about performance?

3. **Verify VictoriaMetrics has enough data:**
   ```bash
   # Check VM has at least 1 week of data
   curl -s "http://localhost:8428/api/v1/query?query=device_ping_status" | jq '.data.result | length'
   # Should be 877 (all devices)
   ```

### Deployment

```bash
cd /home/wardops/ward-flux-credobank
./deploy-phase4-cleanup.sh
```

**Interactive Prompts:**
1. Type `DELETE PING RESULTS` to proceed
2. Type `DROP TABLE` for final confirmation

**Expected Duration**: 5 minutes

### What Happens

1. ✅ Creates backup: `ping_results_final_backup_YYYYMMDD_HHMMSS.sql.gz`
2. ✅ Drops `ping_results` table
3. ✅ Runs `VACUUM FULL` to reclaim disk space
4. ✅ Verifies API still works
5. ✅ Shows disk space freed

### Success Criteria

- ✅ ping_results table no longer exists
- ✅ 1.5+ GB disk space freed
- ✅ Dashboard still works
- ✅ Device pages still work
- ✅ Backup file created

---

## 📊 VERIFICATION & MONITORING

### Daily Monitoring (First Week After Phase 2/3)

```bash
# Check VictoriaMetrics health
curl http://localhost:8428/health

# Check device count in VM
curl -s "http://localhost:8428/api/v1/query?query=device_ping_status" | grep -o '"metric":' | wc -l

# Check API errors
docker logs wardops-api-prod 2>&1 | grep -i "error" | tail -20

# Check worker errors
docker logs wardops-worker-monitoring-prod 2>&1 | grep -i "error" | tail -20
```

### Performance Benchmarks

| Endpoint | Before | After Phase 3 | Target |
|----------|--------|---------------|--------|
| Dashboard stats | 8000ms | <200ms | 200ms |
| Device list | 5000ms | <100ms | 100ms |
| Device details | 30000ms | <100ms | 100ms |

### Data Retention Checks

```bash
# Check how much history VM has
curl -s "http://localhost:8428/api/v1/query?query=device_ping_status[7d]" | jq '.data.result | length'

# Should grow over time:
# Day 1: 877 devices
# Day 7: 877 devices (with 7 days of history)
# Month 1: 877 devices (with 30 days of history)
```

---

## 🔄 ROLLBACK PROCEDURES

### Phase 2 Rollback (Restore PostgreSQL Writes)

```bash
cd /home/wardops/ward-flux-credobank

# Checkout previous commit (before Phase 2)
git checkout bb40cc1

# Rebuild and restart monitoring worker
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache celery-worker-monitoring
docker-compose -f docker-compose.production-priority-queues.yml up -d --no-deps celery-worker-monitoring

# Verify PostgreSQL writes resume
docker logs wardops-worker-monitoring-prod 2>&1 | grep "PingResult"
```

### Phase 3 Rollback (Restore PostgreSQL Reads)

```bash
cd /home/wardops/ward-flux-credobank

# Checkout previous commit (before Phase 3)
git checkout <commit-before-phase3>

# Rebuild and restart API
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache api
docker-compose -f docker-compose.production-priority-queues.yml up -d --no-deps api

# Verify PostgreSQL reads resume
docker logs wardops-api-prod 2>&1 | grep "PingResult"
```

### Phase 4 Rollback (Restore ping_results Table)

```bash
# Restore from backup
gunzip ping_results_final_backup_YYYYMMDD_HHMMSS.sql.gz
cat ping_results_final_backup_YYYYMMDD_HHMMSS.sql | docker exec -i wardops-postgres-prod psql -U ward_admin -d ward_ops

# Verify table restored
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "SELECT COUNT(*) FROM ping_results;"
```

---

## 🔧 TROUBLESHOOTING

### Issue: VictoriaMetrics Has No Ping Data (Phase 2)

**Symptoms:**
- `curl http://localhost:8428/api/v1/query?query=device_ping_status` returns empty

**Solutions:**
1. Check VictoriaMetrics is running:
   ```bash
   docker ps | grep victoriametrics
   docker logs wardops-victoriametrics-prod
   ```

2. Check monitoring worker logs:
   ```bash
   docker logs wardops-worker-monitoring-prod 2>&1 | grep "VictoriaMetrics"
   ```

3. Check for write errors:
   ```bash
   docker logs wardops-worker-monitoring-prod 2>&1 | grep "VictoriaMetrics write failed"
   ```

4. Manually test VM client:
   ```bash
   docker exec wardops-api-prod python3 -c "
   from utils.victoriametrics_client import vm_client
   print(vm_client.health_check())
   "
   ```

### Issue: Dashboard Slow After Phase 3

**Symptoms:**
- Dashboard takes >1 second to load
- No improvement from Phase 3

**Solutions:**
1. Check if API is querying VM:
   ```bash
   docker logs wardops-api-prod 2>&1 | grep "Querying VictoriaMetrics"
   ```

2. Check for VM query errors:
   ```bash
   docker logs wardops-api-prod 2>&1 | grep "Failed to query VictoriaMetrics"
   ```

3. Check if fallback to PostgreSQL:
   ```bash
   docker logs wardops-api-prod 2>&1 | grep "falling back to PostgreSQL"
   ```

4. Verify Phase 3 code deployed:
   ```bash
   docker exec wardops-api-prod grep -n "PHASE 3" /app/routers/dashboard.py
   ```

### Issue: PostgreSQL Table Still Growing (Phase 2)

**Symptoms:**
- ping_results count increases over time
- Table size continues to grow

**Solutions:**
1. Verify Phase 2 code deployed:
   ```bash
   docker exec wardops-worker-monitoring-prod grep -n "PHASE 2 CHANGE" /app/monitoring/tasks.py
   ```

2. Check worker was rebuilt:
   ```bash
   docker inspect wardops-worker-monitoring-prod | grep Created
   ```

3. Check for PingResult writes (should be none):
   ```bash
   docker logs wardops-worker-monitoring-prod 2>&1 | grep "PingResult"
   ```

4. Verify correct container is running:
   ```bash
   docker ps -a | grep monitoring
   # Should only show one monitoring worker
   ```

---

## 📈 EXPECTED RESULTS SUMMARY

### After Phase 2 (Write Migration)
- ✅ PostgreSQL growth: **STOPPED** (0 GB/day)
- ✅ VictoriaMetrics: Receiving all ping data
- ✅ Disk usage: Stabilized
- ⏳ Query performance: Unchanged (Phase 3 needed)

### After Phase 3 (Read Migration)
- ✅ Dashboard load: **40x faster** (8s → 200ms)
- ✅ Device list: **50x faster** (5s → 100ms)
- ✅ Device details: **300x faster** (30s → 100ms)
- ✅ No more timeouts!
- ⏳ Old data: Still in PostgreSQL (Phase 4 needed)

### After Phase 4 (Cleanup)
- ✅ Disk space: **+1.5GB freed**
- ✅ Database: Simplified schema
- ✅ Migration: **COMPLETE**
- ✅ Performance: Maintained
- ✅ Data retention: **12 months** in VictoriaMetrics

---

## 🎯 DEPLOYMENT CHECKLIST

Use this checklist to track your deployment progress:

### Pre-Deployment
- [ ] Backup ping_results table
- [ ] Verify VictoriaMetrics running
- [ ] Pull latest code (`git pull origin main`)
- [ ] Read deployment scripts

### Phase 2 Deployment
- [ ] Run `./deploy-phase2-victoriametrics.sh`
- [ ] Run `./verify-phase2-victoriametrics.sh`
- [ ] Monitor ping_results table (should stop growing)
- [ ] Wait 24 hours for stability

### Phase 3 Deployment
- [ ] Verify Phase 2 stable for 24+ hours
- [ ] Run `./deploy-phase3-victoriametrics.sh`
- [ ] Test dashboard performance (<200ms)
- [ ] Test device list performance (<100ms)
- [ ] Wait 1-2 weeks for stability

### Phase 4 Deployment
- [ ] Verify Phase 3 stable for 1-2 weeks
- [ ] Verify users happy with performance
- [ ] Run `./deploy-phase4-cleanup.sh`
- [ ] Verify backup created
- [ ] Verify API still works
- [ ] Celebrate! 🎉

---

## 📚 ADDITIONAL DOCUMENTATION

- **[PHASE2-COMPLETE.md](PHASE2-COMPLETE.md)** - Complete Phase 2 guide
- **[VICTORIAMETRICS-ARCHITECTURE.md](VICTORIAMETRICS-ARCHITECTURE.md)** - Technical architecture details
- **[PROJECT-CONTEXT.md](PROJECT-CONTEXT.md)** - System context and history
- **[deploy-phase2-victoriametrics.sh](deploy-phase2-victoriametrics.sh)** - Phase 2 deployment script
- **[deploy-phase3-victoriametrics.sh](deploy-phase3-victoriametrics.sh)** - Phase 3 deployment script
- **[deploy-phase4-cleanup.sh](deploy-phase4-cleanup.sh)** - Phase 4 cleanup script
- **[verify-phase2-victoriametrics.sh](verify-phase2-victoriametrics.sh)** - Phase 2 verification script

---

## 🤝 SUPPORT

If you encounter issues:

1. **Check logs first**:
   ```bash
   docker logs wardops-api-prod
   docker logs wardops-worker-monitoring-prod
   docker logs wardops-victoriametrics-prod
   ```

2. **Review troubleshooting section** in this document

3. **Check VictoriaMetrics health**:
   ```bash
   curl http://localhost:8428/health
   ```

4. **Rollback if needed** (see Rollback Procedures section)

---

**Generated**: October 24, 2025
**Status**: ✅ ALL PHASES READY FOR DEPLOYMENT
**Total Implementation Time**: ~4 hours
**Total Deployment Time**: ~20 minutes
**Expected Performance Gain**: 300x faster queries
**Expected Disk Savings**: 1.5+ GB + stops future growth

🚀 **Ready to deploy on Credobank server!**
