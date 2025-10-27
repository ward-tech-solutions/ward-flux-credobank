# CRITICAL FIX: Celery Task Name Mismatch

**Date:** 2025-10-27
**Status:** ✅ FIXED - Ready for deployment
**Impact:** HIGH - Interface metrics collection was completely broken

---

## 🔴 THE PROBLEM

ISP badges showing RED in the UI, even though device 10.195.57.5 has SNMP accessible and 3 ISP interfaces discovered in PostgreSQL.

**Symptoms:**
1. VictoriaMetrics had NO `interface_oper_status` data (empty result)
2. Beat logs showed task being sent every 60 seconds
3. Worker logs NEVER showed task being received
4. UI showed RED badges for all ISP links
5. Manual verification showed SNMP was working fine

---

## 🔍 ROOT CAUSE ANALYSIS

### The Investigation

**Step 1: Check if Beat is sending the task**
```bash
docker logs wardops-celery-beat-prod | grep "collect-interface-metrics"
```
**Result:** ✅ Beat IS sending the task every 60 seconds
```
[2025-10-27 18:39:24,741: INFO/MainProcess] Scheduler: Sending due task collect-interface-metrics (monitoring.tasks_interface_metrics.collect_all_interface_metrics_task)
```

**Step 2: Check if worker has the task registered**
```bash
docker exec wardops-worker-snmp-prod celery -A celery_app inspect registered
```
**Result:** ✅ Worker HAS the task registered
```
[tasks]
  . monitoring.tasks.collect_all_interface_metrics
```

**Step 3: Check if worker is receiving the task**
```bash
docker logs wardops-worker-snmp-prod | grep "collect_all_interface_metrics"
```
**Result:** ❌ Worker NEVER received any task with this name!

**Step 4: Compare task names**
```
Beat sends:     monitoring.tasks_interface_metrics.collect_all_interface_metrics_task
Worker expects: monitoring.tasks.collect_all_interface_metrics
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ MISMATCH! ^^^^^^^
```

### The Bug

**File:** `celery_app_v2_priority_queues.py`

**Line 214 (Beat Schedule):**
```python
'collect-interface-metrics': {
    'task': 'monitoring.tasks_interface_metrics.collect_all_interface_metrics_task',  # WRONG!
    'schedule': 60.0,
},
```

**What the actual task decorator says (monitoring/tasks_interface_metrics.py line 115):**
```python
@shared_task(name="monitoring.tasks.collect_all_interface_metrics", bind=True)  # CORRECT name
def collect_all_interface_metrics_task(self):
    # Task implementation
```

**The Problem:**
- Beat was sending tasks to a name that **doesn't exist**
- Worker was listening for a **different name**
- Result: Task was silently dropped by Redis/Celery routing

---

## ✅ THE FIX

### Changed Files

**File:** `celery_app_v2_priority_queues.py`

### Changes Made

#### 1. Fixed Beat Schedule (lines 214-234)

**BEFORE:**
```python
'collect-interface-metrics': {
    'task': 'monitoring.tasks_interface_metrics.collect_all_interface_metrics_task',  # Wrong!
    'schedule': 60.0,
},
'discover-all-interfaces': {
    'task': 'monitoring.tasks_interface_discovery.discover_all_interfaces_task',  # Wrong!
    'schedule': crontab(hour=2, minute=30),
},
'cleanup-old-interfaces': {
    'task': 'monitoring.tasks_interface_discovery.cleanup_old_interfaces_task',  # Wrong!
    'schedule': crontab(hour=4, minute=0, day_of_week=0),
},
```

**AFTER:**
```python
'collect-interface-metrics': {
    'task': 'monitoring.tasks.collect_all_interface_metrics',  # Correct!
    'schedule': 60.0,
},
'discover-all-interfaces': {
    'task': 'monitoring.tasks.discover_all_interfaces',  # Correct!
    'schedule': crontab(hour=2, minute=30),
},
'cleanup-old-interfaces': {
    'task': 'monitoring.tasks.cleanup_old_interfaces',  # Correct!
    'schedule': crontab(hour=4, minute=0, day_of_week=0),
},
```

