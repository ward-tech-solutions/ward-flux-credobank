# SNMP Polling System - CredoBank Deployment

## Overview

WARD OPS CredoBank deployment includes a comprehensive SNMP polling system that monitors 481 network devices (switches, routers, access points) using SNMP v2c protocol.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      WARD OPS SNMP System                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────────┐  │
│  │   Celery     │───▶│     SNMP     │───▶│  VictoriaMetrics│  │
│  │   Workers    │    │    Poller    │    │   (MetricsDB)   │  │
│  │   (60)       │    │  (pysnmp)    │    │                 │  │
│  └──────────────┘    └──────────────┘    └─────────────────┘  │
│         ▲                    │                      ▲            │
│         │                    │                      │            │
│         │                    ▼                      │            │
│  ┌──────────────┐    ┌──────────────┐             │            │
│  │    Redis     │    │  PostgreSQL  │──────────────┘            │
│  │  (Queue)     │    │  (Devices +  │                           │
│  │              │    │  Credentials)│                           │
│  └──────────────┘    └──────────────┘                           │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## System Components

### 1. PostgreSQL Database
**Purpose**: Stores device information, SNMP credentials, and monitoring configurations

**Key Tables**:
- `standalone_devices` - 875 devices (481 with SNMP, 394 ICMP-only)
- `snmp_credentials` - Encrypted SNMP community strings
- `monitoring_items` - OID polling configurations per device

### 2. VictoriaMetrics (MetricsDB)
**Purpose**: Time-series database for storing SNMP metrics

**Configuration**:
- Port: `8428`
- Retention: 12 months
- Storage: `/victoria-metrics-data`
- Volume: `victoriametrics_prod_data`

**API Endpoints**:
- Write metrics: `POST /api/v1/import/prometheus`
- Query metrics: `GET /api/v1/query`
- Health check: `GET /health`

### 3. Celery Workers (60 concurrent)
**Purpose**: Distributed SNMP polling tasks

**Tasks**:
- `poll_all_devices_snmp` - Every 60 seconds
- `poll_device_snmp` - Individual device polling
- `ping_all_devices` - ICMP monitoring every 30 seconds
- `evaluate_alert_rules` - Alert evaluation every 60 seconds

### 4. SNMP Poller (pysnmp)
**Purpose**: Asynchronous SNMP GET/WALK operations

**Features**:
- SNMPv2c and SNMPv3 support
- Multi-vendor OID library (Cisco, Fortinet, Juniper, HP, MikroTik, etc.)
- Automatic vendor detection via sysObjectID
- Bulk GET operations for efficiency

## SNMP Credentials - CredoBank

**SNMP Version**: v2c
**Community String**: `XoNaz-<h`
**Devices with SNMP**: 481 network devices
  - Switches (Core, Distribution, Access)
  - Routers
  - Access Points
  - Firewalls
  - Load Balancers

**Devices without SNMP**: 394 devices (ICMP-only)
  - PayBoxes
  - ATMs
  - NVRs
  - Cameras
  - Non-SNMP devices

## Monitored OIDs

### Universal OIDs (All Devices)
- **sysDescr** (1.3.6.1.2.1.1.1.0) - Device description
- **sysObjectID** (1.3.6.1.2.1.1.2.0) - Vendor identification
- **sysUpTime** (1.3.6.1.2.1.1.3.0) - Device uptime
- **sysName** (1.3.6.1.2.1.1.5.0) - Hostname
- **ifNumber** (1.3.6.1.2.1.2.1.0) - Interface count

### Vendor-Specific OIDs

#### Cisco Devices
- **CPU Usage** (1.3.6.1.4.1.9.9.109.1.1.1.1.5) - 5-minute average
- **Memory Used** (1.3.6.1.4.1.9.9.48.1.1.1.5) - Bytes
- **Memory Free** (1.3.6.1.4.1.9.9.48.1.1.1.6) - Bytes
- **Temperature** (1.3.6.1.4.1.9.9.13.1.3.1.3) - Celsius

#### Fortinet Devices
- **CPU Usage** (1.3.6.1.4.1.12356.101.4.1.3.0) - Percentage
- **Memory Usage** (1.3.6.1.4.1.12356.101.4.1.4.0) - Percentage
- **Active Sessions** (1.3.6.1.4.1.12356.101.4.1.8.0) - Count
- **VPN Tunnels** (1.3.6.1.4.1.12356.101.12.2.2.1.20) - Status

#### HP/Aruba Switches
- **CPU Usage** (1.3.6.1.4.1.11.2.14.11.5.1.9.6.1.0) - Percentage
- **Total Memory** (1.3.6.1.4.1.11.2.14.11.5.1.1.2.1.1.1.5) - Bytes
- **Free Memory** (1.3.6.1.4.1.11.2.14.11.5.1.1.2.1.1.1.6) - Bytes

## Deployment Steps

### 1. Initial Setup (One-time)

```bash
# On CredoBank server (10.30.25.39)
cd /opt/ward-ops-credobank

# Pull latest code
git pull origin main

# Build containers with VictoriaMetrics
docker-compose -f docker-compose.production-local.yml build

# Start infrastructure (PostgreSQL, Redis, VictoriaMetrics)
docker-compose -f docker-compose.production-local.yml up -d postgres redis victoriametrics

# Wait for services to be healthy
sleep 15

# Run database migrations
docker-compose -f docker-compose.production-local.yml run --rm api python -c "from database import init_db; init_db()"

# Seed database with CredoBank devices
docker-compose -f docker-compose.production-local.yml run --rm api python scripts/export_credobank_seeds.py
```

### 2. Create SNMP Monitoring Items

