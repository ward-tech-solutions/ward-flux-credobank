# Zabbix Integration Fix - Using Old Proven Logic in New UI

## Critical Issues Found

1. **Wrong API Endpoint**: New UI calling `/devices/standalone/list` instead of `/devices` (Zabbix API)
2. **Wrong Status Field**: Looking for `status: 'online'/'offline'` but Zabbix returns `ping_status: 'Up'/'Down'`
3. **Wrong Field Names**: Using `name`/`host` but Zabbix returns `display_name`/`ip`/`branch`/`region`
4. **Data Normalization Breaking Things**: Trying to normalize data instead of using it as-is
5. **Missing Region/Branch Data**: Not using the pre-parsed `branch` (city) and `region` fields from backend

## Zabbix Backend Data Format (PROVEN WORKING)

```javascript
{
  "hostid": "11940",
  "hostname": "device_hostname",
  "display_name": "Khulo-PayBox - 10.159.53.10",  // Clean display name
  "branch": "Khulo",                              // ✅ City name (pre-parsed)
  "region": "Adjara",                             // ✅ Region name (pre-parsed)
  "ip": "10.159.53.10",
  "device_type": "Paybox",                        // ATM, PayBox, NVR, etc.
  "status": "Enabled",                            // Device enabled/disabled
  "available": "Unavailable",                     // ✅ Actual availability status
  "ping_status": "Down",                          // ✅ Ping reachability
  "ping_response_time": null,
  "last_check": 1728194671,                       // Unix timestamp
  "groups": ["Branches", "PayBox ICMP"],
  "problems": 2,                                  // Number of active triggers
  "triggers": [...],                              // Active problem triggers
  "latitude": 41.6428,
  "longitude": 42.3168
}
```

## Status Logic (Old Working Logic)

```javascript
// OLD UI (devices.js line 84-85):
const status = device.ping_status || device.available || 'Unknown';
const statusClass = status === 'Up' ? 'online' : status === 'Down' ? 'offline' : 'unknown';

// CORRECT LOGIC:
- ping_status === 'Up' OR available === 'Available' → Device is ONLINE
- ping_status === 'Down' OR available === 'Unavailable' → Device is OFFLINE
```

## Fix Plan

### 1. Update frontend/src/services/api.ts

**REMOVE ALL NORMALIZATION FUNCTIONS**

```typescript
// ❌ REMOVE normalizeZabbixDevice()
// ❌ REMOVE normalizeStandaloneDevice()
// ❌ REMOVE getAll() Promise.all merging

// ✅ USE THIS INSTEAD:
export const devicesAPI = {
  getAll: () => api.get<Device[]>('/devices'),  // Returns Zabbix devices
  getById: (hostid: string) => api.get<Device>(`/devices/${hostid}`),
  standalone: {
    list: () => api.get('/devices/standalone/list'),
    // ... keep standalone CRUD separate
  }
}
```

### 2. Update Device Interface

```typescript
export interface Device {
  hostid: string                    // ✅ Use hostid (not id)
  hostname: string
  display_name: string              // ✅ Use display_name (not name)
  branch: string                    // ✅ City from backend
  region: string                    // ✅ Region from backend
  ip: string                        // ✅ Use ip (not host)
  device_type: string
  status: string                    // "Enabled" or "Disabled"
  available: string                 // ✅ "Available" or "Unavailable"
  ping_status: string               // ✅ "Up" or "Down"
  ping_response_time: number | null
  last_check: number                // Unix timestamp
  groups: string[]
  problems: number
  triggers: any[]
  latitude: number
  longitude: number
}
```

### 3. Update All Pages

