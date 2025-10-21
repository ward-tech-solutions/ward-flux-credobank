# WARD OPS CredoBank - Comprehensive QA Test Plan

**Date:** October 21, 2025
**Version:** Post-Downtime Fix
**Tester:** Claude Code
**Environment:** Production Local (10.30.25.39:5001)

---

## Executive Summary

This QA plan ensures all critical functionality works correctly after fixing the downtime display issue. The root cause was the API not returning the `down_since` field for standalone devices, despite it being tracked in the database.

---

## Test Categories

### 1. CRITICAL - Monitor Page Functionality
**Priority:** P0 - System Core Feature
**Impact:** High - Primary user interface

#### 1.1 Downtime Display ✓ (FIXED)
- [x] **Test:** Devices that are Down show accurate downtime (e.g., "2h 15m")
- [x] **Verify:** down_since field present in API response
- [x] **Check:** Frontend calculateDowntime() processes timestamps correctly
- **Expected:** "Down 2h 15m" format, not just "Down"
- **Status:** FIXED - Line 311 added to routers/devices.py

#### 1.2 Recent Down Devices Sorting
- [ ] **Test:** Recently down devices (< 10 minutes) appear at top
- [ ] **Verify:** "• RECENT" badge displays
- [ ] **Check:** Sorting algorithm in Monitor.tsx works
- **Expected:** Most recently down devices first
- **API Endpoint:** GET /api/v1/devices

#### 1.3 Device Status Indicators
- [ ] **Test:** Green checkmark for Up devices
- [ ] **Test:** Red alert triangle for Down devices
- [ ] **Test:** Gray icon for Unknown status
- **Expected:** Clear visual indicators for all states

#### 1.4 Auto-Refresh
- [ ] **Test:** Page refreshes every 30 seconds
- [ ] **Verify:** "Refreshing in Xs" countdown displays
- [ ] **Check:** No duplicate requests during refresh
- **Expected:** Smooth updates without flashing

#### 1.5 Filtering
- [ ] **Test:** Region dropdown shows all regions
- [ ] **Test:** Branch dropdown shows all branches
- [ ] **Test:** Device type filter works (ATM, PayBox, Switch, etc.)
- [ ] **Test:** Status filter (All/Up/Down)
- [ ] **Test:** Search by device name/IP
- **Expected:** Instant filtering without API call

#### 1.6 Grid/Table View Toggle
- [ ] **Test:** Grid view displays device cards
- [ ] **Test:** Table view shows data in rows
- [ ] **Test:** Regions view groups by region
- [ ] **Check:** Preference persists on page reload

---

### 2. CRITICAL - Device Management (Devices Page)
**Priority:** P0 - Core CRUD Operations

#### 2.1 Device Creation
- [ ] **Test:** Add new standalone device via form
- [ ] **Verify:** All required fields validated (name, IP)
- [ ] **Test:** IP format validation (IPv4)
- [ ] **Test:** Duplicate IP detection
- [ ] **Check:** Device appears in list immediately
- **API Endpoint:** POST /api/v1/standalone-devices

#### 2.2 Device Edit ✓ (FIXED)
- [x] **Test:** Edit existing device without IP conflict error
- [x] **Verify:** IP conflict check excludes current device
- [x] **Check:** Changes persist in database
- **Expected:** Successful update without 400 errors
- **Status:** FIXED - Line 315 in routers/devices_standalone.py

#### 2.3 Device Delete
- [ ] **Test:** Delete device with confirmation modal
- [ ] **Verify:** Device removed from database
- [ ] **Check:** Associated ping results handled
- [ ] **Test:** Cannot delete device with active alerts
- **API Endpoint:** DELETE /api/v1/standalone-devices/{id}

#### 2.4 Bulk Operations
- [ ] **Test:** Bulk enable/disable devices
- [ ] **Test:** Bulk delete with confirmation
- [ ] **Test:** Bulk tag assignment
- **Expected:** Operations complete without errors

---

### 3. CRITICAL - Branch & Region Management
**Priority:** P0 - Core Data Structure

