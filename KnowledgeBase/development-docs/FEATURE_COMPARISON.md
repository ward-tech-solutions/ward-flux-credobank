# Feature Comparison: Old UI vs New React UI

## Executive Summary

This document provides a comprehensive comparison between the old Flask-based UI and the new React UI for the WARD Network Monitoring System. It identifies missing features, APIs used, and implementation requirements.

---

## 1. Dashboard Page

### Old UI Features (`dashboard.html` + `dashboard.js`)

#### KPI Cards (6 cards) - **PRESENT IN NEW UI**
- Total Devices
- Online Devices
- Offline Devices
- System Uptime %
- Active Alerts
- Critical Issues

**API**: `GET /api/v1/dashboard/stats`
**Response Format**:
```json
{
  "total_devices": 150,
  "online_devices": 142,
  "offline_devices": 8,
  "uptime_percentage": 94.6,
  "active_alerts": 12,
  "critical_alerts": 3,
  "device_types": {...},
  "regions_stats": {...}
}
```

#### Regional Statistics Grid - **MISSING IN NEW UI**
- Shows stats per region (Tbilisi, Kakheti, Imereti, etc.)
- Each region card shows:
  - Total devices
  - Online/Offline count
  - Uptime percentage
  - Clickable to show uptime chart modal

**Implementation**: Uses `data.regions_stats` from dashboard stats API

#### Device Types Overview - **PARTIAL IN NEW UI**
Old UI shows:
- Icon for each type (Paybox, ATM, NVR, Access Point, Switch, Router, etc.)
- Total count per type
- Online/Offline breakdown
- Uptime percentage
- Clickable to show historical chart

**Current New UI**: Has generic pie chart, missing detailed breakdown per type

#### Active Alerts Table - **MISSING IN NEW UI**
- Severity filter dropdown (All/Disaster/High/Average/Warning/Information)
- Columns: Severity, Host, Description, Time
- Shows severity badges with color coding
- Links to device details page
- Live filtering

**API**: `GET /api/v1/alerts`
**Response Format**:
```json
[
  {
    "severity": "High",
    "host": "Tbilisi-Switch-01",
    "hostid": "10084",
    "description": "High CPU usage detected",
    "time": "2025-10-06 14:23:45"
  }
]
```

#### Device Status by Region Table - **MISSING IN NEW UI**
- Columns: Status, Device Name, Branch, IP Address, Type, Problems
- Shows top 20 devices sorted by problems
- Status badges (online/offline)
- Problems count badge
- Clickable rows to open device modal

**API**: `GET /api/v1/devices`

---

## 2. Geographic Map Page

### Old UI Features (`map.html` + `map.js`)

#### Interactive Map - **BASIC PLACEHOLDER IN NEW UI**
- **Leaflet.js** map with Georgia centered at [42.3154, 43.3569]
- Three tile layers: Light, Voyager, Satellite
- Zoom controls (min: 6, max: 18)
- Scale control showing metric units

#### Device Markers - **NEEDS IMPLEMENTATION**
- Markers use device `latitude` and `longitude` from Zabbix
- Color coded by `ping_status`:
  - Green = Up/Online
  - Red = Down/Offline
- Marker clusters for nearby devices
  - Shows device count in cluster
  - Cluster color based on status (all online, all offline, mixed)
- Click marker to show popup

#### Marker Popups - **NEEDS IMPLEMENTATION**
Shows:
- Branch name
- Region
- Total/Online/Offline device counts
- List of all devices at that location with:
  - Display name
  - IP address
  - Status
- "View Devices" button

#### Filter Buttons - **PRESENT IN NEW UI (BASIC)**
- All (shows total count)
- Online (shows online count)
- Offline (shows offline count)
- Active button styling

#### Region Dropdown - **MISSING IN NEW UI**
- "Jump to region" selector
- Filters map to show only devices in selected region
- Auto-zooms to fit selected region's devices

#### Reset View Button - **MISSING IN NEW UI**
- Resets map to show all devices
- Clears region filter
- Fits bounds to all markers

**API**: `GET /api/v1/devices`
**Required Device Fields**:
```json
{
  "hostid": "10084",
  "display_name": "Tbilisi Branch 1",
  "ip": "192.168.1.10",
  "branch": "Tbilisi",
  "region": "Tbilisi",
  "ping_status": "Up",
  "latitude": 41.7151,
  "longitude": 44.8271,
  "device_type": "Switch",
  "problems": 0
}
```

---

## 3. Device Details Page

### Old UI Features (`device-details.html` + device page scripts)

#### Device Information Section - **BASIC IN NEW UI**
Old UI shows:
- Status (Available/Unavailable) with color badge
- Hostname
- IP Address
- Groups (all Zabbix groups)
- Host ID
- Enabled status

**Current New UI**: Shows basic info but missing groups, hostid

#### Status Banner - **MISSING IN NEW UI**
- Large banner showing online/offline status
- Icon and colored background
- If offline:
  - Down since timestamp
  - Current downtime duration

