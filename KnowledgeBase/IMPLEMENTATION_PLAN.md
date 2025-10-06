# WARD FLUX - Standalone Monitoring Implementation Plan

## 🎯 Project Goal

Transform WARD from Zabbix-dependent platform into a **hybrid monitoring system** that can:
1. Work with existing Zabbix (current functionality)
2. Work standalone without Zabbix (NEW)
3. Work in hybrid mode (both sources)

---

## 📊 Technical Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     WARD FLUX CORE                          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Monitoring Mode Selector                     │  │
│  │  [Zabbix Mode] | [Standalone Mode] | [Hybrid Mode]  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────┐  ┌──────────────────────────┐    │
│  │   ZABBIX ENGINE     │  │  STANDALONE ENGINE        │    │
│  │                     │  │                           │    │
│  │  • Zabbix API      │  │  • SNMP Poller           │    │
│  │  • Existing code   │  │  • ICMP Monitor          │    │
│  │  • Legacy support  │  │  • Alert Engine          │    │
│  │                     │  │  • Auto-Discovery        │    │
│  └─────────────────────┘  └──────────────────────────┘    │
│            │                         │                      │
│            └────────┬────────────────┘                      │
│                     ▼                                       │
│         ┌──────────────────────┐                           │
│         │  UNIFIED DATA LAYER  │                           │
│         └──────────────────────┘                           │
│                     │                                       │
│         ┌───────────┴───────────┐                          │
│         ▼                       ▼                           │
│  ┌─────────────┐     ┌──────────────────┐                 │
│  │ PostgreSQL  │     │ VictoriaMetrics  │                 │
│  │ (Config/    │     │ (Time-Series     │                 │
│  │  Users/     │     │  Metrics Data)   │                 │
│  │  Devices)   │     │                  │                 │
│  └─────────────┘     └──────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 📅 14-Day Development Schedule

### **Week 1: Core Infrastructure (Days 1-7)**

#### Day 1-2: Foundation & Database Setup
**Goals:**
- Install VictoriaMetrics
- Create database schema
- Setup mode selector

**Tasks:**
1. Add VictoriaMetrics to docker-compose.yml
2. Create SQLAlchemy models for monitoring tables:
   - `MonitoringProfile` (Zabbix/Standalone/Hybrid mode)
   - `SNMPCredential` (encrypted credentials)
   - `MonitoringItem` (what to monitor)
   - `MonitoringTemplate` (device templates)
   - `AlertRule` (alerting configuration)
   - `AlertHistory` (alert tracking)
   - `DiscoveryRule` (auto-discovery config)
3. Create migration scripts
4. Build mode selector UI in settings

**Deliverables:**
- `monitoring/models.py` - Database models
- `monitoring/victoria_client.py` - VictoriaMetrics client
- `alembic/versions/xxx_add_monitoring_tables.py` - Migration
- UI in settings page for mode selection

---

#### Day 3-4: SNMP Polling Engine
**Goals:**
- Build async SNMP poller
- Support SNMPv2c and SNMPv3
- Store credentials securely

**Tasks:**
1. Create `monitoring/snmp/poller.py`:
   - Async SNMP GET/WALK operations
   - Bulk polling optimization
   - Error handling and retries
   - Connection pooling
2. Create `monitoring/snmp/oids.py`:
   - Common OID definitions (CPU, Memory, Interfaces)
   - OID discovery helpers
3. Create `monitoring/snmp/credentials.py`:
   - Encrypted credential storage
   - SNMPv3 authentication
4. Build API endpoints:
   - POST `/api/v1/monitoring/snmp/credentials` - Add SNMP creds
   - POST `/api/v1/monitoring/snmp/poll` - Manual poll
   - GET `/api/v1/monitoring/snmp/test` - Test SNMP connection

**Deliverables:**
- `monitoring/snmp/poller.py` - SNMP engine
- `monitoring/snmp/oids.py` - OID library
- `routers/monitoring.py` - API endpoints
- Tests in `tests/test_snmp.py`

