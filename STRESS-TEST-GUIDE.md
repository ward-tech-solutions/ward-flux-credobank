# Ward-Ops UI Stress Test Guide

## Overview

Simulates 10 regional managers using Ward-Ops simultaneously to test system performance under load.

**What it tests:**
- ✅ API authentication (login/logout)
- ✅ Device list queries with region filters
- ✅ Device detail queries (status history)
- ✅ Dashboard statistics
- ✅ Alert history queries
- ✅ Concurrent user load
- ✅ Database connection pool handling
- ✅ VictoriaMetrics query performance

---

## Prerequisites

### 1. Create Test Users

You need to create 10 test users in Ward-Ops:

```bash
# On Credobank server
cd /home/wardops/ward-flux-credobank

# Create test users (test1 through test10)
docker exec wardops-api-prod python3 -c "
from database import SessionLocal
from monitoring.models import User
from werkzeug.security import generate_password_hash
import uuid

db = SessionLocal()

regions = ['Tbilisi', 'Batumi', 'Kutaisi', 'Rustavi', 'Gori',
           'Zugdidi', 'Poti', 'Kobuleti', 'Khashuri', 'Telavi']

for i in range(1, 11):
    username = f'test{i}'
    password = f'test{i}'
    region = regions[i-1]

    # Check if user exists
    existing = db.query(User).filter_by(username=username).first()
    if existing:
        print(f'User {username} already exists')
        continue

    # Create user
    user = User(
        id=uuid.uuid4(),
        username=username,
        password_hash=generate_password_hash(password),
        full_name=f'Test User {i}',
        email=f'test{i}@example.com',
        role='regional_manager',
        region=region,
        is_active=True
    )
    db.add(user)
    print(f'Created user: {username} (region: {region})')

db.commit()
db.close()
print('✅ All test users created')
"
```

### 2. Install Python Dependencies (On Your Laptop)

```bash
# Install requests library
pip3 install requests
```

---

## Running the Stress Test

### Basic Usage

```bash
# From your laptop, test the Credobank server
python3 scripts/stress_test_ui.py --url http://CREDOBANK_SERVER_IP:5001 --users 10 --duration 300
```

### Examples

```bash
# 1. Quick test with 5 users for 2 minutes
python3 scripts/stress_test_ui.py \
  --url http://10.x.x.x:5001 \
  --users 5 \
  --duration 120

# 2. Full load test with all 10 users for 5 minutes
python3 scripts/stress_test_ui.py \
  --url http://10.x.x.x:5001 \
  --users 10 \
  --duration 300

# 3. Extended stress test for 15 minutes
python3 scripts/stress_test_ui.py \
  --url http://10.x.x.x:5001 \
  --users 10 \
  --duration 900

# 4. Test against production (use HTTPS)
python3 scripts/stress_test_ui.py \
  --url https://wardops.credobank.ge \
  --users 10 \
  --duration 300
```

---

## What the Script Does

### User Behavior Simulation

Each simulated user performs these actions in a loop:

1. **Login** (once at start)
   - `POST /api/v1/auth/login`
   - Get JWT token
   - Set Authorization header

2. **Load Monitor Page** (every iteration)
   - `GET /api/v1/devices/standalone/list?region={user_region}`
   - Filters devices by user's assigned region
   - Simulates loading the device list

3. **View Device Details** (2-3 random devices)
   - `GET /api/v1/devices/standalone/{device_id}/history?hours=168`
   - Gets 7-day status history
   - Simulates clicking on devices

4. **Load Dashboard**
   - `GET /api/v1/dashboard/stats`
   - Gets overall statistics

5. **Check Alerts**
   - `GET /api/v1/alerts/history?limit=50`
   - Gets recent alerts

6. **Wait 5-15 seconds** (random)
   - Simulates user reading/thinking time

7. **Repeat** until duration expires

---

## Understanding Output

### Real-time Logs

