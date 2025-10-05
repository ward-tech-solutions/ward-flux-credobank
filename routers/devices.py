"""
WARD Tech Solutions - Devices Router
Handles device listing and details
"""
import logging
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from auth import get_current_active_user
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
