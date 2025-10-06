# WARD FLUX - System Architecture

## 📐 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Web UI     │  │   Mobile     │  │  API Client  │              │
│  │  (Browser)   │  │    (PWA)     │  │  (Scripts)   │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│         │                  │                  │                      │
│         └──────────────────┴──────────────────┘                      │
│                            │                                         │
│                      HTTPS / WSS                                     │
└────────────────────────────┼─────────────────────────────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────────────────┐
│                     API GATEWAY LAYER                                │
│                            │                                         │
│                  ┌─────────▼─────────┐                              │
│                  │  Nginx Reverse    │                              │
│                  │      Proxy        │                              │
│                  │  (SSL/TLS, LB)    │                              │
│                  └─────────┬─────────┘                              │
└────────────────────────────┼─────────────────────────────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────────────────┐
│                    APPLICATION LAYER                                 │
│                            │                                         │
│            ┌───────────────▼───────────────┐                        │
│            │     WARD FLUX CORE            │                        │
│            │      (FastAPI)                │                        │
│            └───────────────┬───────────────┘                        │
│                            │                                         │
│         ┌──────────────────┼──────────────────┐                     │
│         │                  │                  │                     │
│    ┌────▼─────┐    ┌──────▼──────┐   ┌──────▼──────┐              │
│    │ Zabbix   │    │ Standalone  │   │   Hybrid    │              │
│    │  Mode    │    │    Mode     │   │    Mode     │              │
│    └────┬─────┘    └──────┬──────┘   └──────┬──────┘              │
│         │                  │                  │                     │
│         │         ┌────────▼────────┐         │                     │
│         │         │ Monitoring Core │         │                     │
│         │         │                 │         │                     │
│         │         │  ┌───────────┐  │         │                     │
│         │         │  │   SNMP    │  │         │                     │
│         │         │  │  Poller   │  │         │                     │
│         │         │  └───────────┘  │         │                     │
│         │         │  ┌───────────┐  │         │                     │
│         │         │  │   ICMP    │  │         │                     │
│         │         │  │  Monitor  │  │         │                     │
│         │         │  └───────────┘  │         │                     │
│         │         │  ┌───────────┐  │         │                     │
│         │         │  │   Alert   │  │         │                     │
│         │         │  │  Engine   │  │         │                     │
│         │         │  └───────────┘  │         │                     │
│         │         │  ┌───────────┐  │         │                     │
│         │         │  │ Discovery │  │         │                     │
│         │         │  └───────────┘  │         │                     │
│         │         └─────────────────┘         │                     │
│         │                  │                  │                     │
└─────────┼──────────────────┼──────────────────┼─────────────────────┘
          │                  │                  │
┌─────────┼──────────────────┼──────────────────┼─────────────────────┐
│         │          TASK QUEUE LAYER           │                     │
│         │                  │                  │                     │
│         │         ┌────────▼────────┐         │                     │
│         │         │  Celery Workers │         │                     │
│         │         │  ┌────────────┐ │         │                     │
│         │         │  │   SNMP     │ │         │                     │
│         │         │  │   Tasks    │ │         │                     │
│         │         │  └────────────┘ │         │                     │
│         │         │  ┌────────────┐ │         │                     │
│         │         │  │   ICMP     │ │         │                     │
│         │         │  │   Tasks    │ │         │                     │
│         │         │  └────────────┘ │         │                     │
│         │         │  ┌────────────┐ │         │                     │
│         │         │  │ Discovery  │ │         │                     │
│         │         │  │   Tasks    │ │         │                     │
│         │         │  └────────────┘ │         │                     │
│         │         └────────┬────────┘         │                     │
│         │                  │                  │                     │
│         │         ┌────────▼────────┐         │                     │
│         │         │  Celery Beat    │         │                     │
│         │         │  (Scheduler)    │         │                     │
│         │         └────────┬────────┘         │                     │
│         │                  │                  │                     │
│         │         ┌────────▼────────┐         │                     │
│         │         │  Redis Message  │         │                     │
│         │         │     Broker      │         │                     │
│         │         └─────────────────┘         │                     │
└─────────┼──────────────────────────────────────┼─────────────────────┘
          │                                      │
