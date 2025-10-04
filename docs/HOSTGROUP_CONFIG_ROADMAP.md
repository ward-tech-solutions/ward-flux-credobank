# Host Group Configuration Feature - Implementation Roadmap

## ✅ Phase 1: Database (COMPLETED)
- [x] Created `monitored_hostgroups` table
- [x] Created `georgian_regions` table with 11 regions + coordinates
- [x] Created `georgian_cities` table with 82 cities + coordinates
- [x] Migration file: `migrations/003_hostgroup_config.sql`

## 🚧 Phase 2: API Endpoints (NEXT)

### 1. Fetch Zabbix Host Groups
```python
# File: main.py
@app.get("/api/v1/config/zabbix-hostgroups")
@requires_auth
async def get_zabbix_hostgroups(request: Request):
    """Fetch all host groups from Zabbix"""
    try:
        groups = zapi.hostgroup.get(output=['groupid', 'name'])
        return {"hostgroups": groups}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 2. Get Monitored Host Groups
```python
@app.get("/api/v1/config/monitored-hostgroups")
@requires_auth
async def get_monitored_hostgroups(request: Request):
    """Get currently monitored host groups from DB"""
    cursor.execute("""
        SELECT groupid, name, display_name, is_active
        FROM monitored_hostgroups
        WHERE is_active = 1
    """)
    groups = cursor.fetchall()
    return {"monitored_groups": groups}
```

### 3. Save Monitored Host Groups
```python
@app.post("/api/v1/config/monitored-hostgroups")
@requires_auth
async def save_monitored_hostgroups(request: Request):
    """Save selected host groups configuration"""
    data = await request.json()
    groups = data.get('groups', [])

    # Deactivate all existing
    cursor.execute("UPDATE monitored_hostgroups SET is_active = 0")

    # Insert/activate selected groups
    for group in groups:
        cursor.execute("""
            INSERT OR REPLACE INTO monitored_hostgroups
            (groupid, name, display_name, is_active)
            VALUES (?, ?, ?, 1)
        """, (group['groupid'], group['name'], group.get('display_name', group['name'])))

    conn.commit()
    return {"status": "success", "saved": len(groups)}
```

### 4. Get Georgian Cities/Regions
```python
@app.get("/api/v1/config/georgian-cities")
@requires_auth
async def get_georgian_cities(request: Request):
    """Get all Georgian cities with regions and coordinates"""
    cursor.execute("""
        SELECT c.id, c.name_en, c.latitude, c.longitude,
               r.name_en as region_name
        FROM georgian_cities c
        JOIN georgian_regions r ON c.region_id = r.id
        WHERE c.is_active = 1
        ORDER BY r.name_en, c.name_en
    """)
    cities = cursor.fetchall()
    return {"cities": cities}
```

## 🚧 Phase 3: Configuration Page UI

### Create: `templates/config.html`

```html
{% extends "base.html" %}
{% block title %}Configuration - Host Groups{% endblock %}

{% block content %}
<div class="config-container">
    <h1>Host Group Configuration</h1>

    <div class="config-section">
        <h2>Select Host Groups to Monitor</h2>
        <button id="fetch-groups-btn" class="btn-primary">
            <i class="fas fa-sync"></i> Fetch from Zabbix
        </button>

        <div id="hostgroups-list" class="hostgroups-grid">
            <!-- Populated via JS -->
        </div>

        <button id="save-config-btn" class="btn-success">
            <i class="fas fa-save"></i> Save Configuration
        </button>
    </div>

    <div class="config-section">
        <h2>City-Region Mapping</h2>
        <p>The following cities are configured with coordinates for map visualization:</p>
        <div id="cities-list" class="cities-grid">
            <!-- Populated via JS -->
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='js/config.js') }}"></script>
{% endblock %}
```

### Create: `static/js/config.js`

```javascript
let availableGroups = [];
let selectedGroups = new Set();

// Fetch Zabbix host groups
document.getElementById('fetch-groups-btn').addEventListener('click', async () => {
    const response = await fetch('/api/v1/config/zabbix-hostgroups');
    const data = await response.json();
    availableGroups = data.hostgroups;
    renderHostGroups();
});

// Render host groups
function renderHostGroups() {
    const container = document.getElementById('hostgroups-list');
    container.innerHTML = availableGroups.map(group => `
        <div class="hostgroup-item">
            <input type="checkbox" id="group-${group.groupid}"
                   value="${group.groupid}"
                   onchange="toggleGroup('${group.groupid}')">
            <label for="group-${group.groupid}">${group.name}</label>
            <input type="text" placeholder="Display name"
                   id="display-${group.groupid}"
                   value="${group.name}">
        </div>
    `).join('');
}