#### 3.1 Regions Dropdown ✓ (FIXED)
- [x] **Test:** Regions dropdown populated dynamically
- [x] **Verify:** `/api/v1/branches/regions` endpoint works
- [x] **Check:** All raw SQL queries wrapped in text()
- **Expected:** All distinct regions from database
- **Status:** FIXED - SQLAlchemy text() wrapping

#### 3.2 Branch CRUD
- [ ] **Test:** Create new branch
- [ ] **Test:** Edit branch (name, region, address)
- [ ] **Test:** Delete branch (with device reassignment)
- [ ] **Test:** Branch statistics accurate
- **API Endpoint:** /api/v1/branches

#### 3.3 Branch-Device Association
- [ ] **Test:** Assign device to branch
- [ ] **Test:** Move device between branches
- [ ] **Test:** Branch device count updates
- [ ] **Test:** Filter devices by branch

---

### 4. HIGH - Worker Monitoring Tasks
**Priority:** P1 - Background Processing

#### 4.1 Ping Task ✓ (VERIFIED)
- [x] **Test:** Ping task executes every 30 seconds
- [x] **Verify:** down_since set when device goes Down
- [x] **Verify:** down_since cleared when device comes Up
- [x] **Check:** State transition logs appear
- **Expected:** "Device [name] went DOWN" in logs
- **Container:** wardops-worker-prod

#### 4.2 SNMP Polling Task
- [ ] **Test:** SNMP task polls devices with credentials
- [ ] **Verify:** System uptime collected
- [ ] **Verify:** Interface statistics collected
- [ ] **Check:** Metrics written to VictoriaMetrics
- **Expected:** No SNMP timeout errors for configured devices

#### 4.3 Celery Worker Health
- [ ] **Test:** Worker container healthy
- [ ] **Test:** Beat scheduler running
- [ ] **Test:** 60 concurrent workers processing tasks
- [ ] **Check:** No stuck tasks in queue
- **Command:** `celery -A celery_app inspect active`

---

### 5. HIGH - API Endpoints
**Priority:** P1 - Data Integrity

#### 5.1 Devices API
- [ ] **GET /api/v1/devices** - Returns all devices with down_since
- [ ] **GET /api/v1/devices/{id}** - Returns device details
- [ ] **POST /api/v1/standalone-devices** - Creates device
- [ ] **PUT /api/v1/standalone-devices/{id}** - Updates device
- [ ] **DELETE /api/v1/standalone-devices/{id}** - Deletes device

#### 5.2 Branches API ✓ (FIXED)
- [x] **GET /api/v1/branches/regions** - Returns distinct regions
- [ ] **GET /api/v1/branches** - Returns all branches
- [ ] **GET /api/v1/branches/{id}** - Returns branch details
- [ ] **GET /api/v1/branches/{id}/devices** - Returns branch devices
- [ ] **POST /api/v1/branches** - Creates branch
- [ ] **PUT /api/v1/branches/{id}** - Updates branch
- [ ] **DELETE /api/v1/branches/{id}** - Deletes branch (with device handling)

#### 5.3 Dashboard API
- [ ] **GET /api/v1/dashboard/stats** - Returns overall statistics
- [ ] **GET /api/v1/dashboard/alerts** - Returns active alerts
- [ ] **GET /api/v1/dashboard/recent-changes** - Returns recent events

#### 5.4 Alerts API
- [ ] **GET /api/v1/alerts** - Returns all alerts
- [ ] **POST /api/v1/alerts** - Creates alert rule
- [ ] **PUT /api/v1/alerts/{id}/acknowledge** - Acknowledges alert
- [ ] **DELETE /api/v1/alerts/{id}** - Deletes alert rule

---

### 6. MEDIUM - Dashboard Page
**Priority:** P2 - Information Display

#### 6.1 Statistics Cards
- [ ] **Test:** Total devices count accurate
- [ ] **Test:** Online/Offline counts match reality
- [ ] **Test:** Uptime percentage calculated correctly
- [ ] **Test:** Recent events list populates

