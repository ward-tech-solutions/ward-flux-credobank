# 🔄 FLAPPING DEVICE ANALYSIS - 10.195.110.51

## 📊 Current Situation

**Device:** PING-Call (10.195.110.51)
**Status:** FLAPPING - Device is experiencing intermittent connectivity

### Evidence of Flapping
Based on our investigation, the device shows a clear pattern of going UP and DOWN every 10-20 seconds:

```
09:09:09 ✅ RECOVERED - Device came back online
09:09:19 ❌ went DOWN - Lost connectivity
09:09:29 ✅ RECOVERED - Back online again
09:09:39 ❌ went DOWN - Lost again
```

### Why This Happens
1. **Intermittent Network Issues**: The device has unstable connectivity
2. **NOT a Software Bug**: Our monitoring system is correctly detecting the flapping
3. **Real Infrastructure Problem**: This needs to be addressed at the network/hardware level

## 🎯 Impact of Flapping

### Current Problems
1. **Alert Fatigue**: Generates excessive DOWN/UP alerts every few seconds
2. **Log Noise**: Fills logs with status change messages
3. **Cache Churning**: Triggers cache clearing on every status change
4. **Database Updates**: Constant updates to `down_since` field
5. **User Confusion**: Device appears randomly UP or DOWN depending on when checked

### Performance Impact
- Every status change triggers:
  - Database update
  - Alert creation/resolution
  - Cache clearing
  - WebSocket broadcast
  - Log entry

## 🛠️ IMMEDIATE SOLUTION: Flapping Detection

Since the existing flapping detector is broken (uses old PingResult table), here's a new implementation:

### Implementation Plan

#### 1. Add Flapping Detection Fields to Database
```sql
-- Add to standalone_devices table
ALTER TABLE standalone_devices
ADD COLUMN is_flapping BOOLEAN DEFAULT FALSE,
ADD COLUMN flap_count INTEGER DEFAULT 0,
ADD COLUMN last_flap_detected TIMESTAMP,
ADD COLUMN flapping_since TIMESTAMP;
```

#### 2. Update monitoring/tasks_batch.py
Add flapping detection logic:

```python
def detect_flapping(device, current_status, db):
    """
    Detect if a device is flapping (rapid UP/DOWN transitions)
    Flapping = 3+ status changes in 5 minutes
    """
    # Get recent status changes from database
    five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)

    # Count status changes in last 5 minutes
    # This would need a status_history table or use VictoriaMetrics data

    if device.is_flapping:
        # Already marked as flapping
        if device.flapping_since < five_minutes_ago:
            # Check if still flapping
            if status_changes < 2:  # Less than 2 changes in 5 min
                # No longer flapping
                device.is_flapping = False
                device.flapping_since = None
                device.flap_count = 0
                logger.info(f"🔄 Device {device.name} ({device.ip}) is no longer flapping")
    else:
        # Not currently flapping
        if status_changes >= 3:  # 3+ changes in 5 min
            # Start of flapping detected
            device.is_flapping = True
            device.flapping_since = datetime.utcnow()
            device.flap_count = status_changes
            logger.warning(f"⚠️ FLAPPING DETECTED: {device.name} ({device.ip}) - {status_changes} changes in 5 minutes")
```

#### 3. Suppress Alerts for Flapping Devices
Modify the alert creation logic:

```python
# In monitoring/tasks_batch.py
if not device_obj.is_reachable:
    if not device_obj.is_flapping:  # Only create alert if not flapping
        # Create DOWN alert
        create_device_down_alert(device_obj)
    else:
        logger.info(f"🔄 Skipping alert for flapping device {device_obj.name}")
```

#### 4. Visual Indicator in UI
Add flapping status to API response:

```python
# In routers/devices.py
device_data = {
    "name": device.name,
    "ip": device.ip,
    "ping_status": ping_status,
    "is_flapping": device.is_flapping,  # Add this
    "flap_count": device.flap_count,     # Add this
    # ... other fields
}
```

## 🔧 QUICK FIX (Without Code Changes)

