"""
WARD Tech Solutions - Devices Router
Handles device listing and details
"""
import logging
import asyncio
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from auth import get_current_active_user, require_manager_or_admin
from database import PingResult, User, UserRole, get_db
from monitoring.device_manager import DeviceManager
from monitoring.models import AlertHistory, MonitoringMode, StandaloneDevice
from routers.utils import get_monitored_groupids, run_in_executor
from utils.optimization_helpers import get_optimal_vm_step

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


def get_user_regions(user: User) -> Optional[List[str]]:
    """Get list of regions for a user, supporting both legacy region and regions array"""
    if user.regions:
        try:
            return json.loads(user.regions) if isinstance(user.regions, str) else user.regions
        except (json.JSONDecodeError, TypeError):
            pass
    if user.region:
        return [user.region]
    return None


def user_can_access_device(user: User, device: dict) -> bool:
    """Check if user has permission to access a device based on role and region/branch"""
    if user.role == UserRole.ADMIN:
        return True

    # Check regions for regional managers
    user_regions = get_user_regions(user)
    if user_regions:
        device_region = device.get("region")
        if device_region and device_region not in user_regions:
            return False

    # Check branches if specified
    if user.branches:
        allowed_branches = [b.strip() for b in user.branches.split(",") if b.strip()]
        device_branch = device.get("branch")
        if allowed_branches and device_branch not in allowed_branches:
            return False

    return True


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
    return _get_standalone_devices(db, region, branch, device_type, current_user)


