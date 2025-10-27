# Deploy ISP Badge Updates NOW

## ✅ What's Ready to Deploy

### Changes Completed:
1. ✅ **Removed ICMP badge** from Monitor page (card + table views)
2. ✅ **GREEN ISP badges** when UP (Magti + Silknet)
3. ✅ **RED ISP badges** when DOWN
4. ✅ **Device API** includes `isp_interfaces` field
5. ✅ **Interface discovery** fixed (SNMPResult bug)

### What You'll See After Deployment:
- .5 routers show: **SNMP**, **Magti**, **Silknet** badges
- Magti/Silknet are **GREEN** when links are UP
- Magti/Silknet turn **RED** when links go DOWN
- Both ISPs independent (one green, one red possible)

---

## 🚀 DEPLOYMENT STEPS

### Step 1: Deploy Code (5 minutes)
```bash
# SSH to production server
cd /home/wardops/ward-flux-credobank
git pull origin main

# Rebuild API container (includes React frontend)
docker compose -f docker-compose.production-priority-queues.yml stop api
docker compose -f docker-compose.production-priority-queues.yml rm -f api
docker compose -f docker-compose.production-priority-queues.yml build --no-cache api
docker compose -f docker-compose.production-priority-queues.yml up -d api

# Wait for API to start
sleep 15

# Check API is running
docker logs wardops-api-prod --tail 20
```

### Step 2: Discover ISP Interfaces (10 minutes)
```bash
# Run interface discovery for all .5 routers
./deploy-isp-monitoring.sh
```

This will:
- Test discovery on 10.195.57.5
- Discover all ~93 .5 routers
- Save ISP interfaces to database

### Step 3: Verify (2 minutes)
```bash
# Check database has ISP interfaces
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT COUNT(*) as total_isp_interfaces
FROM device_interfaces
WHERE interface_type = 'isp';"

# Should show ~186-279 interfaces (93 routers × 2-3 ISPs each)
```

### Step 4: View Frontend
1. Open http://10.30.25.46:5001/monitor
2. Search for any .5 router (e.g., "57.5")
3. You should see:
   - **SNMP** badge (green)
   - **Magti** badge (green if up, red if down)
   - **Silknet** badge (green if up, red if down)

---

## 🟢 Expected Result

### Before (Screenshot you showed):
- ICMP badge (blue)
- Magti badge (purple) ❌
- Silknet badge (orange) ❌

### After (What you'll see):
- SNMP badge (green)
- **Magti badge (green)** ✅
- **Silknet badge (green)** ✅

Both turn **RED** if ISP link goes down!

---

## ⏭️ Next Steps (After Deployment)

Once badges are working, we can add:

### 1. Device Detail Page ISP Status
Add ISP badges to DeviceDetails.tsx showing:
- Current ISP status
- Interface names
- Last seen timestamp

### 2. Topology Integration
Update Topology.tsx to:
- Highlight .5 routers
- Show ISP connection flows
- Color code by ISP provider

### 3. ISP Interface Polling
Add scheduled SNMP polling to update oper_status in real-time:
- Poll every 60 seconds
- Update device_interfaces.oper_status
- Store metrics in VictoriaMetrics

### 4. ISP Alerts
Create alert rules:
- "ISP Link Down - Magti"
- "ISP Link Down - Silknet"
- "Both ISPs Down" (CRITICAL)

---

## 🐛 Troubleshooting

### Problem: API container won't start
```bash
# Check logs
docker logs wardops-api-prod

# If frontend build fails, rebuild without cache
docker compose -f docker-compose.production-priority-queues.yml build --no-cache api
```

### Problem: Badges not showing
```bash
# Check if ISP data exists
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT * FROM device_interfaces
WHERE device_id = (SELECT id FROM standalone_devices WHERE ip = '10.195.57.5')
AND interface_type = 'isp';"

# If no data, run discovery
./deploy-isp-monitoring.sh
```

### Problem: Badges show unknown status
- This means interface discovery hasn't run yet
- Or the device doesn't have ISP interfaces in database
- Run `./deploy-isp-monitoring.sh` to populate data

---

## 📝 Files Changed

**Backend:**
- `routers/devices_standalone.py` - Added isp_interfaces field
- `monitoring/tasks_interface_discovery.py` - Fixed SNMPResult bug
- `trigger_discovery.py` - Manual discovery tool

**Frontend:**
- `frontend/src/pages/Monitor.tsx` - Updated ISP badges (card + table)

**All changes committed and pushed to main branch.**

---

**Status:** READY TO DEPLOY
**Time Required:** ~20 minutes total
**Risk:** Low (only frontend changes + data population)
