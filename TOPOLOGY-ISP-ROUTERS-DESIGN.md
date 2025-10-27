# Topology Page Enhancement - ISP Router Focus
**Date:** 2025-10-27
**Status:** DESIGN - Ready for implementation
**Context Available:** 109k tokens remaining

---

## 📋 REQUIREMENTS

### 1. Filter to .5 Routers Only
- Topology page should ONLY display devices with IPs ending in `.5` (ISP routers)
- Hide all other devices (switches, payboxes, APs, etc.)
- Show ~93 ISP routers across Georgia

### 2. Navigation from Monitor Page
- Only .5 devices in Monitor page should have topology navigation
- Add topology link/button on ISP router cards
- Direct link to specific router in topology view

### 3. Live Interface Bandwidth Display
- Show ISP interfaces (Magti Fa3, Silknet Fa4) for each router
- Display real-time bandwidth from VictoriaMetrics
- Use SNMP interface metrics (ifInOctets, ifOutOctets)
- Update every 30 seconds
- Show IN/OUT traffic with visual indicators

---

## 🏗️ ARCHITECTURE

### Data Flow
```
PostgreSQL (device_interfaces)
    ↓ (interface metadata: if_index, if_name, isp_provider)
    ↓
VictoriaMetrics SNMP metrics
    ↓ (interface_traffic_in, interface_traffic_out)
    ↓
Backend API (/api/v1/interfaces/isp-bandwidth/realtime)
    ↓ (aggregated data: device + interfaces + bandwidth)
    ↓
Frontend (Topology.tsx)
    ↓ (vis.js network graph with live bandwidth labels)
```

### Backend Components

#### 1. New API Endpoint
**File:** `routers/interfaces.py`
**Endpoint:** `GET /api/v1/interfaces/isp-bandwidth/realtime`

**Query Parameters:**
- `device_ips`: Comma-separated list of .5 router IPs

**Response Format:**
```json
{
  "10.195.57.5": {
    "device_id": "61bfeaa1-1434-4b57-aa59-419f33ed232a",
    "device_name": "Batumi3-881",
    "interfaces": [
      {
        "if_name": "Fa3",
        "isp_provider": "magti",
        "if_index": 4,
        "bandwidth_in_mbps": 12.5,
        "bandwidth_out_mbps": 3.2,
        "oper_status": 1,
        "last_updated": "2025-10-27T19:30:00Z"
      },
      {
        "if_name": "Fa4",
        "isp_provider": "silknet",
        "if_index": 5,
        "bandwidth_in_mbps": 8.7,
        "bandwidth_out_mbps": 2.1,
        "oper_status": 1,
        "last_updated": "2025-10-27T19:30:00Z"
      }
    ]
  }
}
```

**Implementation:**
1. Query PostgreSQL `device_interfaces` for ISP interfaces (isp_provider IN ['magti', 'silknet'])
2. Query VictoriaMetrics for latest bandwidth metrics (last 1 minute average)
3. Convert bytes/sec to Mbps
4. Return aggregated data

#### 2. VictoriaMetrics Queries
**Metrics to query:**
- `interface_traffic_in_bytes` - ifInOctets counter
- `interface_traffic_out_bytes` - ifOutOctets counter

**PromQL Query (rate calculation):**
```promql
rate(interface_traffic_in_bytes{device_ip="10.195.57.5",if_index="4"}[1m]) * 8 / 1000000
```
This calculates Mbps from bytes/sec over last 1 minute.

**Labels needed:**
- `device_ip`: Router IP
- `device_name`: Router hostname
- `if_index`: Interface index (4 for Magti, 5 for Silknet)
- `if_name`: Interface name (Fa3, Fa4)
- `isp_provider`: 'magti' or 'silknet'

### Frontend Components

#### 1. Topology Page Modifications
**File:** `frontend/src/pages/Topology.tsx`

**Changes:**

**A. Filter devices to .5 routers only:**
```typescript
// Line ~145 - Add ISP router filter
const ispRouters = useMemo(() => {
  if (!allDevices?.data) return []
  return allDevices.data.filter((d: Device) => d.ip && d.ip.endsWith('.5'))
}, [allDevices])
```

**B. Fetch ISP interface bandwidth:**
```typescript
// New query for real-time bandwidth
const { data: bandwidthData } = useQuery({
  queryKey: ['isp-bandwidth', ispRouterIPs],
  queryFn: async () => {
    if (ispRouterIPs.length === 0) return {}
    const response = await interfacesAPI.getISPBandwidthRealtime(ispRouterIPs)
    return response.data
  },
  enabled: ispRouterIPs.length > 0,
  refetchInterval: 30000, // Refresh every 30 seconds
})
```

