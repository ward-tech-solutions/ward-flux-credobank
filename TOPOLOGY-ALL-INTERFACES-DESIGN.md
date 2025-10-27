# TOPOLOGY - ALL INTERFACES WITH BANDWIDTH VISUALIZATION

## Requirements

**User Request:**
> "I do not need to draw only ISP interfaces I want all interfaces to draw there - and we need to fix topology to use bandwidths of that interfaces from victoria metrics"

## Design Overview

### What Will Be Displayed

For each **. 5 router** on the topology page, we will show:

1. **Router Node** - The .5 device itself
2. **All Interfaces** - Every interface from `device_interfaces` table
3. **Interface Status** - Operational status (UP/DOWN) from PostgreSQL
4. **Bandwidth Metrics** - Real-time bandwidth from VictoriaMetrics

### Visual Layout

```
        [Router: 10.195.57.5]
               |
    +----------+----------+----------+
    |          |          |          |
  [Fa0/0]   [Fa0/1]   [Fa3]      [Fa4]
   UP         DOWN      UP         UP
  ↓2.1M      ↓0        ↓15M       ↓12M
  ↑0.5M      ↑0        ↑8M        ↑5M
   LAN        LAN      Magti     Silknet
```

## Data Architecture

### Data Sources

1. **PostgreSQL `device_interfaces` table**:
   - Interface names (if_name, if_descr)
   - Operational status (oper_status: 1=UP, 2=DOWN)
   - ISP provider (isp_provider: magti, silknet, null)
   - Interface type (interface_type: isp, trunk, access, etc.)
   - Speed capacity (speed: bits/second)

2. **VictoriaMetrics Time-Series Database**:
   - Bandwidth In: `interface_if_hc_in_octets{device_ip="X", if_name="Y"}`
   - Bandwidth Out: `interface_if_hc_out_octets{device_ip="X", if_name="Y"}`
   - Metrics collected every 60 seconds by Celery worker

### API Endpoints Needed

#### 1. Get All Interfaces for .5 Routers
**Endpoint:** `GET /api/v1/interfaces/by-devices`

**Query Params:** `?device_ips=10.195.57.5,10.195.110.62,...`

**Response:**
```json
{
  "10.195.57.5": [
    {
      "id": "uuid",
      "if_name": "FastEthernet3",
      "if_descr": "FastEthernet3",
      "if_alias": "ISP Magti Primary",
      "interface_type": "isp",
      "isp_provider": "magti",
      "oper_status": 1,
      "admin_status": 1,
      "speed": 100000000,
      "if_index": 3
    },
    {
      "if_name": "FastEthernet4",
      "interface_type": "isp",
      "isp_provider": "silknet",
      "oper_status": 1,
      "speed": 100000000,
      "if_index": 4
    },
    {
      "if_name": "FastEthernet0/0",
      "interface_type": "trunk",
      "isp_provider": null,
      "oper_status": 1,
      "speed": 1000000000,
      "if_index": 1
    }
  ]
}
```

#### 2. Get Real-Time Bandwidth for Interfaces
**Endpoint:** `GET /api/v1/interfaces/bandwidth/realtime`

**Query Params:** `?device_ips=10.195.57.5,10.195.110.62,...`

**Backend Logic:**
```python
# For each device IP and interface:
# Query VictoriaMetrics:
query_in = f'rate(interface_if_hc_in_octets{{device_ip="{ip}",if_name="{if_name}"}}[1m])'
query_out = f'rate(interface_if_hc_out_octets{{device_ip="{ip}",if_name="{if_name}"}}[1m])'

# rate() gives bytes/second change rate
# Multiply by 8 to get bits/second
```

