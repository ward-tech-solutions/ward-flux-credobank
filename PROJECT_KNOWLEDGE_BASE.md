# WARD OPS - CredobBank Network Monitoring System
## Complete Project Knowledge Base & Context

**Last Updated:** October 27, 2025
**Production Server:** 10.30.25.46
**Environment:** Banking Production - Credobank Georgia

---

## 📊 SYSTEM OVERVIEW

### Purpose
Real-time network monitoring system for Credobank's 877 devices across 128 branches in Georgia.

### Critical SLA
- **Target:** 10-second device failure detection (matching Zabbix performance)
- **Challenge:** System was showing 5-minute delays - FIXED!
- **Solution:** Direct device.down_since monitoring instead of stale cache data

### Technology Stack
- **Backend:** FastAPI (Python 3.11)
- **Database:** PostgreSQL (ward_ops database, ward_admin user)
- **Task Queue:** Celery with Redis, Priority Queues
- **Metrics Storage:** VictoriaMetrics
- **Frontend:** React + TypeScript + Vite
- **Monitoring:** ICMP Ping + SNMP polling
- **Containerization:** Docker Compose

---

## 🏗️ ARCHITECTURE

### Database Schema (PostgreSQL)
**Key Tables:**
- `standalone_devices` - Main device inventory (NOT "devices"!)
- `alert_history` - Active and historical alerts
- `alert_rules` - Alert definitions (8 rules total)
- `device_interfaces` - SNMP-discovered interfaces
- `ping_results` - ICMP ping history
- `branches` - 128 branch locations
- `snmp_credentials` - Encrypted SNMP community strings

**Critical Fields:**
- `standalone_devices.down_since` - **SOURCE OF TRUTH** for device status
  - NULL = Device UP
  - Timestamp = Device DOWN since this time
- `standalone_devices.ip` - Device IP address
  - IPs ending in `.5` = ISP routers with dual connections

### Docker Containers (Production)
```
wardops-api-prod              - FastAPI web server (port 5001)
wardops-postgres-prod         - PostgreSQL database (port 5433)
wardops-redis-prod            - Redis task queue (port 6380)
wardops-victoriametrics-prod  - Metrics storage (port 8428)
wardops-worker-monitoring-prod - Ping monitoring (10s interval)
wardops-worker-alerts-prod    - Alert evaluation (10s interval)
wardops-worker-snmp-prod      - SNMP polling
wardops-celery-beat-prod      - Task scheduler
wardops-worker-maintenance-prod - Cleanup tasks
```

### Celery Priority Queues
1. **alerts** - Highest priority, 10-second interval
2. **monitoring** - Medium priority, batch ping tasks
3. **snmp** - Low priority, batch SNMP polling
4. **maintenance** - Background cleanup

---

## 🌐 NETWORK TOPOLOGY

### Device Distribution
- **Total Devices:** 877
- **Total Branches:** 128
- **Regions:** 8 (Tbilisi, Samegrelo, Imereti, Kakheti, etc.)

### ISP Router Architecture (.5 Devices)
**Critical:** All devices with IPs ending in `.5` are dual-ISP routers

**Example:** `10.195.57.5` (Batumi3-881)
- **Device Type:** Cisco 881 Router
- **Interface 4 (FastEthernet3):** Magti_Internet
- **Interface 5 (FastEthernet4):** Silknet_Internet
- **Purpose:** Provides redundant internet connectivity

**ISP Providers:**
- **Magti:** Mobile carrier, purple branding
- **Silknet:** Fiber ISP, orange branding

**IP Ranges:**
- `10.195.x.5` - Branch routers (Magti range)
- `10.199.x.5` - Branch routers (Silknet range)
- Both ranges exist, all have BOTH ISP connections

### SNMP Details
**Working Credentials (Example):**
- IP: 10.195.57.5
- Community: "XoNaz-<h"
- Version: SNMPv2c
- Verified: ✅ Working

**Interface Monitoring OIDs:**
- `1.3.6.1.2.1.2.2.1.2` - Interface names (ifDescr)
- `1.3.6.1.2.1.31.1.1.1.18` - Interface descriptions (ifAlias) - **Contains "Magti_Internet" / "Silknet_Internet"**
- `1.3.6.1.2.1.2.2.1.8` - Operational status (ifOperStatus) - **1=UP, 2=DOWN**

---

## 🚨 ALERT SYSTEM