**C. Enhanced node tooltips with bandwidth:**
```typescript
// Add bandwidth info to node titles
const getBandwidthLabel = (deviceIp: string) => {
  const bw = bandwidthData?.[deviceIp]
  if (!bw?.interfaces) return ''

  return bw.interfaces.map(iface => {
    const status = iface.oper_status === 1 ? '🟢' : '🔴'
    const provider = iface.isp_provider === 'magti' ? '📶 Magti' : '🌐 Silknet'
    return `${status} ${provider}: ↓${iface.bandwidth_in_mbps.toFixed(1)} Mbps ↑${iface.bandwidth_out_mbps.toFixed(1)} Mbps`
  }).join('\n')
}
```

**D. Update node rendering:**
```typescript
const enhancedNodes = filteredNodes.map((node: DeviceNode) => {
  const device = deviceMap[node.id]
  const bandwidthLabel = getBandwidthLabel(device.ip)

  return {
    ...node,
    title: `${node.title}\n\n${bandwidthLabel}`,
    label: `${node.label}\n${getBandwidthSummary(device.ip)}`,
  }
})
```

#### 2. Monitor Page Navigation
**File:** `frontend/src/pages/Monitor.tsx`

**Changes:**

**A. Add topology button for .5 routers:**
```typescript
// Inside renderDeviceCard - add topology button for ISP routers
{isISPRouter(device.ip) && (
  <Button
    variant="ghost"
    size="sm"
    onClick={() => navigate(`/topology?device=${device.ip}`)}
    title="View network topology"
  >
    <Network className="w-4 h-4" />
  </Button>
)}
```

#### 3. API Client
**File:** `frontend/src/services/api.ts`

**New method:**
```typescript
export const interfacesAPI = {
  // ... existing methods ...

  getISPBandwidthRealtime: (deviceIps: string[]) =>
    api.get<Record<string, {
      device_id: string;
      device_name: string;
      interfaces: Array<{
        if_name: string;
        isp_provider: string;
        if_index: number;
        bandwidth_in_mbps: number;
        bandwidth_out_mbps: number;
        oper_status: number;
        last_updated: string;
      }>;
    }>>(`/interfaces/isp-bandwidth/realtime?device_ips=${deviceIps.join(',')}`),
}
```

---

## 🔍 IMPLEMENTATION CHECKLIST

### Phase 1: Backend (Priority 1)
- [ ] Create `/api/v1/interfaces/isp-bandwidth/realtime` endpoint
- [ ] Implement VictoriaMetrics bandwidth query logic
- [ ] Test with device 10.195.57.5 (known working SNMP)
- [ ] Add error handling for missing metrics
- [ ] Document endpoint in API docs

### Phase 2: Frontend - Topology Filtering (Priority 2)
- [ ] Add ISP router filter to Topology page
- [ ] Hide non-.5 devices from graph
- [ ] Update stats to show only ISP routers
- [ ] Test with 93 .5 routers
- [ ] Ensure graph layout works with filtered data

### Phase 3: Frontend - Bandwidth Display (Priority 3)
- [ ] Add bandwidth data fetching (30s interval)
- [ ] Update node tooltips with bandwidth info
- [ ] Add visual bandwidth indicators
- [ ] Format bandwidth numbers (Mbps with 1 decimal)
- [ ] Add loading states for bandwidth data

### Phase 4: Frontend - Navigation (Priority 4)
- [ ] Add topology button to ISP router cards in Monitor page
- [ ] Implement deep linking (topology?device=10.195.57.5)
- [ ] Focus on specific device when navigated from Monitor
- [ ] Add back navigation breadcrumb

### Phase 5: Testing & Polish (Priority 5)
- [ ] Test with all 93 ISP routers
- [ ] Verify bandwidth updates every 30 seconds
- [ ] Check performance with large dataset
- [ ] Add fallback for devices without SNMP
- [ ] Add "No data available" state for missing metrics

---

## 🎯 ACCEPTANCE CRITERIA

### Must Have
1. ✅ Topology page shows ONLY .5 routers (no switches, APs, etc.)
2. ✅ Each router node displays real-time bandwidth for Magti and Silknet links
3. ✅ Bandwidth updates automatically every 30 seconds
4. ✅ Monitor page has topology navigation button on .5 router cards
5. ✅ Clicking topology button opens topology page focused on that router