#### 2. Fixed Task Routing (lines 93-117)

**BEFORE:**
```python
'monitoring.tasks_interface_metrics.collect_all_interface_metrics_task': {  # Wrong!
    'queue': 'snmp',
    'routing_key': 'snmp',
    'priority': 3
},
'monitoring.tasks_interface_discovery.discover_all_interfaces_task': {  # Wrong!
    'queue': 'snmp',
    'routing_key': 'snmp',
    'priority': 2
},
```

**AFTER:**
```python
'monitoring.tasks.collect_all_interface_metrics': {  # Correct!
    'queue': 'snmp',
    'routing_key': 'snmp',
    'priority': 3
},
'monitoring.tasks.discover_all_interfaces': {  # Correct!
    'queue': 'snmp',
    'routing_key': 'snmp',
    'priority': 2
},
```

### Why This Happened

The task names in @shared_task decorators use a **hardcoded prefix** of `monitoring.tasks.*` instead of the actual module path (`monitoring.tasks_interface_metrics.*`).

This is a common Celery pattern to:
1. Keep task names stable even if files are moved
2. Group related tasks under a common namespace
3. Simplify task routing configuration

But the Beat schedule and task routing were using the **module path** instead of the **hardcoded task name**, causing the mismatch.

---

## 🚀 DEPLOYMENT

### On Production Server (10.30.25.46)

```bash
# SSH to production server
ssh wardops@10.30.25.46

# Navigate to project directory
cd /home/wardops/ward-flux-credobank

# Pull latest code (includes the fix)
git pull origin main

# Run deployment script
./deploy-task-name-fix.sh
```

The script will:
1. Stop Beat and SNMP worker
2. Remove old containers
3. Rebuild with corrected configuration
4. Start containers back up
5. Show verification logs

---

## ✅ VERIFICATION

### 1. Check Beat is sending correct task name

```bash
docker logs -f wardops-celery-beat-prod
```

**Expected output (wait up to 60 seconds):**
```
[INFO/MainProcess] Scheduler: Sending due task collect-interface-metrics (monitoring.tasks.collect_all_interface_metrics)
```

**Note:** Task name should now be `monitoring.tasks.collect_all_interface_metrics` (NOT `monitoring.tasks_interface_metrics.collect_all_interface_metrics_task`)

### 2. Check worker is receiving the task

```bash
docker logs -f wardops-worker-snmp-prod
```

**Expected output (within 60 seconds):**
```
[INFO/MainProcess] Task monitoring.tasks.collect_all_interface_metrics[uuid] received
[INFO/ForkPoolWorker-1] Collecting interface metrics for all devices
[INFO/ForkPoolWorker-1] Found X devices for metrics collection
[INFO/ForkPoolWorker-1] Task monitoring.tasks.collect_all_interface_metrics[uuid] succeeded
```

### 3. Check VictoriaMetrics has data

Wait 2-3 minutes for metrics to be collected and written, then:

```bash
curl -s "http://localhost:8428/api/v1/query?query=interface_oper_status{isp_provider!=\"\"}" | jq .
```

**Expected output:**
```json
{
  "status": "success",
  "data": {
    "result": [
      {
        "metric": {
          "device_ip": "10.195.57.5",
          "device_name": "Batumi3-881",
          "if_name": "FastEthernet3",
          "isp_provider": "magti",
          "interface_type": "isp"
        },
        "value": [1698408000, "1"]
      }
    ]
  }
}
```

**If empty:** Wait another 60 seconds for the next collection cycle.

### 4. Check UI shows correct ISP status

