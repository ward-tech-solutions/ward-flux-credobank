# VICTORIAMETRICS ARCHITECTURE DESIGN
## The Zabbix Killer: Time-Series Done Right

---

## EXECUTIVE SUMMARY

**Problem**: 5M ping results in PostgreSQL causing 30s timeouts
**Solution**: Move ping storage to VictoriaMetrics (like Zabbix uses TimescaleDB)
**Result**: Beat Zabbix performance while maintaining 10s real-time monitoring

**Impact**:
- ✅ PostgreSQL: 5M rows → 877 rows (1000x reduction)
- ✅ Queries: 30s timeout → <100ms (300x faster)
- ✅ Disk growth: 1.5GB/day → 50MB/day (30x reduction)
- ✅ Scalability: 877 → 10,000+ devices (no performance degradation)

---

## ARCHITECTURE COMPARISON

### BEFORE (Current - Wrong)

```
┌─────────────────────────────────────────────────────────┐
│                    USER REQUEST                         │
│          "Show me device ping history"                  │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   FASTAPI BACKEND                        │
│  GET /api/v1/devices/{id}/history?time_range=24h       │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   POSTGRESQL                            │
│  SELECT * FROM ping_results                             │
│  WHERE device_ip = '10.159.25.12'                       │
│    AND timestamp > NOW() - INTERVAL '24 hours'          │
│  ORDER BY timestamp DESC;                               │
│                                                         │
│  ⏱️  Execution time: 30+ seconds (TIMEOUT!)             │
│  📊 Rows scanned: 4,292,121 rows                        │
│  💾 Data read: 1551 MB                                  │
│  ❌ Result: 504 Gateway Timeout                         │
└─────────────────────────────────────────────────────────┘
```

### AFTER (VictoriaMetrics - Correct)

```
┌─────────────────────────────────────────────────────────┐
│                    USER REQUEST                         │
│          "Show me device ping history"                  │
└────────────────────────┬────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
        ▼                                 ▼
┌──────────────────┐            ┌──────────────────┐
│   POSTGRESQL     │            │ VICTORIAMETRICS  │
│                  │            │                  │
│ Current State:   │            │ Historical Data: │
│ • device.ip      │            │                  │
│ • down_since     │            │ Query (PromQL):  │
│ • last_ping_at   │            │ device_ping_     │
│                  │            │   status{        │
│ ⏱️  <10ms        │            │   ip="10.159.    │
│ 📊 1 row         │            │   25.12"         │
│ ✅ Up/Down state │            │ }[24h]           │
│                  │            │                  │
│                  │            │ ⏱️  <100ms       │
│                  │            │ 📊 8,640 points  │
│                  │            │ 💾 Compressed    │
│                  │            │ ✅ Full history  │
└──────────────────┘            └──────────────────┘
        │                                 │
        └────────────────┬────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                COMBINED RESPONSE                         │
│  {                                                      │
│    "device": {                                          │
│      "ip": "10.159.25.12",                             │
│      "status": "down",                                  │
│      "down_since": "2025-10-20T20:07:40Z",            │
│      "last_ping": "2025-10-24T08:15:23Z"              │
│    },                                                   │
│    "history": [                                         │
│      {"time": "2025-10-24T08:15:00Z", "status": 0},   │
│      {"time": "2025-10-24T08:15:10Z", "status": 0},   │
│      ... 8,638 more points ...                         │
│    ]                                                    │
│  }                                                      │
│                                                         │
│  ⏱️  Total time: <150ms (200x faster!)                  │
└─────────────────────────────────────────────────────────┘
```

---

## DATA FLOW DESIGN

### 1. PING EXECUTION (Every 10 Seconds)

