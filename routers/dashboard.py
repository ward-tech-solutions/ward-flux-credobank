"""
WARD Tech Solutions - Dashboard Router
Handles health checks and dashboard statistics
"""
import logging
import asyncio
import concurrent.futures
import sqlite3
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request

from auth import get_current_active_user
from database import User, UserRole
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

        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Check Zabbix connection
    try:
        zabbix = request.app.state.zabbix
        zabbix_status = "connected" if zabbix.zapi else "disconnected"
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
    request: Request, region: Optional[str] = None, current_user: User = Depends(get_current_active_user)
):
    """Get dashboard statistics with optional region filter and user permissions"""
    zabbix = request.app.state.zabbix

    # Get monitored groups from DB
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

    # If no groups configured, fall back to old behavior
    if not monitored_groups:
        logger.info("[DEBUG] No monitored groups, getting all hosts")
        devices = await run_in_executor(zabbix.get_all_hosts)
    else:
        # Get devices from configured groups only using group IDs
        monitored_groupids = [g["groupid"] for g in monitored_groups]
        logger.info(f"[DEBUG] Fetching hosts for group IDs: {monitored_groupids}")
        loop = asyncio.get_event_loop()
        devices = await loop.run_in_executor(executor, lambda: zabbix.get_all_hosts(group_ids=monitored_groupids))
        logger.info(f"[DEBUG] Retrieved {len(devices)} devices from Zabbix")

    # Apply region filter if requested
    if region:
        devices = [d for d in devices if d.get("region") == region]

    # Apply user permission filtering (non-admin users)
    if current_user.role != UserRole.ADMIN:
        # Filter by region if user has regional restriction
        if current_user.region:
            devices = [d for d in devices if d.get("region") == current_user.region]

        # Filter by branches if user has branch restrictions
        if current_user.branches:
            allowed_branches = [b.strip() for b in current_user.branches.split(",")]
            devices = [d for d in devices if d.get("branch") in allowed_branches]

    alerts = await run_in_executor(zabbix.get_active_alerts)

    total_devices = len(devices)
    online_devices = len([h for h in devices if h.get("ping_status") == "Up"])
    offline_devices = len([h for h in devices if h.get("ping_status") == "Down"])
    warning_devices = len([h for h in devices if h.get("ping_status") == "Unknown"])

    # Device types statistics
    device_types = {}
    for host in devices:
        dt = host["device_type"]
        if dt not in device_types:
            device_types[dt] = {"total": 0, "online": 0, "offline": 0}
        device_types[dt]["total"] += 1
        if host.get("ping_status") == "Up":
            device_types[dt]["online"] += 1
        elif host.get("ping_status") == "Down":
            device_types[dt]["offline"] += 1

    # Region statistics with coordinates from DB
    regions_stats = {}
    for host in devices:
        # Extract city from hostname
        city_name = extract_city_from_hostname(host.get("host", host.get("display_name", "")))

        # Lookup city in DB to get region and coordinates
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

            if region_name not in regions_stats:
                regions_stats[region_name] = {
                    "total": 0,
                    "online": 0,
                    "offline": 0,
                    "latitude": city_data["latitude"],
                    "longitude": city_data["longitude"],
                }

            regions_stats[region_name]["total"] += 1
            if host.get("ping_status") == "Up":
                regions_stats[region_name]["online"] += 1
            elif host.get("ping_status") == "Down":
                regions_stats[region_name]["offline"] += 1
        else:
            # Fallback to existing region field
            region_name = host.get("region", "Unknown")
            if region_name not in regions_stats:
                regions_stats[region_name] = {"total": 0, "online": 0, "offline": 0}
            regions_stats[region_name]["total"] += 1
            if host.get("ping_status") == "Up":
                regions_stats[region_name]["online"] += 1
            elif host.get("ping_status") == "Down":
                regions_stats[region_name]["offline"] += 1

    conn.close()

    return {
        "total_devices": total_devices,
        "online_devices": online_devices,
        "offline_devices": offline_devices,
        "warning_devices": warning_devices,
        "uptime_percentage": round((online_devices / total_devices * 100) if total_devices > 0 else 0, 2),
        "active_alerts": len(alerts),
        "critical_alerts": len([a for a in alerts if a["severity"] in ["High", "Disaster"]]),
        "device_types": device_types,
        "regions_stats": regions_stats,
    }