**Response:**
```json
{
  "10.195.57.5": {
    "FastEthernet3": {
      "bandwidth_in_bps": 15234567,
      "bandwidth_out_bps": 8123456,
      "bandwidth_in_formatted": "15.2 Mbps",
      "bandwidth_out_formatted": "8.1 Mbps",
      "utilization_in_percent": 15.2,
      "utilization_out_percent": 8.1,
      "interface_speed_bps": 100000000,
      "last_updated": "2025-10-27T10:30:00Z"
    },
    "FastEthernet4": {
      "bandwidth_in_bps": 12000000,
      "bandwidth_out_bps": 5000000,
      "bandwidth_in_formatted": "12.0 Mbps",
      "bandwidth_out_formatted": "5.0 Mbps",
      "utilization_in_percent": 12.0,
      "utilization_out_percent": 5.0,
      "interface_speed_bps": 100000000,
      "last_updated": "2025-10-27T10:30:00Z"
    }
  }
}
```

## Frontend Implementation

### Topology Page Changes

**File:** `frontend/src/pages/Topology.tsx`

#### 1. Fetch All Interfaces
```typescript
// Query all interfaces for .5 routers
const { data: interfacesData } = useQuery({
  queryKey: ['device-interfaces', ispRouterIPs],
  queryFn: async () => {
    if (ispRouterIPs.length === 0) return {}
    const response = await interfacesAPI.getByDevices(ispRouterIPs)
    return response.data
  },
  enabled: ispRouterIPs.length > 0,
  refetchInterval: 30000, // Refresh every 30 seconds
})
```

#### 2. Fetch Bandwidth Metrics
```typescript
// Query bandwidth from VictoriaMetrics
const { data: bandwidthData } = useQuery({
  queryKey: ['interface-bandwidth', ispRouterIPs],
  queryFn: async () => {
    if (ispRouterIPs.length === 0) return {}
    const response = await interfacesAPI.getBandwidthRealtime(ispRouterIPs)
    return response.data
  },
  enabled: ispRouterIPs.length > 0,
  refetchInterval: 10000, // Refresh every 10 seconds for real-time
  staleTime: 5000,
})
```

#### 3. Create Interface Nodes

For each router, create child nodes for each interface:

```typescript
// For each .5 router device
const routerNode = {
  id: device.id,
  label: device.display_name,
  shape: 'box',
  color: { background: '#10b981' },
  level: 0,
}

// Create interface nodes
const interfaceNodes = interfacesData[device.ip]?.map((iface, idx) => {
  const bandwidth = bandwidthData?.[device.ip]?.[iface.if_name]
  const status = iface.oper_status === 1 ? 'UP' : 'DOWN'
  const statusIcon = status === 'UP' ? '🟢' : '🔴'

  const label = [
    `${statusIcon} ${iface.if_name}`,
    iface.isp_provider ? `ISP: ${iface.isp_provider.toUpperCase()}` : iface.interface_type || 'LAN',
    bandwidth ? `↓ ${bandwidth.bandwidth_in_formatted}` : '↓ --',
    bandwidth ? `↑ ${bandwidth.bandwidth_out_formatted}` : '↑ --',
  ].join('\n')

  return {
    id: `${device.id}-iface-${iface.if_index}`,
    label: label,
    shape: 'ellipse',
    color: {
      background: status === 'UP' ? '#dcfce7' : '#fee2e2',
      border: status === 'UP' ? '#10b981' : '#ef4444',
    },
    level: 1,
    font: { size: 12, multi: true },
  }
})

// Create edges from router to interfaces
const interfaceEdges = interfacesData[device.ip]?.map((iface, idx) => ({
  from: device.id,
  to: `${device.id}-iface-${iface.if_index}`,
  arrows: '',
  color: { color: '#94a3b8' },
}))
```

### Visual Design