**OIDs to Support:**
```python
# System Info
sysDescr = "1.3.6.1.2.1.1.1.0"
sysUpTime = "1.3.6.1.2.1.1.3.0"
sysName = "1.3.6.1.2.1.1.5.0"

# CPU (Cisco)
cpu_5sec = "1.3.6.1.4.1.9.2.1.56.0"
cpu_1min = "1.3.6.1.4.1.9.2.1.57.0"

# Memory (Cisco)
mem_free = "1.3.6.1.4.1.9.2.1.8.0"
mem_used = "1.3.6.1.4.1.9.2.1.9.0"

# Interfaces (Standard)
ifDescr = "1.3.6.1.2.1.2.2.1.2"      # Interface description
ifOperStatus = "1.3.6.1.2.1.2.2.1.8" # Up/Down status
ifInOctets = "1.3.6.1.2.1.2.2.1.10"  # Bytes in
ifOutOctets = "1.3.6.1.2.1.2.2.1.16" # Bytes out
```

---

#### Day 5-6: ICMP Monitoring
**Goals:**
- Scheduled ping monitoring
- RTT tracking and alerting
- Historical availability

**Tasks:**
1. Create `monitoring/icmp/monitor.py`:
   - Async ping function (using icmplib)
   - Parallel device pinging
   - RTT calculation and storage
   - Availability percentage
2. Create `monitoring/icmp/scheduler.py`:
   - Interval-based scheduling
   - Device grouping for bulk pings
   - Failure tracking
3. Store metrics in VictoriaMetrics:
   - `ping_rtt_ms{device="x", ip="y"}`
   - `ping_packet_loss{device="x", ip="y"}`
   - `ping_availability{device="x", ip="y"}`
4. Build API endpoints:
   - GET `/api/v1/monitoring/icmp/status` - Current status
   - GET `/api/v1/monitoring/icmp/history/{device_id}` - History

**Deliverables:**
- `monitoring/icmp/monitor.py` - ICMP engine
- `monitoring/icmp/scheduler.py` - Scheduler
- Integration with VictoriaMetrics
- Tests in `tests/test_icmp.py`

---

#### Day 7: Task Scheduler (Celery + Redis)
**Goals:**
- Distributed polling
- Background task processing
- Job monitoring

**Tasks:**
1. Add Celery + Redis to docker-compose
2. Create `monitoring/tasks.py`:
   - `poll_device_snmp(device_id)` - SNMP polling task
   - `ping_device(device_id)` - ICMP ping task
   - `discover_network(network_range)` - Discovery task
3. Create `monitoring/scheduler.py`:
   - Periodic task scheduling
   - Device-based polling intervals
   - Task result tracking
4. Setup Celery beat for scheduling
5. Add Flower for monitoring (optional)

**Deliverables:**
- `monitoring/celery_app.py` - Celery configuration
- `monitoring/tasks.py` - Celery tasks
- `docker-compose.yml` - Redis + Celery worker
- Flower dashboard (optional)

---

### **Week 2: Intelligence & Features (Days 8-14)**

#### Day 8-9: Auto-Discovery Engine
**Goals:**
- Automatic network scanning
- Device classification
- SNMP detection

**Tasks:**
1. Create `monitoring/discovery/scanner.py`:
   - ICMP sweep (ping range of IPs)
   - Parallel scanning
   - Alive host detection
2. Create `monitoring/discovery/classifier.py`:
   - SNMP sysDescr analysis
   - Device type detection (router/switch/server)
   - OS fingerprinting
3. Create `monitoring/discovery/rules.py`:
   - Discovery rule management
   - Scheduling (daily/weekly)
   - Duplicate prevention
4. Build API endpoints:
   - POST `/api/v1/monitoring/discovery/scan` - Start scan
   - GET `/api/v1/monitoring/discovery/results` - Get results
   - POST `/api/v1/monitoring/discovery/add-devices` - Add to monitoring

**Deliverables:**
- `monitoring/discovery/scanner.py` - Network scanner
- `monitoring/discovery/classifier.py` - Device classifier
- UI for discovery configuration
- Tests in `tests/test_discovery.py`

---

#### Day 10-11: Alerting Engine
**Goals:**
- Threshold-based alerts
- Multiple notification channels
- Alert correlation

**Tasks:**
1. Create `monitoring/alerts/engine.py`:
   - Trigger evaluation (CPU > 90%, interface down, etc.)
   - Alert generation
   - De-duplication
   - Escalation logic
2. Create `monitoring/alerts/notifications.py`:
   - Email notifications (SMTP)
   - Webhook support (Slack, Teams, Discord)
   - SMS (Twilio integration - optional)
3. Create `monitoring/alerts/rules.py`:
   - Rule builder
   - Expression parser
   - Severity levels (Critical, High, Medium, Low)
