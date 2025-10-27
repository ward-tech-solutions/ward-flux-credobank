# TOPOLOGY PHASE 1 - DEPLOYMENT READY ✅

## Summary
Phase 1 of ISP Router Topology enhancement is **COMPLETE** and ready for production deployment.

## What Was Implemented

### 1. Topology Page Filtering
**File**: `frontend/src/pages/Topology.tsx`

- **Filter to .5 routers ONLY**: Shows approximately 93 ISP routers across Georgia
- **ISP Status Display**: Live Magti/Silknet status from PostgreSQL
- **Enhanced Node Labels**: Shows device name, IP, and ISP link status
  ```
  Example Label:
  Router-Tbilisi-Center
  10.195.57.5
  🟢 Magti: UP | 🟢 Silknet: UP
  ```
- **Auto-refresh**: Status updates every 30 seconds via React Query

### 2. Monitor Page Navigation
**File**: `frontend/src/pages/Monitor.tsx`

- **Grid View**: Topology button added to device cards for .5 routers
- **Table View**: Topology button added to actions column for .5 routers
- **Button Behavior**:
  - Network icon (from lucide-react)
  - Tooltip: "View ISP Topology"
  - Navigates to: `/topology?deviceId=X&deviceName=Y`
  - Only visible for IPs ending in .5

### 3. Data Source (Phase 1)
**Source**: PostgreSQL `device_interfaces` table

```sql
-- Example data that Phase 1 uses:
SELECT if_name, isp_provider, oper_status
FROM device_interfaces
WHERE device_id IN (
  SELECT id FROM standalone_devices WHERE ip = '10.195.57.5'
);

-- Results:
-- Fa3, magti, 1 (UP)
-- Fa4, silknet, 1 (UP)
```

**API Endpoint**: `/api/v1/interfaces/isp-status/bulk?device_ips=10.195.57.5,10.195.110.62,...`

**Response Format**:
```json
{
  "10.195.57.5": {
    "magti": {
      "status": "up",
      "interface": "FastEthernet3",
      "last_checked": "2025-10-27T10:30:00Z"
    },
    "silknet": {
      "status": "up",
      "interface": "FastEthernet4",
      "last_checked": "2025-10-27T10:30:00Z"
    }
  }
}
```

## What Phase 1 Does NOT Include

❌ **Bandwidth Display** - This is Phase 2
- Requires VictoriaMetrics data
- Requires Celery Beat container rebuild
- Will show: "↓12.5 Mbps ↑3.2 Mbps"

❌ **Historical Metrics** - Future enhancement
- Bandwidth graphs over time
- Interface utilization percentages

## Deployment Instructions

### Production Server: 10.30.25.46
SSH to jump server first: `ssh wardops@10.30.25.46`

### Deployment Steps:

```bash
# 1. Navigate to project directory
cd /Users/g.jalabadze/Desktop/WARD\ OPS/ward-ops-credobank

# 2. Pull latest changes
git pull origin main

# 3. Run deployment script
./deploy-topology-phase1.sh

# 4. Monitor deployment
docker-compose -f docker-compose.production-priority-queues.yml logs -f api
```

### Expected Deployment Time: ~3-5 minutes
- Stop API: 10 seconds
- Build (no cache): 2-3 minutes
- Start + healthcheck: 30 seconds

## Testing Checklist

After deployment, verify:

### Monitor Page:
- [ ] Open: http://localhost:5173/monitor
- [ ] Find device with .5 IP (e.g., 10.195.57.5, 10.195.110.62)
- [ ] Verify topology button (Network icon) is visible
- [ ] Click topology button
- [ ] Verify navigation to topology page

### Topology Page:
- [ ] Open: http://localhost:5173/topology
- [ ] Verify ONLY .5 routers are displayed (~93 devices)
- [ ] Verify node labels show ISP status
- [ ] Look for format: "🟢 Magti: UP | 🔴 Silknet: DOWN"
- [ ] Wait 30 seconds, verify status updates automatically
- [ ] Check that non-.5 devices are NOT shown

### PostgreSQL Verification:
```sql
-- Verify interface data exists
SELECT
  sd.ip,
  di.if_name,
  di.isp_provider,
  di.oper_status,
  di.last_checked
FROM device_interfaces di
JOIN standalone_devices sd ON di.device_id = sd.id
WHERE sd.ip LIKE '%.5'
  AND di.isp_provider IN ('magti', 'silknet')
ORDER BY sd.ip, di.isp_provider;
```

## Rollback Procedure

If Phase 1 deployment has issues:

```bash
# Rollback to previous commit
git revert HEAD

# Rebuild API container
docker-compose -f docker-compose.production-priority-queues.yml stop api
docker-compose -f docker-compose.production-priority-queues.yml rm -f api
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache api
docker-compose -f docker-compose.production-priority-queues.yml up -d api
```

## Phase 2 - Next Steps (After Phase 1 Verification)

