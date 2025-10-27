# SNMP Data Storage - PostgreSQL vs VictoriaMetrics

**Question:** Where we are saving SNMP data in Postgres or in VictoriaMetrics and if both what are used for what?

**Answer:** We use BOTH, but for different purposes. This is a **hybrid architecture** optimized for both real-time queries and historical analysis.

---

## 📊 Dual Storage Architecture

```
┌─────────────────────────────────────────────────────────────┐
│           SNMP POLLING (Every 60 seconds)                   │
│     Celery Task: collect_all_interface_metrics              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Polls: snmpwalk -v2c ...
                     │ Gets: oper_status, traffic, errors, etc.
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              interface_metrics.py                           │
│        InterfaceMetricsCollector.collect()                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Split Storage:
                     │
        ┌────────────┴──────────────┐
        │                           │
        ▼                           ▼
┌──────────────────────┐  ┌──────────────────────┐
│   POSTGRESQL         │  │  VICTORIAMETRICS     │
│                      │  │                      │
│ device_interfaces    │  │ interface_oper_status│
│ oper_status = 1      │  │ interface_in_octets  │
│ last_seen = now()    │  │ interface_out_octets │
│                      │  │ interface_in_errors  │
│ ⭐ CURRENT STATE     │  │                      │
│ "What's UP NOW?"     │  │ ⭐ TIME-SERIES       │
│                      │  │ "What happened?"     │
└──────────────────────┘  └──────────────────────┘
```

---

## 1️⃣ PostgreSQL - Current State Database

### What's Stored
**Table:** `device_interfaces`

```sql
CREATE TABLE device_interfaces (
    id UUID PRIMARY KEY,
    device_id UUID REFERENCES standalone_devices(id),
    if_index INTEGER NOT NULL,
    if_name VARCHAR(128),              -- "FastEthernet3"
    if_alias VARCHAR(256),              -- "Magti_Internet"
    if_descr VARCHAR(256),              -- "FastEthernet3"
    interface_type VARCHAR(32),         -- "isp", "trunk", "access"
    isp_provider VARCHAR(32),           -- "magti", "silknet"

    -- ⭐ CURRENT STATUS (Updated every 60s)
    oper_status INTEGER,                -- 1=UP, 2=DOWN
    admin_status INTEGER,               -- 1=UP, 2=DOWN
    speed BIGINT,                       -- Link speed

    -- TIMESTAMPS
    last_seen TIMESTAMP,                -- Last successful SNMP poll
    last_status_change TIMESTAMP,       -- When oper_status changed
    discovered_at TIMESTAMP,

    -- FLAGS
    is_critical BOOLEAN DEFAULT false,
    monitoring_enabled BOOLEAN DEFAULT true,
    enabled BOOLEAN DEFAULT true,

    UNIQUE(device_id, if_index)
);
```

### Update Mechanism
**File:** `monitoring/tasks_interface_discovery.py:286-312`

```python
# UPSERT on every discovery (daily + metrics collection)
interface_record = {
    'device_id': device_id,
    'if_index': interface_data['if_index'],
    'oper_status': interface_data.get('if_oper_status'),  # ⭐ Updated here
    'last_seen': datetime.utcnow(),
    # ... other fields
}

# INSERT ... ON CONFLICT UPDATE
stmt = insert(DeviceInterface).values(**interface_record)
stmt = stmt.on_conflict_do_update(
    index_elements=['device_id', 'if_index'],
    set_={
        'oper_status': stmt.excluded.oper_status,  # ⭐ Updates current status
        'last_seen': stmt.excluded.last_seen,
        # ... other fields
    }
)
db.execute(stmt)
```

**When Updated:**
1. ✅ **Every 60 seconds** - During metrics collection (indirect update)
2. ✅ **Daily at 2:30 AM** - During full interface discovery
3. ✅ **Manual trigger** - When running `trigger_discovery.py`

**Note:** Metrics collection task calls interface discovery internally, which updates PostgreSQL. So effectively updates every 60 seconds when interfaces are polled.

### Used For

1. **Real-Time API Queries** (Fast!)
   ```python
   # routers/interfaces.py:462 - Bulk ISP Status
   SELECT
       d.ip,
       di.isp_provider,
       di.oper_status,     -- ⭐ Current status RIGHT NOW
       di.if_name,
       di.last_seen
   FROM device_interfaces di
   JOIN standalone_devices d ON di.device_id = d.id
   WHERE d.ip IN ('10.195.57.5', '10.195.110.5')
   AND di.isp_provider IS NOT NULL;
   ```

2. **Frontend Badge Display**
   - Monitor.tsx: GREEN/RED badges
   - DeviceDetails.tsx: ISP Links section
   - Query: "Is this ISP link UP or DOWN **right now**?"
   - Response time: ~50ms (indexed query)

3. **Alert Evaluation** (Indirect)
   - Alert engine checks `device.down_since` for device status
   - ISP interface status used for detailed ISP alerts
   - Query: "Are ISP interfaces DOWN?"

4. **Device Management**
   - Show which interfaces exist on device
   - Enable/disable monitoring per interface
   - Track interface configuration changes

