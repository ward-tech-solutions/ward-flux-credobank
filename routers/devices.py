"""
WARD Tech Solutions - Devices Router
Handles device listing and details
"""
import logging
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from auth import get_current_active_user, require_manager_or_admin
from database import User, UserRole
from routers.utils import get_monitored_groupids, run_in_executor

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


@router.get("")
async def get_devices(
    request: Request,
    region: Optional[str] = None,
    branch: Optional[str] = None,
    device_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
):
    """Get devices with optional filters and user permissions"""
    zabbix = request.app.state.zabbix

    # Get monitored group IDs
    groupids = get_monitored_groupids()

    if region:
        devices = await run_in_executor(zabbix.get_devices_by_region, region)
    elif branch:
        devices = await run_in_executor(zabbix.get_devices_by_branch, branch)
    elif device_type:
        devices = await run_in_executor(zabbix.get_devices_by_type, device_type)
    else:
        loop = asyncio.get_event_loop()
        devices = await loop.run_in_executor(None, lambda: zabbix.get_all_hosts(group_ids=groupids))

    # Apply user permission filtering (non-admin users)
    if current_user.role != UserRole.ADMIN:
        # Filter by region if user has regional restriction
        if current_user.region:
            devices = [d for d in devices if d.get("region") == current_user.region]

        # Filter by branches if user has branch restrictions
        if current_user.branches:
            allowed_branches = [b.strip() for b in current_user.branches.split(",")]
            devices = [d for d in devices if d.get("branch") in allowed_branches]

    return devices


@router.get("/{hostid}")
async def get_device_details(request: Request, hostid: str):
    """Get detailed information about a specific device"""
    zabbix = request.app.state.zabbix
    details = await run_in_executor(zabbix.get_host_details, hostid)

    if details:
        return details
    return JSONResponse(status_code=404, content={"error": "Device not found"})


@router.put("/{hostid}")
async def update_device(
    request: Request,
    hostid: str,
    current_user: User = Depends(require_manager_or_admin),
):
    """Update device region/branch assignment"""
    from pydantic import BaseModel

    class DeviceUpdate(BaseModel):
        region: Optional[str] = None
        branch: Optional[str] = None

    data = await request.json()
    update_data = DeviceUpdate(**data)

    # For now, we'll store this in Zabbix host inventory or tags
    # This is a simplified implementation - you may want to enhance this
    # to actually update Zabbix host inventory fields

    zabbix = request.app.state.zabbix

    try:
        # Build inventory update for Zabbix
        # Zabbix uses inventory fields to store custom data
        inventory = {}
        if update_data.region is not None:
            inventory["location"] = update_data.region
        if update_data.branch is not None:
            inventory["site_city"] = update_data.branch

        # Update host inventory in Zabbix
        if inventory:
            update_result = await run_in_executor(
                lambda: zabbix.update_host(hostid, inventory=inventory)
            )

            if not update_result.get("success"):
                raise Exception(update_result.get("message", "Unknown error"))

        return {
            "status": "success",
            "message": "Device updated successfully",
            "hostid": hostid,
            "updated_fields": {
                "region": update_data.region,
                "branch": update_data.branch,
            },
        }
    except Exception as e:
        logger.error(f"Failed to update device {hostid}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to update device: {str(e)}"},
        )


@router.get("/{hostid}/history")
async def get_device_history(
    request: Request,
    hostid: str,
    time_range: str = "24h",  # 24h, 7d, 30d
    current_user: User = Depends(get_current_active_user),
):
    """Get real ping history from Zabbix for a device"""
    import time

    zabbix = request.app.state.zabbix
    loop = asyncio.get_event_loop()

    # Convert time range to seconds
    time_map = {"24h": 86400, "7d": 604800, "30d": 2592000}
    time_from = int(time.time()) - time_map.get(time_range, 86400)

    history = await loop.run_in_executor(
        None,
        lambda: zabbix.get_device_ping_history(hostid, time_from)
    )
    return {"hostid": hostid, "history": history, "time_range": time_range}


@router.post("/{hostid}/ping")
async def ping_device(
    request: Request,
    hostid: str,
    current_user: User = Depends(get_current_active_user),
):
    """Execute ping command for a device"""
    import subprocess
    import time

    zabbix = request.app.state.zabbix

    # Get device details to get IP
    loop = asyncio.get_event_loop()
    device = await loop.run_in_executor(
        None,
        lambda: zabbix.get_host_details(hostid)
    )

    if not device:
        return JSONResponse(
            status_code=404,
            content={"error": "Device not found"}
        )

    ip = device.get("ip")
    if not ip:
        return JSONResponse(
            status_code=400,
            content={"error": "Device has no IP address"}
        )

    try:
        # Execute ping command (platform-independent)
        import platform
        param = "-n" if platform.system().lower() == "windows" else "-c"

        start_time = time.time()
        result = subprocess.run(
            ["ping", param, "4", ip],
            capture_output=True,
            text=True,
            timeout=10
        )
        elapsed_time = int((time.time() - start_time) * 1000)

        success = result.returncode == 0

        # Parse response time from output
        response_time = None
        if success:
            # Try to extract time from output
            output_lower = result.stdout.lower()
            if "time=" in output_lower:
                # Extract time value
                import re
                time_match = re.search(r'time[=<](\d+\.?\d*)\s*ms', output_lower)
                if time_match:
                    response_time = float(time_match.group(1))

        return {
            "success": success,
            "ip": ip,
            "response_time": response_time or elapsed_time // 4 if success else None,
            "output": result.stdout[:500],  # Limit output
            "error": result.stderr[:500] if not success else None
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "ip": ip,
            "response_time": None,
            "error": "Ping timeout (10s)"
        }
    except Exception as e:
        logger.error(f"Failed to ping device {hostid}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to ping device: {str(e)}"}
        )
