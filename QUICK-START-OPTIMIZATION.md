# QUICK START: TOP 3 OPTIMIZATIONS
## Get to Sub-100ms in Under 1 Hour

**Target**: 90% of requests < 100ms
**Time Required**: ~45 minutes
**Risk Level**: Very Low ✅
**Complexity**: Copy-paste friendly

---

## 🎯 THE FASTEST WINS

These 3 optimizations will give you **80% of the performance gains** with **20% of the effort**.

### Success Metrics
- Dashboard: 80ms → 20ms (4x faster)
- Device history: 4.5s → 500ms (9x faster)
- PostgreSQL: Stop growing completely

---

## ⚡ OPTIMIZATION #1: Fix Redis Cache (15 min) - BIGGEST IMPACT

**Problem**: Cache not working → every request hits VictoriaMetrics
**Impact**: 4.5s → 50ms on cache hits (90x faster!)

### Step 1: Check if Redis needs password

```bash
# Try connecting to Redis
docker exec wardops-api-prod redis-cli -h redis ping

# If you see "NOAUTH Authentication required" → needs password
# If you see "PONG" → already working (skip this optimization)
```

### Step 2: Set Redis password

**Option A: Redis already has password (just configure API)**
```bash
# Check Redis config
docker exec $(docker ps -qf "name=redis") redis-cli CONFIG GET requirepass

# If it shows a password, add it to API environment
```

**Option B: Set new Redis password**
```bash
# Edit .env file (create if doesn't exist)
echo "REDIS_PASSWORD=WardOps2025SecurePassword" >> .env
```

### Step 3: Update docker-compose.yml

Edit `docker-compose.production-priority-queues.yml`:

```yaml
# Find the 'api' service section and add/update environment:
  wardops-api-prod:
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      # ... other environment variables
```

### Step 4: Update Redis client initialization

Edit the file where Redis client is created (likely `utils/cache.py` or `database.py`):

```python
# Find redis client initialization
# BEFORE:
redis_client = redis.Redis(
    host='redis',
    port=6379,
    decode_responses=True
)

# AFTER:
import os
redis_client = redis.Redis(
    host='redis',
    port=6379,
    password=os.getenv('REDIS_PASSWORD'),  # Add this line
    decode_responses=True
)
```

### Step 5: Restart API

```bash
# Rebuild API with new code
docker-compose -f docker-compose.production-priority-queues.yml build wardops-api-prod

# Remove old container
docker rm -f $(docker ps -aqf "name=wardops-api-prod")

# Start new container
docker-compose -f docker-compose.production-priority-queues.yml up -d wardops-api-prod

# Wait 10 seconds
sleep 10

# Check logs for errors
docker logs --tail 50 wardops-api-prod | grep -i "redis\|error"
```

### Step 6: Verify caching works

```bash
# First request (cache miss) - should be ~200ms
time curl -s http://localhost:5001/api/v1/dashboard/stats > /dev/null

# Second request (cache hit) - should be <20ms
time curl -s http://localhost:5001/api/v1/dashboard/stats > /dev/null

# If second request is much faster → SUCCESS! ✅
```

**Expected Result**:
- Cache hit rate: 0% → 90%
- Repeated requests: 200ms → 10ms
- Device history (cached): 4.5s → 50ms

---

## ⚡ OPTIMIZATION #2: Stop PostgreSQL Writes (5 min)

**Problem**: Still writing to ping_results table (unnecessary)
**Impact**: Stop database growth, free I/O resources

### Step 1: Edit tasks_batch.py

```bash
# Open file
vim monitoring/tasks_batch.py

# Find line 135 (around there) that says:
#   db.add(ping_result)

# Comment it out:
#   # db.add(ping_result)  # PHASE 4: Using VictoriaMetrics only

# Save and exit (:wq)
```

