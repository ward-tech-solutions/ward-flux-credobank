"""
WARD Tech Solutions - Dashboard Router
Handles health checks and dashboard statistics
"""
import logging
import asyncio
import concurrent.futures
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from auth import get_current_active_user
from database import PingResult, User, UserRole, get_db
from monitoring.device_manager import DeviceManager
from monitoring.models import AlertHistory, AlertSeverity, MonitoringMode, StandaloneDevice
from routers.utils import extract_city_from_hostname, run_in_executor

logger = logging.getLogger(__name__)

# Thread pool executor
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

# Create router
router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/health")
async def health_check(request: Request):
    """Health check endpoint for monitoring and load balancers"""
    try:
        # Check database connection
        from database import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "components": {"database": db_status, "api": "healthy"},
    }


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    request: Request,
    region: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get dashboard statistics with optional region filter and user permissions"""
    return _get_standalone_dashboard_stats(db, region, current_user)


def _get_standalone_dashboard_stats(
    db: Session, region_filter: Optional[str], current_user: User
) -> dict:
    """Compute dashboard stats using standalone inventory and metrics."""
    devices: List[StandaloneDevice] = db.query(StandaloneDevice).all()

    allowed_branches: List[str] = []
    if current_user.branches:
        allowed_branches = [b.strip() for b in current_user.branches.split(",") if b.strip()]

    filtered_devices: List[StandaloneDevice] = []
    for device in devices:
        fields = device.custom_fields or {}
        device_region = fields.get("region")
        device_branch = fields.get("branch")

        if region_filter and device_region != region_filter:
            continue

        if current_user.role != UserRole.ADMIN:
            if current_user.region and device_region != current_user.region:
                continue
            if allowed_branches and device_branch not in allowed_branches:
                continue

        filtered_devices.append(device)

    ping_lookup = _latest_ping_lookup(
        db, [device.ip for device in filtered_devices if device.ip]
    )

    total_devices = len(filtered_devices)
    online_devices = offline_devices = warning_devices = 0

    device_types: Dict[str, Dict[str, int]] = {}
    regions_stats: Dict[str, Dict[str, float]] = {}

    for device in filtered_devices:
        fields = device.custom_fields or {}
        device_region = fields.get("region") or "Unknown"
        latitude = fields.get("latitude")
        longitude = fields.get("longitude")

        ping = ping_lookup.get(device.ip)
        if ping:
            status = "Up" if ping.is_reachable else "Down"
        else:
            status = fields.get("ping_status") or "Unknown"

        if status == "Up":
            online_devices += 1
        elif status == "Down":
            offline_devices += 1
        else:
            warning_devices += 1

        dtype = device.device_type or fields.get("device_type") or "Unknown"
        dtype_entry = device_types.setdefault(dtype, {"total": 0, "online": 0, "offline": 0})
        dtype_entry["total"] += 1
        if status == "Up":
            dtype_entry["online"] += 1
        elif status == "Down":
            dtype_entry["offline"] += 1

        region_entry = regions_stats.setdefault(
            device_region,
            {"total": 0, "online": 0, "offline": 0, "latitude": None, "longitude": None},
        )
        region_entry["total"] += 1
        if status == "Up":
            region_entry["online"] += 1
        elif status == "Down":
            region_entry["offline"] += 1

        if latitude is not None and region_entry.get("latitude") is None:
            region_entry["latitude"] = latitude
            region_entry["longitude"] = longitude

    uptime_percentage = round((online_devices / total_devices * 100) if total_devices > 0 else 0, 2)

    device_ids = [device.id for device in filtered_devices]
    alert_query = db.query(AlertHistory).filter(AlertHistory.resolved_at.is_(None))
    if device_ids:
        alert_query = alert_query.filter(AlertHistory.device_id.in_(device_ids))

    active_alerts = alert_query.count()
    critical_alerts = alert_query.filter(
        AlertHistory.severity.in_([AlertSeverity.CRITICAL, AlertSeverity.HIGH])
    ).count()

    return {
        "total_devices": total_devices,
        "online_devices": online_devices,
        "offline_devices": offline_devices,
        "warning_devices": warning_devices,
        "uptime_percentage": uptime_percentage,
        "active_alerts": active_alerts,
        "critical_alerts": critical_alerts,
        "device_types": device_types,
        "regions_stats": regions_stats,
    }


def _latest_ping_lookup(db: Session, ips: List[str]) -> Dict[str, PingResult]:
    if not ips:
        return {}

    rows = (
        db.query(PingResult)
        .filter(PingResult.device_ip.in_(ips))
        .order_by(PingResult.device_ip, PingResult.timestamp.desc())
        .all()
    )

    lookup: Dict[str, PingResult] = {}
    for row in rows:
        ip = row.device_ip
        if ip and ip not in lookup:
            lookup[ip] = row
    return lookup


