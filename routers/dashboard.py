"""
WARD Tech Solutions - Dashboard Router
Handles health checks and dashboard statistics
"""
import logging
import asyncio
import concurrent.futures
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

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
    """
    Comprehensive health check endpoint for monitoring and load balancers

    Checks:
    - Database connectivity and performance
    - Redis connectivity
    - VictoriaMetrics availability
    - Celery worker status
    - Disk space (if available)

    Returns:
        Status: healthy, degraded, or critical
        Component details for each service
    """
    from database import SessionLocal
    from sqlalchemy import text
    import os
    import shutil

    components = {}
    overall_status = "healthy"

    # 1. Database Health Check
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT 1"))
        db.close()
        components["database"] = "healthy"
    except Exception as e:
        components["database"] = f"unhealthy: {str(e)}"
        overall_status = "critical"

    # 2. Redis Health Check
    try:
        import redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url, socket_connect_timeout=5)
        r.ping()
        components["redis"] = "healthy"
    except Exception as e:
        components["redis"] = f"unhealthy: {str(e)}"
        overall_status = "degraded"

    # 3. VictoriaMetrics Health Check
    try:
        from monitoring.victoria.client import get_victoria_client
        vm_client = get_victoria_client()
        if vm_client.health_check():
            components["victoriametrics"] = "healthy"
        else:
            components["victoriametrics"] = "unhealthy"
            overall_status = "degraded"
    except Exception as e:
        components["victoriametrics"] = f"unhealthy: {str(e)}"
        overall_status = "degraded"

    # 4. Celery Workers Health Check
    try:
        from celery import current_app
        inspect = current_app.control.inspect()
        stats = inspect.stats()
        worker_count = len(stats) if stats else 0

        if worker_count == 0:
            components["celery_workers"] = f"critical: No workers running"
            overall_status = "critical"
        elif worker_count < 5:
            components["celery_workers"] = f"degraded: Only {worker_count} workers (expected 50)"
            if overall_status == "healthy":
                overall_status = "degraded"
        else:
            components["celery_workers"] = f"healthy ({worker_count} workers)"
    except Exception as e:
        components["celery_workers"] = f"error: {str(e)}"
        overall_status = "degraded"

    # 5. Disk Space Check (optional, non-critical)
    try:
        stat = shutil.disk_usage('/')
        free_gb = stat.free / (1024**3)
        total_gb = stat.total / (1024**3)
        percent_free = (stat.free / stat.total) * 100

        if percent_free < 10:
            components["disk_space"] = f"critical: {free_gb:.1f}GB free ({percent_free:.1f}%)"
            overall_status = "critical"
        elif percent_free < 20:
            components["disk_space"] = f"warning: {free_gb:.1f}GB free ({percent_free:.1f}%)"
            if overall_status == "healthy":
                overall_status = "degraded"
        else:
            components["disk_space"] = f"healthy: {free_gb:.1f}GB free ({percent_free:.1f}%)"
    except Exception as e:
        components["disk_space"] = f"unknown: {str(e)}"

    # 6. API itself is always healthy if we got here
    components["api"] = "healthy"

    return {
        "status": overall_status,
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "components": components,
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
            # PHASE 3: ping is now a dict (from VictoriaMetrics), not PingResult object
            status = "Up" if ping.get("is_reachable") else "Down"
        else:
            # PHASE 3 ROBUSTNESS: If VM fails, use device.down_since (always current!)
            # device.down_since is updated in real-time by monitoring worker
            status = "Down" if device.down_since else "Up"

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


def _latest_ping_lookup(db: Session, ips: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    PHASE 3: Get latest ping results from VictoriaMetrics

    ROBUSTNESS: If VictoriaMetrics fails, returns empty dict.
    Callers will use device.down_since for status (always current).

    Returns: Dict mapping IP -> ping data

    CRITICAL: After Phase 2, PostgreSQL ping_results table stops growing!
              DO NOT fallback to PostgreSQL - data will be stale!
    """
    if not ips:
        return {}

    # PHASE 3: Query VictoriaMetrics
    try:
        from utils.victoriametrics_client import vm_client
        return vm_client.get_latest_ping_for_devices(ips)
    except Exception as e:
        logger.error(f"Failed to query VictoriaMetrics for ping data: {e}")
        logger.warning("Returning empty ping data - dashboard will use device.down_since for status")
        # PHASE 3 FIX: DO NOT fallback to PostgreSQL after Phase 2!
        # PostgreSQL ping_results table is stale after Phase 2 deployment.
        # Callers will use device.down_since field which is always current.
        return {}