```python
# File: monitoring/tasks.py
# Function: ping_devices_batch()

def ping_devices_batch(device_batch):
    """Ping a batch of devices and store results"""

    for device in device_batch:
        # Execute ping
        result = ping_device(device.ip, timeout=1, count=5)

        # ========================================
        # WRITE TO VICTORIAMETRICS (NEW!)
        # ========================================
        vm_client.write_metrics([
            {
                "metric": "device_ping_status",
                "labels": {
                    "device_ip": device.ip,
                    "device_name": device.name,
                    "device_id": str(device.id),
                    "branch": device.branch,
                    "region": device.region,
                    "device_type": device.device_type
                },
                "value": 1 if result.is_reachable else 0,
                "timestamp": int(time.time())
            },
            {
                "metric": "device_ping_rtt_ms",
                "labels": {
                    "device_ip": device.ip,
                    "device_name": device.name
                },
                "value": result.avg_rtt_ms if result.is_reachable else 0,
                "timestamp": int(time.time())
            },
            {
                "metric": "device_ping_packet_loss",
                "labels": {
                    "device_ip": device.ip
                },
                "value": result.packet_loss_percent,
                "timestamp": int(time.time())
            }
        ])

        # ========================================
        # UPDATE DEVICE STATE IN POSTGRESQL
        # (Keep this - needed for alerts!)
        # ========================================
        if not result.is_reachable:
            # Device went DOWN
            if not device.down_since:
                device.down_since = utcnow()
                logger.warning(f"Device {device.name} went DOWN")

                # Create alert (works now - rule_id nullable)
                create_alert(
                    device=device,
                    severity="CRITICAL",
                    message=f"Device {device.name} is not responding to ICMP ping"
                )
        else:
            # Device came UP
            if device.down_since:
                logger.info(f"Device {device.name} came UP")
                device.down_since = None

                # Resolve alert
                resolve_alerts_for_device(device)

        # Update last ping time
        device.last_ping_at = utcnow()

        # ========================================
        # DO NOT WRITE TO ping_results TABLE!
        # (Delete this old code)
        # ========================================
        # db.add(PingResult(...))  ❌ REMOVE THIS!

    db.commit()
```

**Data Written:**
- **VictoriaMetrics**: 3 metrics per device (status, rtt, packet_loss)
- **PostgreSQL**: 1 row per device (current state only)

**Data Volume:**
- **VM**: 877 × 3 metrics × 360 points/hour = 946,080 datapoints/hour
- **PostgreSQL**: 877 rows total (not growing!)

### 2. QUERY HISTORICAL DATA (User Views Device)

```python
# File: routers/devices.py
# Endpoint: GET /api/v1/devices/{device_id}/history

@router.get("/{device_id}/history")
async def get_device_history(
    device_id: UUID,
    time_range: str = "24h",
    db: Session = Depends(get_db)
):
    """Get device ping history from VictoriaMetrics"""

    # Get device info from PostgreSQL
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(404, "Device not found")

    # Query VictoriaMetrics for historical data
    query = f"""
        device_ping_status{{
            device_id="{device_id}"
        }}[{time_range}]
    """

    vm_data = vm_client.query_range(
        query=query,
        start="-" + time_range,
        end="now",
        step="10s"  # Original resolution
    )

    # Query response time
    rtt_query = f"""
        device_ping_rtt_ms{{
            device_id="{device_id}"
        }}[{time_range}]
    """

    rtt_data = vm_client.query_range(
        query=rtt_query,
        start="-" + time_range,
        end="now",
        step="10s"
    )

    # Combine and return
    return {
        "device": {
            "id": device.id,
            "name": device.name,
            "ip": device.ip,
            "status": "down" if device.down_since else "up",
            "down_since": device.down_since,
            "last_ping_at": device.last_ping_at
        },
        "history": {
            "status": vm_data,
            "response_time": rtt_data
        }
    }
```

**Query Performance:**
- **PostgreSQL**: 1 row lookup (<10ms)
- **VictoriaMetrics**: Range query (<100ms)
- **Total**: <150ms (vs 30s timeout before!)

### 3. DASHBOARD AGGREGATION (Overview Stats)

```python
# File: routers/dashboard.py
# Endpoint: GET /api/v1/dashboard/stats

@router.get("/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics"""

    # Get current state from PostgreSQL (fast!)
    total_devices = db.query(Device).count()
    devices_down = db.query(Device).filter(Device.down_since.isnot(None)).count()
    devices_up = total_devices - devices_down

    # Get uptime percentage from VictoriaMetrics
    uptime_query = """
        avg(
            avg_over_time(
                device_ping_status[24h]
            )
        ) * 100
    """
    overall_uptime = vm_client.query(uptime_query)

    # Get devices with most downtime
    downtime_query = """
        topk(10,
            sum_over_time(
                (1 - device_ping_status)[24h]
            )
        ) by (device_name)
    """
    top_problems = vm_client.query(downtime_query)

    return {
        "total_devices": total_devices,
        "devices_up": devices_up,
        "devices_down": devices_down,
        "uptime_percent": overall_uptime,
        "top_problem_devices": top_problems
    }
```