#### Regions.tsx
```typescript
const loadDevices = async () => {
  const response = await devicesAPI.getAll()  // ✅ Zabbix API

  // Map to internal format (minimal transformation)
  const devices = response.data.map(device => ({
    id: device.hostid,                        // ✅
    name: device.display_name,                // ✅
    host: device.ip,                          // ✅
    branch: device.branch,                    // ✅ Use backend city
    region: device.region,                    // ✅ Use backend region
    device_type: device.device_type,
    // ✅ Old logic: ping_status === 'Up' means online
    status: (device.ping_status === 'Up' || device.available === 'Available')
      ? 'up' : 'down',
    problems: device.problems,
    last_seen: device.last_check * 1000  // Convert to milliseconds
  }))
}

// Use backend fields directly (NO EXTRACTION)
const city = device.branch   // ✅ Already parsed by backend
const region = device.region // ✅ Already parsed by backend
```

#### Devices.tsx
```typescript
// Display table using Zabbix fields
<td>{device.display_name}</td>
<td>{device.branch}</td>  {/* City */}
<td>{device.ip}</td>
<td>{device.device_type}</td>
<td>
  <Badge variant={device.ping_status === 'Up' ? 'success' : 'danger'}>
    {device.ping_status}
  </Badge>
</td>
<td>{device.problems}</td>
```

#### Topology.tsx
```typescript
const loadDevices = async () => {
  const response = await devicesAPI.getAll()

  const nodes = response.data.map(device => ({
    id: device.hostid,
    name: device.display_name,
    ip: device.ip,
    type: device.device_type,
    status: device.ping_status === 'Up' ? 'online' : 'offline',
    region: device.region,
    x: Math.random() * 800,
    y: Math.random() * 600
  }))
}
```

#### Dashboard.tsx
```typescript
useEffect(() => {
  const fetchData = async () => {
    const devicesRes = await devicesAPI.getAll()

    const online = devicesRes.data.filter(d =>
      d.ping_status === 'Up' || d.available === 'Available'
    ).length

    const offline = devicesRes.data.filter(d =>
      d.ping_status === 'Down' || d.available === 'Unavailable'
    ).length

    setStats({
      total: devicesRes.data.length,
      online,
      offline
    })
  }
}, [])
```

### 4. Remove Unused Files

- ❌ Remove `frontend/src/lib/regions.ts` (city extraction logic not needed)
- ✅ Use backend `branch` and `region` fields directly

### 5. Test Checklist

- [ ] Dashboard shows correct device counts (873 Zabbix devices)
- [ ] Devices page shows all Zabbix devices with correct status
- [ ] Regions page shows all regions including Tbilisi
- [ ] Regions → Cities drill-down works
- [ ] Cities → Devices drill-down works
- [ ] Device detail page loads for Zabbix devices (hostid)
- [ ] Topology shows devices with correct online/offline status
- [ ] Device type filtering works (ATM, PayBox, NVR, Biostar, Router, Switch)
- [ ] Search works across all pages

## Quick Implementation Script

```bash
cd "/Users/g.jalabadze/Desktop/WARD OPS/CredoBranches/frontend"

# 1. Backup current files
cp src/services/api.ts src/services/api.ts.backup
cp src/pages/Regions.tsx src/pages/Regions.tsx.backup

# 2. Update api.ts (remove normalization, use /devices endpoint)
# 3. Update Regions.tsx (use branch/region fields from backend)
# 4. Update Devices.tsx (use Zabbix field names)
# 5. Update Topology.tsx (use Zabbix status logic)
# 6. Update Dashboard.tsx (use Zabbix status logic)

# 7. Build and deploy
npm run build
cd ..
rm -rf static_new
cp -r frontend/dist static_new

# 8. Restart server
lsof -ti:5001 | xargs kill -9
python3 main.py
```

## Expected Results

- **Total Devices**: 873 (all Zabbix branch devices)
- **Regions Visible**: All 11 regions including Tbilisi
- **Cities**: All cities with devices shown
- **Status**: Correct online/offline counts based on ping_status
- **Device Details**: All Zabbix device fields accessible
- **No Errors**: No console errors, no 500 errors, no missing data

## Notes

- Standalone devices are SEPARATE from Zabbix devices
- Don't merge them - keep them as separate features
- Zabbix devices use `/devices` API
- Standalone devices use `/devices/standalone/*` API
- The old UI had this working perfectly - just use the same logic!
