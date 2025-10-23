# Deploy Diagnostics NOW - Quick Start

**Problem:** Device 10.195.83.252 not being pinged (last ping 27+ minutes ago)
**Goal:** Find out WHY (not just restart)
**User Requirement:** "restart is not SOLUTION!"

---

## 🚀 Deploy Diagnostics (5 minutes)

```bash
# Step 1: SSH to server
ssh wardops@credobank-server

# Step 2: Navigate to project
cd /home/wardops/ward-flux-credobank

# Step 3: Pull latest code
git pull origin main

# Step 4: Deploy diagnostic logging
./deploy-diagnostic-logging.sh
```

**The script will:**
1. Rebuild worker and beat with diagnostic logging
2. Restart containers
3. Wait 35 seconds for one ping cycle
4. Show initial diagnostic output

---

## 🔍 Monitor Logs (2-3 minutes)

**After deployment, run this:**

```bash
docker logs wardops-worker-prod -f | grep -E '(ping_all_devices|10.195.83.252)'
```

**Watch for 2-3 minutes** to see 4-5 ping cycles (every 30 seconds).

---

## 📊 What to Look For

### **Scenario 1: Device NOT Retrieved (Most Likely)**

```
ping_all_devices: Retrieved 874 enabled devices from database
ping_all_devices: Device IPs to ping: [10.x.x.x, ...] (no 10.195.83.252)
ping_all_devices: Target device 10.195.83.252 NOT FOUND in enabled devices query!
ping_all_devices: Device 10.195.83.252 exists but enabled=true
```

**This means:** SQLAlchemy query is not returning the device despite enabled=true
**Root cause:** Database session caching/isolation issue
**Fix:** Force session refresh before query

---

### **Scenario 2: Device Retrieved but Not Scheduled**

```
ping_all_devices: Retrieved 875 enabled devices from database
ping_all_devices: Device IPs to ping: [..., 10.195.83.252, ...]
ping_all_devices: Found target device 10.195.83.252
ping_all_devices: Scheduled 875 ping tasks
(No "EXECUTING ping" message)
```

**This means:** Device scheduled but ping task not executing
**Root cause:** Celery task routing or Redis queue issue
**Fix:** Check task queue and worker configuration

---

### **Scenario 3: Device Retrieved and Scheduled**

```
ping_all_devices: Found target device 10.195.83.252
ping_all_devices: Successfully scheduled ping for target device
ping_device: EXECUTING ping for TARGET device 10.195.83.252
```

**This means:** Everything working (device being pinged)
**Root cause:** Was a temporary issue, now resolved
**Action:** Monitor to ensure it continues

---

### **Scenario 4: No Monitoring Profile**

```
ping_all_devices: No active monitoring profile found
```

**This means:** Monitoring disabled at profile level
**Root cause:** Configuration issue
**Fix:** Enable monitoring profile in database

---

## 📋 Report Back With

After running logs for 2-3 minutes, report:

1. **Total devices retrieved:** `Retrieved X enabled devices`
2. **Is 10.195.83.252 in the list?** YES/NO
3. **Was ping scheduled for it?** YES/NO
4. **Did ping execute?** YES/NO (look for "EXECUTING ping")
5. **Any errors?** Copy error messages

---

## 🎯 Why This Matters

**Without diagnostics:**
- Restart → works temporarily → problem comes back
- No idea what's actually broken
- Can't fix root cause

**With diagnostics:**
- Know EXACTLY where failure occurs
- Can implement targeted fix
- Problem stays fixed permanently

---

## ⏱️ Timeline

1. **Deploy:** 2 minutes (rebuild + restart)
2. **Monitor:** 2-3 minutes (watch logs)
3. **Analyze:** 1 minute (identify scenario)
4. **Total:** ~5 minutes

Then we implement the **permanent fix** based on what we find.

---

**Ready? Run the commands above! ⬆️**
