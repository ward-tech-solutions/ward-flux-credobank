# TOPOLOGY ALL INTERFACES - IMPLEMENTATION STATUS

## Current Status: 70% COMPLETE

### ✅ COMPLETED (Backend + Data Layer)

#### 1. Backend API Endpoints
**File:** `routers/interfaces.py`

✅ `/api/v1/interfaces/by-devices` - Get ALL interfaces for devices
- Returns interface list with type, status, speed
- Ordered by if_index
- Filters enabled interfaces only

✅ `/api/v1/interfaces/bandwidth/realtime` - Get bandwidth from VictoriaMetrics
- Queries `interface_if_hc_in_octets` and `interface_if_hc_out_octets`
- Uses `rate()` function for bytes/second calculation
- Returns formatted bandwidth (e.g., "15.2 Mbps")
- Includes utilization percentage
- Graceful degradation if VictoriaMetrics empty

✅ `format_bandwidth()` helper function
- Converts bps to human-readable format
- Gbps / Mbps / Kbps / bps

#### 2. Frontend API Client
**File:** `frontend/src/services/api.ts`

✅ `interfacesAPI.getByDevices(deviceIps)` - TypeScript client
✅ `interfacesAPI.getBandwidthRealtime(deviceIps)` - TypeScript client
✅ Full type definitions for responses

#### 3. Frontend Data Queries
**File:** `frontend/src/pages/Topology.tsx`

✅ `interfacesData` query - Fetches all interfaces
- Refresh: Every 30 seconds
- Stale time: 25 seconds
- Enabled when ISP routers exist

✅ `bandwidthData` query - Fetches real-time bandwidth
- Refresh: Every 10 seconds (real-time)
- Stale time: 5 seconds
- Enabled when ISP routers exist

#### 4. Design Documentation
**File:** `TOPOLOGY-ALL-INTERFACES-DESIGN.md`

✅ Complete architecture document
✅ Visual layout design
✅ API specifications
✅ Deployment strategy
✅ Testing checklist

---

### 🔄 IN PROGRESS (Visualization Layer)

#### Topology Page - loadTopologyData() Function
**File:** `frontend/src/pages/Topology.tsx` (line 392+)

**What Needs to Change:**

Currently, the function loads topology from `/topology` API endpoint which returns router nodes and edges.

**New Implementation Needed:**

Instead of loading from API, build topology from:
1. `networkDevices` - List of .5 routers
2. `interfacesData` - ALL interfaces per router
3. `bandwidthData` - Bandwidth metrics per interface

**Required Node Structure:**

```typescript
// Router Node (Level 0)
{
  id: device.hostid,
  label: `${device.display_name}\n${device.ip}`,
  shape: 'icon',
  icon: { code: '🌍', size: 60, color: '#10b981' },
  level: 0,
}

// Interface Node (Level 1 - child of router)
{
  id: `${device.hostid}-iface-${iface.if_index}`,
  label: `${statusIcon} ${iface.if_name}\n${ispOrType}\n↓ ${bw_in}\n↑ ${bw_out}`,
  shape: 'ellipse',
  color: { background: ifaceUpColor, border: ifaceBorderColor },
  level: 1,
  font: { size: 12, multi: true },
}

// Edge (Router → Interface)
{
  id: `edge-${device.hostid}-${iface.if_index}`,
  from: device.hostid,
  to: `${device.hostid}-iface-${iface.if_index}`,
  arrows: '',
  color: { color: '#94a3b8' },
}
```

**Implementation Steps:**

1. Replace API call with local data processing
2. Loop through `networkDevices` to create router nodes
3. For each router, loop through `interfacesData[router.ip]` to create interface nodes
4. For each interface, look up `bandwidthData[router.ip][iface.if_name]` for bandwidth
5. Create edges from router to each interface
6. Build vis.js DataSet with all nodes and edges

**Code Location to Modify:**

Lines 392-608 in `frontend/src/pages/Topology.tsx`

Replace:
```typescript
const res = await api.getTopology({ view: 'hierarchical', limit: 200 })
const data: TopologyData = res.data as any
```