┌─────────┼──────────────────────────────────────┼─────────────────────┐
│         │           DATA LAYER                 │                     │
│         │                                      │                     │
│    ┌────▼─────┐              ┌────────────────▼──────────┐          │
│    │ Zabbix   │              │    VictoriaMetrics        │          │
│    │   API    │              │   (Time-Series DB)        │          │
│    │          │              │                           │          │
│    │  • Hosts │              │  • SNMP Metrics           │          │
│    │  • Items │              │  • ICMP Metrics           │          │
│    │  • Trigs │              │  • Interface Stats        │          │
│    └──────────┘              │  • Custom Metrics         │          │
│                              └───────────────────────────┘          │
│                                                                      │
│                  ┌──────────────────────────────┐                   │
│                  │      PostgreSQL              │                   │
│                  │   (Configuration DB)         │                   │
│                  │                              │                   │
│                  │  • Users & Auth              │                   │
│                  │  • Devices                   │                   │
│                  │  • SNMP Credentials          │                   │
│                  │  • Monitoring Items          │                   │
│                  │  • Templates                 │                   │
│                  │  • Alert Rules               │                   │
│                  │  • Alert History             │                   │
│                  │  • Discovery Rules           │                   │
│                  └──────────────────────────────┘                   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow Diagrams

### Standalone Mode - SNMP Polling Flow

```
┌─────────────┐
│   Celery    │  Every 60s (configurable)
│    Beat     │
└──────┬──────┘
       │
       │ Trigger
       ▼
┌─────────────────┐
│  SNMP Poll Task │
│  (Celery Worker)│
└──────┬──────────┘
       │
       │ 1. Get device credentials
       ▼
┌─────────────────┐
│   PostgreSQL    │
│  SNMPCredential │
└──────┬──────────┘
       │
       │ 2. Decrypt credentials
       ▼
┌─────────────────┐
│  SNMP Poller    │
│  pysnmp-lextudio│
└──────┬──────────┘
       │
       │ 3. SNMP GET/WALK
       ▼
┌─────────────────┐
│  Target Device  │  (Router/Switch/Server)
│   SNMP Agent    │
└──────┬──────────┘
       │
       │ 4. Return values (CPU, Memory, Interfaces)
       ▼
┌─────────────────┐
│  SNMP Poller    │
│  Parse Response │
└──────┬──────────┘
       │
       │ 5. Format metrics
       ▼
┌─────────────────┐
│ VictoriaMetrics │
│   Write Metrics │
│                 │
│ cpu{device="R1",│
│     ip="1.2.3.4"│
│     } = 45      │
└──────┬──────────┘
       │
       │ 6. Check alert rules
       ▼
┌─────────────────┐
│  Alert Engine   │
│  Evaluate Rules │
└──────┬──────────┘
       │
       │ 7. If threshold exceeded
       ▼
┌─────────────────┐
│  Notification   │
│   Email/Webhook │
└─────────────────┘
```

### Standalone Mode - ICMP Monitoring Flow

```
┌─────────────┐
│   Celery    │  Every 30s
│    Beat     │
└──────┬──────┘
       │
       │ Trigger
       ▼
┌─────────────────┐
│  ICMP Ping Task │
│  (Celery Worker)│
└──────┬──────────┘
       │
       │ 1. Get active devices
       ▼
┌─────────────────┐
│   PostgreSQL    │
│     Devices     │
└──────┬──────────┘
       │
       │ 2. Batch devices (100 at a time)
       ▼
┌─────────────────┐
│  ICMP Monitor   │
│   (icmplib)     │
│                 │
│  Async parallel │
│  ping 100 hosts │
└──────┬──────────┘
       │
       │ 3. ICMP Echo Request
       ▼
┌─────────────────┐
│ Network Devices │
│  (100 hosts)    │
└──────┬──────────┘
       │
       │ 4. ICMP Echo Reply (or timeout)
       ▼
┌─────────────────┐
│  ICMP Monitor   │
│  Calculate RTT  │
│  Packet Loss    │
└──────┬──────────┘
       │
       │ 5. Write metrics
       ▼
┌─────────────────┐
│ VictoriaMetrics │
│                 │
│ ping_rtt_ms{    │
│   device="R1"   │
│ } = 12.5        │
│                 │
│ ping_loss{      │
│   device="R1"   │
│ } = 0           │
└──────┬──────────┘
       │
       │ 6. Check availability
       ▼
┌─────────────────┐
│  Alert Engine   │
│  If device down │
│  for 2+ checks  │
└──────┬──────────┘
       │
       │ 7. Send alert
       ▼
┌─────────────────┐
│  Notification   │
│   Email/Webhook │
└─────────────────┘
```