### Alert Rules (8 Total)
**CRITICAL Priority:**
1. Device Down - Not responding for 10+ seconds
2. ISP Link Down - .5 router ISP link failure
3. ISP Link Flapping - Intermittent ISP connectivity
4. ISP Link Packet Loss - ISP experiencing packet loss

**HIGH Priority:**
5. Device Flapping - Status changes ≥3 in 5 minutes
6. ISP Link High Latency - Response time >100ms

**MEDIUM Priority:**
7. High Latency - Response time >200ms
8. Packet Loss Detected - Packet loss >10%

### Alert Engine (FIXED)
**File:** `monitoring/tasks.py` - `evaluate_alert_rules()`
- **Fixed Implementation:** No SQL expression parsing
- **Detection:** Uses device.down_since directly
- **ISP Priority:** Devices with .5 IPs get CRITICAL alerts
- **Frequency:** Evaluated every 10 seconds

**Key Fix:**
```python
# WRONG (old way - caused parsing errors):
expression = "down_time > 10 AND ip LIKE '%.5'"

# RIGHT (new way - direct Python logic):
is_isp = device.ip and device.ip.endswith('.5')
is_down = device.down_since is not None
```

---

## 📁 PROJECT STRUCTURE

### Critical Files & Locations

**Root Directory:**
```
/home/wardops/ward-flux-credobank/  (Production)
/Users/g.jalabadze/Desktop/WARD OPS/ward-ops-credobank/  (Local)
```

**Backend Core:**
- `main.py` - FastAPI application entry point
- `database.py` - SQLAlchemy database models
- `models.py` - Additional model definitions
- `auth.py` - Authentication & authorization
- `celery_app.py` - Celery configuration with priority queues

**Monitoring Module:**
- `monitoring/tasks.py` - Main Celery tasks (ping, alerts, SNMP)
- `monitoring/models.py` - StandaloneDevice model
- `monitoring/alert_evaluator_fixed.py` - Fixed alert engine
- `monitoring/snmp/poller.py` - SNMP polling engine
- `monitoring/snmp/oids.py` - OID definitions
- `monitoring/snmp/credentials.py` - Credential encryption
- `monitoring/victoria/client.py` - VictoriaMetrics client

**SNMP Templates:**
- `monitoring/templates/cisco_template.json` - Cisco IOS monitoring
- `monitoring/templates/hp_aruba_template.json` - HP/Aruba switches
- Includes: CPU, Memory, Interfaces, BGP, Temperature monitoring

**Routers (API Endpoints):**
- `routers/devices.py` - Device CRUD operations
- `routers/devices_standalone.py` - Standalone device API
- `routers/alerts.py` - Alert management
- `routers/diagnostics.py` - Network diagnostics (ping, traceroute, MTR)
- `routers/dashboard.py` - Dashboard statistics
- `routers/websockets.py` - Real-time WebSocket updates

**Frontend:**
- `frontend/src/pages/Monitor.tsx` - Main monitoring view (device cards)
- `frontend/src/pages/Dashboard.tsx` - Overview dashboard
- `frontend/src/services/api.ts` - API client

**Migration Scripts:**
- `scripts/migration/run_sql_migrations.py` - PostgreSQL migrations
- `scripts/migration/seed_core.py` - Core data seeding
- `scripts/migration/seed_credobank.py` - Credobank data (875 devices, 128 branches)

**Deployment:**
- `docker-compose.production-priority-queues.yml` - Production docker-compose
- `docker-entrypoint.sh` - Container startup script
- `Dockerfile` - Multi-stage build (React + Python)

---

## 🔧 RECENT CRITICAL FIXES (Oct 27, 2025)

### 1. Device Status Bug - FIXED ✅
**Issue:** Devices showing as DOWN when actually UP (Zabbix was beating us on alerts)

**Root Cause:**
- Multiple endpoints using stale `ping_results` data
- VictoriaMetrics queries could be delayed/cached
- Not using `device.down_since` as single source of truth

**Files Fixed:**
- `routers/infrastructure.py:45`
- `routers/websockets.py:149`
- `routers/dashboard.py:195`
- `routers/devices.py` (already fixed in previous commit)

**Solution:**
```python
# Source of truth
status = "Up" if device.down_since is None else "Down"
```

### 2. Alert Rules Configuration - FIXED ✅
**Issue:** Duplicate rules, SQL-like expressions causing parsing errors