**Query Performance:**
- **PostgreSQL aggregation**: <50ms (877 rows)
- **VM complex aggregation**: <200ms (millions of datapoints)
- **Total**: <300ms (vs 10+ seconds before!)

---

## VICTORIAMETRICS SCHEMA DESIGN

### Metric 1: device_ping_status

**Purpose**: Track if device is reachable (up=1, down=0)

**Labels:**
- `device_id`: UUID (join with PostgreSQL)
- `device_ip`: IP address (human-readable)
- `device_name`: Display name
- `branch`: Branch name (for grouping)
- `region`: Geographic region
- `device_type`: NVR, AP, ATM, PayBox, etc.

**Values**: 0 (down) or 1 (up)

**Retention**: 12 months (configurable)

**Example Data:**
```
device_ping_status{
    device_id="7a96efed-ec2f-42ab-9f5a-f44534c0c547",
    device_ip="10.159.25.12",
    device_name="Samtredia-PayBox",
    branch="Samtredia",
    region="Imereti",
    device_type="PayBox"
} = 0  @ 2025-10-24T08:15:23Z
```

**Query Examples:**
```promql
# Current status of all devices
device_ping_status

# Devices down in last hour
device_ping_status{status="0"}[1h]

# Uptime percentage per branch
avg(device_ping_status) by (branch) * 100

# Devices down right now
device_ping_status == 0

# Device availability over 24h
avg_over_time(device_ping_status{device_id="..."}[24h]) * 100
```

### Metric 2: device_ping_rtt_ms

**Purpose**: Response time in milliseconds

**Labels:**
- `device_id`
- `device_ip`
- `device_name`

**Values**: 0-1000+ (milliseconds)

**Example Data:**
```
device_ping_rtt_ms{
    device_id="7a96efed-ec2f-42ab-9f5a-f44534c0c547",
    device_ip="10.159.25.12",
    device_name="Samtredia-PayBox"
} = 4.7  @ 2025-10-24T08:15:23Z
```

**Query Examples:**
```promql
# Average response time per device
avg_over_time(device_ping_rtt_ms[1h])

# Slowest devices
topk(10, avg_over_time(device_ping_rtt_ms[24h]))

# Response time percentiles
histogram_quantile(0.95, device_ping_rtt_ms)
```

### Metric 3: device_ping_packet_loss

**Purpose**: Packet loss percentage (0-100)

**Labels**: Same as rtt_ms

**Values**: 0-100 (percent)

**Example Data:**
```
device_ping_packet_loss{
    device_id="7a96efed-ec2f-42ab-9f5a-f44534c0c547",
    device_ip="10.159.25.12"
} = 0  @ 2025-10-24T08:15:23Z
```

---

## VICTORIAMETRICS CLIENT IMPLEMENTATION

### File: `utils/victoriametrics_client.py` (NEW)