### Why PostgreSQL?
- ✅ **Fast indexed lookups** by device_id or IP
- ✅ **Single query** returns status for multiple devices
- ✅ **Relational joins** with device data
- ✅ **ACID transactions** ensure data consistency
- ✅ **Perfect for:** "What is the status RIGHT NOW?"

---

## 2️⃣ VictoriaMetrics - Time-Series Database

### What's Stored
**Metrics with Labels** (Prometheus format)

```promql
# Operational Status (1=UP, 2=DOWN)
interface_oper_status{
    device_id="uuid",
    device_ip="10.195.57.5",
    device_name="Batumi3-881",
    if_index="4",
    if_name="FastEthernet3",
    interface_type="isp",
    isp_provider="magti",
    is_critical="true"
} = 1  # Value: 1=UP, 2=DOWN

# Traffic Counters (64-bit)
interface_in_octets{...} = 123456789     # Bytes received
interface_out_octets{...} = 987654321    # Bytes sent
interface_in_ucast_pkts{...} = 45678     # Packets received
interface_out_ucast_pkts{...} = 34567    # Packets sent

# Error Counters
interface_in_errors{...} = 0             # Inbound errors
interface_out_errors{...} = 0            # Outbound errors
interface_in_discards{...} = 0           # Inbound discards
interface_out_discards{...} = 0          # Outbound discards

# Link Properties
interface_speed{...} = 100000000         # 100 Mbps
interface_admin_status{...} = 1          # Admin UP
```

### Storage Mechanism
**File:** `monitoring/interface_metrics.py:209-243`

```python
async def _store_metrics_victoriametrics(self, metrics: List[Dict]) -> int:
    """Store metrics in VictoriaMetrics"""

    # Convert to Prometheus format
    lines = []
    for m in metrics:
        # Build label string: {label1="value1",label2="value2"}
        label_parts = [f'{k}="{v}"' for k, v in m['labels'].items()]
        label_string = '{' + ','.join(label_parts) + '}'

        # Format: metric_name{labels} value timestamp
        line = f"{m['metric']}{label_string} {m['value']} {m['timestamp']}"
        lines.append(line)

    # Send to VictoriaMetrics
    payload = '\n'.join(lines)
    response = requests.post(
        f"{self.vm_url}/api/v1/import/prometheus",
        data=payload,
        headers={'Content-Type': 'text/plain'}
    )

    # ⭐ Metrics stored in time-series format
```

**When Stored:**
- ✅ **Every 60 seconds** - After SNMP polling completes
- ✅ **Batch insert** - All interfaces sent at once (efficient)

### Used For

1. **Historical Analysis**
   ```promql
   # Was Magti ISP up last week?
   avg_over_time(interface_oper_status{
       device_ip="10.195.57.5",
       isp_provider="magti"
   }[7d])
   ```

2. **Uptime Calculation**
   ```promql
   # ISP uptime percentage over last 24 hours
   (
       count_over_time(interface_oper_status{isp_provider="magti"}[24h] == 1)
       /
       count_over_time(interface_oper_status{isp_provider="magti"}[24h])
   ) * 100
   ```

3. **Traffic Graphs** (Future - Grafana)
   ```promql
   # ISP bandwidth usage over time
   rate(interface_in_octets{isp_provider="magti"}[5m]) * 8

   # Convert bytes/sec to bits/sec for Mbps
   ```

4. **Trend Analysis**
   ```promql
   # Error rate trend
   rate(interface_in_errors[1h])

   # Detect increasing errors over time
   ```

5. **Performance Monitoring**
   ```promql
   # Link utilization percentage
   (rate(interface_in_octets[5m]) * 8 / interface_speed) * 100
   ```

6. **Complex Alerting** (Future)
   ```promql
   # Alert if ISP down for 5+ minutes
   avg_over_time(interface_oper_status{isp_provider="magti"}[5m]) < 1

   # Alert if error rate exceeds threshold
   rate(interface_in_errors[10m]) > 100
   ```

### Why VictoriaMetrics?
- ✅ **Optimized for time-series** - billions of data points
- ✅ **Efficient compression** - stores 60s × 279 interfaces × months of data
- ✅ **Fast range queries** - "last hour, last day, last week"
- ✅ **Prometheus-compatible** - industry standard query language (PromQL)
- ✅ **Perfect for:** "What happened over time?"

---

## 🔄 Complete Data Flow

### Every 60 Seconds:

```
1. ⏰ CELERY BEAT
   ↓
   Triggers: collect_all_interface_metrics_task

2. 📡 SNMP POLLING (interface_metrics.py)
   ↓
   For each .5 router:
   - snmpwalk ifOperStatus.4  → Get Magti status
   - snmpwalk ifOperStatus.5  → Get Silknet status
   - snmpwalk ifHCInOctets.*  → Get traffic counters
   - snmpwalk ifInErrors.*    → Get error counters

3. 💾 DUAL STORAGE
   ↓
   ├─► POSTGRESQL (device_interfaces)
   │   UPDATE device_interfaces
   │   SET oper_status = 1,          -- Current status
   │       last_seen = NOW()
   │   WHERE device_id = X AND if_index = 4
   │
   └─► VICTORIAMETRICS (time-series)
       POST /api/v1/import/prometheus
       interface_oper_status{...,isp_provider="magti"} 1 1698408000000
       interface_in_octets{...,isp_provider="magti"} 123456789 1698408000000
       interface_in_errors{...,isp_provider="magti"} 0 1698408000000
```