```bash
# Generate monitoring items for all 481 SNMP devices
docker-compose -f docker-compose.production-local.yml run --rm api python scripts/create_snmp_monitoring_items.py

# Expected output:
# Found 481 devices with SNMP credentials
# Devices processed: 481
# Monitoring items created: 2405 (5 OIDs per device average)
```

### 3. Start SNMP Polling Services

```bash
# Start all services
docker-compose -f docker-compose.production-local.yml up -d

# Verify containers are running
docker ps

# Expected containers:
# - wardops-postgres-prod
# - wardops-redis-prod
# - wardops-victoriametrics-prod
# - wardops-api-prod
# - wardops-worker-prod (60 concurrent workers)
# - wardops-beat-prod
```

### 4. Verify SNMP Polling

```bash
# Check Celery worker logs
docker logs -f wardops-worker-prod

# Expected output:
# [INFO] Polling device: <device-id>
# [INFO] Polled 10.195.50.5 - System Uptime: 12345678
# [INFO] Wrote 5 metrics for device <device-id>

# Check Celery beat logs
docker logs -f wardops-beat-prod

# Expected output:
# [INFO] Scheduler: Sending due task poll-all-devices-snmp
# [INFO] Scheduler: Sending due task ping-all-devices
```

### 5. Verify VictoriaMetrics

```bash
# Check VictoriaMetrics health
curl http://10.30.25.39:8428/health

# Query metrics
curl 'http://10.30.25.39:8428/api/v1/query?query=up'

# Check metric count
curl 'http://10.30.25.39:8428/api/v1/query?query=count({__name__=~".+"})'
```

## Monitoring Dashboard

### Frontend Integration

The frontend automatically displays SNMP status via badges:

**ICMP Badge** (Blue):
- Icon: Activity
- Shown for: ALL devices
- Indicates: ICMP ping monitoring active

**SNMP Badge** (Green):
- Icon: Network
- Shown for: 481 devices with SNMP credentials
- Indicates: SNMP polling active

### Real-time Updates

- Downtime counter updates every second
- Device status refreshes every 30 seconds
- SNMP metrics collected every 60 seconds

## Troubleshooting

### No SNMP data in VictoriaMetrics

**Check 1: Celery workers running**
```bash
docker logs wardops-worker-prod | grep "poll_device_snmp"
```

**Check 2: VictoriaMetrics accessible**
```bash
docker exec wardops-worker-prod curl http://victoriametrics:8428/health
```

**Check 3: SNMP credentials correct**
```bash
docker-compose -f docker-compose.production-local.yml run --rm api python -c "
from database import SessionLocal
from monitoring.models import StandaloneDevice
db = SessionLocal()
device = db.query(StandaloneDevice).filter_by(snmp_community='XoNaz-<h').first()
print(f'Device: {device.name}, IP: {device.ip}, Community: {device.snmp_community}')
"
```

**Check 4: SNMP connectivity**
```bash
# Test SNMP from worker container
docker exec wardops-worker-prod snmpget -v2c -c 'XoNaz-<h' 10.195.50.5 sysDescr.0
```

### SNMP polling slow or timing out

**Increase concurrency**:
Edit `docker-compose.production-local.yml`:
```yaml
celery-worker:
  command: celery -A celery_app worker --loglevel=info --concurrency=100
```

**Check network latency**:
```bash
ping -c 10 10.195.50.5
```

### Metrics not showing in frontend

**Check API logs**:
```bash
docker logs wardops-api-prod | grep -i error
```

**Verify device has monitoring items**:
```bash
docker-compose -f docker-compose.production-local.yml run --rm api python -c "
from database import SessionLocal
from monitoring.models import MonitoringItem
db = SessionLocal()
items = db.query(MonitoringItem).limit(10).all()
for item in items:
    print(f'{item.device_id}: {item.name} - {item.oid}')
"
```

## Performance Metrics

### Expected Load (481 SNMP Devices)

**Polling Rate**:
- 481 devices × 5 OIDs per device = 2,405 SNMP queries per minute
- 144,300 SNMP queries per hour
- 3,463,200 SNMP queries per day

**VictoriaMetrics Storage**:
- ~2,405 data points per minute
- ~3.5 million data points per day
- ~1.27 billion data points per year (with 12-month retention)

**Resource Usage**:
- CPU: 2-4 cores (Celery workers)
- Memory: 4-8 GB (VictoriaMetrics + workers)
- Disk: ~10 GB/month for metrics storage
- Network: ~1-2 Mbps for SNMP traffic

## Maintenance

### Daily Tasks
- Monitor Celery worker health
- Check VictoriaMetrics disk usage
- Review alert notifications

### Weekly Tasks
- Review SNMP polling success rate
- Check for devices with failed SNMP queries
- Update SNMP credentials if changed

### Monthly Tasks
- Clean up old metrics (automatic with 12-month retention)
- Review and optimize OID polling list
- Update vendor-specific OID library

## Security

### SNMP Credentials
- Stored encrypted in PostgreSQL
- Community string: `XoNaz-<h` (SNMPv2c)
- Credentials never logged in plaintext
- Access restricted to Celery workers

### Network Security
- SNMP traffic internal only (10.x.x.x network)
- VictoriaMetrics not exposed externally
- Docker network isolation

## Support

**WARD TECH SOLUTIONS**
- Organization: ward-tech-solutions
- GitHub: https://github.com/ward-tech-solutions/ward-flux-credobank
- Deployment Server: 10.30.25.39 (CredoBank)

For issues or questions, check:
1. Docker container logs
2. VictoriaMetrics query interface
3. Celery worker status
4. Database monitoring_items table
