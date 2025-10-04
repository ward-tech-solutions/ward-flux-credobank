# Network Topology Live Interface Monitoring - Complete Implementation Guide

## Overview
This document contains the complete implementation of a modern, dark-themed network topology visualization with live router interface monitoring for the WARD OPS Network Monitoring Dashboard.

---

## What Was Implemented

### ✅ 3-Level Hierarchical Topology
- **Level 0**: Core Routers (Branches_ASR1, Branches_ASR2) - Orange diamond shapes
- **Level 1**: Branch Switches - Teal box shapes connected to core routers
- **Level 2**: End Devices (ATM, NVR, Access Points) - Various colored shapes

### ✅ Live Router Interface Monitoring
- WebSocket-based real-time updates every 5 seconds
- Interface status (up/down)
- Per-interface bandwidth (in/out in Mbps)
- Error counters
- Interface descriptions from Zabbix

### ✅ Modern Dark Theme UI
- Completely redesigned topology page
- Professional dark theme with neon accents
- Card-based interface panel
- Smooth animations and transitions
- Responsive layout

### ✅ Edge Bandwidth Labels
- Shows bandwidth usage on lines between routers and switches
- Format: `↓50.2M ↑30.1M`
- Hover tooltips with detailed interface info

---

## File Changes Summary

### 1. **main.py** - Backend API Changes

#### WebSocket Endpoint (Line ~1724)
```python
@app.websocket("/ws/router-interfaces/{hostid}")
async def websocket_router_interfaces(websocket: WebSocket, hostid: str):
    """WebSocket endpoint for live router interface monitoring - No Auth Required"""
    print(f"[WS] Router interface connection request for hostid: {hostid}")

    try:
        await websocket.accept()
        print(f"[WS] WebSocket accepted for router {hostid}")
    except Exception as e:
        print(f"[WS ERROR] Failed to accept WebSocket: {e}")
        return

    # ... rest of implementation
```

**Key Features:**
- No authentication required
- Comprehensive error logging
- Type checking for interface data
- Updates every 5 seconds
- Returns summary stats + detailed interface list

#### Router Interface API Endpoint (Line ~560)
```python
@app.get("/api/v1/router/{hostid}/interfaces")
async def get_router_interfaces(
    request: Request,
    hostid: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get router interface statistics"""
    zabbix = request.app.state.zabbix
    loop = asyncio.get_event_loop()
    interfaces = await loop.run_in_executor(executor, lambda: zabbix.get_router_interfaces(hostid))
    return {
        'hostid': hostid,
        'interfaces': interfaces
    }
```

#### Topology Endpoints with Bandwidth Labels (Lines ~575 and ~957)
Both `/api/v1/topology` and `/api/topology` now include:
- Interface bandwidth data in edge labels
- Matching interface descriptions to branch names
- Color-coded edges (teal for up, red for down)
- Tooltips with interface details

```python
# Example edge with bandwidth
edges.append({
    'from': core_router['hostid'],
    'to': switch['hostid'],
    'color': '#14b8a6' if status == 'Up' else '#dc3545',
    'width': 2,
    'label': f"↓{bw_in_mbps:.1f}M ↑{bw_out_mbps:.1f}M",
    'title': f"Link: {core_router['display_name']} → {switch['display_name']}\nInterface: {iface_name}\n↓ {bw_in_mbps:.2f} Mbps\n↑ {bw_out_mbps:.2f} Mbps",
    'font': {'size': 10, 'color': '#00d9ff', 'strokeWidth': 2, 'strokeColor': '#000'}
})
```

#### Topology Page Route (Line ~1273)
```python
@app.get("/topology", response_class=HTMLResponse)
async def topology_page_legacy(request: Request):
    """Serve modern topology page with live interface monitoring"""
    return templates.TemplateResponse("topology_new.html", {"request": request})
```

---

### 2. **zabbix_client.py** - Zabbix Data Retrieval

#### get_router_interfaces Method (Line ~434)
Completely rewritten to use correct Zabbix item keys:

```python
def get_router_interfaces(self, hostid):
    """Get network interfaces for a router with bandwidth stats using Zabbix item keys"""
    try:
        # Get all network interface items for this host
        items = self.zapi.item.get(
            hostids=hostid,
            search={'key_': 'net.if'},
            output=['itemid', 'name', 'key_', 'lastvalue', 'lastclock', 'units'],
            sortfield='name'
        )

        # Group items by interface name
        interfaces_data = {}

        for item in items:
            item_name = item.get('name', '')
            key = item.get('key_', '')

            # Extract interface name from item name like:
            # "Interface Gi0(To_Core_1/0/46): Bits received"
            if 'Interface ' in item_name and ':' in item_name:
                iface_part = item_name.split('Interface ')[1].split(':')[0].strip()

                if '(' in iface_part:
                    iface_name = iface_part.split('(')[0].strip()
                    description = iface_part.split('(')[1].rstrip(')')
                else:
                    iface_name = iface_part
                    description = ''

                if iface_name not in interfaces_data:
                    interfaces_data[iface_name] = {
                        'name': iface_name,
                        'description': description,
                        'status': 'unknown',
                        'bandwidth_in': 0,
                        'bandwidth_out': 0,
                        'errors_in': 0,
                        'errors_out': 0
                    }

                # Parse different item types
                lastvalue = item.get('lastvalue', '0')

                try:
                    if 'ifOperStatus' in key or 'Operational status' in item_name:
                        interfaces_data[iface_name]['status'] = 'up' if lastvalue == '1' else 'down'

                    elif 'ifHCInOctets' in key or 'Bits received' in item_name:
                        interfaces_data[iface_name]['bandwidth_in'] = int(float(lastvalue or 0))

                    elif 'ifHCOutOctets' in key or 'Bits sent' in item_name:
                        interfaces_data[iface_name]['bandwidth_out'] = int(float(lastvalue or 0))

                    elif 'ifInErrors' in key or 'Inbound packets with errors' in item_name:
                        interfaces_data[iface_name]['errors_in'] = int(float(lastvalue or 0))

                    elif 'ifOutErrors' in key or 'Outbound packets with errors' in item_name:
                        interfaces_data[iface_name]['errors_out'] = int(float(lastvalue or 0))

                except (ValueError, TypeError):
                    continue

        return interfaces_data

    except Exception as e:
        print(f"Error getting router interfaces for host {hostid}: {e}")
        import traceback
        traceback.print_exc()
        return {}
```

**Important Notes:**
- Returns a **dict**, not a list
- Keys: `name`, `description`, `status`, `bandwidth_in`, `bandwidth_out`, `errors_in`, `errors_out`
- Bandwidth values in bits/second (convert to Mbps by dividing by 1,000,000)
- Status values: 'up', 'down', 'unknown'

---

### 3. **templates/topology_new.html** - Modern UI Template

**Location**: `/templates/topology_new.html`

This is a completely new file with:
- Modern dark theme design
- Card-based interface panel
- Live status indicators with pulsing animations
- Responsive grid layouts
- Professional color scheme

**Key Features:**
- Clean header with search and filters
- Stats bar showing node/edge counts
- Right-side router interface panel
- Bottom-left legend
- Loading overlays
- All dark theme CSS variables

**Color Scheme:**
```css
:root {
    --topology-bg: #0a0e1a;
    --panel-bg: #141824;
    --panel-border: #1e2433;
    --accent-blue: #00d9ff;
    --accent-green: #10b981;
    --accent-red: #ef4444;
    --accent-orange: #FF6B35;
    --accent-yellow: #f59e0b;
}
```

**Panel Structure:**
```html
<div id="router-panel" class="modern-panel router-panel">
    <div class="panel-header">...</div>
    <div class="panel-body">
        <div class="summary-grid"><!-- 2x2 grid of stat cards --></div>
        <div class="live-badge"><!-- Pulsing live indicator --></div>
        <div id="interfaces-container"><!-- Interface cards --></div>
    </div>
</div>
```

---

### 4. **static/js/topology.js** - Frontend JavaScript

#### Updated Functions

**showRouterInterfaces** - Opens router interface panel:
```javascript
function showRouterInterfaces(hostid, routerName) {
    currentRouterHostId = hostid;

    // Close node panel if open
    if (typeof closeNodePanel === 'function') {
        closeNodePanel();
    }

    // Show router panel (supports both old and new IDs)
    const panel = document.getElementById('router-panel') || document.getElementById('interface-panel');
    if (!panel) {
        console.error('Router panel not found');
        return;
    }

    panel.style.display = 'block';

    // Update title
    const titleElement = document.getElementById('router-name') || document.getElementById('interface-panel-title');
    if (titleElement) {
        if (titleElement.tagName === 'SPAN') {
            titleElement.textContent = routerName;
        } else {
            titleElement.innerHTML = `<i class="fas fa-network-wired"></i> ${routerName} Interfaces`;
        }
    }

    // Show loading
    const container = document.getElementById('interfaces-container') || document.getElementById('interface-list');
    if (container) {
        container.innerHTML = `
            <div class="loading-state">
                <i class="fas fa-spinner fa-spin"></i>
                <span>Connecting to live feed...</span>
            </div>
        `;
    }

    // Connect WebSocket
    connectInterfaceWebSocket(hostid);
}
```

