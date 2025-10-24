# WARD-OPS PROJECT CONTEXT & ARCHITECTURE

## PROJECT OVERVIEW

**Ward-Ops** is a comprehensive network monitoring system for CredoBank (Georgia banking infrastructure).
- **Mission**: Replace Zabbix as the primary monitoring solution
- **Current Status**: Production deployment monitoring 877 devices across 128 branches
- **Challenge**: Competing with Zabbix's mature time-series data handling

---

## INFRASTRUCTURE

### Server Details
- **Location**: Credobank production server (10.30.25.46)
- **Access**: Via jump server
- **OS**: Ubuntu Linux
- **Deployment**: Docker Compose
- **Repository**: https://github.com/ward-tech-solutions/ward-flux-credobank
- **Branch**: main

### Hardware Resources
- **Disk**: 491GB total, 298GB available (37% used)
- **Database**: PostgreSQL 15 (1.7GB data)
- **Memory**: 16GB RAM
- **Network**: Internal CredoBank network

---

## CURRENT ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                     WARD-OPS SYSTEM                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Frontend   │  │   Backend    │  │   Workers    │     │
│  │   (React)    │  │  (FastAPI)   │  │   (Celery)   │     │
│  │  Port: 5001  │  │  Port: 5001  │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                  │                  │            │
│         └──────────────────┴──────────────────┘            │
│                            │                               │
│  ┌──────────────┬──────────┴──────────┬──────────────┐    │
│  │              │                     │              │    │
│  │ PostgreSQL   │   VictoriaMetrics   │    Redis     │    │
│  │  Port: 5433  │     Port: 8428      │  Port: 6380  │    │
│  │              │                     │              │    │
│  │ • Devices    │   • SNMP metrics    │  • Tasks     │    │
│  │ • Alerts     │   • (NOT pings yet) │  • Queue     │    │
│  │ • Ping data  │   • Compression     │              │    │
│  │   (5M rows!) │   • Fast queries    │              │    │
│  └──────────────┴─────────────────────┴──────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## DOCKER CONTAINERS

### Production Containers (All Running)

| Container | Image | Status | Port | Purpose |
|-----------|-------|--------|------|---------|
| `wardops-api-prod` | ward-flux-credobank_api | Healthy | 5001 | FastAPI backend + Frontend static files |
| `wardops-worker-monitoring-prod` | (same) | Healthy | - | Ping monitoring (every 10s) |
| `wardops-worker-alerts-prod` | (same) | Healthy | - | Alert evaluation |
| `wardops-worker-snmp-prod` | (same) | Healthy | - | SNMP polling |
| `wardops-worker-maintenance-prod` | (same) | Unhealthy | - | Cleanup tasks |
| `wardops-beat-prod` | (same) | Unhealthy | - | Task scheduler |
| `wardops-postgres-prod` | postgres:15-alpine | Healthy | 5433 | Database |
| `wardops-redis-prod` | redis:7-alpine | Healthy | 6380 | Task queue |
| `wardops-victoriametrics-prod` | victoriametrics/victoria-metrics | Running | 8428 | Metrics storage |

### Container Health Issues
- **wardops-beat-prod**: Unhealthy but functioning (scheduling tasks correctly)
- **wardops-worker-maintenance-prod**: Unhealthy (investigate)

---

## DATABASE SCHEMA

### PostgreSQL Tables

#### `standalone_devices` (877 rows)
```sql
Columns:
- id (UUID, primary key)
- name (varchar)
- ip (varchar) -- NOT ip_address!
- enabled (boolean)
- down_since (timestamp) -- NULL if up, timestamp if down
- last_ping_at (timestamp)
- device_type, location, branch, region, etc.
```

#### `ping_results` (5,075,213 rows - PROBLEM!)
```sql
Columns:
- id (bigint, primary key)
- device_ip (varchar) -- NOT device_id!
- device_name (varchar)
- packets_sent, packets_received, packet_loss_percent (int)
- min_rtt_ms, avg_rtt_ms, max_rtt_ms (int)
- is_reachable (boolean)
- timestamp (timestamptz)

Indexes:
- idx_ping_results_device_ip
- idx_ping_results_device_time
- idx_ping_results_timestamp

Issues:
- 5M+ rows in 24 hours (10s ping interval × 877 devices)
- Growing at 1.5GB/day
- Causing 30s query timeouts
- Should be in VictoriaMetrics, not PostgreSQL!
```