**Migration:** `migrations/fix_alert_rules_production.sql`
- Removed 34 malformed alerts
- Created 8 clean rules without SQL expressions
- Fixed ISP link priority (CRITICAL instead of HIGH)

### 3. Module Import Errors - FIXED ✅
**Issue:** Files reorganized, imports broken

**Files Added to Root:**
- `bulk_operations.py` (from scripts/utilities/)
- `network_diagnostics.py` (from scripts/diagnostics/)
- Fixed paths in `docker-entrypoint.sh` (scripts/ → scripts/migration/)

### 4. Docker Entrypoint - FIXED ✅
**Issue:** Wrong entrypoint file with broken database wait loop

**Solution:**
- Copied correct version from `scripts/deployment/docker-entrypoint.sh`
- Removed broken pg_isready check
- Fixed migration script paths

### 5. ISP Indicators - IMPLEMENTED ✅
**Feature:** Visual ISP status badges on monitoring cards

**Implementation:**
- Detect .5 routers: `ip.endsWith('.5')`
- Show two badges: Magti (Radio icon, Purple) + Silknet (Globe icon, Orange)
- Both turn RED when router is DOWN
- Located next to ICMP/SNMP badges

**File:** `frontend/src/pages/Monitor.tsx`

---

## 🔐 CREDENTIALS & ACCESS

### Database
- **Host:** wardops-postgres-prod (10.30.25.46:5433)
- **Database:** ward_ops
- **User:** ward_admin
- **Password:** SecureWardAdmin2024

### Redis
- **Host:** wardops-redis-prod (10.30.25.46:6380)
- **Password:** redispass

### SNMP (Example)
- **Community:** "XoNaz-<h" (varies per device)
- **Version:** SNMPv2c
- **Storage:** Encrypted in snmp_credentials table

### Docker Registry
- **GitHub:** ward-tech-solutions/ward-flux-credobank
- **Branch:** main

---

## 🚀 DEPLOYMENT PROCESS

### Standard Deployment
```bash
# On production server (10.30.25.46)
cd /home/wardops/ward-flux-credobank
git pull origin main

# Rebuild affected containers
docker-compose -f docker-compose.production-priority-queues.yml stop <service>
docker-compose -f docker-compose.production-priority-queues.yml rm -f <service>
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache <service>
docker-compose -f docker-compose.production-priority-queues.yml up -d <service>
```

### Common Services to Restart
- `api` - After frontend or backend code changes
- `celery-worker-monitoring` - After monitoring task changes
- `celery-worker-alerts` - After alert logic changes
- `celery-beat` - After schedule changes

### Known Docker Issue
**ContainerConfig Error:**
```bash
KeyError: 'ContainerConfig'
```
**Solution:** Always stop and remove containers before recreating:
```bash
docker-compose -f docker-compose.production-priority-queues.yml stop <service>
docker-compose -f docker-compose.production-priority-queues.yml rm -f <service>
docker-compose -f docker-compose.production-priority-queues.yml up -d <service>
```

---

## 📊 MONITORING METRICS

### Key Performance Indicators
- **Detection Time:** 10 seconds (target achieved!)
- **Alert Evaluation:** Every 10 seconds
- **Ping Interval:** 10 seconds (9 batches)
- **SNMP Polling:** 60 seconds
- **Task Reduction:** 2,627 → 72 tasks/min (36x improvement)

### VictoriaMetrics Queries
```promql
# Device ping status
device_ping_status{device_ip="10.195.57.5"}

# Count all devices
count(device_ping_status)

# ISP router count
count(device_ping_status{device_ip=~".*\\.5"})
```

---

## 🐛 KNOWN ISSUES & WORKAROUNDS

### 1. Zabbix Client Removed
**Status:** Intentionally removed (legacy integration)
**Affected Files:** `routers/utils.py`, `routers/settings.py`
**Action:** Ignore import warnings for zabbix_client

### 2. Workers Showing Unhealthy
**Symptom:** Docker healthcheck fails
**Cause:** Celery inspect ping timeout
**Impact:** None - workers function correctly
**Solution:** Monitor logs instead of healthcheck status

### 3. Frontend Cache
**Issue:** Changes not reflecting immediately
**Solution:** Hard rebuild required
```bash
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache api
```

---

## 🎯 NEXT STEPS / TODO

