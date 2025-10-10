"""
WARD Tech Solutions - Devices Router
Handles device listing and details
"""
import logging
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from auth import get_current_active_user, require_manager_or_admin
from database import PingResult, User, UserRole, get_db
from monitoring.device_manager import DeviceManager
from monitoring.models import AlertHistory, MonitoringMode, StandaloneDevice
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
    db: Session = Depends(get_db),
):
    """Get devices with optional filters and user permissions"""
    manager = DeviceManager(db, request)
    mode = manager.get_active_mode()

    if mode == MonitoringMode.ZABBIX:
        return await _get_zabbix_devices(request, region, branch, device_type, current_user)

    return _get_standalone_devices(db, region, branch, device_type, current_user)


@router.get("/{device_id}")
async def get_device_details(
    request: Request,
    device_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get detailed information about a specific device"""
    manager = DeviceManager(db, request)
    mode = manager.get_active_mode()

    if mode == MonitoringMode.ZABBIX:
        details = await run_in_executor(request.app.state.zabbix.get_host_details, device_id)
        if details:
            return details
        return JSONResponse(status_code=404, content={"error": "Device not found"})

    try:
        device_uuid = uuid.UUID(device_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid device ID"})

    device = db.query(StandaloneDevice).filter_by(id=device_uuid).first()
    if not device:
        return JSONResponse(status_code=404, content={"error": "Device not found"})

    response = _standalone_device_to_payload(db, device)
    return response


@router.put("/{hostid}")
async def update_device(
    request: Request,
    hostid: str,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db),
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

    manager = DeviceManager(db, request)
    mode = manager.get_active_mode()

    if mode == MonitoringMode.ZABBIX:
        zabbix = request.app.state.zabbix

        try:
            inventory = {}
            if update_data.region is not None:
                inventory["location"] = update_data.region
            if update_data.branch is not None:
                inventory["site_city"] = update_data.branch

            if inventory:
                update_result = await run_in_executor(lambda: zabbix.update_host(hostid, inventory=inventory))

                if not update_result.get("success"):
                    raise Exception(update_result.get("message", "Unknown error"))

            return {
                "status": "success",
                "message": "Device updated successfully",
                "hostid": hostid,
                "updated_fields": {"region": update_data.region, "branch": update_data.branch},
            }
        except Exception as e:
            logger.error(f"Failed to update device {hostid}: {e}")
            return JSONResponse(status_code=500, content={"error": f"Failed to update device: {str(e)}"})

    try:
        device_uuid = uuid.UUID(hostid)
    except ValueError:
        return {
            "hostid": hostid,
            "history": [],
            "time_range": time_range,
        }

    device = db.query(StandaloneDevice).filter_by(id=device_uuid).first()
    if not device:
        return JSONResponse(status_code=404, content={"error": "Device not found"})

    fields = device.custom_fields or {}
    if update_data.region is not None:
        fields["region"] = update_data.region
    if update_data.branch is not None:
        fields["branch"] = update_data.branch
    device.custom_fields = fields
    db.commit()

    return {
        "status": "success",
        "message": "Device updated successfully",
        "hostid": hostid,
        "updated_fields": {"region": update_data.region, "branch": update_data.branch},
    }


async def _get_zabbix_devices(
    request: Request,
    region: Optional[str],
    branch: Optional[str],
    device_type: Optional[str],
    current_user: User,
):
    zabbix = request.app.state.zabbix
    groupids = get_monitored_groupids()

    if region:
        devices = await run_in_executor(zabbix.get_devices_by_region, region)
    elif branch:
        devices = await run_in_executor(zabbix.get_devices_by_branch, branch)
    elif device_type:
        devices = await run_in_executor(zabbix.get_devices_by_type, device_type)
    else:
        devices = await run_in_executor(lambda: zabbix.get_all_hosts(group_ids=groupids))

    if current_user.role != UserRole.ADMIN:
        if current_user.region:
            devices = [d for d in devices if d.get("region") == current_user.region]
        if current_user.branches:
            allowed = [b.strip() for b in current_user.branches.split(",") if b.strip()]
            devices = [d for d in devices if d.get("branch") in allowed]

    return devices


def _get_standalone_devices(
    db: Session,
    region: Optional[str],
    branch: Optional[str],
    device_type: Optional[str],
    current_user: User,
):
    query = db.query(StandaloneDevice)

    if device_type:
        query = query.filter(StandaloneDevice.device_type == device_type)

    devices = query.all()
    payload = []

    for device in devices:
        fields = device.custom_fields or {}
        if region and fields.get("region") != region:
            continue
        if branch and fields.get("branch") != branch:
            continue

        if current_user.role != UserRole.ADMIN:
            if current_user.region and fields.get("region") != current_user.region:
                continue
            if current_user.branches:
                allowed = [b.strip() for b in current_user.branches.split(",") if b.strip()]
                if allowed and fields.get("branch") not in allowed:
                    continue

        payload.append(_standalone_device_to_payload(db, device))

    return payload


def _standalone_device_to_payload(db: Session, device: StandaloneDevice) -> Dict:
    fields = device.custom_fields or {}
    ping = (
        db.query(PingResult)
        .filter(PingResult.device_ip == device.ip)
        .order_by(PingResult.timestamp.desc())
        .first()
    )

    alert_count = (
        db.query(AlertHistory)
        .filter(AlertHistory.device_id == device.id, AlertHistory.resolved_at.is_(None))
        .count()
    )

    ping_status = "Unknown"
    ping_response_time = None
    last_check = None
    available = "Unknown"
    if ping:
        ping_status = "Up" if ping.is_reachable else "Down"
        ping_response_time = ping.avg_rtt_ms
        last_check = int(ping.timestamp.timestamp()) if ping.timestamp else None
        available = "Available" if ping.is_reachable else "Unavailable"
    else:
        ping_status = fields.get("ping_status", "Unknown")
        ping_response_time = fields.get("ping_response_time")
        available = fields.get("available", "Unknown")
        synced_at = fields.get("synced_at")
        if synced_at:
            try:
                last_check = int(datetime.fromisoformat(synced_at).timestamp())
            except ValueError:
                last_check = None

    return {
        "hostid": str(device.id),
        "hostname": device.hostname or device.name,
        "display_name": device.name,
        "name": device.name,
        "branch": fields.get("branch", ""),
        "region": fields.get("region", ""),
        "ip": device.ip,
        "device_type": device.device_type or fields.get("device_type", ""),
        "status": "Enabled" if device.enabled else "Disabled",
        "enabled": device.enabled,
        "available": available,
        "ping_status": ping_status,
        "ping_response_time": ping_response_time,
        "last_check": last_check or 0,
        "groups": device.tags or [],
        "problems": alert_count,
        "triggers": [],
        "latitude": fields.get("latitude"),
        "longitude": fields.get("longitude"),
        "vendor": device.vendor,
        "model": device.model,
        "created_at": device.created_at.isoformat() if device.created_at else None,
    }


def _store_ping_result(
    db: Session,
    device_id: str,
    device_name: str,
    ip: str,
    result,
    response_time: Optional[float],
    timeout: bool = False,
) -> None:
    def _to_int(value: Optional[float]) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return None

    pkt_sent = 4
    pkt_received = 0 if timeout else (4 if result and result.returncode == 0 else 0)
    packet_loss = 100 if pkt_received == 0 else 0

    ping_record = PingResult(
        device_ip=ip,
        device_name=device_name,
        packets_sent=pkt_sent,
        packets_received=pkt_received,
        packet_loss_percent=packet_loss,
        min_rtt_ms=_to_int(response_time),
        avg_rtt_ms=_to_int(response_time),
        max_rtt_ms=_to_int(response_time),
        is_reachable=not timeout and pkt_received > 0,
    )
    db.add(ping_record)
    db.commit()


@router.get("/{hostid}/history")
async def get_device_history(
    request: Request,
    hostid: str,
    time_range: str = "24h",  # 24h, 7d, 30d
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get real ping history for a device"""
    import time

    manager = DeviceManager(db, request)
    mode = manager.get_active_mode()

    if mode == MonitoringMode.ZABBIX:
        zabbix = request.app.state.zabbix
        loop = asyncio.get_event_loop()
        time_map = {"24h": 86400, "7d": 604800, "30d": 2592000}
        time_from = int(time.time()) - time_map.get(time_range, 86400)
        history = await loop.run_in_executor(None, lambda: zabbix.get_device_ping_history(hostid, time_from))
        return {"hostid": hostid, "history": history, "time_range": time_range}

    try:
        device_uuid = uuid.UUID(hostid)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid device ID"})

    device = db.query(StandaloneDevice).filter_by(id=device_uuid).first()
    if not device:
        return {"hostid": hostid, "history": [], "time_range": time_range}

    time_map = {"24h": 86400, "7d": 604800, "30d": 2592000}
    cutoff = datetime.utcfromtimestamp(time.time() - time_map.get(time_range, 86400))

    ping_rows = (
        db.query(PingResult)
        .filter(PingResult.device_ip == device.ip, PingResult.timestamp >= cutoff)
        .order_by(PingResult.timestamp.desc())
        .limit(200)
        .all()
    )

    history = [
        {
            "clock": int(row.timestamp.timestamp()) if row.timestamp else None,
            "value": row.avg_rtt_ms or 0,
            "reachable": row.is_reachable,
        }
        for row in ping_rows
    ]

    return {"hostid": hostid, "history": history, "time_range": time_range}


@router.post("/{device_id}/ping")
async def ping_device(
    request: Request,
    device_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Execute ping command for a device"""
    import subprocess
    import time

    manager = DeviceManager(db, request)
    mode = manager.get_active_mode()

    if mode == MonitoringMode.ZABBIX:
        zabbix = request.app.state.zabbix
        loop = asyncio.get_event_loop()
        device = await loop.run_in_executor(None, lambda: zabbix.get_host_details(device_id))
        if not device:
            return JSONResponse(status_code=404, content={"error": "Device not found"})
        ip = device.get("ip")
        device_name = device.get("display_name")
    else:
        try:
            device_uuid = uuid.UUID(device_id)
        except ValueError:
            return JSONResponse(status_code=400, content={"error": "Invalid device ID"})

        standalone = db.query(StandaloneDevice).filter_by(id=device_uuid).first()
        if not standalone:
            return JSONResponse(status_code=404, content={"error": "Device not found"})
        ip = standalone.ip
        device_name = standalone.name

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

        if success:
            _store_ping_result(db, device_id, device_name, ip, result, response_time)

        return {
            "success": success,
            "ip": ip,
            "response_time": response_time or (elapsed_time // 4 if success else None),
            "output": result.stdout[:500],
            "error": result.stderr[:500] if not success else None,
        }

    except subprocess.TimeoutExpired:
        _store_ping_result(db, device_id, device_name, ip, None, None, timeout=True)
        return {
            "success": False,
            "ip": ip,
            "response_time": None,
            "error": "Ping timeout (10s)",
        }
    except Exception as e:
        logger.error(f"Failed to ping device {device_id}: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to ping device: {str(e)}"})
