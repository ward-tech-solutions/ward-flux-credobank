# Critical Frontend and Backend Fixes Required

**Date:** October 21, 2025
**Priority:** CRITICAL
**Issues:** 4 major problems identified

---

## ISSUE 1: Timezone Confusion in Downtime Display ❌

### Problem
Frontend shows "Down 4h 26m" but actual downtime is 31 minutes.

### Root Cause
- Database stores timestamps in **UTC**
- Server time is **+04** timezone
- `down_since`: 2025-10-21 **08:33:54** (UTC) = 12:33:54 (+04)
- Current time: 2025-10-21 **09:04:48** (UTC) = 13:04:48 (+04)
- **Actual downtime:** 31 minutes ✓

### BUT WAIT!
Zabbix shows device went down at **12:30:23**, our system shows **12:33:54** (+04 converted).

**The times are CORRECT!** The frontend is calculating correctly.

### Real Issue
Looking at the data again:
- `down_since`: **08:33:54 UTC**
- Current: **09:04:48 UTC**
- Difference: **31 minutes**

But frontend shows **4h 26m**!

This means the frontend is receiving a DIFFERENT timestamp or calculating wrong!

### Fix Required
**Check what timestamp the API is actually sending** to the frontend.

---

## ISSUE 2: Recently Down Devices Not Sorting to Top ❌

### Problem
New down devices don't appear at top of Monitor page.

### Root Cause
Sorting logic uses `last_check` timestamp instead of `down_since`:

```typescript
// Line 621 in Monitor.tsx - WRONG
const aDowntime = a.triggers?.[0] ? parseInt(a.triggers[0].lastchange) : a.last_check
const bDowntime = b.triggers?.[0] ? parseInt(b.triggers[0].lastchange) : b.last_check
```

### Fix Required
```typescript
// Should use down_since timestamp
const aDowntime = a.down_since ? new Date(a.down_since).getTime() : a.last_check
const bDowntime = b.down_since ? new Date(b.down_since).getTime() : b.last_check
```

---

## ISSUE 3: No Delete Button in Frontend ❌

### Problem
Cannot delete devices from UI.

### Current State
- Devices page has no delete button
- DELETE endpoint exists in backend: `DELETE /api/v1/standalone-devices/{device_id}`
- But frontend doesn't expose it

### Fix Required
Add delete button to Devices page with:
1. Delete icon button in device card/row
2. Confirmation dialog
3. Success/error toast notification
4. Refresh device list after deletion

---

## ISSUE 4: No Toast Notifications ❌

### Problem
No user feedback for operations (add device, duplicate IP, etc.)

### Current State
- `sonner` toast library is imported
- But not used for device operations

### Fix Required
Add toast notifications for:
1. **Add device success:** "Device added successfully"
2. **Add device error:** "Error: Device with IP X.X.X.X already exists"
3. **Update device success:** "Device updated successfully"
4. **Update device error:** Show specific error message
5. **Delete device success:** "Device deleted successfully"
6. **Delete device error:** Show error message

---

## PRIORITY FIX ORDER

### Priority 1: Fix Downtime Display (CRITICAL)
**Why:** Users seeing wrong downtime duration causes confusion

**Steps:**
1. Add debug logging to API to see what timestamp is being sent
2. Add debug logging to frontend to see what's being received
3. Check if ISO string parsing is correct
4. Fix timezone handling if needed

### Priority 2: Fix Sorting (HIGH)
**Why:** Recently down devices should be immediately visible

**Steps:**
1. Change sorting to use `down_since` timestamp
2. Test with device going down/up
3. Verify correct order

### Priority 3: Add Toast Notifications (MEDIUM)
**Why:** Users need feedback on their actions

**Steps:**
1. Add toast on device create
2. Add toast on device update
3. Add toast on device delete
4. Add toast on validation errors

### Priority 4: Add Delete Button (MEDIUM)
**Why:** Users need ability to remove devices

**Steps:**
1. Add delete button to Devices page
2. Add confirmation dialog
3. Call DELETE API
4. Show toast and refresh list

---

## DEBUGGING NEEDED FOR ISSUE 1

Run this to see what the API is actually returning:

```bash
# On server
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:5001/api/v1/devices | jq '.[] | select(.ip == "10.195.31.252") | {name, ip, down_since, last_check, ping_status}'
```

This will show:
- Exact timestamp being sent by API
- Format of the timestamp
- Whether it's in UTC or local time

Then we can see if the bug is:
1. API sending wrong timestamp
2. Frontend parsing timestamp incorrectly
3. Frontend calculating duration incorrectly

---

## EXPECTED TIMESTAMPS

For device at 10.195.31.252:

**Database (UTC):**
```
down_since: 2025-10-21 08:33:54.02276
```

**API should send (ISO format):**
```json
{
  "down_since": "2025-10-21T08:33:54.022760"
}
```

**Frontend should calculate:**
```
Current time (UTC): 2025-10-21T09:04:48
Down since (UTC): 2025-10-21T08:33:54
Difference: 31 minutes ✓
Display: "31m" ✓
```

**But frontend is showing: "4h 26m" ✗**

**This means:**
- Either API is sending wrong timestamp
- Or frontend is misinterpreting the timestamp

---

## NEXT STEPS

1. **Get API response** for the device
2. **Check frontend console** for received data
3. **Identify where calculation goes wrong**
4. **Apply fixes**

Once we see the actual API response, I can pinpoint the exact bug and fix all 4 issues.