### 1. Disable Alerting for This Device
```sql
-- Temporarily disable alerts for flapping device
UPDATE standalone_devices
SET alert_enabled = false
WHERE ip = '10.195.110.51';
```

### 2. Increase Ping Timeout
```python
# In monitoring/config.py or environment variable
PING_TIMEOUT = 5  # Increase from 2 to 5 seconds
PING_RETRY_COUNT = 3  # Add retries before marking as DOWN
```

### 3. Add Dampening Logic
Don't immediately mark as DOWN - require 2 consecutive failures:

```python
# Simple dampening - require 2 failures
if not is_reachable:
    if device.pending_down_count is None:
        device.pending_down_count = 1
    else:
        device.pending_down_count += 1

    if device.pending_down_count >= 2:
        # Now mark as DOWN
        device.down_since = datetime.utcnow()
else:
    # Reset counter on success
    device.pending_down_count = 0
```

## 📈 Long-term Solutions

### 1. Implement Proper Flapping Detection
- Track status change frequency
- Suppress alerts during flapping periods
- Send single "Device is Flapping" alert
- Resume normal alerting when stable

### 2. Status History Table
```sql
CREATE TABLE device_status_history (
    id SERIAL PRIMARY KEY,
    device_id INTEGER REFERENCES standalone_devices(id),
    status VARCHAR(10),
    timestamp TIMESTAMP DEFAULT NOW(),
    response_time_ms FLOAT
);

-- Index for quick queries
CREATE INDEX idx_status_history_device_time
ON device_status_history(device_id, timestamp DESC);
```

### 3. Intelligent Alert Suppression
- First DOWN: Alert immediately
- Flapping detected: Suppress individual alerts
- Send summary: "Device flapped 15 times in last hour"
- Stable again: Resume normal alerting

### 4. Root Cause Analysis
For device 10.195.110.51 specifically:
- Check physical cable connections
- Verify switch port configuration
- Check for network loops
- Monitor switch logs for port flapping
- Check device power supply stability
- Verify no IP conflicts

## 🚨 IMMEDIATE ACTION ITEMS

### For Operations Team
1. **Check Physical Connection**: Inspect cables and ports for 10.195.110.51
2. **Review Network Logs**: Check switch/router logs for this device
3. **Power Cycle**: Try power cycling the device if possible
4. **Replace Hardware**: Consider replacing network cable or switch port

### For Development Team
1. **Disable Alerts**: Temporarily disable alerts for this device
2. **Implement Dampening**: Add simple 2-failure requirement
3. **Add Flapping Detection**: Implement proper flapping detection
4. **Update UI**: Show flapping indicator in monitor page

## 📊 Monitoring the Flapping

### Check Current Status
```bash
# Database status
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops \
  -c "SELECT name, ip, down_since,
      CASE WHEN down_since IS NULL THEN 'UP' ELSE 'DOWN' END as status
      FROM standalone_devices WHERE ip = '10.195.110.51';"

# Recent metrics from VictoriaMetrics
curl "http://10.30.25.46:8428/api/v1/query?query=device_ping_status{device_ip='10.195.110.51'}"

# Monitor logs for this device
docker logs wardops-worker-monitoring-prod --tail 100 2>&1 | grep "10.195.110.51"
```

### Track Flapping Frequency
```bash
# Count status changes in last hour
docker logs wardops-worker-monitoring-prod --since 1h 2>&1 | \
  grep "10.195.110.51" | grep -E "DOWN|RECOVERED" | wc -l
```

## ✅ Summary

**The Issue**: Device 10.195.110.51 is genuinely flapping - this is NOT a software bug

**The Impact**: Excessive alerts, cache clearing, and database updates

**The Solution**:
1. **Immediate**: Investigate physical network issue
2. **Short-term**: Disable alerts for this specific device
3. **Long-term**: Implement proper flapping detection and suppression

**Key Point**: The monitoring system is working correctly - it's detecting real connectivity issues that need to be fixed at the infrastructure level.

---

*Created: October 26, 2025*
*Issue: Device flapping causing alert spam*
*Resolution: Infrastructure fix needed + flapping detection implementation*