4. Build API endpoints:
   - POST `/api/v1/monitoring/alerts/rules` - Create rule
   - GET `/api/v1/monitoring/alerts/active` - Active alerts
   - POST `/api/v1/monitoring/alerts/{id}/acknowledge` - ACK alert

**Deliverables:**
- `monitoring/alerts/engine.py` - Alert engine
- `monitoring/alerts/notifications.py` - Notifications
- Alert management UI
- Tests in `tests/test_alerts.py`

**Alert Rule Examples:**
```python
{
    "name": "High CPU Usage",
    "expression": "avg(cpu_usage) > 90 for 5m",
    "severity": "critical",
    "notifications": ["email", "webhook"]
}

{
    "name": "Interface Down",
    "expression": "interface_status == 0",
    "severity": "high",
    "notifications": ["email"]
}
```

---

#### Day 12-13: Monitoring Templates
**Goals:**
- Pre-built templates
- Template builder UI
- Common device support

**Tasks:**
1. Create `monitoring/templates/builder.py`:
   - Template CRUD operations
   - Item/trigger management
   - Template variables
2. Create default templates:
   - Generic SNMP (basic OIDs)
   - Cisco IOS (CPU, Memory, Interfaces)
   - Linux SNMP (Net-SNMP)
   - Windows SNMP (Windows SNMP service)
3. Create `monitoring/templates/applier.py`:
   - Apply template to device
   - Override default values
   - Bulk application
4. Build Template UI:
   - Template library
   - Template editor
   - Device assignment

**Deliverables:**
- `monitoring/templates/builder.py` - Template engine
- `monitoring/templates/defaults/` - Default templates
- Template management UI
- Tests in `tests/test_templates.py`

**Template Structure:**
```json
{
  "name": "Cisco IOS Router",
  "description": "Standard Cisco IOS monitoring",
  "device_types": ["router", "switch"],
  "items": [
    {
      "name": "CPU Usage",
      "oid": "1.3.6.1.4.1.9.2.1.56.0",
      "interval": 60,
      "units": "%",
      "value_type": "integer"
    },
    {
      "name": "Memory Free",
      "oid": "1.3.6.1.4.1.9.2.1.8.0",
      "interval": 300,
      "units": "bytes",
      "value_type": "integer"
    }
  ],
  "triggers": [
    {
      "name": "High CPU",
      "expression": "cpu_usage > 90",
      "severity": "high"
    }
  ]
}
```

---

#### Day 14: Integration & Testing
**Goals:**
- Mode switching
- End-to-end testing
- Documentation

**Tasks:**
1. Build mode switcher:
   - Settings UI for mode selection
   - Data source abstraction layer
   - Unified API responses
2. Create migration tools:
   - Import devices from Zabbix → Standalone
   - Export standalone config
3. Performance testing:
   - Load test with 1000 devices
   - Memory profiling
   - Query optimization
4. Documentation:
   - User guide for standalone mode
   - API documentation updates
   - Deployment guide

**Deliverables:**
- Mode switching functionality
- Migration scripts
- Performance report
- Updated documentation

---

## 📦 Dependencies to Add

### requirements.txt additions:
```txt
# Time-Series Database
victoriametrics>=0.1.0

# SNMP
pysnmp-lextudio>=5.0.0
pyasn1>=0.5.0

# Task Queue
celery[redis]>=5.3.0
redis>=5.0.0
flower>=2.0.0

# ICMP
icmplib>=3.0.0

# Security
cryptography>=41.0.0

# Scheduling
APScheduler>=3.10.0

# Notifications
aiosmtplib>=3.0.0
```

---

## 🗄️ Database Schema

### New Tables

