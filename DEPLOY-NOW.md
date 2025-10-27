# 🚀 DEPLOY ISP MONITORING - QUICK START

## TLDR: Run These Commands

```bash
ssh wardops@10.30.25.46
cd /home/wardops/ward-flux-credobank

# Step 1: Deploy SNMP fix (2 minutes)
./deploy-snmp-fix.sh

# Step 2: Run interface discovery (5 minutes)
./deploy-isp-monitoring.sh

# Step 3: Verify frontend
# Open: http://10.30.25.46/monitor
# Check any .5 router for Magti/Silknet badges
```

That's it! 🎉

---

## What Was Fixed

### The Problem
```
ImportError: No module named 'pysnmp.hlapi.v3arch'
```

SNMP library imports were broken, blocking interface discovery.

### The Solution
Used correct 2025 pysnmp API:
```python
# ✅ CORRECT (now used):
from pysnmp.hlapi.asyncio import getCmd, bulkCmd, nextCmd
```

### What This Enables
- ✅ SNMP polling works
- ✅ Interface discovery on 93 .5 routers
- ✅ Real-time ISP status (Magti/Silknet)
- ✅ Independent RED/GREEN badges per ISP
- ✅ 60s backend polling, 30s frontend refresh

---

## Expected Results

### After deploy-snmp-fix.sh
```
Testing pysnmp asyncio imports (2025)...
✅ SUCCESS: pysnmp.hlapi.asyncio imports work!

Testing SNMP poller module...
✅ SUCCESS: SNMPPoller imports successfully!

🎉 All imports and tests successful!
```

### After deploy-isp-monitoring.sh
```
Discovering ISP interfaces on 93 .5 routers...
Found 186 interfaces (93 Magti + 93 Silknet)
✅ Interface discovery complete!
```

### Frontend (Monitor Page)
Every .5 router shows two badges:
- 🟣 **Magti** (purple=UP, red=DOWN)
- 🟠 **Silknet** (orange=UP, red=DOWN)

Status updates every 30 seconds.

---

## Files Changed

1. **monitoring/snmp/poller.py** - Fixed imports (asyncio + CamelCase)
2. **requirements.txt** - Updated to pysnmp-lextudio 6.1.0+
3. **deploy-snmp-fix.sh** - Automated deployment script
4. **deploy-isp-monitoring.sh** - Interface discovery script

---

## Commits

- **1dd594b** - ROBUST FIX 2025: Use pysnmp.hlapi.asyncio
- **702a0a6** - Update deployment script tests
- **55872ed** - Add comprehensive documentation

---

## Troubleshooting

### If imports still fail:
```bash
# Check container logs
docker logs wardops-worker-snmp-prod --tail 50

# Verify package installed
docker exec wardops-worker-snmp-prod pip list | grep pysnmp
```

### If discovery finds 0 interfaces:
```bash
# Check SNMP credentials in database
docker exec wardops-worker-snmp-prod python3 -c "
import sys
sys.path.insert(0, '/app')
from database import SessionLocal
from monitoring.models import SNMPCredential
db = SessionLocal()
creds = db.query(SNMPCredential).all()
print(f'SNMP credentials configured: {len(creds)}')
for c in creds:
    print(f'  - {c.name}: v{c.version}')
db.close()
"
```

### If frontend shows "unknown":
```bash
# Check API endpoint
curl -s http://localhost:8000/api/v1/interfaces/isp-status/bulk?device_ips=10.195.57.5 | jq

# Check database
docker exec wardops-worker-snmp-prod python3 -c "
import sys
sys.path.insert(0, '/app')
from database import SessionLocal
from monitoring.models import DeviceInterface
db = SessionLocal()
count = db.query(DeviceInterface).filter(
    DeviceInterface.interface_type == 'isp'
).count()
print(f'ISP interfaces in DB: {count} (expected: 186)')
db.close()
"
```

---

## Documentation

- **Full Details**: [SNMP-FIX-2025-FINAL.md](SNMP-FIX-2025-FINAL.md)
- **Project Docs**: [PROJECT_KNOWLEDGE_BASE.md](PROJECT_KNOWLEDGE_BASE.md)
- **Architecture**: Hybrid PostgreSQL + VictoriaMetrics

---

## Support

If issues persist:
1. Check logs: `docker logs wardops-worker-snmp-prod`
2. Review: [SNMP-FIX-2025-FINAL.md](SNMP-FIX-2025-FINAL.md)
3. Verify network access to .5 routers (SNMP port 161)

---

**Status**: ✅ READY TO DEPLOY

**Time to Deploy**: ~7 minutes total

**Impact**: Real-time ISP monitoring for 93 routers