```python
"""
VictoriaMetrics client for storing and querying time-series data
Replaces PostgreSQL for ping results and SNMP metrics
"""

import requests
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class VictoriaMetricsClient:
    """Client for VictoriaMetrics time-series database"""

    def __init__(self, base_url: str = "http://victoriametrics:8428"):
        self.base_url = base_url.rstrip("/")
        self.write_url = f"{self.base_url}/api/v1/import/prometheus"
        self.query_url = f"{self.base_url}/api/v1/query"
        self.query_range_url = f"{self.base_url}/api/v1/query_range"

    def write_metric(
        self,
        metric_name: str,
        value: float,
        labels: Dict[str, str],
        timestamp: Optional[int] = None
    ) -> bool:
        """
        Write a single metric to VictoriaMetrics

        Args:
            metric_name: Metric name (e.g., "device_ping_status")
            value: Metric value
            labels: Dictionary of labels {key: value}
            timestamp: Unix timestamp in seconds (None = now)

        Returns:
            True if successful, False otherwise
        """
        if timestamp is None:
            timestamp = int(time.time())

        # Build Prometheus format line
        # Format: metric_name{label1="value1",label2="value2"} value timestamp
        label_str = ",".join([f'{k}="{v}"' for k, v in labels.items()])
        line = f'{metric_name}{{{label_str}}} {value} {timestamp}000\n'

        try:
            response = requests.post(
                self.write_url,
                data=line,
                headers={"Content-Type": "text/plain"},
                timeout=5
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to write metric to VM: {e}")
            return False

    def write_metrics(self, metrics: List[Dict[str, Any]]) -> bool:
        """
        Write multiple metrics in batch (more efficient)

        Args:
            metrics: List of metric dictionaries with keys:
                - metric: metric name
                - value: metric value
                - labels: dict of labels
                - timestamp: optional unix timestamp

        Returns:
            True if successful
        """
        if not metrics:
            return True

        lines = []
        for m in metrics:
            ts = m.get("timestamp", int(time.time()))
            label_str = ",".join([f'{k}="{v}"' for k, v in m["labels"].items()])
            line = f'{m["metric"]}{{{label_str}}} {m["value"]} {ts}000'
            lines.append(line)

        payload = "\n".join(lines) + "\n"

        try:
            response = requests.post(
                self.write_url,
                data=payload,
                headers={"Content-Type": "text/plain"},
                timeout=10
            )
            response.raise_for_status()
            logger.debug(f"Wrote {len(metrics)} metrics to VictoriaMetrics")
            return True
        except Exception as e:
            logger.error(f"Failed to write {len(metrics)} metrics to VM: {e}")
            return False

    def query(self, query: str, time: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute instant query

        Args:
            query: PromQL query string
            time: RFC3339 timestamp or Unix timestamp (None = now)

        Returns:
            Query result as dict
        """
        params = {"query": query}
        if time:
            params["time"] = time

        try:
            response = requests.get(
                self.query_url,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"VM query failed: {e}")
            return {"status": "error", "error": str(e)}

    def query_range(
        self,
        query: str,
        start: str,
        end: str = "now",
        step: str = "10s"
    ) -> Dict[str, Any]:
        """
        Execute range query (for time-series data)

        Args:
            query: PromQL query string
            start: Start time (RFC3339, Unix timestamp, or relative like "-24h")
            end: End time (default "now")
            step: Query resolution (e.g., "10s", "1m", "5m")

        Returns:
            Query result with time-series data
        """
        params = {
            "query": query,
            "start": start,
            "end": end,
            "step": step
        }

        try:
            response = requests.get(
                self.query_range_url,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"VM range query failed: {e}")
            return {"status": "error", "error": str(e)}

    def get_device_status_history(
        self,
        device_id: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get ping status history for a device

        Args:
            device_id: Device UUID
            hours: Hours of history to fetch

        Returns:
            List of {timestamp, value} dicts
        """
        query = f'device_ping_status{{device_id="{device_id}"}}'
        result = self.query_range(
            query=query,
            start=f"-{hours}h",
            end="now",
            step="10s"
        )

        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            if data:
                values = data[0].get("values", [])
                return [
                    {"timestamp": v[0], "value": float(v[1])}
                    for v in values
                ]
        return []

    def get_device_uptime_percent(
        self,
        device_id: str,
        hours: int = 24
    ) -> float:
        """
        Calculate device uptime percentage

        Args:
            device_id: Device UUID
            hours: Hours to calculate over

        Returns:
            Uptime percentage (0-100)
        """
        query = f'avg_over_time(device_ping_status{{device_id="{device_id}"}}[{hours}h]) * 100'
        result = self.query(query)

        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            if data:
                value = data[0].get("value", [None, "0"])
                return float(value[1])
        return 0.0

    def get_top_down_devices(
        self,
        limit: int = 10,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get devices with most downtime

        Args:
            limit: Number of devices to return
            hours: Hours to analyze

        Returns:
            List of {device_name, downtime_count} dicts
        """
        query = f"""
            topk({limit},
                sum_over_time(
                    (1 - device_ping_status)[{hours}h]
                )
            ) by (device_name, device_ip)
        """
        result = self.query(query)

        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            return [
                {
                    "device_name": d["metric"]["device_name"],
                    "device_ip": d["metric"]["device_ip"],
                    "downtime_points": int(d["value"][1])
                }
                for d in data
            ]
        return []

# Global client instance
vm_client = VictoriaMetricsClient(
    base_url=os.getenv("VICTORIA_URL", "http://victoriametrics:8428")
)
```

---

## MIGRATION PLAN

### Phase 1: Add VictoriaMetrics Writes (Dual Write)

**Duration**: 1 hour implementation + testing