@router.get("/{device_id}")
async def get_device_details(
    request: Request,
    device_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get detailed information about a specific device"""
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

    try:
        device_uuid = uuid.UUID(hostid)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid device ID format",
                "hostid": hostid,
            }
        )

    device = db.query(StandaloneDevice).filter_by(id=device_uuid).first()
    if not device:
        return JSONResponse(status_code=404, content={"error": "Device not found"})

    try:
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
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update device {hostid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update device: {str(e)}")


def _get_standalone_devices(
    db: Session,
    region: Optional[str],
    branch: Optional[str],
    device_type: Optional[str],
    current_user: User,
):
    from models import Branch
    from sqlalchemy import and_
    from sqlalchemy.sql import func

    query = db.query(StandaloneDevice)

    if device_type:
        query = query.filter(StandaloneDevice.device_type == device_type)

    devices = query.all()

    # PERFORMANCE OPTIMIZATION: Bulk fetch all related data
    # This replaces 2,628 queries (876 devices × 3 queries) with just 4 queries

    device_ips = [d.ip for d in devices if d.ip]
    device_ids = [d.id for d in devices]

    # Bulk query 1: Get latest ping for all devices
    # Use subquery to get latest timestamp per device, then join
    subq = (
        db.query(
            PingResult.device_ip,
            func.max(PingResult.timestamp).label('max_timestamp')
        )
        .filter(PingResult.device_ip.in_(device_ips))
        .group_by(PingResult.device_ip)
        .subquery()
    )

    latest_pings = (
        db.query(PingResult)
        .join(
            subq,
            and_(
                PingResult.device_ip == subq.c.device_ip,
                PingResult.timestamp == subq.c.max_timestamp
            )
        )
        .all()
    )
    ping_lookup = {ping.device_ip: ping for ping in latest_pings}

    # Bulk query 2: Get active alert counts for all devices
    alert_counts = (
        db.query(
            AlertHistory.device_id,
            func.count(AlertHistory.id).label('count')
        )
        .filter(
            AlertHistory.device_id.in_(device_ids),
            AlertHistory.resolved_at.is_(None)
        )
        .group_by(AlertHistory.device_id)
        .all()
    )
    alert_lookup = {str(device_id): count for device_id, count in alert_counts}

    # Bulk query 3: Get all branches
    branch_ids = [d.branch_id for d in devices if d.branch_id]
    if branch_ids:
        branches = db.query(Branch).filter(Branch.id.in_(branch_ids)).all()
        branch_lookup = {b.id: b for b in branches}
    else:
        branch_lookup = {}

    # Build payload using pre-fetched data (no more queries in loop!)
    payload = []
    for device in devices:
        fields = device.custom_fields or {}
        if region and fields.get("region") != region:
            continue
        if branch and fields.get("branch") != branch:
            continue

        # Apply region/branch filtering
        if not user_can_access_device(current_user, {
            "region": fields.get("region"),
            "branch": fields.get("branch")
        }):
            continue

        # Use pre-fetched data - no database queries here!
        ping = ping_lookup.get(device.ip)
        alert_count = alert_lookup.get(str(device.id), 0)
        branch_obj = branch_lookup.get(device.branch_id) if device.branch_id else None

        # Build payload directly instead of calling _standalone_device_to_payload
        branch_name = ""
        region_name = ""
        if branch_obj:
            branch_name = branch_obj.display_name
            region_name = branch_obj.region or ""

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

        payload.append({
            "hostid": str(device.id),
            "hostname": device.hostname or device.name,
            "display_name": device.normalized_name or device.name,
            "name": device.normalized_name or device.name,
            "original_name": device.original_name or device.name,
            "branch": branch_name or fields.get("branch", ""),
            "region": region_name or fields.get("region", ""),
            "ip": device.ip,
            "device_type": device.device_type or fields.get("device_type", ""),
            "status": "Enabled" if device.enabled else "Disabled",
            "enabled": device.enabled,
            "available": available,
            "ping_status": ping_status,
            "ping_response_time": ping_response_time,
            "last_check": last_check or 0,
            "down_since": device.down_since.replace(tzinfo=timezone.utc).isoformat() if device.down_since else None,
            "groups": device.tags or [],
            "problems": alert_count,
            "triggers": [],
            "latitude": fields.get("latitude"),
            "longitude": fields.get("longitude"),
            "vendor": device.vendor,
            "model": device.model,
            "created_at": device.created_at.isoformat() if device.created_at else None,
        })

    return payload


def _standalone_device_to_payload(db: Session, device: StandaloneDevice) -> Dict:
    from models import Branch

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

    # Get branch information from branches table
    branch_name = ""
    region_name = ""
    if device.branch_id:
        branch = db.query(Branch).filter(Branch.id == device.branch_id).first()
        if branch:
            branch_name = branch.display_name
            region_name = branch.region or ""

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
        "display_name": device.normalized_name or device.name,
        "name": device.normalized_name or device.name,
        "original_name": device.original_name or device.name,
        "branch": branch_name or fields.get("branch", ""),
        "region": region_name or fields.get("region", ""),
        "ip": device.ip,
        "device_type": device.device_type or fields.get("device_type", ""),
        "status": "Enabled" if device.enabled else "Disabled",
        "enabled": device.enabled,
        "available": available,
        "ping_status": ping_status,
        "ping_response_time": ping_response_time,
        "last_check": last_check or 0,
        "down_since": device.down_since.replace(tzinfo=timezone.utc).isoformat() if device.down_since else None,
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
    try:
        db.add(ping_record)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save ping record for {ip}: {e}")


@router.get("/{hostid}/history")
async def get_device_history(
    request: Request,
    hostid: str,
    time_range: str = "24h",  # 24h, 7d, 30d
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get real ping history for a device

    OPTIMIZATION: Redis caching with 30-second TTL
    - Cache hit: 5-10ms (200x faster)
    - Cache miss: 50-200ms (database query)
    """
    import time
    import json as json_lib

    try:
        device_uuid = uuid.UUID(hostid)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid device ID"})

    # Build cache key
    cache_key = f"device:history:{hostid}:{time_range}"

    # Try to get from cache
    try:
        from utils.cache import get_redis_client
        redis_client = get_redis_client()
        if redis_client:
            cached = redis_client.get(cache_key)
            if cached:
                logger.debug(f"Cache HIT for device history: {hostid}")
                return json_lib.loads(cached)
    except Exception as e:
        logger.debug(f"Cache read error (non-critical): {e}")

    # Cache miss - query VictoriaMetrics (PHASE 3)
    device = db.query(StandaloneDevice).filter_by(id=device_uuid).first()
    if not device:
        return {"hostid": hostid, "history": [], "time_range": time_range}

    # PHASE 3: Query VictoriaMetrics instead of PostgreSQL
    time_map = {"24h": 24, "7d": 168, "30d": 720}  # Convert to hours
    hours = time_map.get(time_range, 24)

    # OPTIMIZATION: Use dynamic query resolution based on time range
    step = get_optimal_vm_step(hours)  # 5m for 24h, 15m for 7d, 1h for 30d

    try:
        from utils.victoriametrics_client import vm_client
        import asyncio
        import concurrent.futures

        # OPTIMIZATION: Run both VM queries in parallel using thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            status_future = executor.submit(
                vm_client.get_device_status_history,
                str(device.id),
                hours,
                step  # Dynamic resolution
            )
            rtt_future = executor.submit(
                vm_client.get_device_rtt_history,
                str(device.id),
                hours,
                step  # Dynamic resolution
            )

            # Wait for both queries to complete (runs in parallel)
            status_history = status_future.result(timeout=5)
            rtt_history = rtt_future.result(timeout=5)

        # Merge status and RTT data by timestamp
        rtt_by_timestamp = {item["timestamp"]: item["rtt_ms"] for item in rtt_history}

        history = [
            {
                "clock": item["timestamp"],
                "value": rtt_by_timestamp.get(item["timestamp"], 0),
                "reachable": item["value"] == 1.0,
            }
            for item in status_history
        ]

        # Sort by timestamp descending and limit to 200 points
        history = sorted(history, key=lambda x: x["clock"], reverse=True)[:200]

    except Exception as e:
        logger.error(f"Failed to query VictoriaMetrics for device history: {e}")
        # Fallback to empty history instead of PostgreSQL
        history = []

    result = {"hostid": hostid, "history": history, "time_range": time_range}

    # Store in cache (30-second TTL)
    try:
        if redis_client:
            redis_client.setex(cache_key, 30, json_lib.dumps(result, default=str))
            logger.debug(f"Cached device history for 30 seconds: {hostid}")
    except Exception as e:
        logger.debug(f"Cache write error (non-critical): {e}")

    return result


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