**connectInterfaceWebSocket** - Establishes WebSocket connection:
```javascript
function connectInterfaceWebSocket(hostid) {
    if (interfaceWebSocket) {
        interfaceWebSocket.close();
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/router-interfaces/${hostid}`;

    try {
        interfaceWebSocket = new WebSocket(wsUrl);

        interfaceWebSocket.onopen = () => {
            console.log(`WebSocket connected for router ${hostid}`);
        };

        interfaceWebSocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'interface_update') {
                updateInterfacePanel(data);
            }
        };

        interfaceWebSocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            const container = document.getElementById('interfaces-container') || document.getElementById('interface-list');
            if (container) {
                container.innerHTML = `
                    <div class="loading-state" style="color: #ef4444;">
                        <i class="fas fa-exclamation-triangle"></i>
                        <span>Connection error - Check server logs</span>
                    </div>
                `;
            }
        };

        interfaceWebSocket.onclose = () => {
            console.log('WebSocket closed');
        };

    } catch (error) {
        console.error('Failed to connect WebSocket:', error);
    }
}
```

**updateInterfacePanel** - Updates UI with live data:
```javascript
function updateInterfacePanel(data) {
    // Update summary stats (supports both old and new element IDs)
    const upEl = document.getElementById('iface-up') || document.getElementById('interfaces-up');
    const downEl = document.getElementById('iface-down') || document.getElementById('interfaces-down');
    const bwInEl = document.getElementById('total-bw-in') || document.getElementById('bandwidth-in');
    const bwOutEl = document.getElementById('total-bw-out') || document.getElementById('bandwidth-out');

    if (upEl) upEl.textContent = data.summary.up;
    if (downEl) downEl.textContent = data.summary.down;
    if (bwInEl) bwInEl.textContent = data.summary.bandwidth_in_mbps.toFixed(1);
    if (bwOutEl) bwOutEl.textContent = data.summary.bandwidth_out_mbps.toFixed(1);

    // Update interface list
    const interfaceList = document.getElementById('interfaces-container') || document.getElementById('interface-list');

    if (!interfaceList) {
        console.error('Interface list container not found');
        return;
    }

    if (!data.interfaces || data.interfaces.length === 0) {
        interfaceList.innerHTML = `
            <div class="loading-state">
                <i class="fas fa-info-circle"></i>
                <span>No interfaces found</span>
            </div>
        `;
        return;
    }

    // Render interface cards
    interfaceList.innerHTML = data.interfaces.map(iface => `
        <div class="interface-card">
            <div class="interface-header">
                <div class="interface-name">${iface.name}</div>
                <span class="interface-badge ${iface.status}">${iface.status.toUpperCase()}</span>
            </div>
            ${iface.description ? `<div class="interface-desc">${iface.description}</div>` : ''}
            <div class="interface-metrics">
                <div class="metric">
                    <i class="fas fa-arrow-down"></i>
                    <span class="metric-value">${iface.bandwidth_in_mbps.toFixed(2)}</span> Mbps
                </div>
                <div class="metric">
                    <i class="fas fa-arrow-up"></i>
                    <span class="metric-value">${iface.bandwidth_out_mbps.toFixed(2)}</span> Mbps
                </div>
                ${iface.errors_in > 0 || iface.errors_out > 0 ? `
                    <div class="error-indicator">
                        <i class="fas fa-exclamation-triangle"></i>
                        Errors: ${iface.errors_in} in / ${iface.errors_out} out
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
}
```

---

## Testing Instructions

### 1. **Restart the Server**
```bash
cd /Users/g.jalabadze/Desktop/WARD\ OPS/CredoBranches
pkill -9 -f "python.*run.py"
source venv/bin/activate
python3 run.py > server.log 2>&1 &
```

### 2. **Access the Topology Page**
- Navigate to: `http://localhost:5001/topology`
- You should see the new modern dark theme UI

### 3. **Test Live Interface Monitoring**
1. **Click on a Core Router** (orange diamond - Branches_ASR1 or Branches_ASR2)
2. **Router interface panel should appear** on the right side
3. **Watch for live updates** every 5 seconds
4. **Check the console** for WebSocket connection logs

### 4. **Verify Data Display**
- **Summary cards** show: Interfaces Up/Down, Total Bandwidth In/Out
- **Interface cards** show: Name, Status, Bandwidth, Errors
- **Green pulsing dot** indicates live data
- **Hover over edges** to see bandwidth labels

### 5. **Check Server Logs**
```bash
tail -f /Users/g.jalabadze/Desktop/WARD\ OPS/CredoBranches/server.log
```

Look for:
```
[WS] Router interface connection request for hostid: 10689
[WS] WebSocket accepted for router 10689
```

---

## Troubleshooting

### Issue: "Connection error" in interface panel

**Check:**
1. Server logs for WebSocket errors
2. Browser console for JavaScript errors
3. Zabbix connection status

**Solution:**
```bash
# Check if Zabbix is accessible
curl http://10.30.25.34:8080

# Verify interface data retrieval
cd /Users/g.jalabadze/Desktop/WARD\ OPS/CredoBranches
source venv/bin/activate
python3 -c "
from zabbix_client import ZabbixClient
zabbix = ZabbixClient()
data = zabbix.get_router_interfaces('10689')
print(f'Found {len(data)} interfaces')
for name, iface in list(data.items())[:3]:
    print(f'{name}: {iface}')
"
```

### Issue: Bandwidth showing 0

**Possible causes:**
1. Zabbix items not collecting data
2. Interface names not matching correctly
3. Data type conversion error

**Solution:**
- Check Zabbix web UI for the router's items
- Verify `net.if.in[ifHCInOctets.X]` items have recent values
- Check server logs for parsing errors

### Issue: WebSocket 403 Forbidden

**Cause:** FastAPI version or CORS issue

**Solution:**
- Check FastAPI version: `pip show fastapi`
- Ensure no authentication middleware on WebSocket route
- Check CORS configuration in main.py

---

## Data Flow Diagram

```
Browser                  WebSocket                Backend                  Zabbix
   │                        │                        │                        │
   │  Click Core Router     │                        │                        │
   ├────────────────────────┤                        │                        │
   │                        │                        │                        │
   │  WebSocket Connect     │                        │                        │
   │  ws://localhost:5001   │                        │                        │
   │  /ws/router-interfaces │                        │                        │
   │  /10689                │                        │                        │
   ├───────────────────────►│                        │                        │
   │                        │  Accept Connection     │                        │
   │                        ├───────────────────────►│                        │
   │                        │                        │                        │
   │                        │                        │  get_router_interfaces │
   │                        │                        │  (hostid=10689)        │
   │                        │                        ├───────────────────────►│
   │                        │                        │                        │
   │                        │                        │  Query items:          │
   │                        │                        │  net.if.in[...]        │
   │                        │                        │  net.if.out[...]       │
   │                        │                        │  net.if.status[...]    │
   │                        │                        │◄───────────────────────┤
   │                        │                        │                        │
   │                        │                        │  Parse & aggregate     │
   │                        │                        │  by interface name     │
   │                        │                        │                        │
   │                        │  Send JSON:            │                        │
   │                        │  {                     │                        │
   │                        │    type: 'interface    │                        │
   │                        │      _update',         │                        │
   │                        │    summary: {...},     │                        │
   │                        │    interfaces: [...]   │                        │
   │                        │  }                     │                        │
   │◄───────────────────────┤◄───────────────────────┤                        │
   │                        │                        │                        │
   │  Update UI:            │                        │                        │
   │  - Summary stats       │                        │                        │
   │  - Interface cards     │                        │  (Repeat every 5s)     │
   │                        │                        │                        │
   │                        │                        │                        │
```

---

## WebSocket Message Format

### Server → Client

**Connection Confirmation:**
```json
{
  "type": "connected",
  "hostid": "10689",
  "timestamp": "2025-10-04T03:48:00.000Z"
}
```

**Interface Update (every 5 seconds):**
```json
{
  "type": "interface_update",
  "hostid": "10689",
  "timestamp": "2025-10-04T03:48:05.000Z",
  "summary": {
    "total": 15,
    "up": 12,
    "down": 3,
    "bandwidth_in_mbps": 150.45,
    "bandwidth_out_mbps": 89.32,
    "errors_in": 0,
    "errors_out": 2
  },
  "interfaces": [
    {
      "name": "Gi0",
      "status": "up",
      "bandwidth_in_mbps": 45.23,
      "bandwidth_out_mbps": 32.15,
      "errors_in": 0,
      "errors_out": 0,
      "description": "To_Core_1/0/46"
    },
    {
      "name": "Gi0/0/0",
      "status": "up",
      "bandwidth_in_mbps": 105.22,
      "bandwidth_out_mbps": 57.17,
      "errors_in": 0,
      "errors_out": 2,
      "description": "To_External1_7Port"
    }
  ]
}
```

---

## Known Limitations

1. **Branch-to-Interface Matching**: Currently uses simple string matching to associate branch switches with router interfaces. In production, use LLDP/CDP data.

2. **Performance**: Limited to 100 end devices and 20 devices per type to maintain performance.

3. **Interface Discovery**: Relies on Zabbix item naming convention. If your Zabbix uses different naming, update the parsing logic in `get_router_interfaces()`.

4. **Caching**: No caching implemented for interface data. Every request fetches fresh data from Zabbix.

---

## Future Enhancements

### Short Term
- [ ] Add interface speed utilization percentage
- [ ] Color-code edges based on bandwidth usage (green <50%, yellow 50-80%, red >80%)
- [ ] Add filter to show only interfaces with errors
- [ ] Export interface data to CSV/Excel

### Medium Term
- [ ] Historical bandwidth graphs per interface
- [ ] SNMP trap integration for instant interface down notifications
- [ ] Multi-router comparison view
- [ ] Automated topology discovery using LLDP/CDP

### Long Term
- [ ] Predictive analytics for bandwidth trends
- [ ] Automatic rerouting suggestions for congested links
- [ ] Integration with ticketing system for interface errors
- [ ] Mobile app support

---

## Code Maintenance Notes

### Adding New Interface Metrics

To add a new metric (e.g., packet drops):

1. **Update `zabbix_client.py`:**
```python
# In get_router_interfaces(), add new parsing:
elif 'ifDrops' in key or 'packets dropped' in item_name:
    interfaces_data[iface_name]['drops'] = int(float(lastvalue or 0))
```

2. **Update WebSocket response in `main.py`:**
```python
# In stream_interfaces(), add to summary:
'total_drops': sum(iface.get('drops', 0) for iface in interfaces.values())

# And to individual interface data:
'drops': data.get('drops', 0)
```

3. **Update UI in `topology_new.html`:**
```html
<!-- Add new summary card -->
<div class="summary-card warning">
    <div class="card-icon"><i class="fas fa-exclamation"></i></div>
    <div class="card-data">
        <div class="card-value" id="total-drops">0</div>
        <div class="card-label">Total Drops</div>
    </div>
</div>
```

4. **Update JavaScript in `topology.js`:**
```javascript
// In updateInterfacePanel():
document.getElementById('total-drops').textContent = data.summary.total_drops;

// And in interface card rendering:
<div class="metric">
    <i class="fas fa-exclamation"></i>
    <span class="metric-value">${iface.drops}</span> Drops
</div>
```

---

## Support & Contacts

- **Zabbix Server**: http://10.30.25.34:8080
- **Zabbix Credentials**: User: Python, Password: Ward123Ops
- **Core Routers**:
  - Branches_ASR1: 10.195.195.64
  - Branches_ASR2: 10.195.195.65
- **Database**: SQLite at `/data/ward_ops.db`

---

## Changelog

### Version 1.0 (2025-10-04)
- ✅ Implemented 3-level hierarchical topology
- ✅ Added WebSocket live interface monitoring
- ✅ Created modern dark theme UI
- ✅ Added bandwidth labels on edges
- ✅ Fixed Zabbix item key parsing
- ✅ Implemented error handling and logging

---

## Summary

The system now provides a professional, live-updating network topology visualization with detailed router interface monitoring. The dark theme UI is optimized for 24/7 NOC displays, and the WebSocket implementation ensures minimal server load while providing real-time data.

**Key Success Metrics:**
- 🔄 Live updates every 5 seconds
- 📊 Per-interface bandwidth visibility
- 🎨 Modern, professional dark theme
- 🚀 Fast, responsive UI
- 📡 Reliable WebSocket connections
- 🔍 Easy troubleshooting with detailed logging

**Next Steps:**
1. Refresh your browser: `http://localhost:5001/topology`
2. Click on a core router (orange diamond)
3. Watch the live interface data update
4. Check server logs for WebSocket connection confirmations

If you encounter any issues, refer to the Troubleshooting section or check the server logs for detailed error messages.