1. Open http://10.30.25.46:5001/monitor
2. Search for ".5" routers (type `.5` in search box)
3. Look at device 10.195.57.5 (Batumi3-881)
4. ISP badges should now show:
   - **Magti badge:** GREEN (if link is up) or RED (if link is down)
   - **Silknet badge:** GREEN (if link is up) or RED (if link is down)

**Note:** Currently only device 10.195.57.5 has SNMP accessible. Other .5 routers will show RED until SNMP is opened on them.

---

## 📊 EXPECTED RESULTS

### Before Fix
- ❌ Beat sending task with wrong name
- ❌ Worker never receiving task
- ❌ No data in VictoriaMetrics
- ❌ All ISP badges showing RED
- ❌ Interface metrics collection completely broken

### After Fix
- ✅ Beat sending task with correct name
- ✅ Worker receiving and executing task every 60 seconds
- ✅ VictoriaMetrics receiving interface_oper_status metrics
- ✅ ISP badges showing correct GREEN/RED status
- ✅ Interface metrics collection working as designed

---

## 🔍 RELATED FILES

### Task Decorators (Source of Truth)
- [monitoring/tasks_interface_metrics.py:115](monitoring/tasks_interface_metrics.py#L115) - `@shared_task(name="monitoring.tasks.collect_all_interface_metrics")`
- [monitoring/tasks_interface_metrics.py:20](monitoring/tasks_interface_metrics.py#L20) - `@shared_task(name="monitoring.tasks.collect_device_interface_metrics")`
- [monitoring/tasks_interface_discovery.py:421](monitoring/tasks_interface_discovery.py#L421) - `@shared_task(name="monitoring.tasks.discover_all_interfaces")`
- [monitoring/tasks_interface_discovery.py:345](monitoring/tasks_interface_discovery.py#L345) - `@shared_task(name="monitoring.tasks.discover_device_interfaces")`
- [monitoring/tasks_interface_discovery.py:521](monitoring/tasks_interface_discovery.py#L521) - `@shared_task(name="monitoring.tasks.cleanup_old_interfaces")`

### Celery Configuration
- [celery_app_v2_priority_queues.py:214-234](celery_app_v2_priority_queues.py#L214-L234) - Beat schedule (FIXED)
- [celery_app_v2_priority_queues.py:93-117](celery_app_v2_priority_queues.py#L93-L117) - Task routing (FIXED)

### Related Documentation
- [ISP-MONITORING-ARCHITECTURE-FIX.md](ISP-MONITORING-ARCHITECTURE-FIX.md) - VictoriaMetrics migration
- [ARCHITECTURE-REVIEW-COMPLETE.md](ARCHITECTURE-REVIEW-COMPLETE.md) - Architecture validation
- [PROJECT_KNOWLEDGE_BASE.md](PROJECT_KNOWLEDGE_BASE.md) - System overview

---

## 🎯 SUMMARY

**What was wrong:**
- Celery Beat schedule had task names that didn't match the @shared_task decorators
- Task routing configuration also had mismatched names
- Result: Tasks were sent but never received by the worker

**What was fixed:**
- Updated Beat schedule to use correct task names (monitoring.tasks.* instead of monitoring.tasks_interface_metrics.*)
- Updated task routing to match
- Added comments explaining the hardcoded task name pattern

**Impact:**
- Interface metrics collection now works
- ISP status badges will show correct status
- VictoriaMetrics receives interface_oper_status data
- No more silent task failures

**Risk:** Low - This is a configuration fix, no code logic changes

---

**Status:** ✅ FIXED AND READY FOR DEPLOYMENT
**Commit:** afe362d - "CRITICAL FIX: Correct Celery task names for interface metrics collection"
**Deployment Script:** `./deploy-task-name-fix.sh`
**Estimated Downtime:** <1 minute (only Beat and SNMP worker restart)

---

*This was a TASK NAME MISMATCH bug - Beat was broadcasting to an address that didn't exist, and the worker was listening on a different address. Now they match!*