**Calculation**: Uses trigger `lastchange` timestamp

#### Active Problems/Triggers - **MISSING IN NEW UI**
- Table showing active problems
- Severity badges (Disaster/High/Average/Warning/Information)
- Problem description
- Timestamp when problem started
- Duration of problem

**API**: Included in `GET /api/device/{hostid}` response
```json
{
  "triggers": [
    {
      "priority": "4",
      "description": "High CPU usage",
      "lastchange": "1728234567",
      "value": "1"
    }
  ]
}
```

#### Monitored Items Table - **MISSING IN NEW UI**
- Shows all Zabbix items being monitored
- Columns: Name, Last Value (with units), Last Check
- Examples: CPU usage, Memory usage, Ping response time

**API**: Included in device response as `items` array

#### Network Diagnostics Tools - **MISSING IN NEW UI**
1. **Ping Check**
   - Button to run ping test
   - Shows results with packet loss, min/max/avg latency
   - Real-time progress

2. **Traceroute**
   - Button to trace network path
   - Shows hop-by-hop route to device
   - Latency per hop

**Implementation**: Uses `NetworkDiagnostics` class from `network-diagnostics.js`
**APIs**:
- `POST /api/diagnostics/ping` - body: `{host: "192.168.1.10", count: 5}`
- `POST /api/diagnostics/traceroute` - body: `{host: "192.168.1.10", max_hops: 30}`

#### Quick Actions Bar - **MISSING IN NEW UI**
- SSH Terminal button (opens modal)
- Web UI link (opens device IP in new tab)
- Copy IP button
- View Branch link
- Refresh button
- Maintenance toggle

#### Incident Timeline - **MISSING IN NEW UI**
- Shows historical up/down events
- Calculated from Zabbix history data
- For each incident:
  - Type (went offline/came online)
  - Timestamp
  - Duration of downtime
- Shows last 20 incidents

**Data Source**: `ping_data.history` array from device response

#### Delete Device Button - **MISSING IN NEW UI**
**API**: `DELETE /api/host/delete/{hostid}`

---

## 4. Devices Page

### Old UI Features (`devices.html` + `devices.js`)

#### View Switcher - **MISSING IN NEW UI**
- Table view (default)
- Honeycomb/Cards view
- Persistent selection

#### Advanced Search/Filters - **PARTIAL IN NEW UI**
Old UI has:
- Search box (device name, IP, branch)
- Status filter dropdown (All/Online/Offline/Unknown)
- Type filter dropdown (Paybox/ATM/NVR/Access Point/Switch/Router)
- Advanced search toggle button

#### Add Device Button - **NEEDS REVIEW**
Links to `/add-host` page
**Page**: `add-host.html` - **MISSING IN NEW UI**

#### Device Modal - **ENHANCED IN OLD UI**
When clicking device row, shows modal with:
- Status banner with downtime info
- Quick action buttons (SSH, Web UI, Copy IP, etc.)
- Performance metrics cards (CPU, Memory, Disk, Network In/Out, Uptime)
- Device information grid
- Recent activity timeline
- Active problems list

**Current New UI**: Basic device details page, missing modal version

#### Edit Device Modal - **PRESENT IN OLD UI**
- Edit hostname, visible name, IP, branch
- Loads cities dropdown from API
- Inline editing without leaving page

**API**:
- `GET /api/device/{hostid}` - Get device data
- `POST /api/host/update/{hostid}` - Update device

#### SSH Terminal Modal - **PRESENT IN OLD UI**
- Embedded terminal using xterm.js
- WebSocket connection to device
- Username/password form
- Real-time terminal interaction

**Implementation**: Uses `ssh-terminal.js` script

#### Actions Per Device - **MORE IN OLD UI**
- View button (opens modal)
- Edit button (opens edit modal)
- SSH button (opens terminal)

---

## 5. Add/Edit Host Page

### Old UI Features (`add-host.html`)

#### Add Zabbix Host Form - **MISSING IN NEW UI**
Fields:
- Hostname (technical name)
- Display Name (friendly name)
- IP Address (with validation)
- Branch/City dropdown
- Device Type dropdown
- SNMP Community (optional)
- SNMP Version (v1/v2c/v3)
- Template selection (multiple)
- Host Groups (multiple select)
- Latitude/Longitude for map

**API**: `POST /api/host/add`
**Request Body**:
```json
{
  "hostname": "Tbilisi-Switch-01",
  "visible_name": "Tbilisi Branch Switch 1",
  "ip": "192.168.1.100",
  "branch": "Tbilisi",
  "device_type": "Switch",
  "snmp_community": "public",
  "snmp_version": "2",
  "templates": ["Template SNMP Device"],
  "groups": ["Switches", "Tbilisi"],
  "latitude": 41.7151,
  "longitude": 44.8271
}
```

---

## Summary of Missing Features in New UI

### High Priority (Core Functionality)

1. **Dashboard**
   - Regional Statistics grid
   - Device Types detailed breakdown
   - Active Alerts table with severity filter
   - Device Status by Region table