**Or use sed for quick edit**:
```bash
cd /path/to/ward-ops-credobank

# Backup first
cp monitoring/tasks_batch.py monitoring/tasks_batch.py.backup

# Comment out the line
sed -i 's/^\(\s*\)db\.add(ping_result)/\1# db.add(ping_result)  # PHASE 4: Using VictoriaMetrics only/' monitoring/tasks_batch.py

# Verify change
grep -n "db.add(ping_result)" monitoring/tasks_batch.py
# Should show the line commented out
```

### Step 2: Rebuild monitoring worker

```bash
# Rebuild worker
docker-compose -f docker-compose.production-priority-queues.yml build wardops-worker-monitoring-prod

# Remove old container
docker rm -f $(docker ps -aqf "name=wardops-worker-monitoring-prod")

# Start new container
docker-compose -f docker-compose.production-priority-queues.yml up -d wardops-worker-monitoring-prod

# Check logs
docker logs --tail 20 wardops-worker-monitoring-prod
```

### Step 3: Verify ping_results stops growing

```bash
# Get initial count
INITIAL=$(docker exec wardops-postgres-prod psql -U wardops -d ward_ops -t -c "SELECT COUNT(*) FROM ping_results;" | tr -d ' ')
echo "Initial count: $INITIAL"

# Wait 5 minutes
echo "Waiting 5 minutes..."
sleep 300

# Get new count
FINAL=$(docker exec wardops-postgres-prod psql -U wardops -d ward_ops -t -c "SELECT COUNT(*) FROM ping_results;" | tr -d ' ')
echo "Final count: $FINAL"

# Compare
if [ "$INITIAL" -eq "$FINAL" ]; then
    echo "✅ SUCCESS! Table stopped growing"
else
    echo "⚠️ Table grew by $((FINAL - INITIAL)) rows - check if Phase 4 code deployed"
fi
```

**Expected Result**:
- PostgreSQL writes: 875 inserts/10s → 0
- ping_results table: Stops growing
- Database I/O: Reduced significantly

---

## ⚡ OPTIMIZATION #3: Dynamic Query Resolution (20 min)

**Problem**: 30-day queries fetch 8,640 data points (too much!)
**Impact**: 30d queries 12x faster (4.5s → 500ms)

### Step 1: Create helper function

Create new file `utils/optimization_helpers.py`:

```python
"""
Optimization helper functions for Ward-Ops
"""

def get_optimal_vm_step(hours: int) -> str:
    """
    Choose optimal VictoriaMetrics query resolution based on time range

    Args:
        hours: Number of hours of history requested

    Returns:
        Step interval (e.g., "5m", "15m", "1h")

    Resolution targets:
        24h at 5m  = 288 points  ✓ High detail for recent data
        7d at 15m  = 672 points  ✓ Good balance
        30d at 1h  = 720 points  ✓ Overview without overwhelming
    """
    if hours <= 24:
        return "5m"   # 288 points - high detail
    elif hours <= 168:  # 7 days
        return "15m"  # 672 points - balanced
    else:  # 30+ days
        return "1h"   # 720 points - overview

    # Future: Could add more granular steps
    # elif hours <= 720:  # 30 days
    #     return "1h"
    # else:  # 90+ days
    #     return "6h"
```

**Quick create**:
```bash
cat > utils/optimization_helpers.py << 'EOF'
"""Optimization helper functions for Ward-Ops"""

def get_optimal_vm_step(hours: int) -> str:
    """Choose optimal VictoriaMetrics query resolution"""
    if hours <= 24:
        return "5m"
    elif hours <= 168:
        return "15m"
    else:
        return "1h"
EOF
```

### Step 2: Update devices.py

Edit `routers/devices.py` - find the device history endpoint (around line 456-480):