// Toggle group selection
function toggleGroup(groupid) {
    if (selectedGroups.has(groupid)) {
        selectedGroups.delete(groupid);
    } else {
        selectedGroups.add(groupid);
    }
}

// Save configuration
document.getElementById('save-config-btn').addEventListener('click', async () => {
    const groups = Array.from(selectedGroups).map(groupid => {
        const group = availableGroups.find(g => g.groupid === groupid);
        const displayName = document.getElementById(`display-${groupid}`).value;
        return {
            groupid,
            name: group.name,
            display_name: displayName
        };
    });

    const response = await fetch('/api/v1/config/monitored-hostgroups', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({groups})
    });

    if (response.ok) {
        alert('Configuration saved successfully!');
    }
});
```

## 🚧 Phase 4: Update Dashboard Logic

### Modify: `main.py` - Dashboard endpoint

```python
@app.get("/api/v1/dashboard/stats")
@requires_auth
async def get_dashboard_stats(request: Request):
    """Get dashboard statistics using configured host groups"""

    # Get monitored groups from DB
    cursor.execute("""
        SELECT groupid, display_name
        FROM monitored_hostgroups
        WHERE is_active = 1
    """)
    monitored_groups = cursor.fetchall()

    if not monitored_groups:
        return {"error": "No host groups configured"}

    # Single Zabbix query with all groupids
    groupids = [g['groupid'] for g in monitored_groups]
    hosts = zapi.host.get(
        groupids=groupids,
        output=['hostid', 'host', 'status'],
        selectGroups=['groupid', 'name']
    )

    # Parse hostnames to extract cities
    regional_stats = {}

    for host in hosts:
        # Extract city from hostname (e.g., "Batumi-ATM" -> "Batumi")
        city_name = extract_city_from_hostname(host['host'])

        # Lookup city in DB to get region
        cursor.execute("""
            SELECT r.name_en as region, c.latitude, c.longitude
            FROM georgian_cities c
            JOIN georgian_regions r ON c.region_id = r.id
            WHERE c.name_en = ?
        """, (city_name,))

        city_data = cursor.fetchone()

        if city_data:
            region = city_data['region']
            if region not in regional_stats:
                regional_stats[region] = {
                    'total': 0, 'online': 0, 'offline': 0,
                    'latitude': city_data['latitude'],
                    'longitude': city_data['longitude']
                }

            regional_stats[region]['total'] += 1
            if host['status'] == '0':
                regional_stats[region]['online'] += 1
            else:
                regional_stats[region]['offline'] += 1

    return {"regional_stats": regional_stats}

def extract_city_from_hostname(hostname):
    """Extract city name from hostname"""
    # Remove IP if present: "Batumi-ATM 10.199.96.163" -> "Batumi-ATM"
    name = hostname.split()[0]

    # Extract city: "Batumi-ATM" -> "Batumi", "Batumi1-NVR" -> "Batumi"
    city = name.split('-')[0]

    # Remove numbers: "Batumi1" -> "Batumi"
    city = ''.join([c for c in city if not c.isdigit()])

    return city.strip()
```

## 🚧 Phase 5: Update Map to Use DB Coordinates

### Modify: `static/js/map.js`

```javascript
// Fetch regional stats with coordinates from API
async function loadMapData() {
    const response = await fetch('/api/v1/dashboard/stats');
    const data = await response.json();

    // Clear existing markers
    markers.clearLayers();

    // Add markers for each region
    for (const [region, stats] of Object.entries(data.regional_stats)) {
        const marker = L.marker([stats.latitude, stats.longitude])
            .bindPopup(`
                <b>${region}</b><br>
                Total: ${stats.total}<br>
                Online: ${stats.online}<br>
                Offline: ${stats.offline}
            `);
        markers.addLayer(marker);
    }

    map.fitBounds(markers.getBounds());
}
```

## 📝 Implementation Order:

1. ✅ Database migration (DONE)
2. Add API endpoints to `main.py`
3. Create `templates/config.html`
4. Create `static/js/config.js`
5. Add route in `main.py`: `@app.get("/config")` -> render config.html
6. Update dashboard stats logic
7. Update map.js to use DB coordinates
8. Update Add Device form to use monitored groups

## 🔧 Testing Checklist:

- [ ] Can fetch Zabbix host groups
- [ ] Can select and save monitored groups
- [ ] Dashboard shows correct regional stats
- [ ] Map displays cities with correct coordinates
- [ ] Add Device form shows only monitored groups
- [ ] Hostname parsing works for all city formats

## 🚀 Next Steps:

Continue implementation starting from Phase 2 (API Endpoints). All database structure is ready, coordinates are loaded, and this roadmap provides the complete implementation path.