```
[13:45:21] [test1] Logging in...
[13:45:21] [test1] ✅ Logged in successfully (0.34s) - Region: Tbilisi
[13:45:21] [test1] --- Iteration 1 ---
[13:45:22] [test1] 📋 Loaded 156 devices (0.89s)
[13:45:23] [test1] 🔍 Viewed device 'Vake SW1' details (1.23s)
[13:45:25] [test1] 🔍 Viewed device 'Saburtalo SW2' details (1.15s)
[13:45:28] [test1] 📊 Dashboard: 874 devices, 820 UP, 54 DOWN (0.45s)
[13:45:29] [test1] 🚨 Loaded 23 alerts (0.67s)
[13:45:30] [test1] 💤 Waiting 8.3s before next action...
```

### Per-User Statistics

```
============================================================
📊 Statistics for test1
============================================================
Total Requests:    45
Successful:        45 (100.0%)
Failed:            0
Avg Response Time: 0.87s
============================================================
```

### Aggregate Statistics

```
============================================================
📊 AGGREGATE STATISTICS - ALL USERS
============================================================
Total Users:       10
Total Requests:    487
Successful:        487 (100.0%)
Failed:            0
Avg Response Time: 0.92s
Requests/Second:   1.62
============================================================

📋 Per-User Summary:
User       Requests     Success Rate    Avg Response
------------------------------------------------------------
test1      52           100.0%          0.85s
test2      48           100.0%          0.91s
test3      51           100.0%          0.88s
test4      49           100.0%          0.95s
test5      47           100.0%          0.89s
test6      50           100.0%          0.93s
test7      49           100.0%          0.90s
test8      48           100.0%          0.94s
test9      51           100.0%          0.87s
test10     42           100.0%          0.98s

✅ Stress test completed at 2025-10-24 13:50:35
```

---

## Interpreting Results

### Good Performance Indicators

✅ **Success Rate: 95%+**
- Most requests complete successfully
- Few timeout or error responses

✅ **Avg Response Time: < 2s**
- Fast enough for good user experience
- Database queries optimized

✅ **Requests/Second: 1-3**
- System handling concurrent load well
- Connection pools not exhausted

### Warning Signs

⚠️ **Success Rate: 80-95%**
- Some requests failing
- May indicate connection pool issues
- Check database logs

⚠️ **Avg Response Time: 2-5s**
- Slower than ideal
- Users may notice lag
- Check query performance

❌ **Success Rate: < 80%**
- Significant failures
- System overloaded
- Check server resources (CPU, memory, DB connections)

❌ **Avg Response Time: > 5s**
- Very slow responses
- Unacceptable user experience
- Immediate optimization needed

---

## Monitoring During Test

### On Credobank Server

**1. Monitor API Logs:**
```bash
docker logs -f wardops-api-prod | grep -E "GET|POST|ERROR"
```

**2. Monitor Database Connections:**
```bash
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \
  "SELECT state, count(*) FROM pg_stat_activity WHERE datname='ward_ops' GROUP BY state;"
```

**3. Monitor System Resources:**
```bash
# CPU and memory
docker stats wardops-api-prod wardops-postgres-prod wardops-victoriametrics-prod

# API container resource usage
docker exec wardops-api-prod top -bn1 | head -20
```

**4. Monitor VictoriaMetrics:**
```bash
# Check query performance
curl "http://localhost:8428/api/v1/status/active_queries" | jq
```

---

## Expected Results

### With Tier 1 Optimizations

**Before Tier 1:**
- Avg Response Time: 3-5s
- Success Rate: 70-80%
- Frequent timeouts under load

**After Tier 1:**
- Avg Response Time: 0.5-1.5s ✅
- Success Rate: 95-100% ✅
- No timeouts ✅

### Target Metrics (10 Concurrent Users)

| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| Success Rate | > 99% | 95-99% | < 95% |
| Avg Response | < 1s | 1-2s | > 2s |
| Device List | < 500ms | 500ms-1s | > 1s |
| Device Details | < 1.5s | 1.5-3s | > 3s |
| Dashboard | < 500ms | 500ms-1s | > 1s |
| Alerts | < 800ms | 800ms-1.5s | > 1.5s |

---

## Troubleshooting

### Issue: High Failure Rate

**Symptoms:** Success rate < 90%, many timeout errors

**Possible Causes:**
1. Database connection pool exhausted
2. VictoriaMetrics overloaded
3. Too many concurrent users

**Solutions:**
```bash
# Check database connections
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \
  "SELECT count(*) FROM pg_stat_activity WHERE datname='ward_ops';"

# If close to 300 (pool limit), restart API to clear connections
docker-compose -f docker-compose.production-priority-queues.yml restart api

# Reduce concurrent users
python3 scripts/stress_test_ui.py --url ... --users 5 --duration 300
```

### Issue: Slow Response Times

**Symptoms:** Avg response time > 3s

**Possible Causes:**
1. Slow database queries
2. VictoriaMetrics query taking too long
3. CPU/memory exhaustion

**Solutions:**
```bash
# Check slow queries in PostgreSQL
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \
  "SELECT query, state, wait_event, query_start FROM pg_stat_activity WHERE state != 'idle' ORDER BY query_start;"

# Check VictoriaMetrics metrics
curl "http://localhost:8428/metrics" | grep vm_slow_queries

# Check CPU/memory
docker stats --no-stream
```

### Issue: Login Failures

**Symptoms:** Many users failing to login

**Possible Causes:**
1. Test users not created
2. Wrong credentials
3. Auth endpoint down

**Solutions:**
```bash
# Verify test users exist
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \
  "SELECT username, role, region, is_active FROM users WHERE username LIKE 'test%';"

# Check API logs for auth errors
docker logs wardops-api-prod --tail 100 | grep auth
```

---

## Advanced: Custom Scenarios

### Test Specific Region

Modify the script to test only Tbilisi region users:

```python
# In stress_test_ui.py, change:
username = f"test{i}"  # Uses test1, test2, test3 (all Tbilisi users)
```

### Increase Load Gradually

```bash
# Start with 2 users
python3 scripts/stress_test_ui.py --url ... --users 2 --duration 60

# Increase to 5 users
python3 scripts/stress_test_ui.py --url ... --users 5 --duration 120

# Increase to 10 users
python3 scripts/stress_test_ui.py --url ... --users 10 --duration 300

# Find breaking point - try 15, 20 users
```

### Peak Hour Simulation

Simulate peak usage (8-10 AM when managers check overnight alerts):

```bash
# 10 users, 30 minutes
python3 scripts/stress_test_ui.py --url ... --users 10 --duration 1800
```

---

## Cleanup

### Remove Test Users (After Testing)

```bash
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \
  "DELETE FROM users WHERE username LIKE 'test%';"
```

---

## Performance Benchmarks

### Target: 10 Concurrent Users

With Tier 1 optimizations deployed:

| Endpoint | Target Time | Acceptable | Poor |
|----------|------------|------------|------|
| Login | < 300ms | 300-500ms | > 500ms |
| Device List (filtered) | < 500ms | 500ms-1s | > 1s |
| Device Details (7d) | < 1.5s | 1.5-3s | > 3s |
| Dashboard Stats | < 500ms | 500ms-1s | > 1s |
| Alert History | < 800ms | 800ms-1.5s | > 1.5s |

**Overall Success Rate:** 99%+
**Overall Avg Response:** < 1s

---

## Next Steps

After running the stress test:

1. ✅ Review aggregate statistics
2. ✅ Check per-user performance
3. ✅ Identify slowest endpoints
4. ✅ Monitor database connection usage
5. ✅ Check VictoriaMetrics query performance
6. ✅ Optimize slow queries if needed
7. ✅ Re-run test to verify improvements