### Auto-Discovery Flow

```
┌─────────────┐
│    User     │
│   Triggers  │
│  Discovery  │
└──────┬──────┘
       │
       │ POST /api/v1/monitoring/discovery/scan
       ▼
┌─────────────────┐
│  Discovery API  │
│  Create Job     │
└──────┬──────────┘
       │
       │ Enqueue Celery task
       ▼
┌─────────────────┐
│ Discovery Task  │
│ (Celery Worker) │
└──────┬──────────┘
       │
       │ 1. ICMP Sweep (192.168.1.0/24)
       ▼
┌─────────────────┐
│  ICMP Scanner   │
│  Ping 254 IPs   │
│  in parallel    │
└──────┬──────────┘
       │
       │ 2. Alive hosts (e.g., 50 replied)
       ▼
┌─────────────────┐
│ SNMP Classifier │
│  Try SNMP on    │
│  each alive IP  │
└──────┬──────────┘
       │
       │ 3. Get sysDescr (OID 1.3.6.1.2.1.1.1.0)
       ▼
┌─────────────────┐
│  SNMP Response  │
│  "Cisco IOS..."│
│  "Linux 5.15..."│
│  "Windows..."   │
└──────┬──────────┘
       │
       │ 4. Classify device type
       ▼
┌─────────────────┐
│  Classifier     │
│  • Router       │
│  • Switch       │
│  • Server       │
│  • Unknown      │
└──────┬──────────┘
       │
       │ 5. Save discovery results
       ▼
┌─────────────────┐
│   PostgreSQL    │
│ DiscoveryResult │
│                 │
│ ip, hostname,   │
│ device_type,    │
│ sys_descr       │
└──────┬──────────┘
       │
       │ 6. Return to user
       ▼
┌─────────────────┐
│    Web UI       │
│  Show discovered│
│  devices        │
│  [Add to        │
│   Monitoring]   │
└─────────────────┘
```

---

## 🏛️ Module Structure