### Prerequisites for Phase 2:
1. Phase 1 must be working correctly
2. VictoriaMetrics must be accessible
3. Celery Beat queue fix must be deployed

### Phase 2 Deployment:
```bash
# Deploy Celery Beat fix
./deploy-task-routing-fix.sh

# Wait 2-3 minutes for metrics collection
sleep 180

# Verify metrics in VictoriaMetrics
curl -s 'http://localhost:8428/api/v1/query?query=interface_if_hc_in_octets{device_ip="10.195.57.5"}' | jq .
```

### Phase 2 Implementation Tasks:
1. Create `/api/v1/interfaces/isp-bandwidth/realtime` endpoint
2. Query VictoriaMetrics for bandwidth metrics
3. Add bandwidth labels to topology nodes
4. Format: "↓12.5 Mbps ↑3.2 Mbps" below ISP status

## Architecture Decisions

### Why Two Phases?

**Phase 1 (PostgreSQL)** - Low Risk:
- ✅ Data already exists (oper_status field)
- ✅ No Celery changes required
- ✅ Fast deployment
- ✅ Immediate value (ISP status display)

**Phase 2 (VictoriaMetrics)** - Higher Risk:
- ⚠️ Requires Celery task fix
- ⚠️ Requires container rebuild
- ⚠️ 2-3 minutes for first metrics
- ⚠️ More complex error handling

### Data Flow

**Phase 1**:
```
PostgreSQL → FastAPI → React Query → Topology Page
(Real-time: oper_status field updated by SNMP poller)
```

**Phase 2** (Pending):
```
SNMP Collector → VictoriaMetrics → FastAPI → React Query → Topology Page
(Real-time: bandwidth metrics from interface_if_hc_in_octets/out_octets)
```

## Git Commits

### Phase 1 Commits:
1. `74bde80` - CRITICAL FIX: Use device.down_since as source of truth
2. `e90dfa0` - FEATURE: ISP Router Topology Navigation - Phase 1 Complete

### Phase 2 Commits (Pending):
- Celery Beat queue fix (ready to commit)
- Bandwidth display implementation (after Celery fix verification)

## Support Information

### Files Modified (Phase 1):
- `frontend/src/pages/Topology.tsx` - ISP router filtering and status display
- `frontend/src/pages/Monitor.tsx` - Navigation button for .5 routers
- `frontend/src/services/api.ts` - Changed to PostgreSQL endpoint

### Files Ready for Phase 2:
- `celery_app.py` - Task routing fix (not yet deployed)
- `deploy-task-routing-fix.sh` - Deployment script

### Key Metrics:
- **ISP Routers**: ~93 devices with .5 IPs
- **ISP Providers**: 2 (Magti, Silknet)
- **Status Refresh**: Every 30 seconds
- **Data Source**: PostgreSQL (Phase 1), VictoriaMetrics (Phase 2)

## Production Environment

### Server Details:
- **Production Server**: 10.30.25.46
- **SSH User**: wardops
- **Project Path**: `/Users/g.jalabadze/Desktop/WARD OPS/ward-ops-credobank`
- **Docker Compose File**: `docker-compose.production-priority-queues.yml`
- **Docker Version**: Older version (requires `docker-compose` with hyphen)

### Container Names:
- `wardops-api-prod` - FastAPI backend + Frontend
- `wardops-beat-prod` - Celery Beat scheduler
- `wardops-worker-snmp-prod` - SNMP polling worker
- `wardops-postgres-prod` - PostgreSQL database
- `wardops-victoriametrics-prod` - VictoriaMetrics TSDB

### Port Mappings:
- API: 5001 (internal) → 5001 (external)
- Frontend: 80 (internal) → 5173 (external)
- PostgreSQL: 5432 (internal) → 5433 (external)
- VictoriaMetrics: 8428 (internal) → 8428 (external)

## Success Criteria

Phase 1 is considered successful when:

✅ **Functional Requirements**:
1. Topology page displays ONLY .5 routers
2. ISP status shows for Magti and Silknet
3. Status colors are correct (🟢 UP, 🔴 DOWN)
4. Navigation works from Monitor page
5. Status updates every 30 seconds

✅ **Technical Requirements**:
1. No console errors in browser
2. API responds within 200ms
3. PostgreSQL queries are efficient
4. No memory leaks in React components
5. Docker containers are healthy

✅ **User Experience**:
1. Topology loads within 2 seconds
2. Navigation is instant (no lag)
3. Status updates are seamless
4. Button placement is intuitive
5. Tooltips are helpful

## Contact

For issues or questions:
- Review git commit messages
- Check container logs: `docker-compose logs -f api`
- Verify PostgreSQL data exists
- Ensure ISP routers have .5 IPs

---

**Status**: ✅ READY FOR PRODUCTION DEPLOYMENT
**Version**: Phase 1 Complete
**Date**: 2025-10-27
**Deployment Script**: `./deploy-topology-phase1.sh`