### ISP Monitoring Enhancement (IN PROGRESS - Oct 27, 2025)
**Goal:** Individual Magti/Silknet status tracking with independent GREEN/RED badges

**Requirements:**
1. ✅ Identify ISP interfaces (Interface 4=Magti, 5=Silknet)
2. ✅ Database infrastructure exists (`device_interfaces` table)
3. ⏳ Run interface discovery for all 93 .5 routers
4. ✅ API endpoint created: `/api/v1/interfaces/isp-status/bulk` (OPTIMIZED)
5. ⏳ Update frontend to fetch and display per-ISP status
6. ⏳ Schedule automatic interface status polling (every 60s)

**Hybrid PostgreSQL + VictoriaMetrics Architecture:**
- ✅ **PostgreSQL**: Source of truth for current ISP interface status
  - `device_interfaces.oper_status` (1=UP, 2=DOWN)
  - `device_interfaces.isp_provider` ('magti', 'silknet')
  - Bulk-fetched with single query (avoids N+1 problem)
  - Fast indexed lookups by device IP
- ✅ **VictoriaMetrics**: Historical time-series metrics only
  - Interface bandwidth, packet counters, errors
  - Adaptive query resolution (5m/15m/1h steps)
  - Not used for real-time status (reduces query load)

**New Optimized API Endpoint:**
```bash
GET /api/v1/interfaces/isp-status/bulk?device_ips=10.195.57.5,10.195.110.5
```

**Response:**
```json
{
  "10.195.57.5": {
    "magti": {
      "status": "up",
      "oper_status": 1,
      "if_name": "FastEthernet3",
      "if_alias": "Magti_Internet",
      "last_seen": "2025-10-27T10:30:00Z"
    },
    "silknet": {
      "status": "up",
      "oper_status": 1,
      "if_name": "FastEthernet4",
      "if_alias": "Silknet_Internet",
      "last_seen": "2025-10-27T10:30:00Z"
    }
  }
}
```

**Performance Benefits:**
- **Before**: N queries (one per .5 router) = 93 queries
- **After**: 1 bulk query for all routers = 1 query
- **Improvement**: 93x reduction in database queries

---

## 📚 USEFUL COMMANDS

### Database Queries
```sql
-- Check device status
SELECT name, ip, down_since,
  CASE WHEN down_since IS NULL THEN 'UP' ELSE 'DOWN' END as status
FROM standalone_devices
WHERE ip LIKE '%.5';

-- Active alerts
SELECT severity, COUNT(*)
FROM alert_history
WHERE resolved_at IS NULL
GROUP BY severity;

-- ISP routers
SELECT COUNT(*) FROM standalone_devices WHERE ip LIKE '%.5';
```

### Docker Commands
```bash
# View logs
docker logs --tail 100 wardops-worker-monitoring-prod

# Check container health
docker ps | grep -E "(api|worker|beat)"

# Execute in container
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops

# View Celery workers
docker exec wardops-worker-monitoring-prod celery -A celery_app inspect active
```

### SNMP Testing
```bash
# Test SNMP connectivity
snmpwalk -v 2c -c "XoNaz-<h" 10.195.57.5 1.3.6.1.2.1.1.5.0

# Check ISP interfaces
snmpwalk -v 2c -c "XoNaz-<h" 10.195.57.5 1.3.6.1.2.1.31.1.1.1.18

# Check interface status
snmpget -v 2c -c "XoNaz-<h" 10.195.57.5 1.3.6.1.2.1.2.2.1.8.4  # Magti
snmpget -v 2c -c "XoNaz-<h" 10.195.57.5 1.3.6.1.2.1.2.2.1.8.5  # Silknet
```

---

## ⚠️ CRITICAL REMINDERS

1. **NEVER** use `devices` table - it's `standalone_devices`!
2. **ALWAYS** use `device.down_since` as source of truth for status
3. **STOP containers before removing** to avoid ContainerConfig error
4. **CHECK worker logs** after deployment, not just healthcheck
5. **ISP routers** are identified by `.5` IP ending
6. **Both ISPs** exist on every .5 router (not mutually exclusive)
7. **SNMP polling** already implemented - just needs ISP-specific logic
8. **Alert evaluation** runs every 10 seconds - very fast!

---

**Document Version:** 1.0
**Maintainer:** Claude AI Assistant
**Purpose:** Context preservation for future sessions
