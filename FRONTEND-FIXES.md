# Frontend Critical Fixes - Implementation Guide

**Priority:** CRITICAL
**Files to modify:** Monitor.tsx, Devices.tsx, DeviceDetailsModal.tsx

---

## FIX 1: Monitor.tsx Sorting ✅ DONE

**File:** `frontend/src/pages/Monitor.tsx`
**Lines:** 620-628
**Status:** Fixed and ready to commit

**Change:** Use `down_since` timestamp for sorting instead of `last_check`

This ensures recently down devices appear at the top.

---

## FIX 2: Add Delete Functionality to Devices Page

**File:** `frontend/src/pages/Devices.tsx`

### Step 1: Import Trash icon
```typescript
import { Trash2 } from 'lucide-react'
```

### Step 2: Add delete mutation
```typescript
const deleteDeviceMutation = useMutation({
  mutationFn: (deviceId: string) => devicesAPI.deleteDevice(deviceId),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['devices'] })
    toast.success('Device deleted successfully')
    setDeleteDialogOpen(false)
    setDeviceToDelete(null)
  },
  onError: (error: any) => {
    toast.error(error.response?.data?.detail || 'Failed to delete device')
  }
})
```

### Step 3: Add state for delete dialog
```typescript
const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
const [deviceToDelete, setDeviceToDelete] = useState<Device | null>(null)
```

### Step 4: Add delete button to device card/row
In the device card/row actions, add:
```typescript
<Button
  variant="ghost"
  size="sm"
  onClick={() => {
    setDeviceToDelete(device)
    setDeleteDialogOpen(true)
  }}
  className="text-red-600 hover:text-red-700 hover:bg-red-50"
>
  <Trash2 className="h-4 w-4" />
</Button>
```

### Step 5: Add confirmation dialog
```typescript
{deleteDialogOpen && deviceToDelete && (
  <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
    <Card className="w-full max-w-md">
      <CardContent className="pt-6">
        <h3 className="text-lg font-semibold mb-2">Delete Device</h3>
        <p className="text-gray-600 mb-4">
          Are you sure you want to delete "{deviceToDelete.display_name}"?
          This action cannot be undone.
        </p>
        <div className="flex justify-end gap-2">
          <Button
            variant="outline"
            onClick={() => {
              setDeleteDialogOpen(false)
              setDeviceToDelete(null)
            }}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={() => deleteDeviceMutation.mutate(deviceToDelete.hostid)}
            disabled={deleteDeviceMutation.isPending}
          >
            {deleteDeviceMutation.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      </CardContent>
    </Card>
  </div>
)}
```

---

## FIX 3: Add Toast Notifications

### Device Creation (in form submit handler)
```typescript
const createMutation = useMutation({
  mutationFn: devicesAPI.createDevice,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['devices'] })
    toast.success('Device added successfully')
    setIsAddModalOpen(false)
    form.reset()
  },
  onError: (error: any) => {
    const errorMessage = error.response?.data?.detail || 'Failed to add device'
    toast.error(errorMessage)
  }
})
```

### Device Update
```typescript
const updateMutation = useMutation({
  mutationFn: ({ id, data }: { id: string, data: any }) =>
    devicesAPI.updateDevice(id, data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['devices'] })
    toast.success('Device updated successfully')
    setIsEditModalOpen(false)
  },
  onError: (error: any) => {
    const errorMessage = error.response?.data?.detail || 'Failed to update device'
    toast.error(errorMessage)
  }
})
```

### Duplicate IP Error Handling
The backend will return:
```json
{
  "detail": "Device with IP 10.195.31.252 already exists"
}
```

This will automatically show in the toast via `error.response?.data?.detail`.

---

## FIX 4: Debug Downtime Calculation

### Add console logging to Monitor.tsx

