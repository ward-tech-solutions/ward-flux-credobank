# 🚀 Corrected Deployment Steps for CredoBank Server

**Important**: Apply indexes AFTER Docker deployment, not before!

---

## ✅ Correct Deployment Sequence

```bash
# 1. Pull latest code (already done ✅)
git pull origin main

# 2. Deploy with Docker first
bash deploy-on-server.sh

# 3. Then apply indexes from within Docker
docker-compose -f docker-compose.production-local.yml exec api python scripts/apply_performance_indexes.py

# 4. Verify deployment
curl http://localhost:5001/api/v1/health
```

---

## 📋 Step-by-Step Instructions

### Step 1: Complete the Docker Deployment

The deployment was interrupted. Let's complete it:

```bash
cd /home/wardops/ward-flux-credobank

# Clean up any partial builds
docker-compose -f docker-compose.production-local.yml down
docker system prune -f

# Deploy with fresh build
bash deploy-on-server.sh
```

**This will take 5-10 minutes** as it rebuilds the frontend and backend.

**Wait for**:
```
✅ All containers started successfully
✅ API health check passed
```

### Step 2: Apply Database Indexes (Inside Docker)

Once containers are running:

```bash
# Apply indexes from within the API container
docker-compose -f docker-compose.production-local.yml exec api python scripts/apply_performance_indexes.py
```

**Expected output**:
```
============================================================
WARD OPS - Performance Index Application
============================================================
✅ Database connection successful
Database table sizes:
  ping_results: X GB
  standalone_devices: X MB
✅ Successfully applied all performance indexes!

Found 10 performance indexes:
  ✓ ping_results.idx_ping_results_device_timestamp
  ✓ standalone_devices.idx_standalone_devices_enabled_vendor
  ...

Performance Optimization Complete!
```

### Step 3: Verify Everything Works

```bash
# 1. Check API health
curl http://localhost:5001/api/v1/health
# Expected: {"status":"healthy",...}

# 2. Check all containers
docker-compose -f docker-compose.production-local.yml ps
# Expected: All containers "Up"

# 3. Check database connections
docker-compose -f docker-compose.production-local.yml exec postgres psql -U ward_admin -d ward_ops -c "SELECT count(*) FROM pg_stat_activity WHERE datname='ward_ops';"
# Expected: 20-50 connections (not 60!)

# 4. Check indexes were created
docker-compose -f docker-compose.production-local.yml exec postgres psql -U ward_admin -d ward_ops -c "SELECT tablename, indexname FROM pg_indexes WHERE indexname LIKE 'idx_%' ORDER BY tablename;"
# Expected: 10+ indexes listed

# 5. Check worker logs
docker-compose -f docker-compose.production-local.yml logs --tail=50 celery-worker | grep -E "Fetched|succeeded"
# Expected: See batched queries like "Fetched 100 ping results for 50 devices"

# 6. Test performance
time curl -s http://localhost:5001/api/v1/devices/standalone/list?limit=100 > /dev/null
# Expected: < 1 second
```

---

## 🐛 Troubleshooting

### If Docker build gets stuck

```bash
# Cancel with Ctrl+C (you already did this)

# Clean everything
docker-compose -f docker-compose.production-local.yml down -v
docker system prune -af  # This removes all unused images

# Try again
bash deploy-on-server.sh
```

### If build is too slow

The frontend build can take 5-10 minutes. This is normal. You'll see:

```
Step 4/29 : RUN npm ci --prefer-offline --no-audit --legacy-peer-deps
 ---> Running in 233b5127ef5f
```

**Just let it run.** Don't cancel it. It's installing Node packages.

### If you need to skip the build

```bash
# Use existing images (faster, but may be outdated)
docker-compose -f docker-compose.production-local.yml up -d
```

---

## ⚡ Alternative: Manual Index Application

If the Docker exec method doesn't work, apply indexes manually:

```bash
# Copy SQL file to a location postgres can access
docker cp migrations/postgres/012_add_performance_indexes.sql wardops-postgres-prod:/tmp/

# Execute SQL directly
docker-compose -f docker-compose.production-local.yml exec postgres psql -U ward_admin -d ward_ops -f /tmp/012_add_performance_indexes.sql

# Verify
docker-compose -f docker-compose.production-local.yml exec postgres psql -U ward_admin -d ward_ops -c "SELECT count(*) FROM pg_indexes WHERE indexname LIKE 'idx_%';"
# Expected: 10 or more
```

---

## 📊 Post-Deployment Verification

After everything is running, run this comprehensive check:

```bash
cat > /tmp/check-deployment.sh << 'EOF'
#!/bin/bash
echo "=========================================="
echo "WARD OPS Deployment Verification"
echo "=========================================="

echo -e "\n1. Container Status:"
docker-compose -f docker-compose.production-local.yml ps

echo -e "\n2. API Health:"
curl -s http://localhost:5001/api/v1/health | grep -o '"status":"[^"]*"'

echo -e "\n3. Database Connections:"
docker-compose -f docker-compose.production-local.yml exec -T postgres psql -U ward_admin -d ward_ops -c "SELECT count(*) as connections FROM pg_stat_activity WHERE datname='ward_ops';" -t

echo -e "\n4. Performance Indexes:"
docker-compose -f docker-compose.production-local.yml exec -T postgres psql -U ward_admin -d ward_ops -c "SELECT count(*) as index_count FROM pg_indexes WHERE indexname LIKE 'idx_%';" -t

echo -e "\n5. Recent Worker Activity:"
docker-compose -f docker-compose.production-local.yml logs --tail=5 celery-worker | grep "succeeded"

echo -e "\n6. Memory Usage:"
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}" | grep wardops

echo -e "\n=========================================="
echo "Verification Complete!"
echo "=========================================="
EOF

chmod +x /tmp/check-deployment.sh
/tmp/check-deployment.sh
```

**Expected Results**:
- ✅ All containers "Up"
- ✅ API status "healthy"
- ✅ DB connections 20-100 (not 300/300)
- ✅ 10+ indexes
- ✅ Worker tasks succeeding
- ✅ Worker memory < 200MB

---

## 🎯 Success Criteria

Deployment is successful when:

1. ✅ All 6 containers running
2. ✅ API returns `{"status":"healthy"}`
3. ✅ Database has 10+ performance indexes
4. ✅ Database connections < 150
5. ✅ Worker logs show "Fetched N ping results" (batched queries)
6. ✅ No "timezone" or "datetime" errors in logs
7. ✅ Device list loads in < 1 second
8. ✅ Worker memory < 200MB per worker

If all criteria met: **Deployment Complete!** 🎉

---

## 🔄 If Something Goes Wrong

**Rollback to backup**:

```bash
# Stop current deployment
docker-compose -f docker-compose.production-local.yml down

# Restore backup
cd /home/wardops/ward-flux-backup-20251022-134336
docker-compose -f docker-compose.production-local.yml up -d

# Verify
curl http://localhost:5001/api/v1/health
```

---

## 📞 Next Steps

Once deployment succeeds:

1. Keep the terminal open and monitor logs for 5 minutes
2. Check Monitor page: http://10.30.25.39:5001/monitor
3. Verify devices show correct UP/DOWN status
4. Check that ping tasks run every 30 seconds
5. Verify SNMP polling works (if configured)

**All good?** The system is now optimized and ready! 🚀