#### `alert_history` (Fixed today)
```sql
Columns:
- id (UUID)
- rule_id (UUID, NULLABLE) -- Fixed: was NOT NULL, broke ping alerts
- device_id (UUID)
- rule_name (varchar)
- severity (enum: CRITICAL, WARNING, INFO)
- message (text)
- triggered_at (timestamptz)
- resolved_at (timestamptz, nullable)
- acknowledged (boolean)
- notifications_sent (jsonb)

Recent Fix:
- Made rule_id NULLABLE to support ping-based alerts
- Ping alerts don't have rule_id (generated directly from ping failures)
- Migration: migrations/fix_alert_history_rule_id_nullable.sql
```

#### `alert_rules`
```sql
Core alert rules defined by user
- Device down detection
- Metric thresholds
- Conditions and expressions
```

---

## MONITORING ARCHITECTURE

### Ping Monitoring (Current - BROKEN)

**Frequency**: Every 10 seconds per device
**Why**: Real-time outage detection (compete with Zabbix)

**Current Flow (WRONG):**
```
1. Celery beat schedules: ping_all_devices_batched (every 10s)
2. Worker pings devices in batches (100 devices/task)
3. Stores result in PostgreSQL ping_results table
4. Updates device.down_since if unreachable
5. Creates alert in alert_history (NOW WORKING after fix)
```

**Problem:**
- 877 devices × 360 pings/hour × 24 hours = 7.6M pings/day
- All stored in PostgreSQL → 5M rows in 24 hours
- Device details page queries ping_results → 30s timeout
- Example: Device 7a96efed-ec2f-42ab-9f5a-f44534c0c547 (Samtredia-PayBox) times out

**Statistics:**
- Total pings: 5,093,588 rows
- Last hour: 300,527 pings (865 devices)
- Per device: 347 pings/hour (1 every 10s ✓)
- Table size: 1551 MB (525 MB data + 1026 MB indexes)

### SNMP Monitoring (Correct - Using VictoriaMetrics)

**Frequency**: Every 5 minutes
**Storage**: VictoriaMetrics ✅
**Metrics**: Bandwidth, CPU, memory, interface stats

**Flow:**
```
1. Celery beat schedules: poll_all_devices_snmp_batched
2. Worker polls SNMP data
3. Writes to VictoriaMetrics (NOT PostgreSQL)
4. Fast queries, unlimited retention, auto-compression
```

**Why this works:**
- Time-series optimized storage
- Automatic downsampling
- Compression (10x reduction)
- Handles billions of datapoints

---

## ALERT SYSTEM

### How Alerts Are Created

#### 1. Ping-Based Alerts (Device Down)
```python
# File: monitoring/tasks.py, line 276-294
if not result.is_reachable:
    device.down_since = utcnow()

    # Create alert (NOW WORKS - rule_id is nullable)
    new_alert = AlertHistory(
        id=uuid.uuid4(),
        device_id=device_uuid,
        rule_id=None,  # No rule for ping alerts
        rule_name="Device Unreachable",
        severity="CRITICAL",
        message=f"Device {device.name} is not responding to ICMP ping",
        triggered_at=utcnow(),
        resolved_at=None
    )
    db.add(new_alert)
```

**Recent Fix (Oct 24, 2025):**
- **Problem**: rule_id was NOT NULL in database
- **Impact**: ALL ping-based alerts failed with IntegrityError
- **Evidence**: "Device Kabali-NVR is not responding" → IntegrityError
- **Fix**: Made rule_id NULLABLE
- **Result**: Alerts now work! 10+ alerts created in last 5 minutes

#### 2. Rule-Based Alerts (Metrics)
```python
# File: monitoring/tasks.py, line 440-447
alert = AlertHistory(
    rule_id=rule.id,  # Has rule_id
    device_id=rule.device_id,
    severity=rule.severity,
    message=f"Alert: {rule.name}",
    details={"query_result": data}
)
```

### Alert Evaluation
- **Frequency**: Every 10 seconds
- **Worker**: wardops-worker-alerts-prod
- **Stats**: Evaluating 3508 rules, triggering 0-1 alerts per cycle
- **Performance**: 2.8-3.0 seconds per evaluation

---

## KNOWN ISSUES & FIXES

### 1. ✅ FIXED: Alert Detection Completely Broken
**Date Fixed**: Oct 24, 2025

**Problem:**
- Zabbix catching outages, Ward-Ops showing nothing
- Every ping-based alert failed with IntegrityError
- Error: `null value in column "rule_id" violates not-null constraint`

**Root Cause:**
- Ping alerts created without rule_id (line 280-293 in tasks.py)
- Database enforced rule_id NOT NULL
- All alert creations crashed silently