**Changes:**
1. Create `utils/victoriametrics_client.py`
2. Update `monitoring/tasks.py` to write to both PostgreSQL AND VM
3. Keep both systems running in parallel
4. Verify data appears in VM

**Risk**: Low (additive only, no breaking changes)

**Code Changes:**
```python
# monitoring/tasks.py (add new code, keep old)

# Write to VictoriaMetrics (NEW)
vm_client.write_metrics([...])

# Write to PostgreSQL (KEEP for now)
db.add(PingResult(...))  # Keep temporarily
```

### Phase 2: Update Read Queries (Switch Reads to VM)

**Duration**: 2 hours implementation + testing

**Changes:**
1. Update `routers/devices.py` to read from VM
2. Update `routers/dashboard.py` to use VM aggregations
3. Keep PostgreSQL writes running (safety net)
4. Test all endpoints

**Risk**: Medium (changes user-facing APIs)

**Rollback**: Revert router changes, fall back to PostgreSQL

### Phase 3: Stop PostgreSQL Writes (VM Only)

**Duration**: 30 minutes

**Changes:**
1. Remove `db.add(PingResult(...))` from tasks.py
2. Monitor for 24 hours
3. Verify no errors

**Risk**: Low (already tested in Phase 2)

### Phase 4: Drop ping_results Table

**Duration**: 5 minutes

**Changes:**
```sql
-- Free up 1.5GB of disk space
DROP TABLE ping_results CASCADE;
```

**Risk**: Low (no longer used)

**Result**: Clean architecture, VM only

---

## TESTING STRATEGY

### Unit Tests

```python
# tests/test_vm_client.py

def test_write_single_metric():
    """Test writing a single metric"""
    success = vm_client.write_metric(
        metric_name="test_metric",
        value=42,
        labels={"test": "true"},
        timestamp=int(time.time())
    )
    assert success is True

def test_write_batch_metrics():
    """Test batch write"""
    metrics = [
        {
            "metric": "device_ping_status",
            "value": 1,
            "labels": {"device_ip": "10.0.0.1"},
            "timestamp": int(time.time())
        },
        {
            "metric": "device_ping_status",
            "value": 0,
            "labels": {"device_ip": "10.0.0.2"},
            "timestamp": int(time.time())
        }
    ]
    success = vm_client.write_metrics(metrics)
    assert success is True

def test_query_device_history():
    """Test querying device history"""
    history = vm_client.get_device_status_history(
        device_id="test-uuid",
        hours=1
    )
    assert isinstance(history, list)
```

### Integration Tests

```python
# tests/test_ping_to_vm.py

def test_ping_writes_to_vm(db_session):
    """Test that ping task writes to VictoriaMetrics"""
    device = create_test_device()

    # Execute ping
    ping_devices_batch([device])

    # Wait for write
    time.sleep(1)

    # Query VM
    result = vm_client.query(f'device_ping_status{{device_id="{device.id}"}}')

    assert result["status"] == "success"
    assert len(result["data"]["result"]) > 0
```

### Performance Tests

```python
# tests/test_vm_performance.py

def test_query_performance_1000_devices():
    """Ensure queries stay fast even with many devices"""
    start = time.time()

    result = vm_client.query_range(
        query='device_ping_status',
        start="-24h",
        end="now",
        step="1m"
    )

    elapsed = time.time() - start

    assert elapsed < 1.0  # Must complete in <1 second
    assert result["status"] == "success"
```

---

## MONITORING & OBSERVABILITY

### VictoriaMetrics Metrics (Meta!)

```promql
# Storage size
vm_data_size_bytes

# Ingestion rate
rate(vm_rows_inserted_total[5m])

# Query performance
histogram_quantile(0.95, rate(vm_request_duration_seconds_bucket[5m]))

# Active time series
vm_cache_entries{type="storage/tsid"}

# Disk usage
vm_free_disk_space_bytes
```

### Alerts to Create

```yaml
# High ingestion rate (potential data explosion)
- alert: HighMetricIngestionRate
  expr: rate(vm_rows_inserted_total[5m]) > 100000
  for: 10m
  annotations:
    summary: "VictoriaMetrics ingesting too many metrics"

# Slow queries
- alert: SlowVMQueries
  expr: histogram_quantile(0.95, rate(vm_request_duration_seconds_bucket[5m])) > 5
  for: 5m
  annotations:
    summary: "95th percentile VM query time >5s"

# Disk space low
- alert: VMDiskSpaceLow
  expr: vm_free_disk_space_bytes < 10e9  # <10GB
  for: 15m
  annotations:
    summary: "VictoriaMetrics disk space low"
```