```
/app
├── main.py                      # FastAPI application entry
├── database.py                  # SQLAlchemy setup
├── config.py                    # Configuration management
│
├── routers/                     # API endpoints
│   ├── auth.py                  # Authentication
│   ├── devices.py               # Device management
│   ├── diagnostics.py           # Ping/Traceroute/MTR
│   ├── reports.py               # Reporting
│   ├── monitoring.py            # NEW - Standalone monitoring API
│   ├── alerts.py                # NEW - Alert management API
│   └── discovery.py             # NEW - Discovery API
│
├── monitoring/                  # NEW - Standalone monitoring engine
│   ├── __init__.py
│   ├── celery_app.py           # Celery configuration
│   ├── tasks.py                # Celery tasks
│   ├── models.py               # Database models
│   │
│   ├── snmp/                   # SNMP Monitoring
│   │   ├── __init__.py
│   │   ├── poller.py           # SNMP GET/WALK operations
│   │   ├── oids.py             # OID definitions
│   │   └── credentials.py      # Credential encryption
│   │
│   ├── icmp/                   # ICMP Monitoring
│   │   ├── __init__.py
│   │   ├── monitor.py          # Ping operations
│   │   └── scheduler.py        # Ping scheduling
│   │
│   ├── alerts/                 # Alerting Engine
│   │   ├── __init__.py
│   │   ├── engine.py           # Alert evaluation
│   │   ├── notifications.py    # Email/Webhook/SMS
│   │   └── rules.py            # Rule management
│   │
│   ├── discovery/              # Auto-Discovery
│   │   ├── __init__.py
│   │   ├── scanner.py          # ICMP sweep
│   │   ├── classifier.py       # Device classification
│   │   └── rules.py            # Discovery rules
│   │
│   ├── templates/              # Monitoring Templates
│   │   ├── __init__.py
│   │   ├── builder.py          # Template CRUD
│   │   ├── applier.py          # Apply templates
│   │   └── defaults/           # Default templates
│   │       ├── generic_snmp.json
│   │       ├── cisco_ios.json
│   │       ├── linux_snmp.json
│   │       └── windows_snmp.json
│   │
│   └── victoria/               # VictoriaMetrics integration
│       ├── __init__.py
│       ├── client.py           # VM client
│       └── queries.py          # PromQL queries
│
├── models/                     # Database models
│   ├── user.py
│   ├── device.py
│   ├── monitoring.py           # NEW - Monitoring models
│   ├── alert.py                # NEW - Alert models
│   └── discovery.py            # NEW - Discovery models
│
├── services/                   # Business logic
│   ├── zabbix_service.py       # Zabbix integration
│   └── monitoring_service.py   # NEW - Monitoring service
│
├── templates/                  # Jinja2 HTML templates
│   ├── index.html
│   ├── diagnostics.html
│   ├── monitoring.html         # NEW - Monitoring UI
│   └── alerts.html             # NEW - Alerts UI
│
├── static/                     # Static files
│   ├── css/
│   ├── js/
│   │   ├── monitoring.js       # NEW - Monitoring UI
│   │   └── alerts.js           # NEW - Alerts UI
│   └── img/
│
├── tests/                      # Test suite
│   ├── test_snmp.py           # NEW - SNMP tests
│   ├── test_icmp.py           # NEW - ICMP tests
│   ├── test_alerts.py         # NEW - Alert tests
│   └── test_discovery.py      # NEW - Discovery tests
│
├── alembic/                    # Database migrations
│   └── versions/
│       └── xxx_add_monitoring_tables.py  # NEW
│
└── docker-compose.yml          # Updated with Victoria, Redis, Celery
```

---

## 🔐 Security Architecture

### Credential Encryption

```python
from cryptography.fernet import Fernet

# Encryption key stored in environment variable
ENCRYPTION_KEY = os.getenv("WARD_ENCRYPTION_KEY")
cipher = Fernet(ENCRYPTION_KEY)

# Encrypt SNMP community string
def encrypt_credential(plaintext: str) -> str:
    return cipher.encrypt(plaintext.encode()).decode()

# Decrypt when needed
def decrypt_credential(encrypted: str) -> str:
    return cipher.decrypt(encrypted.encode()).decode()
```

### API Authentication

```
Client Request
     │
     ▼
┌─────────────────┐
│  JWT Token      │  Bearer eyJhbGc...
│  Validation     │
└────────┬────────┘
         │
         ▼ Valid?
     ┌───┴───┐
    Yes      No
     │        │
     ▼        ▼
  Process   401 Unauthorized
  Request
```

### RBAC Model

```
User Roles:
├── Admin
│   ├── All permissions
│   └── Can manage monitoring configuration
├── Manager
│   ├── View all devices
│   ├── Configure alerts
│   └── Run diagnostics
├── Technician
│   ├── View assigned devices
│   ├── Run diagnostics
│   └── Acknowledge alerts
└── Viewer
    └── Read-only access
```

---

## 📊 Data Models

### Monitoring Configuration

```python
class MonitoringProfile(Base):
    __tablename__ = "monitoring_profiles"

    id = Column(UUID, primary_key=True)
    name = Column(String(100))
    mode = Column(Enum("zabbix", "standalone", "hybrid"))
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### SNMP Credential

```python
class SNMPCredential(Base):
    __tablename__ = "snmp_credentials"

    id = Column(UUID, primary_key=True)
    device_id = Column(UUID, ForeignKey("devices.id"))
    version = Column(String(10))  # "v2c" or "v3"

    # v2c
    community_encrypted = Column(Text)

    # v3
    auth_protocol = Column(String(20))  # MD5, SHA
    auth_key_encrypted = Column(Text)
    priv_protocol = Column(String(20))  # DES, AES
    priv_key_encrypted = Column(Text)
