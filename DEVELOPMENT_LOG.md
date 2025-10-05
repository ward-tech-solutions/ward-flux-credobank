# WARD FLUX - Standalone Monitoring Development Log

## 📋 Project Overview

**Goal:** Build hybrid monitoring system (Zabbix + Standalone) with SNMP, ICMP, and Alerting
**Timeline:** 14 days
**Database:** VictoriaMetrics (time-series) + PostgreSQL (config)
**Status:** 🟡 In Progress

---

## 🎯 Architecture Decision

### Selected Technology Stack:
- **Time-Series DB:** VictoriaMetrics (lightweight, fast, Prometheus-compatible)
- **SNMP Library:** pysnmp-lextudio (async, modern)
- **Task Queue:** Celery + Redis
- **ICMP Library:** icmplib (async)

### Why VictoriaMetrics?
- 20x faster writes than InfluxDB
- 10x smaller disk footprint
- 500MB-1GB RAM usage
- Single binary deployment
- Prometheus-compatible (PromQL)

---

## 📅 Development Timeline

### Week 1: Core Infrastructure
- **Day 1-2:** Database & Architecture Setup
- **Day 3-4:** SNMP Polling Engine
- **Day 5-6:** ICMP Monitoring
- **Day 7:** Task Scheduler (Celery/Redis)

### Week 2: Intelligence & Features
- **Day 8-9:** Auto-Discovery Engine
- **Day 10-11:** Alerting System
- **Day 12-13:** Monitoring Templates
- **Day 14:** Integration & Testing

---

## 📝 Session Log

### Session 1 - 2025-10-06

**Completed:**
1. ✅ Fixed MTR/Traceroute issue - added `traceroute` and `iputils-ping` to Dockerfile
2. ✅ Created v1.1.2 release tag
3. ✅ Decided on product name: **WARD FLUX**
4. ✅ Planned hybrid architecture (Zabbix + Standalone monitoring)
5. ✅ Selected VictoriaMetrics as time-series database
6. ✅ Created development tracking system

**Architecture Decided:**
```
WARD FLUX CORE
├── Mode Selector (Zabbix/Standalone/Hybrid)
├── Zabbix Engine (existing)
├── Standalone Engine (NEW)
│   ├── SNMP Poller
│   ├── ICMP Monitor
│   ├── Alert Engine
│   └── Auto-Discovery
├── PostgreSQL (config/users/devices)
└── VictoriaMetrics (time-series metrics)
```

**Critical Decision - Universal Vendor Support:**
- Changed from Cisco-only to **universal vendor support**
- Auto-detection via sysObjectID
- Three-tier OID strategy (Universal → Vendor-Specific → Dynamic Discovery)
- Support for: Cisco, Fortinet, Juniper, HP, Linux, Windows, MikroTik, Ubiquiti, Palo Alto, and more

**Next Steps:**
1. Add VictoriaMetrics + Redis + Celery to docker-compose
2. Create monitoring database models
3. Build universal OID library
4. Create vendor auto-detection system

**Files Created:**
- `DEVELOPMENT_LOG.md` (this file)
- `IMPLEMENTATION_PLAN.md`
- `ARCHITECTURE.md`
- `UNIVERSAL_VENDOR_SUPPORT.md`

**Files Modified:**
- `Dockerfile` - Added traceroute and iputils-ping packages

**Git Status:**
- Current commit: ffe6c20 "Fix: Add traceroute and ping utilities to Docker image"
- Current tag: v1.1.2
- Branch: main

**Known Issues:**
- None currently - MTR/traceroute fixed in v1.1.2

**Dependencies to Add:**
```
victoriametrics>=0.1.0
pysnmp-lextudio>=5.0.0
celery[redis]>=5.3.0
redis>=5.0.0
icmplib>=3.0.0
cryptography>=41.0.0
APScheduler>=3.10.0
```

**Database Schema to Create:**
- monitoring_profiles
- snmp_credentials
- monitoring_items
- monitoring_templates
- alert_rules
- alert_history
- discovery_rules

---

## 🔄 Current Status: 🟢 IMPLEMENTATION STARTED

**Current Action:** Day 1 - Foundation Setup (VictoriaMetrics, Database Models, OID Library)

**Approved:** Universal vendor support approach - proceeding with implementation

---

## 📚 Important Notes

### Context for New Sessions:
1. This is a **hybrid approach** - keep Zabbix support, add standalone monitoring
2. VictoriaMetrics chosen for performance and lightweight footprint
3. All code must have: error handling, logging, type hints, tests, documentation
4. 14-day development timeline with daily milestones
5. Full responsibility accepted for precision and quality

### Project Structure:
```
/app
├── monitoring/          # NEW - Standalone monitoring engine
│   ├── snmp/           # SNMP poller
│   ├── icmp/           # ICMP monitor
│   ├── alerts/         # Alert engine
│   ├── discovery/      # Auto-discovery
│   └── templates/      # Monitoring templates
├── routers/            # Existing API routes
├── database.py         # Database models
└── main.py            # FastAPI app
```

### Critical Requirements:
- Maintain backward compatibility with Zabbix mode
- Allow users to switch between modes
- Encrypt sensitive credentials (SNMP community strings)
- Performance: handle 1000+ devices
- Scalability: distributed polling via Celery

---

## 🐛 Issues & Resolutions

### Issue #1: MTR/Traceroute showing "No route found"
**Date:** 2025-10-06
**Cause:** Docker container missing `traceroute` and `iputils-ping` packages
**Solution:** Added packages to Dockerfile
**Commit:** ffe6c20
**Tag:** v1.1.2
**Status:** ✅ Resolved

---

## 📊 Metrics to Track

- [ ] Lines of code added
- [ ] Test coverage percentage
- [ ] API response times
- [ ] Memory usage (target: <1GB)
- [ ] Devices supported per instance
- [ ] Polling accuracy

---

## 🎓 Learning & Decisions

### Why Not Prometheus?
- Pull-based architecture doesn't fit SNMP polling
- Higher memory usage
- No native push support for SNMP data
- VictoriaMetrics is Prometheus-compatible anyway

### Why Celery?
- Proven distributed task queue
- Easy scaling (add more workers)
- Built-in retry mechanisms
- Monitoring via Flower

### Why pysnmp-lextudio?
- Active maintenance (original pysnmp abandoned)
- Async/await support
- SNMPv3 support
- Better error handling

---

**Last Updated:** 2025-10-06
**Session:** 1
**Developer:** Claude (Sonnet 4.5)
**Supervisor:** g.jalabadze