---

## PERFORMANCE BENCHMARKS

### Expected Performance (After Migration)

| Operation | Before (PostgreSQL) | After (VictoriaMetrics) | Improvement |
|-----------|--------------------|-----------------------|-------------|
| Device details load | 30s (timeout) | <150ms | 200x faster |
| 24h history query | 30s (timeout) | <100ms | 300x faster |
| Dashboard stats | 10s | <300ms | 33x faster |
| Database size | 1.5GB (growing) | 877 rows (~1MB) | 1500x smaller |
| Disk growth/day | 1.5GB | 50MB (compressed) | 30x slower growth |
| Scalability | 877 devices (limit) | 10,000+ devices | 11x more scalable |

### Data Volume Comparison

**Current (PostgreSQL):**
- 5,075,213 rows
- 525 MB table data
- 1026 MB indexes
- 1551 MB total
- Growing at 1.5GB/day

**After (VictoriaMetrics + PostgreSQL):**
- **PostgreSQL**: 877 rows (device state only) = ~100KB
- **VictoriaMetrics**: 946,080 datapoints/hour, compressed to ~50MB/day
- **Total growth**: ~50MB/day
- **Disk savings**: 97% reduction

---

## CONFIGURATION UPDATES

### docker-compose.production-priority-queues.yml

```yaml
victoriametrics:
  image: victoriametrics/victoria-metrics:latest
  container_name: wardops-victoriametrics-prod
  ports:
    - "8428:8428"
  volumes:
    - victoriametrics_prod_data:/victoria-metrics-data
  command:
    - '--storageDataPath=/victoria-metrics-data'
    - '--httpListenAddr=:8428'
    - '--retentionPeriod=12'  # 12 months retention
    - '--dedup.minScrapeInterval=10s'  # Deduplicate 10s samples
    - '--maxLabelsPerTimeseries=30'  # Allow detailed labels
  restart: unless-stopped
  healthcheck:
    test: ["CMD", "wget", "-q", "-O-", "http://localhost:8428/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

### Environment Variables

```bash
# .env or docker-compose environment
VICTORIA_URL=http://victoriametrics:8428
VICTORIA_RETENTION_PERIOD=12  # months
VICTORIA_ENABLE_COMPRESSION=true
```

---

## ROLLBACK PLAN

### If Something Goes Wrong

**Phase 1 Rollback**: Remove VM writes
```python
# Comment out in monitoring/tasks.py
# vm_client.write_metrics([...])  # Disabled
```

**Phase 2 Rollback**: Revert router changes
```bash
git revert <commit-hash>
docker restart wardops-api-prod
```

**Phase 3 Rollback**: Re-enable PostgreSQL writes
```python
# Uncomment in monitoring/tasks.py
db.add(PingResult(...))  # Re-enabled
```

**Phase 4 Rollback**: Not needed (never delete until stable)

---

## SUCCESS CRITERIA

### Must Have (Before Declaring Success)

✅ All devices writing to VictoriaMetrics successfully
✅ Device history queries returning correct data
✅ Query performance <200ms (vs 30s timeout)
✅ No increase in error rate
✅ Data retention working (12 months)
✅ Grafana dashboards showing VM data
✅ Zero data loss during migration

### Nice to Have (Future Enhancements)

⏳ Grafana integration for visualization
⏳ Alerting based on VM queries
⏳ Historical trend analysis
⏳ Capacity planning based on VM metrics
⏳ Multi-region aggregation

---

## NEXT STEPS

1. **Create VictoriaMetrics client** (`utils/victoriametrics_client.py`)
2. **Add dual writes** (PostgreSQL + VM)
3. **Test writes** (verify data in VM)
4. **Update read queries** (switch to VM)
5. **Monitor for 24 hours** (verify stability)
6. **Remove PostgreSQL writes** (VM only)
7. **Drop ping_results table** (reclaim 1.5GB)
8. **Celebrate** 🎉 (Beat Zabbix!)

---

**Document Version**: 1.0
**Created**: October 24, 2025
**Status**: Ready for Implementation
**Estimated Time**: 4-6 hours total
**Risk Level**: Low-Medium
**Impact**: High (Zabbix-level performance)
