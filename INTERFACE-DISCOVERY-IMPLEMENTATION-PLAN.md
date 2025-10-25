# Interface Discovery & Monitoring Implementation Plan

**Project:** Ward Ops - Credobank Network Monitoring System
**Date:** 2025-10-26
**Author:** Claude AI (Implementation Planning Session)
**Target Environment:** Credobank Production Server (Flux)

---

## Table of Contents

1. [Current Environment Overview](#current-environment-overview)
2. [Project Objectives](#project-objectives)
3. [Architecture Design](#architecture-design)
4. [Implementation Phases](#implementation-phases)
5. [Database Schema](#database-schema)
6. [Code Components](#code-components)
7. [Deployment Instructions](#deployment-instructions)
8. [Testing & Validation](#testing--validation)
9. [Monitoring & Alerts](#monitoring--alerts)
10. [Troubleshooting Guide](#troubleshooting-guide)

---

## Current Environment Overview

### Server Details

**Production Server:**
- **Hostname:** Flux
- **IP Address:** 10.30.25.46
- **Public Access:** http://flux.credobank.ge:5001
- **OS:** Ubuntu 24.04 LTS (Noble)
- **Location:** Credobank Data Center, Tbilisi, Georgia (GMT+4)
- **Access:** SSH only (no direct server access, all operations via SSH as `wardops` user)

**Project Location:**
```
Server Path: /home/wardops/ward-flux-credobank
Local Dev: /Users/g.jalabadze/Desktop/WARD OPS/ward-ops-credobank
Git Repo: https://github.com/ward-tech-solutions/ward-flux-credobank.git
Branch: main
```

### Docker Infrastructure

**Docker Compose File:**
```
docker-compose.production-priority-queues.yml
```

**Active Containers:**
```
wardops-api-prod              - FastAPI application (port 5001)
wardops-postgres-prod         - PostgreSQL 15 database (port 5433)
wardops-redis-prod            - Redis cache (port 6380)
wardops-victoriametrics-prod  - VictoriaMetrics TSDB (port 8428)
wardops-worker-monitoring-prod - Celery worker (monitoring queue)
wardops-worker-snmp-prod      - Celery worker (SNMP queue)
wardops-worker-alerts-prod    - Celery worker (alerts queue)
wardops-worker-maintenance-prod - Celery worker (maintenance queue)
wardops-beat-prod             - Celery beat scheduler
```

**Container Network:**
- Network: `bridge` mode with NAT
- Internal network: `172.18.0.0/16`
- Containers access external networks via host IP `10.30.25.46`

### Database Details

**PostgreSQL:**
- **Container:** `wardops-postgres-prod`
- **Version:** PostgreSQL 15-alpine
- **Database:** `ward_ops`
- **User:** `ward_admin`
- **Password:** `ward_admin_password`
- **Port:** 5433 (external), 5432 (internal)
- **Access:** `docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops`

**Current Schema:**
- `standalone_devices` - 876 devices (routers, switches, access points, ATMs, NVRs, servers)
- `monitoring_items` - 2,385 SNMP monitoring items
- `monitoring_profiles` - Active monitoring configuration
- `alert_history` - Historical alerts
- `ping_results` - ICMP ping results (30-day retention)

**Redis:**
- **Container:** `wardops-redis-prod`
- **Password:** `redispass`
- **Memory Limit:** 1GB with LRU eviction
- **TTL:** 30 seconds for device list cache

**VictoriaMetrics:**
- **Container:** `wardops-victoriametrics-prod`
- **Endpoint:** http://localhost:8428
- **Storage:** `/victoriametrics-data`
- **Current Metrics:** `device_ping_*` (ICMP ping data for 876 devices)
- **Retention:** Default (indefinite, manage via storage limits)

### Network Topology

**Device Network Ranges:**
```
10.195.0.0/16 - Credobank network devices
  .5 = Routers (e.g., 10.195.136.5, 10.195.91.5)
  .245-.255 = Switches (e.g., 10.195.136.245, 10.195.91.245)
  .252 = Ruckus Wireless APs (e.g., 10.195.136.252)
  .1-.244 = Other devices (ATMs, NVRs, servers)
```

**Example Devices:**
- `10.195.10.5` - Saburtalo1 (Switch)
- `10.195.91.245` - Isani-1111 (Switch)
- `10.195.29.245` - Khobi-881 (Router)

### SNMP Configuration

**SNMP Community String:** `XoNaz-<h`
**SNMP Version:** v2c
**SNMP Port:** 161 (UDP)

**Current Issue:**
- ❌ Cisco devices have SNMP ACL configured
- ❌ Only Zabbix server IP is whitelisted
- ❌ Flux server IP (10.30.25.46) is **NOT whitelisted**
- ✅ **Action Required:** Network admins must whitelist 10.30.25.46

**Verification:**
```bash
# SNMP is reachable (UDP port 161 open)
nc -zvu 10.195.91.245 161  # Success

# But SNMP requests timeout (ACL blocking)
snmpwalk -v2c -c 'XoNaz-<h' 10.195.91.245 1.3.6.1.2.1.1.1.0  # Timeout

# tcpdump shows requests going OUT but NO responses coming back
tcpdump -i any -n port 161
```

### Current Monitoring Status

**Working:**
- ✅ ICMP ping monitoring (876 devices, 30-second interval)
- ✅ Device up/down detection
- ✅ Alert generation and history
- ✅ VictoriaMetrics integration (ping metrics only)
- ✅ Redis caching for device lists

**Not Working:**
- ❌ SNMP monitoring (ACL blocked)
- ❌ Interface discovery
- ❌ Bandwidth monitoring
- ❌ CPU/Memory monitoring
- ❌ Network topology mapping

**Monitoring Items Per Device:**
Currently only 5 basic SNMP items configured:
1. System Description (1.3.6.1.2.1.1.1.0)
2. System Object ID (1.3.6.1.2.1.1.2.0)
3. System Uptime (1.3.6.1.2.1.1.3.0)
4. System Name (1.3.6.1.2.1.1.5.0)
5. Interface Count (1.3.6.1.2.1.2.1.0)

**Missing:** Interface-level monitoring (ifDescr, ifOperStatus, traffic, errors, etc.)

---

## Project Objectives

### Primary Goals

1. **Interface Discovery**
   - Automatically discover all network interfaces on routers and switches
   - Parse interface descriptions to identify purpose (ISP, trunk, access, etc.)
   - Store interface metadata in PostgreSQL
   - Store interface metrics in VictoriaMetrics

2. **ISP Link Monitoring**
   - Identify ISP uplink interfaces (Magti, Silknet, Veon, Beeline, Geocell)
   - Monitor ISP interface status in real-time
   - Generate critical alerts when ISP links go down
   - Differentiate between single ISP failure (backup working) vs total outage

3. **Network Topology**
   - Build topology relationships between devices and interfaces
   - Visualize network topology in frontend
   - Enable impact analysis (which devices affected when interface goes down)

4. **Performance Monitoring**
   - Track interface bandwidth utilization
   - Monitor interface errors and discards
   - Detect interface flapping
   - Alert on high bandwidth utilization or error rates

### Business Value

**Problem Statement:**
- Currently only monitoring device availability (ping up/down)
- No visibility into interface-level issues
- When ISP link fails, no specific alert (just "device down" on downstream devices)
- No way to visualize network topology
- Cannot identify root cause of outages (ISP vs local vs equipment)

**Solution Benefits:**
- **Faster incident response:** Know immediately which ISP link failed
- **Proactive monitoring:** Detect interface errors before complete failure
- **Better visibility:** See entire network topology at a glance
- **Root cause analysis:** Quickly identify if outage is ISP, switch, or router
- **Capacity planning:** Track bandwidth utilization trends

---

## Architecture Design

### Data Storage Strategy (Hybrid Approach)

**Why Hybrid?**
- PostgreSQL: Excellent for relational data, complex queries, metadata
- VictoriaMetrics: Optimized for time-series data, handles millions of metrics/second
- Separation of concerns: metadata vs metrics

#### PostgreSQL Stores:

**Interface Metadata (Updated every 1 hour during discovery):**
- Interface inventory (if_index, if_name, if_descr, if_alias)
- Interface classification (ISP, trunk, access, server, branch)
- ISP provider identification (Magti, Silknet, etc.)
- Critical interface flags
- Topology relationships (which interface connects to which device)
- Discovery timestamps (discovered_at, last_seen)

**Write Load:**
```
876 devices × 24 interfaces/device × 1 discovery/hour = 21,024 writes/hour
= ~6 writes/second (very light for PostgreSQL)
```

**Query Patterns:**
```sql
-- Fast lookups for specific use cases
SELECT * FROM device_interfaces WHERE interface_type = 'isp';
SELECT * FROM device_interfaces WHERE is_critical = true;
SELECT * FROM device_interfaces WHERE device_id = '...';
```

#### VictoriaMetrics Stores:

**Time-Series Metrics (Updated every 30-60 seconds):**
- Interface operational status (up/down over time)
- Traffic in/out (bytes, packets)
- Errors in/out (errors, discards)
- Bandwidth utilization percentage
- Interface speed changes
- Admin status changes

**Write Load:**
```
876 devices × 24 interfaces × 10 metrics × 60 polls/hour = 12,614,400 data points/hour
= ~3,500 writes/second (VictoriaMetrics handles this easily)
```

**Query Patterns:**
```promql
# Current interface status
interface_oper_status{device="Saburtalo1", if_name="Gi0/0/0"}

# ISP interface status
interface_oper_status{interface_type="isp", isp_provider="magti"}

# Interface traffic over time
rate(interface_traffic_in_bytes[5m])

# High error rate detection
rate(interface_errors_in[5m]) > 100
```

### Performance Comparison

| Metric | PostgreSQL Only | Hybrid (PG + VM) |
|--------|----------------|------------------|
| **Writes/second** | ~3,500 (metric writes) | ~6 (metadata only) |
| **Query speed (metadata)** | Fast (100ms) | Fast (100ms) |
| **Query speed (time-series)** | Slow (1-5s) | Fast (50-200ms) |
| **Storage efficiency** | Low (1x) | High (10x compression) |
| **Database load** | High (80-90% CPU) | Low (<5% CPU) |
| **Scalability** | Limited (5k devices max) | Excellent (50k+ devices) |

**Conclusion:** Hybrid approach is optimal for this use case.

---

## Implementation Phases

### Phase 1: Foundation (Week 1)

**Objective:** Database schema, basic interface discovery, data storage

**Tasks:**
1. Create PostgreSQL migration for `device_interfaces` table
2. Implement interface description parser with regex patterns
3. Create Celery task for periodic interface discovery (SNMP walk)
4. Store discovered interfaces in PostgreSQL
5. Test with 3-5 devices manually

**Deliverables:**
- [ ] Migration file: `migrations/add_device_interfaces_table.sql`
- [ ] Parser module: `monitoring/interface_parser.py`
- [ ] Discovery task: `monitoring/tasks_interface_discovery.py`
- [ ] Unit tests for parser

**Success Criteria:**
- Successfully discover interfaces on test devices
- Correctly classify ISP interfaces from descriptions
- Store interface metadata in PostgreSQL
- Run discovery task via Celery beat every 1 hour

---

### Phase 2: Metrics & Monitoring (Week 2)

**Objective:** Send interface metrics to VictoriaMetrics, create alerts

**Tasks:**
1. Create SNMP polling task for interface metrics (every 60s)
2. Send interface metrics to VictoriaMetrics
3. Create alert rules for critical interfaces
4. Build API endpoint: `GET /api/v1/devices/{id}/interfaces`
5. Test ISP interface down alerting

**Deliverables:**
- [ ] Metrics task: `monitoring/tasks_interface_metrics.py`
- [ ] Alert rules: Database entries for interface alerts
- [ ] API endpoint: `routers/interfaces.py`
- [ ] Integration tests

**Success Criteria:**
- Interface metrics visible in VictoriaMetrics
- Alerts triggered when ISP interface goes down
- API returns interface list with current status
- Dashboard shows ISP interface status widget

---

### Phase 3: Topology & Visualization (Week 3)

**Objective:** Build topology relationships, create frontend visualization

**Tasks:**
1. Implement LLDP/CDP neighbor discovery
2. Build topology relationships in database
3. Create frontend topology page (React component)
4. Add interface detail modal
5. Implement impact analysis queries

**Deliverables:**
- [ ] Topology discovery: Enhancement to discovery task
- [ ] Frontend component: `frontend/src/pages/Topology.tsx`
- [ ] API endpoints: `GET /api/v1/topology`, `GET /api/v1/devices/{id}/topology`
- [ ] Documentation: User guide for topology view

**Success Criteria:**
- Topology map shows devices and their connections
- Click on device shows interfaces with status
- Interface status updates in real-time (or near real-time)
- Can identify affected devices when interface goes down

---

## Database Schema

### Main Table: device_interfaces

```sql
-- ============================================================================
-- Device Interfaces Table
-- Stores discovered network interfaces from routers and switches
-- ============================================================================

CREATE TABLE IF NOT EXISTS device_interfaces (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Device relationship
    device_id UUID NOT NULL REFERENCES standalone_devices(id) ON DELETE CASCADE,

    -- SNMP interface data (from IF-MIB)
    if_index INTEGER NOT NULL,                    -- Interface index from SNMP
    if_name VARCHAR(255),                         -- Interface name (Gi0/0/0, Fa0/1, etc.)
    if_descr VARCHAR(255),                        -- Interface description from ifDescr
    if_alias VARCHAR(500),                        -- User description from ifAlias (THIS HAS ISP INFO!)
    if_type VARCHAR(100),                         -- Interface type (ethernetCsmacd, etc.)
    if_mtu INTEGER,                               -- Maximum transmission unit

    -- Parsed/Classified data (computed from if_alias/if_descr)
    interface_type VARCHAR(50),                   -- isp, trunk, access, server_link, branch_link, unknown
    isp_provider VARCHAR(50),                     -- magti, silknet, veon, geocell, beeline (if ISP interface)
    is_critical BOOLEAN DEFAULT false,            -- Mark ISP and critical uplinks

    -- Interface configuration (from SNMP)
    admin_status INTEGER,                         -- 1=up, 2=down, 3=testing
    oper_status INTEGER,                          -- 1=up, 2=down, 3=testing, 4=unknown, 5=dormant, 6=notPresent, 7=lowerLayerDown
    speed BIGINT,                                 -- Interface speed in bps (bits per second)
    duplex VARCHAR(20),                           -- full, half, auto (from EtherLike-MIB)

    -- Topology relationships (populated by LLDP/CDP discovery)
    connected_to_device_id UUID REFERENCES standalone_devices(id) ON DELETE SET NULL,
    connected_to_interface_id UUID REFERENCES device_interfaces(id) ON DELETE SET NULL,

    -- MAC address (for layer 2 topology)
    mac_address VARCHAR(17),                      -- Format: AA:BB:CC:DD:EE:FF

    -- Metadata
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_status_change TIMESTAMP WITH TIME ZONE,  -- When oper_status last changed
    enabled BOOLEAN DEFAULT true,                 -- Set to false if interface no longer exists

    -- Ensure one interface per device
    CONSTRAINT unique_device_interface UNIQUE(device_id, if_index)
);

-- Indexes for performance
CREATE INDEX idx_device_interfaces_device ON device_interfaces(device_id);
CREATE INDEX idx_device_interfaces_type ON device_interfaces(interface_type);
CREATE INDEX idx_device_interfaces_isp ON device_interfaces(isp_provider) WHERE isp_provider IS NOT NULL;
CREATE INDEX idx_device_interfaces_critical ON device_interfaces(is_critical) WHERE is_critical = true;
CREATE INDEX idx_device_interfaces_oper_status ON device_interfaces(oper_status);
CREATE INDEX idx_device_interfaces_last_seen ON device_interfaces(last_seen);
CREATE INDEX idx_device_interfaces_topology ON device_interfaces(connected_to_device_id) WHERE connected_to_device_id IS NOT NULL;

-- Comments for documentation
COMMENT ON TABLE device_interfaces IS 'Network interfaces discovered via SNMP from routers and switches';
COMMENT ON COLUMN device_interfaces.if_alias IS 'User-configured description containing ISP name, purpose, etc. (e.g., Magti_Internet, Trunk_to_CoreSwitch)';
COMMENT ON COLUMN device_interfaces.interface_type IS 'Classified interface type: isp, trunk, access, server_link, branch_link, unknown';
COMMENT ON COLUMN device_interfaces.is_critical IS 'Mark as true for ISP uplinks and critical trunk ports';
```

### Supporting Tables

```sql
-- ============================================================================
-- Interface Alert Rules
-- Alert rules specific to interface monitoring
-- ============================================================================

CREATE TABLE IF NOT EXISTS interface_alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Scope
    interface_type VARCHAR(50),                   -- Apply to specific type (isp, trunk, etc.)
    is_critical_only BOOLEAN DEFAULT false,       -- Apply only to critical interfaces

    -- Condition
    metric VARCHAR(100) NOT NULL,                 -- oper_status, traffic_in_bps, error_rate, etc.
    operator VARCHAR(20) NOT NULL,                -- eq, ne, gt, lt, gte, lte
    threshold NUMERIC,                            -- Threshold value
    duration_seconds INTEGER DEFAULT 60,          -- Must be true for this long

    -- Alert properties
    severity VARCHAR(20) NOT NULL,                -- info, warning, error, critical
    message_template TEXT,                        -- Template with variables: {device_name}, {if_name}, {isp_provider}

    -- Metadata
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CHECK (severity IN ('info', 'warning', 'error', 'critical'))
);

-- Example rules
INSERT INTO interface_alert_rules (name, description, interface_type, metric, operator, threshold, duration_seconds, severity, message_template) VALUES
('ISP Interface Down', 'Alert when ISP uplink interface goes down', 'isp', 'oper_status', 'eq', 2, 60, 'critical',
 'CRITICAL: ISP link {if_name} ({isp_provider}) on {device_name} is DOWN'),

('High Interface Errors', 'Alert when interface error rate exceeds 100 errors/sec', NULL, 'error_rate', 'gt', 100, 300, 'warning',
 'WARNING: High error rate on {device_name}:{if_name} - {value} errors/sec'),

('Interface Bandwidth Saturation', 'Alert when interface utilization exceeds 90%', NULL, 'bandwidth_utilization_pct', 'gt', 90, 300, 'warning',
 'WARNING: Interface {device_name}:{if_name} bandwidth utilization at {value}%');
```

---

## Code Components

### 1. Interface Description Parser

**File:** `monitoring/interface_parser.py`

```python
"""
Interface Description Parser

Parses interface descriptions (ifAlias) to classify interfaces and extract metadata.
Supports multiple naming conventions and patterns.
"""

import re
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class InterfaceClassification:
    """Result of interface classification"""
    interface_type: str  # isp, trunk, access, server_link, branch_link, unknown
    isp_provider: Optional[str] = None  # magti, silknet, veon, geocell, beeline
    is_critical: bool = False
    confidence: float = 0.0  # 0.0 to 1.0


class InterfaceParser:
    """
    Parse and classify network interface descriptions

    Handles various description formats:
    - Magti_Internet, internet_magti, INTERNET-MAGTI
    - Silknet_Internet, internet_silknet
    - Trunk_to_CoreSwitch, TRUNK-CORE
    - Server_Connection, SRV-HOST-01
    """

    # Classification patterns (order matters - most specific first)
    INTERFACE_PATTERNS = {
        'isp': [
            # ISP providers with "internet" keyword
            r'(?i)(magti|silknet|veon|beeline|geocell)[\s_-]*(internet|inet|wan|uplink)',
            r'(?i)(internet|inet|wan|uplink)[\s_-]*(magti|silknet|veon|beeline|geocell)',

            # Generic ISP patterns
            r'(?i)(isp|wan|uplink|bgp|fiber)[\s_-]*\d*',
            r'(?i)(mpls|metro)[\s_-]*(provider|carrier)',
            r'(?i)external[\s_-]*(link|connection)',
        ],
        'trunk': [
            r'(?i)trunk[\s_-]*(to|link)?[\s_-]*\w*',
            r'(?i)po\d+',                              # Port-channel
            r'(?i)port[\s_-]*channel[\s_-]*\d+',
            r'(?i)lag\d+',                             # Link aggregation
            r'(?i)to[\s_-]*(switch|router|core|agg)',
            r'(?i)(uplink|downlink)[\s_-]*to',
        ],
        'server_link': [
            r'(?i)(server|srv|host|vm|esxi)[\s_-]*\w*',
            r'(?i)to[\s_-]*(server|host|vm)',
        ],
        'branch_link': [
            r'(?i)(branch|office|site|remote)[\s_-]*\w*',
            r'(?i)to[\s_-]*(rustavi|tbilisi|batumi|kutaisi|gori|telavi|zugdidi|poti)',  # Georgian cities
            r'(?i)vpn[\s_-]*(tunnel|link)',
        ],
        'access': [
            r'(?i)(access|user|client|endpoint)[\s_-]*',
            r'(?i)vlan[\s_-]*\d+',
            r'(?i)(workstation|pc|desktop)',
        ],
    }

    # ISP provider patterns
    ISP_PROVIDERS = {
        'magti': [r'(?i)magti(com)?', r'(?i)mgt'],
        'silknet': [r'(?i)silk(net)?', r'(?i)slk'],
        'veon': [r'(?i)veon', r'(?i)beeline'],
        'geocell': [r'(?i)geocell', r'(?i)geo(?!rgia)'],  # geo but not georgia
        'beeline': [r'(?i)beeline'],
    }

    def classify_interface(self, if_alias: str, if_descr: str = None) -> InterfaceClassification:
        """
        Classify an interface based on its description

        Args:
            if_alias: Interface alias (user description, e.g., "Magti_Internet")
            if_descr: Interface description (e.g., "GigabitEthernet0/0/0")

        Returns:
            InterfaceClassification with type, ISP provider, and confidence
        """
        # Use alias primarily, fallback to descr
        description = if_alias or if_descr or ""

        # Try to match interface type
        interface_type = 'unknown'
        confidence = 0.0

        for itype, patterns in self.INTERFACE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, description):
                    interface_type = itype
                    confidence = 0.8  # High confidence on pattern match
                    break
            if interface_type != 'unknown':
                break

        # Extract ISP provider if ISP interface
        isp_provider = None
        if interface_type == 'isp':
            isp_provider = self._extract_isp_provider(description)
            if isp_provider:
                confidence = 0.95  # Very high confidence when ISP matched

        # Determine if critical
        is_critical = interface_type == 'isp' or \
                     (interface_type == 'trunk' and 'core' in description.lower())

        return InterfaceClassification(
            interface_type=interface_type,
            isp_provider=isp_provider,
            is_critical=is_critical,
            confidence=confidence
        )

    def _extract_isp_provider(self, description: str) -> Optional[str]:
        """Extract ISP provider name from description"""
        for provider, patterns in self.ISP_PROVIDERS.items():
            for pattern in patterns:
                if re.search(pattern, description):
                    return provider
        return None


# Example usage
if __name__ == '__main__':
    parser = InterfaceParser()

    test_cases = [
        "Magti_Internet",
        "internet_magti",
        "INTERNET-MAGTI",
        "Silknet_Internet",
        "Trunk_to_CoreSwitch",
        "Server_Connection_01",
        "VLAN100",
        "GigabitEthernet0/0/0",  # No alias
    ]

    for desc in test_cases:
        result = parser.classify_interface(desc)
        print(f"{desc:30} → {result.interface_type:15} ISP={result.isp_provider or 'N/A':10} Critical={result.is_critical} ({result.confidence:.0%})")
```

### 2. Interface Discovery Task

**File:** `monitoring/tasks_interface_discovery.py`

```python
"""
Interface Discovery Task

Periodically discovers network interfaces via SNMP and stores them in PostgreSQL.
Runs every 1 hour via Celery beat.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from celery import shared_task
from sqlalchemy.orm import Session

from database import SessionLocal
from models import StandaloneDevice
from monitoring.snmp.poller import SNMPPoller, SNMPCredentialData
from monitoring.interface_parser import InterfaceParser, InterfaceClassification
from monitoring.models import DeviceInterface  # New model

logger = logging.getLogger(__name__)


# SNMP OIDs for interface discovery (IF-MIB)
INTERFACE_OIDS = {
    'ifIndex': '1.3.6.1.2.1.2.2.1.1',         # Interface index
    'ifDescr': '1.3.6.1.2.1.2.2.1.2',         # Interface description
    'ifType': '1.3.6.1.2.1.2.2.1.3',          # Interface type
    'ifMtu': '1.3.6.1.2.1.2.2.1.4',           # MTU
    'ifSpeed': '1.3.6.1.2.1.2.2.1.5',         # Speed (32-bit, use ifHighSpeed for > 4Gbps)
    'ifAdminStatus': '1.3.6.1.2.1.2.2.1.7',   # Admin status
    'ifOperStatus': '1.3.6.1.2.1.2.2.1.8',    # Operational status
    'ifAlias': '1.3.6.1.2.1.31.1.1.1.18',     # Interface alias (user description)
    'ifName': '1.3.6.1.2.1.31.1.1.1.1',       # Interface name
    'ifHighSpeed': '1.3.6.1.2.1.31.1.1.1.15', # High-speed interfaces (Mbps)
}


def utcnow():
    """Get current UTC time with timezone info"""
    return datetime.now(timezone.utc)


@shared_task(name="monitoring.tasks.discover_all_interfaces")
def discover_all_interfaces():
    """
    Discover interfaces on all devices that support SNMP

    Runs every 1 hour (configured in Celery beat schedule)
    """
    db = None
    try:
        db = SessionLocal()

        # Get all devices with SNMP enabled
        devices = db.query(StandaloneDevice).filter(
            StandaloneDevice.snmp_community.isnot(None),
            StandaloneDevice.snmp_community != ''
        ).all()

        logger.info(f"Starting interface discovery for {len(devices)} devices")

        total_discovered = 0
        total_updated = 0
        errors = 0

        for device in devices:
            try:
                discovered, updated = discover_device_interfaces(device.id)
                total_discovered += discovered
                total_updated += updated
            except Exception as e:
                logger.error(f"Failed to discover interfaces for device {device.name} ({device.ip}): {e}")
                errors += 1

        logger.info(f"Interface discovery complete: {total_discovered} new, {total_updated} updated, {errors} errors")

        return {
            'devices_scanned': len(devices),
            'interfaces_discovered': total_discovered,
            'interfaces_updated': total_updated,
            'errors': errors
        }

    except Exception as e:
        logger.error(f"Error in discover_all_interfaces: {e}")
        raise
    finally:
        if db:
            db.close()


def discover_device_interfaces(device_id: str) -> tuple[int, int]:
    """
    Discover interfaces for a single device

    Args:
        device_id: Device UUID

    Returns:
        Tuple of (newly_discovered_count, updated_count)
    """
    db = None
    try:
        db = SessionLocal()

        # Get device
        device = db.query(StandaloneDevice).filter_by(id=device_id).first()
        if not device:
            logger.error(f"Device {device_id} not found")
            return 0, 0

        # Build SNMP credentials
        credentials = SNMPCredentialData(
            version=device.snmp_version or "v2c",
            community=device.snmp_community,
        )

        # Get device info
        device_ip = device.ip
        device_name = device.name
        snmp_port = device.snmp_port or 161

        # Close DB session before network operations (avoid "idle in transaction")
        db.commit()
        db.close()
        db = None

        # Discover interfaces via SNMP
        poller = SNMPPoller()
        interfaces = asyncio.run(_snmp_walk_interfaces(poller, device_ip, snmp_port, credentials))

        if not interfaces:
            logger.warning(f"No interfaces discovered for device {device_name} ({device_ip})")
            return 0, 0

        # Parse and classify interfaces
        parser = InterfaceParser()

        # Reopen DB session for writes
        db = SessionLocal()
        device = db.query(StandaloneDevice).filter_by(id=device_id).first()

        discovered_count = 0
        updated_count = 0

        for if_data in interfaces:
            try:
                # Classify interface
                classification = parser.classify_interface(
                    if_alias=if_data.get('ifAlias'),
                    if_descr=if_data.get('ifDescr')
                )

                # Check if interface already exists
                existing = db.query(DeviceInterface).filter_by(
                    device_id=device.id,
                    if_index=if_data['ifIndex']
                ).first()

                if existing:
                    # Update existing interface
                    existing.if_name = if_data.get('ifName')
                    existing.if_descr = if_data.get('ifDescr')
                    existing.if_alias = if_data.get('ifAlias')
                    existing.if_type = if_data.get('ifType')
                    existing.if_mtu = if_data.get('ifMtu')
                    existing.admin_status = if_data.get('ifAdminStatus')
                    existing.oper_status = if_data.get('ifOperStatus')
                    existing.speed = if_data.get('ifHighSpeed', if_data.get('ifSpeed'))
                    existing.interface_type = classification.interface_type
                    existing.isp_provider = classification.isp_provider
                    existing.is_critical = classification.is_critical
                    existing.last_seen = utcnow()

                    # Track status changes
                    if existing.oper_status != if_data.get('ifOperStatus'):
                        existing.last_status_change = utcnow()

                    updated_count += 1
                else:
                    # Create new interface
                    new_interface = DeviceInterface(
                        device_id=device.id,
                        if_index=if_data['ifIndex'],
                        if_name=if_data.get('ifName'),
                        if_descr=if_data.get('ifDescr'),
                        if_alias=if_data.get('ifAlias'),
                        if_type=if_data.get('ifType'),
                        if_mtu=if_data.get('ifMtu'),
                        admin_status=if_data.get('ifAdminStatus'),
                        oper_status=if_data.get('ifOperStatus'),
                        speed=if_data.get('ifHighSpeed', if_data.get('ifSpeed')),
                        interface_type=classification.interface_type,
                        isp_provider=classification.isp_provider,
                        is_critical=classification.is_critical,
                        discovered_at=utcnow(),
                        last_seen=utcnow(),
                    )
                    db.add(new_interface)
                    discovered_count += 1

            except Exception as e:
                logger.error(f"Error processing interface {if_data.get('ifIndex')} on {device_name}: {e}")

        db.commit()

        logger.info(f"Device {device_name}: {discovered_count} new interfaces, {updated_count} updated")

        return discovered_count, updated_count

    except Exception as e:
        logger.error(f"Error in discover_device_interfaces for {device_id}: {e}")
        if db:
            db.rollback()
        raise
    finally:
        if db:
            db.close()


async def _snmp_walk_interfaces(poller: SNMPPoller, ip: str, port: int, credentials: SNMPCredentialData) -> List[Dict[str, Any]]:
    """
    Perform SNMP walk to discover all interfaces

    Returns:
        List of interface dictionaries with SNMP data
    """
    interfaces = {}

    # Walk each interface OID table
    for oid_name, oid in INTERFACE_OIDS.items():
        try:
            # SNMP walk (get all entries in table)
            results = await poller.walk(ip, oid, credentials, port=port)

            if results:
                for result in results:
                    if result.success:
                        # Extract interface index from OID
                        # OID format: 1.3.6.1.2.1.2.2.1.X.INDEX
                        oid_parts = result.oid.split('.')
                        if_index = int(oid_parts[-1])

                        # Initialize interface dict if needed
                        if if_index not in interfaces:
                            interfaces[if_index] = {'ifIndex': if_index}

                        # Store value
                        interfaces[if_index][oid_name] = result.value

        except Exception as e:
            logger.error(f"SNMP walk failed for {ip} OID {oid_name}: {e}")

    return list(interfaces.values())
```

### 3. Database Model

**File:** `monitoring/models.py` (add to existing file)

```python
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

# ... existing imports and Base ...


class DeviceInterface(Base):
    """Network interface discovered via SNMP"""

    __tablename__ = 'device_interfaces'

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Device relationship
    device_id = Column(UUID(as_uuid=True), ForeignKey('standalone_devices.id', ondelete='CASCADE'), nullable=False)
    device = relationship("StandaloneDevice", back_populates="interfaces")

    # SNMP interface data
    if_index = Column(Integer, nullable=False)
    if_name = Column(String(255))
    if_descr = Column(String(255))
    if_alias = Column(String(500))  # User description with ISP info
    if_type = Column(String(100))
    if_mtu = Column(Integer)

    # Parsed/Classified data
    interface_type = Column(String(50))  # isp, trunk, access, server_link, branch_link, unknown
    isp_provider = Column(String(50))    # magti, silknet, veon, geocell, beeline
    is_critical = Column(Boolean, default=False)

    # Interface configuration
    admin_status = Column(Integer)  # 1=up, 2=down, 3=testing
    oper_status = Column(Integer)   # 1=up, 2=down, 3=testing, 4=unknown, 5=dormant, 6=notPresent, 7=lowerLayerDown
    speed = Column(BigInteger)      # Speed in bps
    duplex = Column(String(20))     # full, half, auto

    # Topology relationships
    connected_to_device_id = Column(UUID(as_uuid=True), ForeignKey('standalone_devices.id', ondelete='SET NULL'))
    connected_to_interface_id = Column(UUID(as_uuid=True), ForeignKey('device_interfaces.id', ondelete='SET NULL'))

    # MAC address
    mac_address = Column(String(17))

    # Metadata
    discovered_at = Column(DateTime(timezone=True))
    last_seen = Column(DateTime(timezone=True))
    last_status_change = Column(DateTime(timezone=True))
    enabled = Column(Boolean, default=True)

    # Unique constraint
    __table_args__ = (
        UniqueConstraint('device_id', 'if_index', name='unique_device_interface'),
        Index('idx_device_interfaces_device', 'device_id'),
        Index('idx_device_interfaces_type', 'interface_type'),
        Index('idx_device_interfaces_isp', 'isp_provider', postgresql_where=Column('isp_provider').isnot(None)),
        Index('idx_device_interfaces_critical', 'is_critical', postgresql_where=Column('is_critical') == True),
        Index('idx_device_interfaces_oper_status', 'oper_status'),
        Index('idx_device_interfaces_last_seen', 'last_seen'),
        Index('idx_device_interfaces_topology', 'connected_to_device_id', postgresql_where=Column('connected_to_device_id').isnot(None)),
    )


# Add relationship to StandaloneDevice model
# In the StandaloneDevice class, add:
# interfaces = relationship("DeviceInterface", back_populates="device", cascade="all, delete-orphan")
```

---

## Deployment Instructions

### Prerequisites

1. **Network Admin Task (CRITICAL):**
   ```
   Whitelist Flux server IP (10.30.25.46) for SNMP access on all Cisco devices.

   Cisco Configuration:
   access-list <acl_number> permit 10.30.25.46
   snmp-server community XoNaz-<h RO <acl_number>
   ```

2. **Verify SNMP Access:**
   ```bash
   # SSH to Flux server
   ssh wardops@10.30.25.46

   # Test SNMP (should get response, not timeout)
   snmpwalk -v2c -c 'XoNaz-<h' 10.195.91.245 1.3.6.1.2.1.1.1.0
   ```

### Phase 1 Deployment

**Step 1: Create Database Migration**

```bash
# On Flux server
cd /home/wardops/ward-flux-credobank

# Create migration file
cat > migrations/add_device_interfaces_table.sql << 'EOF'
-- Migration: Add device_interfaces table for interface discovery
-- Date: 2025-10-26
-- Author: Claude AI

BEGIN;

-- Main table
CREATE TABLE IF NOT EXISTS device_interfaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES standalone_devices(id) ON DELETE CASCADE,

    -- SNMP data
    if_index INTEGER NOT NULL,
    if_name VARCHAR(255),
    if_descr VARCHAR(255),
    if_alias VARCHAR(500),
    if_type VARCHAR(100),
    if_mtu INTEGER,

    -- Classified data
    interface_type VARCHAR(50),
    isp_provider VARCHAR(50),
    is_critical BOOLEAN DEFAULT false,

    -- Configuration
    admin_status INTEGER,
    oper_status INTEGER,
    speed BIGINT,
    duplex VARCHAR(20),

    -- Topology
    connected_to_device_id UUID REFERENCES standalone_devices(id) ON DELETE SET NULL,
    connected_to_interface_id UUID REFERENCES device_interfaces(id) ON DELETE SET NULL,
    mac_address VARCHAR(17),

    -- Metadata
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_status_change TIMESTAMP WITH TIME ZONE,
    enabled BOOLEAN DEFAULT true,

    CONSTRAINT unique_device_interface UNIQUE(device_id, if_index)
);

-- Indexes
CREATE INDEX idx_device_interfaces_device ON device_interfaces(device_id);
CREATE INDEX idx_device_interfaces_type ON device_interfaces(interface_type);
CREATE INDEX idx_device_interfaces_isp ON device_interfaces(isp_provider) WHERE isp_provider IS NOT NULL;
CREATE INDEX idx_device_interfaces_critical ON device_interfaces(is_critical) WHERE is_critical = true;
CREATE INDEX idx_device_interfaces_oper_status ON device_interfaces(oper_status);
CREATE INDEX idx_device_interfaces_last_seen ON device_interfaces(last_seen);
CREATE INDEX idx_device_interfaces_topology ON device_interfaces(connected_to_device_id) WHERE connected_to_device_id IS NOT NULL;

COMMIT;
EOF

# Run migration
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -f /migrations/add_device_interfaces_table.sql
```

**Step 2: Add Code Files**

```bash
# Copy new Python files to server
# (Use git or scp to transfer files)

git add monitoring/interface_parser.py
git add monitoring/tasks_interface_discovery.py
git add monitoring/models.py  # Updated with DeviceInterface model
git commit -m "Add interface discovery: parser, tasks, and models"
git push origin main

# On server, pull changes
cd /home/wardops/ward-flux-credobank
git pull origin main
```

**Step 3: Update Celery Beat Schedule**

```bash
# Edit celery_app.py or beat configuration
# Add interface discovery to schedule

# In monitoring/celery_app.py, add to beat_schedule:
beat_schedule = {
    # ... existing tasks ...

    'discover-interfaces': {
        'task': 'monitoring.tasks.discover_all_interfaces',
        'schedule': 3600.0,  # Every 1 hour
    },
}
```

**Step 4: Rebuild and Restart Containers**

```bash
cd /home/wardops/ward-flux-credobank

# Build updated images
docker-compose -f docker-compose.production-priority-queues.yml build api celery-worker-snmp celery-beat

# Stop containers
docker-compose -f docker-compose.production-priority-queues.yml stop api celery-worker-snmp celery-beat

# Remove old containers
docker rm wardops-api-prod wardops-worker-snmp-prod wardops-beat-prod

# Start new containers
docker-compose -f docker-compose.production-priority-queues.yml up -d api celery-worker-snmp celery-beat

# Verify containers are running
docker ps | grep -E "(api|snmp|beat)"
```

**Step 5: Test Discovery Manually**

```bash
# Trigger discovery task manually for one device
docker exec wardops-worker-snmp-prod python -c "
from monitoring.tasks_interface_discovery import discover_device_interfaces
from database import SessionLocal

db = SessionLocal()
device = db.query(StandaloneDevice).filter_by(ip='10.195.91.245').first()
db.close()

if device:
    result = discover_device_interfaces(str(device.id))
    print(f'Discovered: {result[0]} new, {result[1]} updated')
else:
    print('Device not found')
"

# Check results in database
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \
  "SELECT d.name, di.if_name, di.if_alias, di.interface_type, di.isp_provider, di.is_critical
   FROM device_interfaces di
   JOIN standalone_devices d ON d.id = di.device_id
   WHERE d.ip = '10.195.91.245'
   ORDER BY di.if_index;"
```

---

## Testing & Validation

### Unit Tests

**File:** `tests/test_interface_parser.py`

```python
import pytest
from monitoring.interface_parser import InterfaceParser


def test_magti_variants():
    """Test various Magti ISP description formats"""
    parser = InterfaceParser()

    test_cases = [
        "Magti_Internet",
        "internet_magti",
        "INTERNET-MAGTI",
        "Magticom_WAN",
    ]

    for desc in test_cases:
        result = parser.classify_interface(desc)
        assert result.interface_type == 'isp'
        assert result.isp_provider == 'magti'
        assert result.is_critical == True


def test_trunk_interfaces():
    """Test trunk interface detection"""
    parser = InterfaceParser()

    test_cases = [
        "Trunk_to_CoreSwitch",
        "TRUNK-CORE",
        "Po1",  # Port-channel 1
        "Uplink_to_Core",
    ]

    for desc in test_cases:
        result = parser.classify_interface(desc)
        assert result.interface_type == 'trunk'
        assert result.isp_provider is None


def test_unknown_interfaces():
    """Test interfaces with no clear classification"""
    parser = InterfaceParser()

    result = parser.classify_interface("GigabitEthernet0/0/0")
    assert result.interface_type == 'unknown'
    assert result.is_critical == False
```

### Integration Tests

```bash
# Test SNMP connectivity
snmpwalk -v2c -c 'XoNaz-<h' 10.195.91.245 1.3.6.1.2.1.2.2.1.2  # ifDescr

# Test discovery task
docker exec wardops-worker-snmp-prod celery -A monitoring.celery_app call monitoring.tasks.discover_all_interfaces

# Verify database entries
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \
  "SELECT interface_type, COUNT(*) FROM device_interfaces GROUP BY interface_type;"

# Check ISP interfaces
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \
  "SELECT d.name, di.if_name, di.if_alias, di.isp_provider
   FROM device_interfaces di
   JOIN standalone_devices d ON d.id = di.device_id
   WHERE di.interface_type = 'isp';"
```

---

## Monitoring & Alerts

### Expected Metrics in VictoriaMetrics (Phase 2)

```promql
# Interface operational status
interface_oper_status{device="Saburtalo1", if_name="Gi0/0/0", interface_type="isp", isp_provider="magti"}

# Traffic metrics
interface_traffic_in_bytes{device="Saburtalo1", if_name="Gi0/0/0"}
interface_traffic_out_bytes{device="Saburtalo1", if_name="Gi0/0/0"}

# Error metrics
interface_errors_in{device="Saburtalo1", if_name="Gi0/0/0"}
interface_errors_out{device="Saburtalo1", if_name="Gi0/0/0"}

# Bandwidth utilization
interface_bandwidth_utilization_pct{device="Saburtalo1", if_name="Gi0/0/0"}
```

### Alert Rules (Phase 2)

```yaml
# ISP interface down
alert: ISPInterfaceDown
expr: interface_oper_status{interface_type="isp"} == 2
for: 1m
severity: critical
message: "CRITICAL: ISP link {{.if_name}} ({{.isp_provider}}) on {{.device}} is DOWN"

# Both ISPs down (total outage)
alert: TotalISPOutage
expr: count(interface_oper_status{interface_type="isp"} == 2) == count(interface_oper_status{interface_type="isp"})
for: 1m
severity: critical
message: "CRITICAL: ALL ISP links are down - Total internet outage!"

# High interface errors
alert: HighInterfaceErrors
expr: rate(interface_errors_in[5m]) > 100
for: 5m
severity: warning
message: "WARNING: High error rate on {{.device}}:{{.if_name}} - {{.value}} errors/sec"

# Interface bandwidth saturation
alert: InterfaceBandwidthSaturation
expr: interface_bandwidth_utilization_pct > 90
for: 5m
severity: warning
message: "WARNING: Interface {{.device}}:{{.if_name}} bandwidth utilization at {{.value}}%"
```

---

## Troubleshooting Guide

### Issue: No Interfaces Discovered

**Symptoms:**
- Discovery task runs but no interfaces in database
- Worker logs show SNMP timeouts

**Diagnosis:**
```bash
# Check SNMP access from container
docker exec wardops-worker-snmp-prod ping -c 3 10.195.91.245

# Test SNMP manually (need to install snmp tools in container first)
docker exec -u root wardops-worker-snmp-prod apt-get update && apt-get install -y snmp
docker exec wardops-worker-snmp-prod snmpwalk -v2c -c 'XoNaz-<h' 10.195.91.245 1.3.6.1.2.1.1.1.0

# Check worker logs
docker logs wardops-worker-snmp-prod --tail 100 | grep -i "interface\|snmp"
```

**Solutions:**
1. Verify SNMP ACL whitelisting on Cisco devices
2. Check community string in database matches actual device config
3. Ensure SNMP port 161 is not blocked by firewall

---

### Issue: Interfaces Not Classified Correctly

**Symptoms:**
- Interfaces discovered but `interface_type = 'unknown'`
- ISP interfaces not marked as critical

**Diagnosis:**
```bash
# Check actual interface descriptions
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \
  "SELECT if_index, if_name, if_alias, interface_type, isp_provider
   FROM device_interfaces
   WHERE device_id IN (SELECT id FROM standalone_devices WHERE ip = '10.195.91.245');"
```

**Solutions:**
1. Review interface descriptions - they may not match regex patterns
2. Add new patterns to `InterfaceParser.INTERFACE_PATTERNS`
3. Manually update classification if needed:
   ```sql
   UPDATE device_interfaces
   SET interface_type = 'isp', isp_provider = 'magti', is_critical = true
   WHERE if_alias LIKE '%magti%';
   ```

---

### Issue: High PostgreSQL Load

**Symptoms:**
- PostgreSQL CPU usage high
- Slow API responses

**Diagnosis:**
```bash
# Check active queries
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \
  "SELECT pid, state, query_start, LEFT(query, 100)
   FROM pg_stat_activity
   WHERE state = 'active'
   ORDER BY query_start;"

# Check table sizes
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \
  "SELECT
     schemaname,
     tablename,
     pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
   FROM pg_tables
   WHERE schemaname = 'public'
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

**Solutions:**
1. Ensure indexes are created (check migration script)
2. Reduce discovery frequency from 1 hour to 2-4 hours
3. Archive old interface history (interfaces not seen in 30+ days)
4. Consider moving metrics to VictoriaMetrics (Phase 2)

---

### Issue: SNMP Worker Container Out of Memory

**Symptoms:**
- Container restarts frequently
- OOMKilled in `docker ps -a`

**Diagnosis:**
```bash
# Check container memory usage
docker stats --no-stream wardops-worker-snmp-prod

# Check container logs
docker logs wardops-worker-snmp-prod --tail 100
```

**Solutions:**
1. Increase worker container memory limit in docker-compose
2. Reduce worker concurrency (fewer parallel SNMP polls)
3. Add memory limit to celery worker: `--max-tasks-per-child=100`

---

## Success Metrics

### Phase 1 Success Criteria

- [ ] Database table `device_interfaces` created successfully
- [ ] Interface discovery runs every 1 hour via Celery beat
- [ ] At least 80% of interfaces discovered on test devices
- [ ] ISP interfaces correctly classified (interface_type='isp', is_critical=true)
- [ ] Interface parser correctly identifies Magti, Silknet from various description formats
- [ ] API endpoint returns interface list for device
- [ ] No performance degradation (PostgreSQL CPU <10%, API response <200ms)

### Phase 2 Success Criteria

- [ ] Interface metrics flowing to VictoriaMetrics
- [ ] ISP interface down alerts triggering correctly
- [ ] Alert differentiation: single ISP down vs total outage
- [ ] Dashboard widget showing ISP interface status
- [ ] Interface bandwidth graphs available in UI

### Phase 3 Success Criteria

- [ ] Topology visualization showing devices and connections
- [ ] Click on device shows interface list with status
- [ ] LLDP/CDP neighbor discovery working
- [ ] Impact analysis: identify affected devices when interface fails
- [ ] Real-time status updates in topology view

---

## Appendix

### Useful Commands

```bash
# SSH to server
ssh wardops@10.30.25.46

# Navigate to project
cd /home/wardops/ward-flux-credobank

# Pull latest code
git pull origin main

# View container logs
docker logs wardops-worker-snmp-prod -f --tail 100

# Execute psql query
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "SELECT COUNT(*) FROM device_interfaces;"

# Clear Redis cache
docker exec wardops-redis-prod redis-cli -a redispass FLUSHDB

# Restart specific container
docker-compose -f docker-compose.production-priority-queues.yml restart celery-worker-snmp

# Check VictoriaMetrics metrics
curl -s "http://localhost:8428/api/v1/label/__name__/values" | grep interface

# Manual Celery task trigger
docker exec wardops-worker-snmp-prod celery -A monitoring.celery_app call monitoring.tasks.discover_all_interfaces
```

### SNMP OID Reference

```
# System Information
1.3.6.1.2.1.1.1.0  - sysDescr (Device description)
1.3.6.1.2.1.1.3.0  - sysUpTime (Uptime)
1.3.6.1.2.1.1.5.0  - sysName (Device hostname)

# Interface Table (IF-MIB)
1.3.6.1.2.1.2.2.1.1   - ifIndex
1.3.6.1.2.1.2.2.1.2   - ifDescr (Interface description)
1.3.6.1.2.1.2.2.1.7   - ifAdminStatus (1=up, 2=down)
1.3.6.1.2.1.2.2.1.8   - ifOperStatus (1=up, 2=down)
1.3.6.1.2.1.2.2.1.10  - ifInOctets (32-bit counter)
1.3.6.1.2.1.2.2.1.14  - ifInErrors
1.3.6.1.2.1.2.2.1.16  - ifOutOctets (32-bit counter)
1.3.6.1.2.1.2.2.1.20  - ifOutErrors

# 64-bit counters (IF-MIB extended)
1.3.6.1.2.1.31.1.1.1.1   - ifName (Interface name)
1.3.6.1.2.1.31.1.1.1.6   - ifHCInOctets (64-bit)
1.3.6.1.2.1.31.1.1.1.10  - ifHCOutOctets (64-bit)
1.3.6.1.2.1.31.1.1.1.15  - ifHighSpeed (Mbps)
1.3.6.1.2.1.31.1.1.1.18  - ifAlias (User description - HAS ISP INFO!)

# Cisco-specific
1.3.6.1.4.1.9.9.109.1.1.1.1.8  - CPU utilization
1.3.6.1.4.1.9.9.48.1.1.1.5     - Memory used
1.3.6.1.4.1.9.9.48.1.1.1.6     - Memory free
```

### Git Workflow

```bash
# On local machine
cd /Users/g.jalabadze/Desktop/WARD\ OPS/ward-ops-credobank

# Create feature branch
git checkout -b feature/interface-discovery

# Make changes, commit
git add monitoring/interface_parser.py
git commit -m "Add interface description parser with ISP detection"

# Push to GitHub
git push origin feature/interface-discovery

# Merge to main (via PR or direct)
git checkout main
git merge feature/interface-discovery
git push origin main

# On server, pull changes
ssh wardops@10.30.25.46
cd /home/wardops/ward-flux-credobank
git pull origin main
```

---

**End of Document**

This implementation plan provides a complete guide for implementing interface discovery and monitoring on the Ward Ops Credobank system. Follow phases sequentially, test thoroughly at each stage, and refer to troubleshooting section for common issues.

For questions or issues, reference this document and provide:
1. Current phase being implemented
2. Specific error messages or symptoms
3. Relevant logs from containers
4. Database query results (if applicable)