2. **Map Page**
   - Real Leaflet.js map implementation
   - Device markers with lat/lng from Zabbix
   - Marker clustering
   - Interactive popups
   - Region filter dropdown
   - Proper tile layers

3. **Device Details**
   - Status banner with downtime tracking
   - Active triggers/problems table
   - Monitored items table
   - Network diagnostics (ping, traceroute)
   - Quick actions bar
   - Incident timeline
   - Delete device functionality

4. **Add/Edit Host Page**
   - Complete form for adding Zabbix hosts
   - Full integration with Zabbix API

### Medium Priority (UX Enhancements)

1. **Devices Page**
   - Device modal (quick view)
   - Edit device inline modal
   - SSH terminal modal
   - Honeycomb/cards view
   - Advanced filters

2. **General**
   - Auto-refresh functionality (30s intervals)
   - Better loading states
   - Error handling modals

---

## API Endpoints Used by Old UI

### Dashboard APIs
- `GET /api/v1/dashboard/stats` - KPIs, device types, regional stats
- `GET /api/v1/alerts` - Active alerts with severity
- `GET /api/v1/devices` - All devices with full details

### Device APIs
- `GET /api/v1/devices` - List all devices
- `GET /api/device/{hostid}` - Single device with triggers, items, history
- `POST /api/host/add` - Add new Zabbix host
- `POST /api/host/update/{hostid}` - Update existing host
- `DELETE /api/host/delete/{hostid}` - Delete host

### Diagnostics APIs
- `POST /api/diagnostics/ping` - Run ping test
- `POST /api/diagnostics/traceroute` - Run traceroute

### Configuration APIs
- `GET /api/cities` - Get list of cities/branches
- `GET /api/device-types` - Get device types
- `GET /api/templates` - Get Zabbix templates
- `GET /api/groups` - Get host groups

---

## Data Format Examples

### Device Object (Full)
```json
{
  "hostid": "10084",
  "hostname": "Tbilisi-Switch-01",
  "display_name": "Tbilisi Branch Switch 1",
  "ip": "192.168.1.100",
  "branch": "Tbilisi",
  "region": "Tbilisi",
  "device_type": "Switch",
  "ping_status": "Up",
  "available": "Available",
  "latitude": 41.7151,
  "longitude": 44.8271,
  "status": "Enabled",
  "problems": 2,
  "groups": ["Switches", "Tbilisi", "Network Devices"],
  "triggers": [
    {
      "triggerid": "17832",
      "description": "High CPU usage on Tbilisi-Switch-01",
      "priority": "4",
      "value": "1",
      "lastchange": "1728234567"
    }
  ],
  "items": [
    {
      "itemid": "28765",
      "name": "CPU utilization",
      "lastvalue": "78",
      "units": "%",
      "lastclock": "1728234600"
    }
  ],
  "ping_data": {
    "history": [
      {
        "clock": "1728234000",
        "value": "1"
      }
    ]
  }
}
```

---

## Implementation Priority Recommendations

### Phase 1: Critical Features
1. Implement proper Map page with Leaflet and real coordinates
2. Add Regional Statistics to Dashboard
3. Add Active Alerts table to Dashboard
4. Enhance DeviceDetails with triggers and items

### Phase 2: Enhanced Functionality
1. Add Device Types detailed breakdown to Dashboard
2. Implement network diagnostics (ping/traceroute)
3. Add incident timeline to DeviceDetails
4. Create Add/Edit Host page

### Phase 3: UX Polish
1. Add device modal to Devices page
2. Implement SSH terminal
3. Add auto-refresh everywhere
4. Add honeycomb view to Devices

---

## Technology Stack Comparison

### Old UI
- **Framework**: Flask (Python) with Jinja2 templates
- **Map**: Leaflet.js with marker clustering
- **Charts**: Chart.js
- **HTTP**: Fetch API with custom auth wrapper
- **Styling**: Custom CSS with CSS variables
- **Icons**: Font Awesome
- **Terminal**: xterm.js for SSH

### New UI (Current)
- **Framework**: React 18 + TypeScript
- **Router**: React Router v6
- **State**: TanStack Query (React Query) + Zustand
- **Charts**: Recharts
- **Map**: Basic placeholder (needs react-leaflet)
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **Components**: Custom shadcn-style components

### Required New Dependencies
```json
{
  "leaflet": "^1.9.4",
  "react-leaflet": "^4.2.1",
  "@types/leaflet": "^1.9.8",
  "leaflet.markercluster": "^1.5.3"
}
```

---

## Conclusion

The new React UI has the foundation in place but is missing several critical features from the old UI:

**Missing Pages**: Add/Edit Host page, proper Map implementation
**Missing Dashboard Components**: Regional stats, detailed device types, active alerts table
**Missing DeviceDetails Features**: Triggers, items, diagnostics, timeline, quick actions

**Recommended Action**: Implement missing features in the priority order listed above, starting with Map page and Dashboard enhancements.