In the `calculateDowntime` function (line 53), add logging:
```typescript
const calculateDowntime = (device: Device) => {
  // Priority 2: Use down_since timestamp (accurate for standalone devices)
  if (device.ping_status === 'Down' && device.down_since) {
    const downSinceTime = new Date(device.down_since).getTime()
    const now = Date.now()
    const diff = now - downSinceTime

    // DEBUG: Log the calculation
    if (device.name.includes('khashuri')) {
      console.log('DEBUG khashuri-AP downtime:', {
        device_name: device.name,
        down_since_raw: device.down_since,
        down_since_parsed: new Date(device.down_since).toISOString(),
        downSinceTime: downSinceTime,
        now: now,
        diff_ms: diff,
        diff_minutes: diff / (1000 * 60)
      })
    }

    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))

    if (days > 0) return `${days}d ${hours}h ${minutes}m`
    if (hours > 0) return `${hours}h ${minutes}m`
    if (minutes > 0) return `${minutes}m`
    return '< 1m'
  }

  // ... rest of function
}
```

This will log in browser console what values are being calculated.

---

## TESTING CHECKLIST

### After applying fixes:

**Test 1: Sorting**
- [ ] Go to Monitor page
- [ ] Take a device down (unplug or block ping)
- [ ] Wait 30 seconds for it to be detected
- [ ] Verify device appears at top of list
- [ ] Verify it shows in "recently down" section

**Test 2: Delete**
- [ ] Go to Devices page
- [ ] Click delete button on a test device
- [ ] Confirm deletion in dialog
- [ ] Verify toast shows "Device deleted successfully"
- [ ] Verify device removed from list

**Test 3: Notifications**
- [ ] Try to add device with duplicate IP
- [ ] Verify toast shows error: "Device with IP X.X.X.X already exists"
- [ ] Add device with valid data
- [ ] Verify toast shows "Device added successfully"
- [ ] Update a device
- [ ] Verify toast shows "Device updated successfully"

**Test 4: Downtime**
- [ ] Open browser console (F12)
- [ ] Go to Monitor page
- [ ] Find khashuri-AP device
- [ ] Check console for DEBUG log
- [ ] Verify timestamps are correct
- [ ] Check if displayed downtime matches calculation

---

## EXPECTED BEHAVIOR AFTER FIXES

### Monitor Page:
1. ✅ Recently down devices at top
2. ✅ Sorted by most recent down first
3. ✅ Correct downtime duration displayed

### Devices Page:
1. ✅ Delete button visible on each device
2. ✅ Confirmation dialog before deletion
3. ✅ Success toast after deletion
4. ✅ Device removed from list

### All Pages with Device Operations:
1. ✅ Toast on success (green)
2. ✅ Toast on error (red)
3. ✅ Specific error messages (e.g., duplicate IP)
4. ✅ Loading states during operations

---

## API ENDPOINTS USED

**Delete Device:**
```
DELETE /api/v1/standalone-devices/{device_id}
Authorization: Bearer {token}
```

**Response:**
- Success (200): `{"message": "Device deleted successfully"}`
- Error (404): `{"detail": "Device not found"}`
- Error (403): `{"detail": "Not authorized"}`

**Already exists in:** `frontend/src/services/api.ts`

---

## DEPLOYMENT

After making changes:

1. **Commit changes:**
```bash
git add frontend/src/pages/Monitor.tsx
git add frontend/src/pages/Devices.tsx
git commit -m "Fix sorting, add delete button, and toast notifications"
git push origin client/credo-bank
```

2. **Rebuild frontend:**
```bash
# On production server
cd /home/wardops/ward-flux-credobank
docker-compose -f docker-compose.production-local.yml down
docker-compose -f docker-compose.production-local.yml up -d --build
```

3. **Verify fixes:**
- Test each functionality
- Check browser console for errors
- Verify all toasts appear correctly

---

## SUMMARY OF FILES TO MODIFY

1. ✅ **Monitor.tsx** - Sorting fixed (already done)
2. ⏳ **Devices.tsx** - Add delete button + notifications
3. ⏳ **Monitor.tsx** - Add debug logging for downtime

Total changes needed: Small additions to existing code, no major refactoring required.