#### 6.2 Charts & Graphs
- [ ] **Test:** Device status pie chart renders
- [ ] **Test:** Uptime trend line chart displays
- [ ] **Test:** Regional distribution chart accurate
- [ ] **Test:** Charts update on data change

---

### 7. MEDIUM - Alert System
**Priority:** P2 - Notification System

#### 7.1 Alert Rules
- [ ] **Test:** Create alert rule for device down
- [ ] **Test:** Alert triggers when condition met
- [ ] **Test:** Alert clears when condition resolves
- [ ] **Test:** Alert notification sent (if configured)

#### 7.2 Alert History
- [ ] **Test:** Historical alerts stored
- [ ] **Test:** Filter alerts by severity
- [ ] **Test:** Filter alerts by device
- [ ] **Test:** Export alert history

---

### 8. MEDIUM - Authentication & Authorization
**Priority:** P2 - Security

#### 8.1 Login
- [ ] **Test:** Login with correct credentials
- [ ] **Test:** Login fails with incorrect credentials
- [ ] **Test:** JWT token generated and stored
- [ ] **Test:** Token refresh works

#### 8.2 User Roles
- [ ] **Test:** Admin sees all regions
- [ ] **Test:** Regional user sees only their region
- [ ] **Test:** Read-only user cannot edit
- [ ] **Test:** Unauthorized API calls return 401

---

### 9. LOW - Additional Features
**Priority:** P3 - Nice to Have

#### 9.1 Topology Map
- [ ] **Test:** Topology graph renders
- [ ] **Test:** Device connections display
- [ ] **Test:** Interactive node selection

#### 9.2 Reports
- [ ] **Test:** Generate uptime report
- [ ] **Test:** Export to PDF/CSV
- [ ] **Test:** Schedule automated reports

#### 9.3 Discovery
- [ ] **Test:** Network scan functionality
- [ ] **Test:** Device auto-discovery
- [ ] **Test:** Import discovered devices

---

## Database Integrity Tests

### 10.1 Schema Validation
- [x] **Test:** down_since column exists in standalone_devices
- [ ] **Test:** All foreign keys valid
- [ ] **Test:** Indexes exist for performance
- [ ] **Test:** No orphaned records

### 10.2 Data Consistency
- [ ] **Test:** All devices have valid branch_id or NULL
- [ ] **Test:** All ping_results reference valid device IPs
- [ ] **Test:** All alert_history references valid device_id
- [ ] **Test:** Monitoring mode set correctly (standalone only)

### 10.3 Migrations
- [ ] **Test:** All migrations applied successfully
- [ ] **Test:** Database version matches code
- [ ] **Test:** Rollback capability tested

---

## Performance Tests

### 11.1 API Response Times
- [ ] **Test:** /api/v1/devices responds < 500ms (876 devices)
- [ ] **Test:** Dashboard loads < 1s
- [ ] **Test:** Device edit saves < 200ms
- [ ] **Test:** No N+1 query issues

### 11.2 Worker Performance
- [ ] **Test:** Ping tasks complete in < 3s
- [ ] **Test:** SNMP tasks complete in < 10s
- [ ] **Test:** No task timeouts
- [ ] **Test:** Queue depth stays < 100

### 11.3 Frontend Performance
- [ ] **Test:** Monitor page renders < 2s
- [ ] **Test:** Filtering instant (< 100ms)
- [ ] **Test:** No memory leaks on long sessions
- [ ] **Test:** Bundle size < 2MB

---

## Browser Compatibility Tests