With:
```typescript
// Build topology from device + interface data
const allNodes = []
const allEdges = []

networkDevices.forEach(device => {
  // Create router node
  const routerNode = {
    id: device.hostid,
    label: `${device.display_name}\n${device.ip}`,
    title: `${device.display_name}\n${device.ip}\nType: ${device.device_type}`,
    shape: 'icon',
    icon: { code: '🌍', size: 60, color: '#10b981' },
    level: 0,
  }
  allNodes.push(routerNode)

  // Create interface nodes
  const interfaces = interfacesData?.[device.ip] || []
  interfaces.forEach(iface => {
    const bandwidth = bandwidthData?.[device.ip]?.[iface.if_name]
    const status = iface.oper_status === 1 ? 'UP' : 'DOWN'
    const statusIcon = status === 'UP' ? '🟢' : '🔴'
    const ispOrType = iface.isp_provider ? `ISP: ${iface.isp_provider.toUpperCase()}` : (iface.interface_type || 'LAN')

    const ifaceNode = {
      id: `${device.hostid}-iface-${iface.if_index}`,
      label: [
        `${statusIcon} ${iface.if_name}`,
        ispOrType,
        bandwidth ? `↓ ${bandwidth.bandwidth_in_formatted}` : '↓ --',
        bandwidth ? `↑ ${bandwidth.bandwidth_out_formatted}` : '↑ --',
      ].join('\n'),
      title: `Interface: ${iface.if_name}\nStatus: ${status}\nType: ${iface.interface_type}\nSpeed: ${iface.speed} bps`,
      shape: 'ellipse',
      color: {
        background: status === 'UP' ? '#dcfce7' : '#fee2e2',
        border: status === 'UP' ? '#10b981' : '#ef4444',
      },
      level: 1,
      font: { size: 12, multi: true },
    }
    allNodes.push(ifaceNode)

    // Create edge
    allEdges.push({
      id: `edge-${device.hostid}-${iface.if_index}`,
      from: device.hostid,
      to: `${device.hostid}-iface-${iface.if_index}`,
      arrows: '',
      color: { color: '#94a3b8' },
    })
  })
})

// Continue with existing node/edge enhancement logic...
```

---

### ⏳ PENDING (Infrastructure)

#### Celery Beat Queue Fix Deployment

**Why Needed:**
VictoriaMetrics is currently empty because the interface metrics collection task (`collect_all_interface_metrics`) is not running. The task is being sent to the wrong queue.

**File Already Prepared:** `celery_app.py`

**Fix Applied (Not Yet Deployed):**
```python
'collect-interface-metrics': {
    'task': 'monitoring.tasks.collect_all_interface_metrics',
    'schedule': 60.0,
    'options': {'queue': 'snmp', 'routing_key': 'snmp', 'priority': 3}  # FIXED
},
```

**Deployment Script Needed:**
`deploy-celery-beat-queue-fix.sh` for production server 10.30.25.46

**Commands:**
```bash
cd /home/wardops/ward-flux-credobank
git pull origin main
docker-compose -f docker-compose.production-priority-queues.yml stop celery-beat celery-worker-snmp
docker-compose -f docker-compose.production-priority-queues.yml rm -f celery-beat celery-worker-snmp
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache celery-beat
docker-compose -f docker-compose.production-priority-queues.yml up -d celery-beat celery-worker-snmp

# Wait 2-3 minutes for metrics to start collecting
sleep 180

# Verify VictoriaMetrics has data
curl -s 'http://localhost:8428/api/v1/query?query=count(interface_if_hc_in_octets)' | jq .
```

---

## Deployment Plan

### Phase 1: Deploy Celery Beat Fix (FIRST!)

**Why First:** VictoriaMetrics needs data before bandwidth display works

**Server:** ssh wardops@10.30.25.46

**Steps:**
1. Push code to GitHub
2. SSH to production server
3. Pull latest code
4. Deploy Celery Beat fix
5. Wait 2-3 minutes
6. Verify metrics collecting

**Verification:**
```bash
# Check VictoriaMetrics has metrics
curl -s 'http://localhost:8428/api/v1/query?query=count(interface_if_hc_in_octets)'

# Should return non-zero count
```

### Phase 2: Complete Topology Implementation (AFTER Celery Fix)

**Steps:**
1. Finish `loadTopologyData()` implementation
2. Test locally if possible
3. Commit and push
4. Deploy to production

**Deployment Command:**
```bash
cd /home/wardops/ward-flux-credobank
git pull origin main
docker-compose -f docker-compose.production-priority-queues.yml stop api
docker-compose -f docker-compose.production-priority-queues.yml rm -f api
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache api
docker-compose -f docker-compose.production-priority-queues.yml up -d api
```

**Testing:**
1. Open http://10.30.25.46:5001/topology
2. Verify ONLY .5 routers shown
3. Verify each router has interface children
4. Verify bandwidth shows on interfaces
5. Check browser console for errors

---

## Testing Checklist