**Node Colors:**
- Router Node: Green box (#10b981)
- Interface UP: Light green ellipse (#dcfce7)
- Interface DOWN: Light red ellipse (#fee2e2)

**Node Layout:**
- Routers: Level 0 (hierarchical layout)
- Interfaces: Level 1 (children of router)

**Label Format:**
```
🟢 FastEthernet3
ISP: MAGTI
↓ 15.2 Mbps
↑ 8.1 Mbps
```

**Refresh Rates:**
- Interface list: Every 30 seconds (slow change)
- Bandwidth metrics: Every 10 seconds (real-time)

## Backend Implementation

### File: `routers/interfaces.py`

#### 1. Get All Interfaces by Devices

```python
@router.get("/by-devices")
async def get_interfaces_by_devices(
    device_ips: str,  # Comma-separated IPs
    db: Session = Depends(get_db)
):
    """
    Get all interfaces for specified device IPs
    Returns interface details from PostgreSQL
    """
    ip_list = [ip.strip() for ip in device_ips.split(',') if ip.strip()]

    # Query devices
    devices = db.query(StandaloneDevice).filter(
        StandaloneDevice.ip.in_(ip_list)
    ).all()

    result = {}
    for device in devices:
        # Query all interfaces for this device
        interfaces = db.query(DeviceInterface).filter(
            DeviceInterface.device_id == device.id,
            DeviceInterface.enabled == True
        ).order_by(DeviceInterface.if_index).all()

        result[device.ip] = [
            {
                "id": str(iface.id),
                "if_index": iface.if_index,
                "if_name": iface.if_name,
                "if_descr": iface.if_descr,
                "if_alias": iface.if_alias,
                "interface_type": iface.interface_type,
                "isp_provider": iface.isp_provider,
                "oper_status": iface.oper_status,
                "admin_status": iface.admin_status,
                "speed": iface.speed,
                "is_critical": iface.is_critical,
            }
            for iface in interfaces
        ]

    return result
```

#### 2. Get Real-Time Bandwidth

```python
@router.get("/bandwidth/realtime")
async def get_interface_bandwidth_realtime(
    device_ips: str,  # Comma-separated IPs
    db: Session = Depends(get_db)
):
    """
    Get real-time bandwidth for all interfaces from VictoriaMetrics
    Uses rate() function to calculate bytes/sec
    """
    from utils.victoriametrics_client import vm_client

    ip_list = [ip.strip() for ip in device_ips.split(',') if ip.strip()]

    # Get devices and their interfaces
    devices = db.query(StandaloneDevice).filter(
        StandaloneDevice.ip.in_(ip_list)
    ).all()

    result = {}
    for device in devices:
        interfaces = db.query(DeviceInterface).filter(
            DeviceInterface.device_id == device.id,
            DeviceInterface.enabled == True
        ).all()

        device_bandwidth = {}
        for iface in interfaces:
            # Query VictoriaMetrics for bandwidth
            # rate() calculates per-second change over 1 minute window
            query_in = f'rate(interface_if_hc_in_octets{{device_ip="{device.ip}",if_name="{iface.if_name}"}}[1m]) * 8'
            query_out = f'rate(interface_if_hc_out_octets{{device_ip="{device.ip}",if_name="{iface.if_name}"}}[1m]) * 8'

            try:
                result_in = vm_client.query(query_in)
                result_out = vm_client.query(query_out)

                bw_in_bps = 0
                bw_out_bps = 0

                if result_in and len(result_in) > 0:
                    bw_in_bps = float(result_in[0]['value'][1])

                if result_out and len(result_out) > 0:
                    bw_out_bps = float(result_out[0]['value'][1])

                # Calculate utilization
                util_in = (bw_in_bps / iface.speed * 100) if iface.speed else 0
                util_out = (bw_out_bps / iface.speed * 100) if iface.speed else 0

                device_bandwidth[iface.if_name] = {
                    "bandwidth_in_bps": bw_in_bps,
                    "bandwidth_out_bps": bw_out_bps,
                    "bandwidth_in_formatted": format_bandwidth(bw_in_bps),
                    "bandwidth_out_formatted": format_bandwidth(bw_out_bps),
                    "utilization_in_percent": round(util_in, 1),
                    "utilization_out_percent": round(util_out, 1),
                    "interface_speed_bps": iface.speed,
                    "last_updated": datetime.utcnow().isoformat()
                }
            except Exception as e:
                logger.error(f"Failed to get bandwidth for {device.ip} {iface.if_name}: {e}")
                device_bandwidth[iface.if_name] = {
                    "bandwidth_in_bps": 0,
                    "bandwidth_out_bps": 0,
                    "bandwidth_in_formatted": "0 bps",
                    "bandwidth_out_formatted": "0 bps",
                    "utilization_in_percent": 0,
                    "utilization_out_percent": 0,
                    "interface_speed_bps": iface.speed,
                    "last_updated": datetime.utcnow().isoformat()
                }

        result[device.ip] = device_bandwidth

    return result


def format_bandwidth(bps: float) -> str:
    """Format bandwidth in human-readable form"""
    if bps >= 1_000_000_000:  # Gbps
        return f"{bps / 1_000_000_000:.1f} Gbps"
    elif bps >= 1_000_000:  # Mbps
        return f"{bps / 1_000_000:.1f} Mbps"
    elif bps >= 1_000:  # Kbps
        return f"{bps / 1_000:.1f} Kbps"
    else:  # bps
        return f"{bps:.0f} bps"
```

## Deployment Strategy

### Prerequisites

1. **Celery Beat Must Be Fixed** - Interface metrics collection task needs to run
2. **VictoriaMetrics Must Have Data** - Wait 2-3 minutes after Celery fix
3. **PostgreSQL Must Have Interfaces** - Already populated

### Deployment Steps

**On production server (10.30.25.46):**

```bash
# Step 1: Deploy Celery Beat fix first (to start collecting metrics)
cd /home/wardops/ward-flux-credobank
git pull origin main
bash deploy-celery-beat-queue-fix.sh

# Wait 2-3 minutes for metrics to collect
sleep 180

# Step 2: Verify VictoriaMetrics has data
curl -s 'http://localhost:8428/api/v1/query?query=count(interface_if_hc_in_octets)' | jq .

# Step 3: Deploy full topology implementation
bash deploy-topology-all-interfaces.sh
```

### Testing Checklist

After deployment:

1. [ ] Open http://10.30.25.46:5001/topology
2. [ ] Verify ONLY .5 routers are displayed
3. [ ] For each router, verify ALL interfaces are shown as child nodes
4. [ ] Verify interface status (UP/DOWN) is correct
5. [ ] Verify ISP interfaces show "ISP: MAGTI" or "ISP: SILKNET"
6. [ ] Verify bandwidth shows "↓ X Mbps" and "↑ Y Mbps"
7. [ ] Wait 10 seconds, verify bandwidth updates
8. [ ] Check browser console for errors
9. [ ] Verify VictoriaMetrics queries are fast (<200ms)

## Risk Mitigation

### What If VictoriaMetrics Is Empty?

**Fallback Display:**
```
🟢 FastEthernet3
ISP: MAGTI
↓ -- (no data)
↑ -- (no data)
```

Interface will still show with status from PostgreSQL, just no bandwidth metrics.

### What If Too Many Interfaces?

For routers with 20+ interfaces:
- Use pagination or collapsible groups
- Show only critical interfaces by default
- Add "Show All" toggle

### Performance Considerations

- **VictoriaMetrics Queries**: Batch queries per device (not per interface)
- **React Query Caching**: 10-second stale time for bandwidth
- **Network Graph**: vis.js handles 1000+ nodes efficiently

## Implementation Checklist

- [ ] Update `routers/interfaces.py` with new endpoints
- [ ] Add VictoriaMetrics client queries
- [ ] Update `frontend/src/services/api.ts` with new API calls
- [ ] Update `frontend/src/pages/Topology.tsx` to create interface nodes
- [ ] Test locally with sample data
- [ ] Deploy Celery Beat fix first
- [ ] Wait for VictoriaMetrics data collection
- [ ] Deploy full topology implementation
- [ ] Test on production

## Files to Modify

1. **Backend:**
   - `routers/interfaces.py` - Add `/by-devices` and `/bandwidth/realtime` endpoints
   - `utils/victoriametrics_client.py` - Ensure query() method works

2. **Frontend:**
   - `frontend/src/services/api.ts` - Add API methods
   - `frontend/src/pages/Topology.tsx` - Create interface nodes

3. **Deployment:**
   - Create `deploy-celery-beat-queue-fix.sh` (for Celery)
   - Create `deploy-topology-all-interfaces.sh` (for full deployment)

---

**Status:** Design Complete - Ready for Implementation
**Next Step:** Implement backend API endpoints