```

### Monitoring Item

```python
class MonitoringItem(Base):
    __tablename__ = "monitoring_items"

    id = Column(UUID, primary_key=True)
    device_id = Column(UUID, ForeignKey("devices.id"))
    template_id = Column(UUID, ForeignKey("monitoring_templates.id"))
    name = Column(String(200))
    oid = Column(String(200))
    interval_seconds = Column(Integer, default=60)
    value_type = Column(String(20))  # integer, float, string
    units = Column(String(20))
    enabled = Column(Boolean, default=True)
```

---

## 🚀 Deployment Architecture

### Single Instance (Small Scale)

```
┌─────────────────────────────────────┐
│         Docker Host                 │
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │   Nginx      │  │ WARD FLUX   │ │
│  │   (Proxy)    │→ │   (FastAPI) │ │
│  └──────────────┘  └─────────────┘ │
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │ Celery       │  │ Celery Beat │ │
│  │ Worker       │  │ (Scheduler) │ │
│  └──────────────┘  └─────────────┘ │
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │ PostgreSQL   │  │ Victoria    │ │
│  │              │  │ Metrics     │ │
│  └──────────────┘  └─────────────┘ │
│                                     │
│  ┌──────────────┐                  │
│  │   Redis      │                  │
│  └──────────────┘                  │
└─────────────────────────────────────┘
```

### Distributed (Large Scale)

```
┌─────────────────────────────────────────────────────────┐
│                  Load Balancer                          │
│                  (HAProxy / Nginx)                      │
└────────────┬────────────────────────┬───────────────────┘
             │                        │
      ┌──────▼──────┐          ┌──────▼──────┐
      │  WARD FLUX  │          │  WARD FLUX  │
      │  Instance 1 │          │  Instance 2 │
      └──────┬──────┘          └──────┬──────┘
             │                        │
             └────────┬───────────────┘
                      │
      ┌───────────────┼───────────────┐
      │               │               │
┌─────▼─────┐  ┌──────▼──────┐  ┌────▼────┐
│ Celery    │  │ Celery      │  │ Celery  │
│ Worker 1  │  │ Worker 2    │  │ Worker 3│
└───────────┘  └─────────────┘  └─────────┘
      │               │               │
      └───────────────┼───────────────┘
                      │
              ┌───────▼────────┐
              │  Redis Cluster │
              │   (Sentinel)   │
              └───────┬────────┘
                      │
      ┌───────────────┼───────────────┐
      │               │               │
┌─────▼─────┐  ┌──────▼──────┐  ┌────▼─────────┐
│PostgreSQL │  │ Victoria    │  │   Zabbix     │
│  Primary  │  │ Metrics     │  │   (Optional) │
│           │  │  Cluster    │  │              │
└───────────┘  └─────────────┘  └──────────────┘
```

---

## 📈 Scalability Considerations

### Horizontal Scaling
- **API Servers:** Add more FastAPI instances behind load balancer
- **Celery Workers:** Scale workers based on queue depth
- **VictoriaMetrics:** Use VM cluster for high write throughput

### Performance Optimization
- **Connection Pooling:** SNMP session pooling
- **Batch Operations:** Poll multiple OIDs in single SNMP request
- **Caching:** Redis cache for frequently accessed data
- **Query Optimization:** Indexed database queries

### Resource Allocation
```
Component          CPU      RAM       Disk
─────────────────────────────────────────
WARD FLUX API      2 cores  2GB       10GB
Celery Worker      2 cores  1GB       5GB
VictoriaMetrics    4 cores  4GB       100GB (metrics)
PostgreSQL         2 cores  2GB       50GB
Redis              1 core   512MB     1GB
```

---

## 🔄 Monitoring the Monitor

### Health Checks
- API endpoint: `/api/v1/health`
- Celery worker status
- VictoriaMetrics reachability
- PostgreSQL connection pool

### Metrics to Track
- API response times
- Celery queue depth
- SNMP poll success rate
- ICMP ping success rate
- Alert delivery rate
- Database query performance

---

**Document Version:** 1.0
**Last Updated:** 2025-10-06
**Owner:** g.jalabadze
**Developer:** Claude (Sonnet 4.5)