### 12.1 Browsers
- [ ] Chrome/Chromium (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

### 12.2 Responsive Design
- [ ] Desktop (1920x1080)
- [ ] Laptop (1366x768)
- [ ] Tablet (768x1024)
- [ ] Mobile (375x667)

---

## Error Handling Tests

### 13.1 Network Errors
- [ ] **Test:** API timeout handling
- [ ] **Test:** Connection lost recovery
- [ ] **Test:** Retry logic for failed requests

### 13.2 Data Validation
- [ ] **Test:** Invalid IP format rejected
- [ ] **Test:** Empty required fields prevented
- [ ] **Test:** SQL injection attempts blocked
- [ ] **Test:** XSS attempts sanitized

### 13.3 User Feedback
- [ ] **Test:** Success messages display
- [ ] **Test:** Error messages user-friendly
- [ ] **Test:** Loading indicators present
- [ ] **Test:** Confirmation modals for destructive actions

---

## Regression Tests (Recently Fixed Issues)

### 14.1 Downtime Display Bug ✓
- [x] **Issue:** down_since not returned in API
- [x] **Fix:** Added line 311 to routers/devices.py
- [x] **Test:** API includes down_since for down devices
- [x] **Test:** Frontend displays "Down 2h 15m"
- **Status:** VERIFIED WORKING

### 14.2 Device Edit IP Conflict ✓
- [x] **Issue:** Editing device IP shows conflict with itself
- [x] **Fix:** Line 315 excludes current device from check
- [x] **Test:** Edit device IP without false conflict
- **Status:** VERIFIED WORKING

### 14.3 SQLAlchemy text() Errors ✓
- [x] **Issue:** Raw SQL queries not wrapped in text()
- [x] **Fix:** Wrapped all queries in routers/branches.py
- [x] **Test:** All branch endpoints work
- [x] **Test:** Regions dropdown populates
- **Status:** VERIFIED WORKING

### 14.4 Docker Compose ContainerConfig Bug
- [ ] **Issue:** Cannot recreate containers
- [ ] **Workaround:** Use down + up instead of restart
- [ ] **Test:** Document proper deployment procedure
- **Status:** KNOWN ISSUE - WORKAROUND EXISTS

---

## Test Execution Priority

### Phase 1: Critical Fixes Verification (Today)
1. ✅ Downtime display working
2. ✅ Device edit IP conflict fixed
3. ✅ Regions dropdown populated
4. ✅ Worker tracking down_since
5. ✅ Database schema correct

### Phase 2: Core Functionality (Next)
6. Monitor page full test
7. Device CRUD operations
8. Branch management
9. API endpoint validation
10. Worker task verification

### Phase 3: Extended Features (After Core)
11. Dashboard functionality
12. Alert system
13. Authentication/Authorization
14. Performance testing
15. Browser compatibility

### Phase 4: Documentation & Handoff
16. Test report generation
17. Known issues documentation
18. Deployment procedure
19. Monitoring guide
20. Troubleshooting playbook

---

## Known Issues & Limitations

1. **Docker Compose Bug:** ContainerConfig KeyError when recreating containers
   - **Workaround:** Use `docker-compose down` then `up -d`
   - **Impact:** Deployment process requires extra step

2. **Zabbix Mode Disabled:** System only uses standalone monitoring
   - **Status:** Intentional - no Zabbix integration
   - **Impact:** None - working as designed

3. **SNMP Timeouts:** Some devices don't respond to SNMP
   - **Status:** Expected - device configuration issue
   - **Impact:** SNMP metrics not available for those devices

---

## Test Automation Recommendations

### Automated Test Suite Needed:
1. **Unit Tests:** API endpoints, data models, business logic
2. **Integration Tests:** Worker tasks, database operations
3. **E2E Tests:** Critical user workflows (Playwright/Cypress)
4. **Performance Tests:** Load testing, stress testing
5. **CI/CD Pipeline:** Run tests on every commit

### Coverage Goals:
- API endpoints: 80%+ coverage
- Business logic: 90%+ coverage
- Critical paths: 100% coverage
- Frontend components: 70%+ coverage

---

## Test Report Template

After completing tests, generate report with:
- Total tests executed
- Pass/Fail/Blocked count
- Critical issues found
- Severity breakdown
- Time to resolution estimates
- Recommended fixes prioritization

---

## Contact & Escalation

**QA Lead:** Claude Code
**Product Owner:** User
**Dev Team:** WARD Tech Solutions
**Production URL:** http://10.30.25.39:5001
**GitHub Repo:** https://github.com/ward-tech-solutions/ward-flux-credobank

---

**Document Version:** 1.0
**Last Updated:** October 21, 2025
**Next Review:** After Phase 2 completion