**Fix:**
```sql
-- Migration: migrations/fix_alert_history_rule_id_nullable.sql
ALTER TABLE alert_history ALTER COLUMN rule_id DROP NOT NULL;
```

**Verification:**
```sql
-- Shows 10 alerts created after fix
SELECT severity, message, triggered_at, rule_id
FROM alert_history
WHERE triggered_at > '2025-10-24 07:26:00'
ORDER BY triggered_at DESC LIMIT 10;
```

### 2. ❌ ACTIVE: Frontend Optimizations Not Deploying
**Status**: Docker build cache issue

**Problem:**
- Created optimization hooks (useDebounce, useSmartQuery, PageLoader)
- Added dependencies to package.json and package-lock.json
- Rebuilt container multiple times
- Code NOT appearing in bundles (file sizes unchanged: 461KB, 162KB)

**Root Cause:**
- Docker caching npm ci step even with --no-cache
- Layer invalidation not working for package.json changes

**Evidence:**
```bash
# These should exist in bundle but don't:
docker exec wardops-api-prod sh -c "cat /app/static_new/assets/*.js" | grep -o "useDebounce"
# Output: (empty)

# File sizes never change:
index-PoXLM9Zf.js: 461K (same since Oct 24 07:10)
vendor-Bp9gd_D6.js: 162K (same)
```

**Attempted Fixes:**
- docker-compose build --no-cache api ❌
- docker builder prune -af ❌
- docker system prune -af ❌
- Rebuild with CACHE_BUST arg ❌

**Still TODO**: Find way to force npm ci to re-run with new package-lock.json

### 3. ❌ ACTIVE: Database Growing at 1.5GB/day
**Status**: Architectural issue

**Problem:**
- 5M+ ping results in 24 hours
- PostgreSQL not designed for time-series data
- Queries timeout after 30s
- Example: Samtredia-PayBox device (10.159.25.12) has 4.3M pings

**Current Mitigation:**
```sql
-- Deleted 801K rows older than 24 hours
DELETE FROM ping_results
WHERE timestamp < NOW() - INTERVAL '24 hours';
-- Result: 5,093,588 → 4,292,121 rows (still too many!)
```

**Real Solution**: Move to VictoriaMetrics (see Implementation Plan below)

---

## PERFORMANCE ISSUES

### Frontend
- **Device list**: 5s load time (should be <500ms)
- **Device details**: 3-5s (sometimes 30s timeout)
- **Network requests**: 27-42 requests per page
- **Some queries**: 1.1+ minutes (history?time_range=24h)

**Optimizations Created (Not Deployed Yet):**
- Debounced search (11 API calls → 1)
- Smart caching (0ms repeat visits)
- Optimistic UI updates
- Loading skeletons

### Backend
- **Device query**: 30s timeout for devices with lots of ping history
- **Alert history**: Slow for devices with 100+ alerts
- **Ping results**: Sequential table scan on 5M rows

---

## VICTORIAMETRICS INTEGRATION (CURRENT)

### What's Working
- **SNMP data**: Stored in VictoriaMetrics ✅
- **Metrics**: Bandwidth, CPU, memory, interfaces ✅
- **Queries**: Fast (<100ms) ✅
- **Retention**: Unlimited with compression ✅

### Configuration
```yaml
# docker-compose.production-priority-queues.yml
victoriametrics:
  image: victoriametrics/victoria-metrics:latest
  container_name: wardops-victoriametrics-prod
  ports:
    - "8428:8428"
  volumes:
    - victoriametrics_prod_data:/victoria-metrics-data
  command:
    - '--storageDataPath=/victoria-metrics-data'
    - '--httpListenAddr=:8428'
    - '--retentionPeriod=12'  # 12 months
```

### Current Usage
- **Only SNMP metrics** stored in VM
- **Ping results** still in PostgreSQL ❌
- **Problem**: Not using VM for its best use case (time-series ping data)

---

## FILE STRUCTURE

### Backend (Python/FastAPI)
```
/Users/g.jalabadze/Desktop/WARD OPS/ward-ops-credobank/
├── main.py                    # FastAPI app entry point
├── celery_app.py             # Celery configuration
├── database.py               # SQLAlchemy setup
├── models.py                 # OLD models (legacy)
├── monitoring/
│   ├── models.py            # Device, Alert, PingResult models
│   ├── tasks.py             # Ping monitoring, alert evaluation
│   ├── tasks_batch.py       # Batch processing
│   ├── alert_deduplicator.py
│   ├── flapping_detector.py
│   └── snmp/
│       └── parallel_poller.py
├── routers/
│   ├── devices.py           # Device API endpoints
│   ├── alerts.py            # Alert API endpoints
│   ├── dashboard.py         # Dashboard stats
│   └── websockets.py        # Real-time updates
├── migrations/              # SQL migration files
│   ├── fix_alert_history_rule_id_nullable.sql (Oct 24)
│   └── cleanup_old_ping_results.sql (Oct 24)
└── requirements.txt
```