### After Phase 1 (Celery Beat Fix):
- [ ] VictoriaMetrics has `interface_if_hc_in_octets` metrics
- [ ] VictoriaMetrics has `interface_if_hc_out_octets` metrics
- [ ] Metrics exist for at least one .5 router (10.195.57.5)
- [ ] Celery worker logs show "Collecting interface metrics" every 60s

### After Phase 2 (Full Deployment):
- [ ] Topology page loads without errors
- [ ] ONLY .5 routers are displayed (~93 devices)
- [ ] Each router shows ALL interfaces as children
- [ ] Interface status (UP/DOWN) is correct
- [ ] ISP interfaces show "ISP: MAGTI" or "ISP: SILKNET"
- [ ] Bandwidth displays "↓ X Mbps" and "↑ Y Mbps"
- [ ] Bandwidth updates every 10 seconds
- [ ] Interface nodes color-coded (green=UP, red=DOWN)
- [ ] No console errors in browser

---

## Files Modified

### Backend:
- ✅ `routers/interfaces.py` - Added 2 new endpoints + helper function

### Frontend:
- ✅ `frontend/src/services/api.ts` - Added 2 API client methods
- 🔄 `frontend/src/pages/Topology.tsx` - Added queries, need to finish visualization

### Configuration:
- ✅ `celery_app.py` - Fixed task routing (not yet deployed)

### Documentation:
- ✅ `TOPOLOGY-ALL-INTERFACES-DESIGN.md` - Complete design
- ✅ `TOPOLOGY-IMPLEMENTATION-STATUS.md` - This file

---

## Next Steps

### Immediate (Complete Implementation):

1. **Finish Topology Visualization** (30 minutes):
   - Modify `loadTopologyData()` function
   - Build nodes from `networkDevices` + `interfacesData` + `bandwidthData`
   - Test interface node creation
   - Test bandwidth label display

2. **Create Deployment Scripts** (10 minutes):
   - `deploy-celery-beat-queue-fix.sh`
   - `deploy-topology-complete.sh`

3. **Commit and Push** (5 minutes):
   - Commit topology visualization changes
   - Push all changes to GitHub

### Deployment (On Production Server):

1. **Deploy Celery Beat Fix**:
   ```bash
   ssh wardops@10.30.25.46
   cd /home/wardops/ward-flux-credobank
   bash deploy-celery-beat-queue-fix.sh
   ```

2. **Wait for Metrics** (2-3 minutes):
   - Verify VictoriaMetrics has data

3. **Deploy Complete Topology**:
   ```bash
   bash deploy-topology-complete.sh
   ```

4. **Test and Verify**:
   - Open http://10.30.25.46:5001/topology
   - Verify all requirements met

---

## Known Limitations

1. **VictoriaMetrics Must Have Data**:
   - Bandwidth display requires Celery Beat fix first
   - Shows "↓ --" and "↑ --" if no data (graceful degradation)

2. **Only .5 Routers**:
   - Topology shows ONLY ISP routers with .5 IPs
   - This is intentional per user requirement

3. **Performance**:
   - ~93 routers × ~10 interfaces each = ~930 interface nodes
   - vis.js can handle this, but may be slow on weak devices
   - Consider pagination if needed

4. **Refresh Rates**:
   - Interface list: 30 seconds
   - Bandwidth: 10 seconds
   - Balance between real-time and API load

---

## Support Information

**Production Server:**
- Host: 10.30.25.46 (Flux)
- User: wardops
- Project: /home/wardops/ward-flux-credobank
- Docker Compose: docker-compose.production-priority-queues.yml

**Container Names:**
- wardops-api-prod (API + Frontend)
- wardops-beat-prod (Celery Beat)
- wardops-worker-snmp-prod (SNMP worker)
- wardops-postgres-prod (PostgreSQL)
- wardops-victoriametrics-prod (VictoriaMetrics)

**Useful Commands:**
```bash
# Check API logs
docker logs -f wardops-api-prod

# Check Celery Beat logs
docker logs -f wardops-beat-prod

# Check SNMP worker logs
docker logs -f wardops-worker-snmp-prod

# Query VictoriaMetrics
curl -s 'http://localhost:8428/api/v1/query?query=interface_if_hc_in_octets{device_ip="10.195.57.5"}' | jq .
```

---

**Status:** 70% Complete - Backend + Data Queries Done
**Remaining:** Topology Visualization + Deployment
**Estimated Time:** 1 hour total (45 min implementation + 15 min deployment/testing)

**Last Updated:** 2025-10-27
**Git Commit:** fb54df0 - "WIP: Topology with ALL interfaces and bandwidth - Backend + Data Queries"