### Frontend Query (Every 30 seconds):

```
4. 🌐 FRONTEND (Monitor.tsx)
   ↓
   Fetches: GET /api/v1/interfaces/isp-status/bulk?device_ips=...

5. 🔍 API QUERY (routers/interfaces.py)
   ↓
   Queries: POSTGRESQL only (fast!)
   SELECT oper_status FROM device_interfaces
   WHERE isp_provider IN ('magti', 'silknet')

6. 🎨 DISPLAY
   ↓
   oper_status = 1 → Show GREEN badge
   oper_status = 2 → Show RED badge
```

### Historical Query (When needed):

```
7. 📊 GRAFANA / ANALYSIS
   ↓
   Queries: VICTORIAMETRICS
   avg_over_time(interface_oper_status{...}[24h])

8. 📈 GRAPHS
   ↓
   Display uptime graphs, traffic graphs, error trends
```

---

## 🆚 Comparison Table

| Feature | PostgreSQL | VictoriaMetrics |
|---------|-----------|-----------------|
| **Data Type** | Current state (snapshot) | Time-series (history) |
| **Update Frequency** | Every 60s (UPSERT) | Every 60s (INSERT) |
| **Query Type** | "What's UP now?" | "What happened over time?" |
| **Storage Size** | ~1 row per interface (~300 rows) | Millions of data points |
| **Query Speed** | Very fast (~50ms) | Fast for ranges (~200ms) |
| **Use Case** | Real-time status badges | Graphs, trends, analytics |
| **Frontend Use** | ✅ Monitor badges | ❌ Not used directly |
| **Alert Engine** | ✅ ISP link down detection | ❌ Not used for alerts |
| **Historical Analysis** | ❌ Limited (only last_seen) | ✅ Full history |
| **Data Retention** | Forever (current state only) | Configurable (default: 1 month) |

---

## 💡 Why Both?

### Problem: PostgreSQL Alone
- ❌ No historical data
- ❌ Can't generate uptime graphs
- ❌ Can't analyze trends
- ❌ No time-series aggregations

### Problem: VictoriaMetrics Alone
- ❌ Slow for "current status" queries
- ❌ No relational joins with device data
- ❌ No transactional guarantees
- ❌ Complex queries for simple "is it UP?"

### Solution: Both! (Best of Both Worlds)
- ✅ PostgreSQL: Fast real-time queries
- ✅ VictoriaMetrics: Historical analysis
- ✅ Each database optimized for its use case
- ✅ No compromise on performance

---

## 🔍 Example Queries

### PostgreSQL: "Is Magti UP on 10.195.57.5?"
```sql
SELECT oper_status
FROM device_interfaces
WHERE device_id = (SELECT id FROM standalone_devices WHERE ip = '10.195.57.5')
AND isp_provider = 'magti';

-- Result: 1 (UP) or 2 (DOWN)
-- Query time: ~5ms
```

### VictoriaMetrics: "What was Magti uptime last week?"
```promql
avg_over_time(interface_oper_status{
    device_ip="10.195.57.5",
    isp_provider="magti"
}[7d]) * 100

-- Result: 99.5% (average over 7 days)
-- Query time: ~150ms (processes 10,080 data points)
```

---

## 📝 Summary

**PostgreSQL = "Snapshot Camera"**
- Takes a picture every 60 seconds
- Only keeps the latest picture
- Fast to view the latest picture
- Perfect for: "Show me current status RIGHT NOW"

**VictoriaMetrics = "Security Camera"**
- Records video continuously
- Keeps all historical footage
- Can replay any time period
- Perfect for: "Show me what happened last week"

**Both Together = Complete Monitoring Solution**
- Real-time status monitoring (PostgreSQL)
- Historical analysis and trends (VictoriaMetrics)
- Fast queries for both use cases
- No compromise on performance or features

---

## 🎯 Key Takeaway

**Question:** Where is SNMP data saved?
**Answer:** BOTH places, but for different reasons:

1. **PostgreSQL** - Current ISP link status (UP/DOWN right now)
   - Used by: Frontend badges, API queries, alerts
   - Updated: Every 60 seconds via UPSERT

2. **VictoriaMetrics** - Historical metrics and trends
   - Used by: Grafana dashboards, analytics, reports
   - Updated: Every 60 seconds via batch INSERT

This hybrid architecture gives us:
- ⚡ **Fast** real-time queries (PostgreSQL)
- 📊 **Powerful** historical analysis (VictoriaMetrics)
- 🔧 **Flexible** - Best tool for each job

---

*Last Updated: 2025-10-27*
*Related: ISP-MONITORING-COMPLETE.md, FINAL-IMPLEMENTATION-SUMMARY.md*