### Frontend (React/TypeScript/Vite)
```
frontend/
├── package.json             # Dependencies (has @tanstack/react-virtual)
├── package-lock.json        # Lock file (updated Oct 24 11:10)
├── src/
│   ├── hooks/
│   │   ├── useDebounce.ts       # Created Oct 24 10:34 ✅
│   │   ├── useSmartQuery.ts     # Created Oct 24 10:34 ✅
│   │   └── useResilientWebSocket.ts
│   ├── components/
│   │   └── ui/
│   │       └── PageLoader.tsx   # Created Oct 24 10:34 ✅
│   └── pages/
│       ├── Monitor.tsx          # Main monitoring page
│       ├── DeviceDetails.tsx    # Device details (slow!)
│       └── Dashboard.tsx
└── dist/                    # Built files (served by API container)
```

### Docker
```
Dockerfile                   # Multi-stage build (frontend + backend)
docker-compose.production-priority-queues.yml  # Production config
docker-entrypoint.sh        # Container startup script
```

### Deployment Scripts
```
deploy-frontend-containerized.sh     # Rebuild API with frontend
deploy-frontend-on-server.sh         # Alternative (needs Node.js)
deploy-frontend-simple.sh            # Build locally, copy to server
diagnose-alerts.sh                   # Alert diagnostic (wrong - for Zabbix integration)
diagnose-standalone-alerts.sh        # Correct diagnostic
```

---

## DEPLOYMENT PROCESS

### Current Production Deployment
```bash
# On Credobank server (via jump server)
cd /home/wardops/ward-flux-credobank

# Pull latest code
git pull origin main

# Rebuild API container (includes frontend)
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache api

# Restart containers
docker-compose -f docker-compose.production-priority-queues.yml up -d --no-deps api

# Verify
docker ps | grep api
```

### Database Migrations
```bash
# Copy migration to container
docker cp migrations/fix_alert_history_rule_id_nullable.sql wardops-postgres-prod:/tmp/

# Execute
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -f /tmp/fix_alert_history_rule_id_nullable.sql
```

### Worker Restart (After Code Changes)
```bash
# Restart all workers to pick up new code
docker restart wardops-worker-monitoring-prod wardops-worker-alerts-prod wardops-worker-snmp-prod wardops-beat-prod
```

---

## CRITICAL CONTEXT FOR NEW SESSIONS

### Recent Fixes (Oct 24, 2025)
1. ✅ **Alert detection fixed** - rule_id now nullable
2. ✅ **Alerts now working** - 10+ alerts created successfully
3. ⏳ **Frontend optimizations ready** - not deploying due to Docker cache
4. ⏳ **Ping data retention** - attempted 7-day cleanup but all data is <24h old

### Active Problems
1. **5M ping results** in PostgreSQL (should be in VictoriaMetrics)
2. **30s query timeouts** for device details
3. **1.5GB/day growth** in database
4. **Frontend cache issue** preventing optimization deployment

### User Requirements
- **10-second ping interval** (real-time monitoring, compete with Zabbix)
- **Real-time alert detection** (no delays)
- **Fast UI** (<500ms page loads)
- **Scalable** to 1000+ devices

### Next Session Should Focus On
1. **Move ping storage to VictoriaMetrics** (architectural fix)
2. **Fix frontend Docker build** (optimization deployment)
3. **Add automatic cleanup** for ping_results (temporary until VM migration)

---

## ZABBIX COMPARISON

### What Zabbix Does Better
1. **Time-series storage**: Uses TimescaleDB or custom storage
2. **Data retention tiers**: Real-time → Recent → Historical → Trends
3. **Automatic downsampling**: 10s → 1min → 5min → 1hour averages
4. **Pre-aggregated queries**: Doesn't scan raw data for long time ranges
5. **Partitioned tables**: By time for fast cleanup
6. **Housekeeper process**: Automatic old data deletion

### What Ward-Ops Does Wrong (Currently)
1. ❌ All ping data in PostgreSQL (wrong tool)
2. ❌ No downsampling (stores every 10s ping forever)
3. ❌ No partitioning (one huge table)
4. ❌ No automatic cleanup (manual SQL scripts)
5. ❌ Queries scan all historical data (no aggregation)