```python
# monitoring_profiles
- id (UUID)
- name (String)
- mode (Enum: zabbix, standalone, hybrid)
- is_active (Boolean)
- created_at, updated_at

# snmp_credentials
- id (UUID)
- device_id (FK)
- version (String: v2c, v3)
- community_encrypted (String)  # For v2c
- auth_protocol (String)        # For v3
- auth_key_encrypted (String)
- priv_protocol (String)
- priv_key_encrypted (String)
- created_at, updated_at

# monitoring_items
- id (UUID)
- device_id (FK)
- template_id (FK, nullable)
- name (String)
- oid (String)
- interval_seconds (Integer)
- value_type (String: integer, float, string)
- units (String)
- enabled (Boolean)
- created_at, updated_at

# monitoring_templates
- id (UUID)
- name (String)
- description (Text)
- device_types (JSON)  # ["router", "switch"]
- items (JSON)
- triggers (JSON)
- created_at, updated_at

# alert_rules
- id (UUID)
- name (String)
- expression (String)
- severity (Enum: critical, high, medium, low)
- enabled (Boolean)
- notification_channels (JSON)
- created_at, updated_at

# alert_history
- id (UUID)
- device_id (FK)
- rule_id (FK)
- severity (String)
- message (Text)
- triggered_at (DateTime)
- acknowledged (Boolean)
- acknowledged_by (FK User)
- acknowledged_at (DateTime)
- resolved_at (DateTime)
- created_at

# discovery_rules
- id (UUID)
- name (String)
- network_range (String)  # "192.168.1.0/24"
- enabled (Boolean)
- schedule (String)  # Cron expression
- last_run (DateTime)
- created_at, updated_at

# discovery_results
- id (UUID)
- rule_id (FK)
- ip_address (String)
- hostname (String)
- device_type (String)
- snmp_reachable (Boolean)
- sys_descr (Text)
- discovered_at (DateTime)
- added_to_monitoring (Boolean)
```

---

## 🔐 Security Considerations

1. **Credential Encryption:**
   - Use `cryptography.fernet` for SNMP credentials
   - Store encryption key in environment variable
   - Rotate keys periodically

2. **Access Control:**
   - Role-based permissions for monitoring configuration
   - Audit log for configuration changes

3. **Network Security:**
   - SNMPv3 with authentication preferred
   - Rate limiting on discovery scans
   - Whitelist monitoring sources

---

## 📊 Performance Targets

- **Devices Supported:** 1000+ per instance
- **Polling Accuracy:** ±5 seconds of scheduled time
- **Memory Usage:** <1GB for core engine
- **API Response:** <100ms average
- **Alert Latency:** <30 seconds from trigger to notification
- **Discovery Speed:** 1000 IPs in <5 minutes

---

## 🧪 Testing Strategy

1. **Unit Tests:**
   - SNMP poller functions
   - ICMP monitor
   - Alert engine logic
   - Template builder

2. **Integration Tests:**
   - End-to-end polling flow
   - Alert notification delivery
   - Discovery → Add to monitoring

3. **Performance Tests:**
   - 1000 device polling
   - Concurrent SNMP queries
   - VictoriaMetrics write performance

4. **Security Tests:**
   - Credential encryption/decryption
   - SQL injection prevention
   - API authentication

---

## 📝 Documentation Deliverables

1. **User Documentation:**
   - Standalone mode setup guide
   - Template creation guide
   - Alert configuration guide
   - Migration from Zabbix guide

2. **API Documentation:**
   - OpenAPI/Swagger updates
   - Code examples
   - Authentication guide

3. **Developer Documentation:**
   - Architecture overview
   - Adding new device templates
   - Extending SNMP OID library
   - Custom notification channels

---

## 🚀 Deployment Strategy

### Docker Compose Update:
```yaml
services:
  ward-flux:
    # Existing service

  victoriametrics:
    image: victoriametrics/victoria-metrics:latest
    ports:
      - "8428:8428"
    volumes:
      - vm-data:/victoria-metrics-data
    command:
      - "-storageDataPath=/victoria-metrics-data"
      - "-retentionPeriod=12"  # 12 months

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

  celery-worker:
    build: .
    command: celery -A monitoring.celery_app worker --loglevel=info
    depends_on:
      - redis
      - victoriametrics
    environment:
      - REDIS_URL=redis://redis:6379/0
      - VICTORIA_URL=http://victoriametrics:8428

  celery-beat:
    build: .
    command: celery -A monitoring.celery_app beat --loglevel=info
    depends_on:
      - redis

volumes:
  vm-data:
  redis-data:
```

---

## ✅ Definition of Done

Each component is complete when:
- [ ] Code written with type hints and docstrings
- [ ] Unit tests pass with >80% coverage
- [ ] Integration tests pass
- [ ] Error handling implemented
- [ ] Logging added
- [ ] API documentation updated
- [ ] User documentation written
- [ ] Code reviewed
- [ ] Performance tested

---

**Document Version:** 1.0
**Last Updated:** 2025-10-06
**Owner:** g.jalabadze
**Developer:** Claude (Sonnet 4.5)
