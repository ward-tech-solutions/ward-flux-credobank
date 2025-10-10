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

    # Check Zabbix connection
    try:
        zabbix = getattr(request.app.state, "zabbix", None)
        if zabbix and getattr(zabbix, "zapi", None):
            zabbix_status = "connected"
        else:
            zabbix_status = "not_configured"
    except Exception as e:
        zabbix_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "components": {"database": db_status, "zabbix": zabbix_status, "api": "healthy"},
    }


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    request: Request,
    region: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get dashboard statistics with optional region filter and user permissions"""
    manager = DeviceManager(db, request)
    mode = manager.get_active_mode()

    if mode == MonitoringMode.zabbix:
        return await _get_zabbix_dashboard_stats(request, region, current_user)

    if mode == MonitoringMode.standalone:
        return _get_standalone_dashboard_stats(db, region, current_user)

    if mode == MonitoringMode.hybrid:
        standalone_stats = _get_standalone_dashboard_stats(db, region, current_user)
        zabbix_stats = await _get_zabbix_dashboard_stats(request, region, current_user)
        return _merge_dashboard_stats(standalone_stats, zabbix_stats)

    logger.warning("Unknown monitoring mode detected, defaulting to standalone stats")
    return _get_standalone_dashboard_stats(db, region, current_user)


async def _get_zabbix_dashboard_stats(request: Request, region: Optional[str], current_user: User) -> dict:
    """Existing Zabbix-powered dashboard statistics."""
    zabbix = request.app.state.zabbix

    conn = sqlite3.connect("data/ward_ops.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT groupid, display_name
        FROM monitored_hostgroups
        WHERE is_active = 1
    """
    )
    monitored_groups = [dict(row) for row in cursor.fetchall()]

    logger.info(f"[DEBUG] Monitored groups from DB: {monitored_groups}")

    if not monitored_groups:
        logger.info("[DEBUG] No monitored groups, getting all hosts")
        devices = await run_in_executor(zabbix.get_all_hosts)
    else:
        monitored_groupids = [g["groupid"] for g in monitored_groups]
        logger.info(f"[DEBUG] Fetching hosts for group IDs: {monitored_groupids}")
        loop = asyncio.get_event_loop()
        devices = await loop.run_in_executor(
            executor, lambda: zabbix.get_all_hosts(group_ids=monitored_groupids)
        )
        logger.info(f"[DEBUG] Retrieved {len(devices)} devices from Zabbix")

    if region:
        devices = [d for d in devices if d.get("region") == region]

    if current_user.role != UserRole.ADMIN:
        if current_user.region:
            devices = [d for d in devices if d.get("region") == current_user.region]

        if current_user.branches:
            allowed_branches = [b.strip() for b in current_user.branches.split(",")]
            devices = [d for d in devices if d.get("branch") in allowed_branches]

    alerts = await run_in_executor(zabbix.get_active_alerts)

    total_devices = len(devices)
    online_devices = len([h for h in devices if h.get("ping_status") == "Up"])
    offline_devices = len([h for h in devices if h.get("ping_status") == "Down"])
    warning_devices = len([h for h in devices if h.get("ping_status") == "Unknown"])

    device_types: Dict[str, Dict[str, int]] = {}
    for host in devices:
        dt = host.get("device_type") or "Unknown"
        entry = device_types.setdefault(dt, {"total": 0, "online": 0, "offline": 0})
        entry["total"] += 1
        if host.get("ping_status") == "Up":
            entry["online"] += 1
        elif host.get("ping_status") == "Down":
            entry["offline"] += 1

    regions_stats: Dict[str, Dict[str, float]] = {}
    for host in devices:
        city_name = extract_city_from_hostname(host.get("host", host.get("display_name", "")))

        cursor.execute(
            """
            SELECT r.name_en as region, c.latitude, c.longitude
            FROM georgian_cities c
            JOIN georgian_regions r ON c.region_id = r.id
            WHERE c.name_en LIKE ? AND c.is_active = 1
            LIMIT 1
        """,
            (f"%{city_name}%",),
        )

        city_data = cursor.fetchone()

        if city_data:
            city_data = dict(city_data)
            region_name = city_data["region"]
            entry = regions_stats.setdefault(
                region_name,
                {
                    "total": 0,
                    "online": 0,
                    "offline": 0,
                    "latitude": city_data["latitude"],
                    "longitude": city_data["longitude"],
                },
            )
        else:
            region_name = host.get("region", "Unknown")
            entry = regions_stats.setdefault(region_name, {"total": 0, "online": 0, "offline": 0})

        entry["total"] += 1
        if host.get("ping_status") == "Up":
            entry.setdefault("online", 0)
            entry["online"] += 1
        elif host.get("ping_status") == "Down":
            entry.setdefault("offline", 0)
            entry["offline"] += 1

    conn.close()

    uptime_percentage = round((online_devices / total_devices * 100) if total_devices > 0 else 0, 2)

    return {
        "total_devices": total_devices,
        "online_devices": online_devices,
        "offline_devices": offline_devices,
        "warning_devices": warning_devices,
        "uptime_percentage": uptime_percentage,
        "active_alerts": len(alerts),
        "critical_alerts": len([a for a in alerts if a.get("severity") in ["High", "Disaster"]]),
        "device_types": device_types,
        "regions_stats": regions_stats,
    }


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


def _merge_dashboard_stats(primary: dict, secondary: dict) -> dict:
    total_devices = primary["total_devices"] + secondary["total_devices"]
    online_devices = primary["online_devices"] + secondary["online_devices"]
    offline_devices = primary["offline_devices"] + secondary["offline_devices"]
    warning_devices = primary["warning_devices"] + secondary["warning_devices"]

    uptime_percentage = round((online_devices / total_devices * 100) if total_devices > 0 else 0, 2)

    device_types = _merge_device_type_stats(
        primary.get("device_types", {}), secondary.get("device_types", {})
    )
    regions_stats = _merge_region_stats(
        primary.get("regions_stats", {}), secondary.get("regions_stats", {})
    )

    return {
        "total_devices": total_devices,
        "online_devices": online_devices,
        "offline_devices": offline_devices,
        "warning_devices": warning_devices,
        "uptime_percentage": uptime_percentage,
        "active_alerts": primary.get("active_alerts", 0) + secondary.get("active_alerts", 0),
        "critical_alerts": primary.get("critical_alerts", 0) + secondary.get("critical_alerts", 0),
        "device_types": device_types,
        "regions_stats": regions_stats,
    }


def _merge_device_type_stats(*stats_dicts: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, int]]:
    merged: Dict[str, Dict[str, int]] = {}
    for stats in stats_dicts:
        for dtype, values in stats.items():
            entry = merged.setdefault(dtype, {"total": 0, "online": 0, "offline": 0})
            entry["total"] += values.get("total", 0)
            entry["online"] += values.get("online", 0)
            entry["offline"] += values.get("offline", 0)
    return merged


def _merge_region_stats(*stats_dicts: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    merged: Dict[str, Dict[str, float]] = {}
    for stats in stats_dicts:
        for region, values in stats.items():
            entry = merged.setdefault(
                region,
                {"total": 0, "online": 0, "offline": 0, "latitude": None, "longitude": None},
            )
            entry["total"] += values.get("total", 0)
            entry["online"] += values.get("online", 0)
            entry["offline"] += values.get("offline", 0)
            if entry.get("latitude") is None and values.get("latitude") is not None:
                entry["latitude"] = values.get("latitude")
                entry["longitude"] = values.get("longitude")
    return merged