```python
# Add import at top of file
from utils.optimization_helpers import get_optimal_vm_step

# Find this section (around line 456-480):
def get_device_history(...):
    time_map = {"24h": 24, "7d": 168, "30d": 720}
    hours = time_map.get(time_range, 24)

    # ADD THIS LINE:
    step = get_optimal_vm_step(hours)

    # Find where it calls vm_client.get_device_status_history
    # BEFORE:
    status_future = executor.submit(
        vm_client.get_device_status_history,
        str(device.id),
        hours,
        "5m"  # ← This is hardcoded!
    )

    # AFTER:
    status_future = executor.submit(
        vm_client.get_device_status_history,
        str(device.id),
        hours,
        step  # ← Now dynamic!
    )

    # Do the same for rtt_future:
    rtt_future = executor.submit(
        vm_client.get_device_rtt_history,
        str(device.id),
        hours,
        step  # ← Use dynamic step here too
    )
```

**Quick sed edit** (if you're confident):
```bash
# Add import
sed -i '/^from typing import/a from utils.optimization_helpers import get_optimal_vm_step' routers/devices.py

# You'll need to manually add the step variable and update the calls
# This is safer to do manually to avoid breaking code
```

### Step 3: Rebuild API

```bash
# Rebuild
docker-compose -f docker-compose.production-priority-queues.yml build wardops-api-prod

# Remove old
docker rm -f $(docker ps -aqf "name=wardops-api-prod")

# Start new
docker-compose -f docker-compose.production-priority-queues.yml up -d wardops-api-prod

# Check logs
docker logs --tail 50 wardops-api-prod | grep -i error
```

### Step 4: Verify query optimization

```bash
# Test 24h query (should use 5m step, 288 points)
echo "Testing 24h query..."
time curl -s "http://localhost:5001/api/v1/devices/{device_id}/history?time_range=24h" | \
    jq '.history | length'
# Should show ~288 points, ~200ms

# Test 30d query (should use 1h step, 720 points)
echo "Testing 30d query..."
time curl -s "http://localhost:5001/api/v1/devices/{device_id}/history?time_range=30d" | \
    jq '.history | length'
# Should show ~720 points (not 8640!), ~500ms
```

**Expected Result**:
- 24h query: 288 points, ~200ms ✅
- 7d query: 672 points, ~300ms ✅
- 30d query: 720 points, ~500ms ✅ (was 8,640 points, 4.5s)

---

## 🎯 VERIFICATION CHECKLIST

After completing all 3 optimizations:

### ✅ Quick Checks
```bash
# 1. API is running
docker ps | grep wardops-api-prod

# 2. Worker is running
docker ps | grep wardops-worker-monitoring-prod

# 3. No critical errors in logs
docker logs --tail 100 wardops-api-prod | grep -i "error\|critical\|fatal"
docker logs --tail 100 wardops-worker-monitoring-prod | grep -i "error\|critical\|fatal"

# 4. Redis cache working
curl -s http://localhost:5001/api/v1/dashboard/stats > /dev/null  # First request
time curl -s http://localhost:5001/api/v1/dashboard/stats > /dev/null  # Should be <50ms

# 5. PostgreSQL ping_results not growing
docker exec wardops-postgres-prod psql -U wardops -d ward_ops -c \
    "SELECT COUNT(*) as current_count FROM ping_results;"
# Run again in 5 minutes - count should be same
```

### 📊 Performance Test

```bash
# Run performance test (100 samples)
echo "Running performance test..."

for i in {1..100}; do
    curl -w "%{time_total}\n" -o /dev/null -s http://localhost:5001/api/v1/dashboard/stats
    sleep 0.2
done | sort -n | awk '
    BEGIN {sum=0; count=0}
    {times[count++]=$1; sum+=$1}
    END {
        avg = sum/count*1000
        p50 = times[int(count*0.5)]*1000
        p95 = times[int(count*0.95)]*1000
        p99 = times[int(count*0.99)]*1000

        print "Results (100 samples):"
        print "  Average:", avg, "ms"
        print "  p50:", p50, "ms"
        print "  p95:", p95, "ms"
        print "  p99:", p99, "ms"
        print ""

        if (avg < 50 && p95 < 100) {
            print "✅ EXCELLENT! Target achieved"
        } else if (avg < 100 && p95 < 200) {
            print "✅ GOOD! Close to target"
        } else {
            print "⚠️ NEEDS IMPROVEMENT"
            print "Expected: avg <50ms, p95 <100ms"
        }
    }
'
```

**Expected Output**:
```
Results (100 samples):
  Average: 25 ms
  p50: 18 ms
  p95: 45 ms
  p99: 85 ms

✅ EXCELLENT! Target achieved
```

---

## 🚨 TROUBLESHOOTING

### Issue: "NOAUTH" error persists after Redis fix

**Solution**:
```bash
# Check Redis password is set
docker exec $(docker ps -qf "name=redis") redis-cli CONFIG GET requirepass

# Check API has the password
docker exec wardops-api-prod env | grep REDIS

# If password missing, check .env file and restart API
```

---

### Issue: PostgreSQL ping_results still growing

**Solution**:
```bash
# Check if Phase 4 code deployed
docker exec wardops-worker-monitoring-prod cat /app/monitoring/tasks_batch.py | grep -A2 "db.add(ping_result)"

# Should show commented out:
#   # db.add(ping_result)  # PHASE 4: Using VictoriaMetrics only

# If not commented, rebuild worker container
```

---

### Issue: API crashes after deployment

**Solution**:
```bash
# Check logs for specific error
docker logs wardops-api-prod 2>&1 | tail -50

# Common errors:
# - Import error → check file paths
# - Syntax error → check code edits
# - Connection error → check VictoriaMetrics/Redis running

# Rollback if needed:
cp monitoring/tasks_batch.py.backup monitoring/tasks_batch.py
# Rebuild and restart
```

---

### Issue: Queries still slow after optimization

**Solution**:
```bash
# Check if Redis cache is actually working
docker exec wardops-api-prod redis-cli -h redis -a "${REDIS_PASSWORD}" KEYS "device:history:*" | wc -l
# Should show cache entries

# Check VictoriaMetrics query times
docker logs wardops-api-prod | grep "VM query"

# If VM queries slow, check:
# 1. VictoriaMetrics health
curl -s http://localhost:8428/health

# 2. VM data present
curl -s "http://localhost:8428/api/v1/query?query=count(device_ping_status)" | jq
```

---

## 🎉 SUCCESS!

If all verifications pass, you've successfully:

- ✅ **Fixed Redis caching** → 90% cache hit rate
- ✅ **Stopped PostgreSQL writes** → No more growth
- ✅ **Optimized query resolution** → 12x less data for long ranges

**Performance Achieved**:
- Dashboard: 80ms → 20ms (4x faster)
- Device history (24h): 1.5s → 200ms (7.5x faster)
- Device history (30d): 4.5s → 500ms (9x faster)
- Cache hit rate: 0% → 90%

**Next Steps**:
1. Monitor for 24 hours to ensure stability
2. Apply additional Tier 1 optimizations (see [OPTIMIZATION-OPPORTUNITIES.md](OPTIMIZATION-OPPORTUNITIES.md))
3. Set up Grafana dashboards for better visibility

---

## 📚 RELATED DOCUMENTS

- [OPTIMIZATION-SUMMARY.md](OPTIMIZATION-SUMMARY.md) - All optimizations overview
- [PERFORMANCE-ROADMAP.md](PERFORMANCE-ROADMAP.md) - Detailed performance targets
- [OPTIMIZATION-OPPORTUNITIES.md](OPTIMIZATION-OPPORTUNITIES.md) - Full optimization catalog

---

**Total Time**: ~45 minutes
**Difficulty**: Easy (copy-paste friendly)
**Risk**: Very Low
**Impact**: 🔥🔥🔥 High

**Go make it fast! 🚀**