### Nice to Have
1. Color-coded bandwidth (green <10Mbps, yellow 10-50Mbps, red >50Mbps)
2. Historical bandwidth graph on hover
3. Alert indicators for high bandwidth usage
4. Export topology to PNG/SVG

---

## 🚨 RISKS & MITIGATION

### Risk 1: VictoriaMetrics has no bandwidth data
**Mitigation:**
- Check if SNMP polling collects interface traffic metrics
- If not, add `ifInOctets` and `ifOutOctets` to SNMP polling
- Show "No data" message for devices without metrics

### Risk 2: Performance with 93 routers
**Mitigation:**
- Use pagination or virtual scrolling
- Limit bandwidth queries to visible/focused devices
- Cache bandwidth data for 30 seconds

### Risk 3: SNMP not accessible on all .5 routers
**Current state:** Only 10.195.57.5 has SNMP open
**Mitigation:**
- Show "SNMP not configured" badge
- Display last known bandwidth (if any)
- Gracefully handle missing data

---

## 📊 EXISTING DATA STATUS

### Device Interfaces (PostgreSQL)
✅ **EXISTS** - Device 10.195.57.5 has 20 interfaces including:
- Fa3 (Magti_Internet): `isp_provider='magti'`, `oper_status=1`
- Fa4 (Silknet_Internet): `isp_provider='silknet'`, `oper_status=1`

### VictoriaMetrics Metrics
❓ **UNKNOWN** - Need to check if bandwidth metrics exist:
```bash
curl -s "http://localhost:8428/api/v1/query?query=interface_traffic_in_bytes{device_ip=\"10.195.57.5\"}"
```

If metrics don't exist, SNMP polling needs to collect them.

---

## 🔧 TECHNICAL NOTES

### SNMP OIDs for Bandwidth
- **ifInOctets:** `1.3.6.1.2.1.2.2.1.10.{if_index}` - Incoming bytes counter
- **ifOutOctets:** `1.3.6.1.2.1.2.2.1.16.{if_index}` - Outgoing bytes counter

### Rate Calculation
```
Mbps = (current_octets - previous_octets) / time_diff * 8 / 1_000_000
```

VictoriaMetrics `rate()` function handles this automatically.

### Color Coding
- **Green:** 0-10 Mbps (normal)
- **Yellow:** 10-50 Mbps (moderate)
- **Orange:** 50-80 Mbps (high)
- **Red:** >80 Mbps (critical)

---

## 🚀 DEPLOYMENT PLAN

### Step 1: Verify VictoriaMetrics has data
```bash
# Check if bandwidth metrics exist
docker exec wardops-api-prod curl -s "http://localhost:8428/api/v1/query?query=interface_traffic_in_bytes{device_ip=~\".*\\.5\"}" | jq .
```

### Step 2: Deploy backend changes
```bash
git pull origin main
docker-compose -f docker-compose.production-priority-queues.yml stop api
docker-compose -f docker-compose.production-priority-queues.yml rm -f api
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache api
docker-compose -f docker-compose.production-priority-queues.yml up -d api
```

### Step 3: Test endpoint
```bash
curl "http://localhost:5001/api/v1/interfaces/isp-bandwidth/realtime?device_ips=10.195.57.5" | jq .
```

### Step 4: Deploy frontend
Frontend is bundled in API container, so rebuilding API deploys both.

### Step 5: Verify in UI
1. Open Monitor page
2. Search for ".5"
3. Click topology button on Batumi3-881
4. Verify topology shows only ISP routers
5. Check bandwidth labels update every 30 seconds

---

## 📚 RELATED FILES

### Backend
- `routers/interfaces.py` - ISP bandwidth API endpoint
- `monitoring/interface_metrics.py` - VictoriaMetrics client
- `monitoring/victoria/client.py` - VM query functions

### Frontend
- `frontend/src/pages/Topology.tsx` - Main topology visualization
- `frontend/src/pages/Monitor.tsx` - Add topology navigation
- `frontend/src/services/api.ts` - API client methods

### Documentation
- `ISP-MONITORING-ARCHITECTURE-FIX.md` - Architecture overview
- `PROJECT_KNOWLEDGE_BASE.md` - System documentation

---

**Status:** READY TO IMPLEMENT
**Estimated Implementation Time:** 3-4 hours
**Risk Level:** LOW (non-breaking changes, additive features)
**Context Remaining:** 109k tokens (sufficient for full implementation)