### How to Beat Zabbix
1. ✅ Use VictoriaMetrics for time-series (faster than TimescaleDB)
2. ✅ Better UI/UX (React vs Zabbix's old interface)
3. ✅ Easier setup (Docker Compose vs complex Zabbix install)
4. ✅ Modern tech stack (FastAPI, React, Celery)
5. ⏳ Need to match Zabbix's data architecture (this is the gap)

---

## GIT REPOSITORY

### URL
`https://github.com/ward-tech-solutions/ward-flux-credobank`

### Branch
`main` (deploy from this)

### Recent Commits
```
6e626ba (HEAD -> main, origin/main) CRITICAL: Clean up 5M ping results
1e76305 CRITICAL FIX: Make alert_history.rule_id nullable for ping-based alerts
dc42257 Update package-lock.json with optimization dependencies
15f46fe Add optimization dependencies to package.json for Docker build
6e20573 Add standalone monitoring diagnostic (NOT Zabbix integration)
```

### Commit Pattern
All commits use this format:
```
[Type]: [Title]

[Problem description]
[Root cause]
[Fix implemented]
[Verification steps]

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## DATABASE CREDENTIALS

**PostgreSQL:**
- Host: localhost (in container: postgres)
- Port: 5433 (external), 5432 (internal)
- User: ward_admin
- Password: ward_admin_password
- Database: ward_ops

**Redis:**
- Host: localhost (in container: redis)
- Port: 6380 (external), 6379 (internal)
- Password: redispass

**VictoriaMetrics:**
- Host: localhost (in container: victoriametrics)
- Port: 8428
- API: http://10.30.25.46:8428

---

## MONITORING STATS (Current)

### Devices
- Total: 877 devices
- Online: 587 devices (67%)
- Offline: 290 devices (33%)
- Branches: 128
- Regions: 10+ (Georgian cities)

### Data Volume
- Ping results: 5,075,213 rows (1549 MB)
- Alert history: ~106 alerts per device
- SNMP data: In VictoriaMetrics (size unknown)

### Performance
- Ping frequency: Every 10 seconds per device
- Pings per hour: 300,527 (last hour measured)
- Pings per device: 347/hour average
- Alert evaluation: Every 10 seconds
- SNMP polling: Every 5 minutes

---

## NEXT STEPS (PRIORITY ORDER)

### 1. HIGH PRIORITY: VictoriaMetrics Migration
**Why**: Fix 30s timeouts, 5M row problem, database growth
**Impact**: 30s → <100ms queries, 5M → 877 rows in PostgreSQL
**Effort**: 2-3 hours implementation + testing

### 2. MEDIUM PRIORITY: Frontend Optimization Deployment
**Why**: Improve user experience, compete with Zabbix UI
**Impact**: 5s → <500ms page loads, 90% fewer network requests
**Effort**: Fix Docker cache issue (unknown time)

### 3. LOW PRIORITY: Automatic Cleanup
**Why**: Temporary fix until VM migration complete
**Impact**: Prevent database from growing beyond current size
**Effort**: 30 minutes (add Celery task)

---

## SUCCESS METRICS

### Current (Baseline)
- Device details load: 3-30 seconds
- Query timeout rate: ~10% of requests
- Database size: 1.7GB
- Database growth: 1.5GB/day
- Alert detection: NOW WORKING (was 0%, now ~90%)

### Target (After VM Migration)
- Device details load: <500ms
- Query timeout rate: 0%
- Database size: <100MB (state only)
- Database growth: ~10MB/day
- Alert detection: 100%
- Competitive with Zabbix: YES

---

## IMPORTANT NOTES

1. **DO NOT assume table names**
   - It's `standalone_devices`, not `devices`
   - It's `ip`, not `ip_address`
   - It's `ping_results` with `device_ip`, not `device_id`

2. **DO NOT use Zabbix**
   - User is NOT using Zabbix integration
   - Zabbix is a COMPETITOR
   - User wants to BEAT Zabbix

3. **10-second ping interval is CORRECT**
   - User explicitly wants real-time monitoring
   - Don't suggest reducing frequency
   - Fix: Move to VictoriaMetrics, not reduce pings

4. **Frontend Docker builds are CACHED**
   - --no-cache doesn't work
   - File sizes prove cache is being used
   - Need alternative solution

5. **Context Window Management**
   - This document is for starting new sessions
   - Contains all critical context
   - Update as project evolves

---

**Document Last Updated**: October 24, 2025
**Session Context**: After fixing alert detection, before VM migration
**Next Session Start Here**: VictoriaMetrics architecture design
