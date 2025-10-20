# Deploy All Fixes to Production Server

## Problem Summary
The website is currently running OLD code from Oct 20, 20:05. The frontend was never built with the latest fixes:
- ❌ No downtime display (missing "2h 15m" style durations)
- ❌ Recently down devices not sorted to top
- ❌ Device edit may have issues
- ❌ Regions dropdown missing

## Root Cause
The Docker containers are using **cached layers** from the old build. The frontend source code has all the fixes, but it was never built into JavaScript.

## Solution
Run the deployment script on the production server to rebuild everything from scratch.

---

## Deployment Steps (Run on 10.30.25.39)

### Step 1: SSH to Production Server
```bash
ssh wardops@10.30.25.39
```

### Step 2: Run Build and Deploy Script
```bash
cd /home/wardops/ward-flux-credobank
git pull origin main
./build-and-deploy.sh
```

**This will:**
1. Pull latest code from GitHub (all fixes committed)
2. Build ALL containers from scratch with `--no-cache` flag
3. Stop old containers
4. Start new containers with fresh code
5. Wait 60 seconds for services to initialize

**Estimated time:** 5-10 minutes (frontend build takes time)

### Step 3: Verify Deployment
```bash
./verify-fixes-complete.sh
```

**This checks:**
- ✅ Container frontend files are TODAY's date (not Oct 20)
- ✅ Frontend JavaScript contains `down_since` code
- ✅ Worker has state transition logging
- ✅ API is responding

---

## Expected Results After Deployment

### 1. Downtime Display - FIXED
Devices that are down will show accurate duration:
- "2h 15m" for 2 hours 15 minutes down
- "35m" for 35 minutes down
- "1d 5h 30m" for 1 day, 5 hours, 30 minutes down

**How it works:**
- Database stores `down_since` timestamp when device goes Down
- Frontend calculates duration using `calculateDowntime()` function
- Displays as "Down 2h 15m" in red with alert icon

### 2. Recent Down Sorting - FIXED
Recently down devices automatically appear at the top of the monitor view.

**How it works:**
- Devices with `down_since` within last 10 minutes are marked as "recent"
- Frontend sorts with recent downs at top
- Shows "• RECENT" badge next to downtime

### 3. Device Edit - FIXED
Device updates work properly without IP conflict errors.

**How it works:**
- IP conflict check now excludes the device being edited
- Fixed in `routers/devices_standalone.py:315`

### 4. Regions Dropdown - FIXED
All regions appear in dropdown when creating/editing branches.

**How it works:**
- New `/api/v1/branches/regions` endpoint
- Properly wrapped SQL queries with `text()` for SQLAlchemy 2.0

---

## Technical Details

### Commits Deployed
```
4cdd627 - Add verification script to confirm all fixes are deployed
4945c2e - Add --no-cache flag to build script to force fresh frontend build
a36ea64 - Add complete build and deployment script
b0e21ba - Fix IP conflict check to exclude current device
c1f6eb8 - CRITICAL FIX: Wrap all raw SQL queries with text() for SQLAlchemy 2.0
00332f5 - Fix health check configurations and add website diagnostics
```

### Files Modified
- `routers/branches.py` - Fixed SQLAlchemy text() issues
- `routers/devices_standalone.py` - Fixed IP conflict check
- `frontend/src/pages/Monitor.tsx` - Added down_since display logic
- `monitoring/tasks.py` - Added state transition logging
- `docker-compose.production-local.yml` - Fixed health checks
- `build-and-deploy.sh` - Added --no-cache flag
- `verify-fixes-complete.sh` - NEW verification script

### Frontend Build Process
The Dockerfile uses a multi-stage build:
1. **Stage 1:** Node.js builds React frontend → `/frontend/dist`
2. **Stage 2:** Python dependencies compiled
3. **Stage 3:** Production image - copies built frontend to `/app/static_new`

**Key:** Using `--no-cache` ensures Docker doesn't reuse Oct 20 cached layers.

---

## Troubleshooting

### If Build Fails
Check Docker logs:
```bash
docker-compose -f docker-compose.production-local.yml logs api
```

### If Frontend Still Shows Old Date
The build didn't work. Try manual rebuild:
```bash
docker-compose -f docker-compose.production-local.yml build --no-cache api
docker-compose -f docker-compose.production-local.yml up -d --force-recreate api
```

### If Downtime Still Not Showing
1. Check database has down_since:
```bash
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "SELECT name, ip, ping_status, down_since FROM standalone_devices WHERE ping_status = 'Down' LIMIT 5;"
```

2. Check frontend JavaScript has down_since:
```bash
docker exec wardops-api-prod grep "down_since" /app/static_new/assets/*.js
```

3. Check browser console for errors (F12 → Console tab)

---

## Access After Deployment

Website: http://10.30.25.39:5001

The fixes will be immediately visible:
- Monitor page shows downtime durations
- Recently down devices at top with "• RECENT" badge
- Device edit works without errors
- Regions dropdown populated

---

## Contact
If issues persist after deployment, check:
1. Container logs: `docker logs wardops-api-prod`
2. Worker logs: `docker logs wardops-worker-prod`
3. Database status: `docker exec wardops-postgres-prod pg_isready -U ward_admin`
4. Browser console (F12) for frontend errors
