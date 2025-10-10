"""
WARD Tech Solutions - Zabbix Integration Router
Handles Zabbix host management, alerts, groups, templates, and search
"""
import logging
import asyncio
from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_active_user
from database import User, UserRole, get_db
from monitoring.models import AlertHistory, MonitoringMode, MonitoringProfile
from routers.utils import get_monitored_groupids, run_in_executor

# Thread pool executor
import concurrent.futures

logger = logging.getLogger(__name__)

executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

# Create router
router = APIRouter(prefix="/api/v1/zabbix", tags=["zabbix"])


# Pydantic models for request validation
class CreateHostRequest(BaseModel):
    hostname: str
    visible_name: str
    ip_address: str
    group_ids: List[str]
    template_ids: List[str]


class UpdateHostRequest(BaseModel):
    hostname: Optional[str] = None
    visible_name: Optional[str] = None
    ip_address: Optional[str] = None
    branch: Optional[str] = None


@router.get("/alerts")
async def get_alerts(request: Request, db: Session = Depends(get_db)):
    """Get all active alerts"""
    profile = db.query(MonitoringProfile).filter_by(is_active=True).first()
    mode = profile.mode if profile else MonitoringMode.STANDALONE

    if mode == MonitoringMode.ZABBIX:
        zabbix = request.app.state.zabbix
        return await run_in_executor(zabbix.get_active_alerts)

    alerts = (
        db.query(AlertHistory)
        .filter(AlertHistory.resolved_at.is_(None))
        .order_by(AlertHistory.triggered_at.desc())
        .limit(100)
        .all()
    )

    return [
        {
            "id": str(alert.id),
            "device_id": str(alert.device_id) if alert.device_id else None,
            "severity": alert.severity.value if hasattr(alert.severity, "value") else alert.severity,
            "message": alert.message,
            "value": alert.value,
            "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None,
        }
        for alert in alerts
    ]


@router.get("/mttr/stats")
async def get_mttr_stats(request: Request):
    """Get MTTR statistics"""
    zabbix = request.app.state.zabbix
    stats = await run_in_executor(zabbix.get_mttr_stats)
    return stats


@router.get("/groups")
async def get_groups(request: Request):
    """Get all host groups"""
    zabbix = request.app.state.zabbix
    groups = await run_in_executor(zabbix.get_all_groups)
    return groups


@router.get("/templates")
async def get_templates(request: Request):
    """Get all templates"""
    zabbix = request.app.state.zabbix
    templates = await run_in_executor(zabbix.get_all_templates)
    return templates


@router.post("/hosts")
async def create_host(request: Request, host_data: CreateHostRequest):
    """Create a new host in Zabbix"""
    zabbix = request.app.state.zabbix

    result = await run_in_executor(
        lambda: zabbix.create_host(
            hostname=host_data.hostname,
            visible_name=host_data.visible_name,
            ip_address=host_data.ip_address,
            group_ids=host_data.group_ids,
            template_ids=host_data.template_ids,
        )
    )

    if result.get("success"):
        return result
    return JSONResponse(status_code=500, content=result)


@router.put("/hosts/{hostid}")
async def update_host(request: Request, hostid: str, host_data: UpdateHostRequest):
    """Update host properties"""
    zabbix = request.app.state.zabbix

    update_data = host_data.dict(exclude_unset=True)
    if not update_data:
        return JSONResponse(status_code=400, content={"error": "No fields to update"})

    result = await run_in_executor(lambda: zabbix.update_host(hostid, **update_data))

    if result.get("success"):
        return result
    return JSONResponse(status_code=500, content=result)


@router.delete("/hosts/{hostid}")
async def delete_host(request: Request, hostid: str):
    """Delete a host"""
    zabbix = request.app.state.zabbix
    result = await run_in_executor(zabbix.delete_host, hostid)

    if result.get("success"):
        return result
    return JSONResponse(status_code=500, content=result)


@router.get("/search")
async def search_devices(
    request: Request,
    q: Optional[str] = None,
    region: Optional[str] = None,
    branch: Optional[str] = None,
    device_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
):
    """Advanced search endpoint with user permissions"""
    zabbix = request.app.state.zabbix
    groupids = get_monitored_groupids()
    loop = asyncio.get_event_loop()
    devices = await loop.run_in_executor(executor, lambda: zabbix.get_all_hosts(group_ids=groupids))

    # Apply user permission filtering first (non-admin users)
    if current_user.role != UserRole.ADMIN:
        # Filter by region if user has regional restriction
        if current_user.region:
            devices = [d for d in devices if d.get("region") == current_user.region]

        # Filter by branches if user has branch restrictions
        if current_user.branches:
            allowed_branches = [b.strip() for b in current_user.branches.split(",")]
            devices = [d for d in devices if d.get("branch") in allowed_branches]

    # Apply text search
    if q:
        query = q.lower()
        devices = [
            d
            for d in devices
            if (
                query in d["display_name"].lower()
                or query in d["branch"].lower()
                or query in d["ip"].lower()
                or query in d["region"].lower()
            )
        ]

    # Apply filters
    if region:
        devices = [d for d in devices if d["region"] == region]
    if branch:
        devices = [d for d in devices if branch.lower() in d["branch"].lower()]
    if device_type:
        devices = [d for d in devices if d["device_type"] == device_type]
    if status:
        devices = [d for d in devices if d["ping_status"] == status]

    return devices
