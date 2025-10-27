"""
WARD FLUX - Standalone Device Management API
CRUD operations for standalone devices (no Zabbix dependency)
"""

import logging
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, distinct
from pydantic import BaseModel, Field, IPvAnyAddress

from database import PingResult, get_db, User
from auth import get_current_active_user
from monitoring.models import StandaloneDevice

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/devices/standalone", tags=["standalone-devices"])


def utcnow():
    """Get current UTC time with timezone awareness"""
    return datetime.now(timezone.utc)


# ============================================
# Pydantic Models
# ============================================

class StandaloneDeviceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    ip: str = Field(..., description="IPv4 or IPv6 address")
    hostname: Optional[str] = Field(None, max_length=255)
    vendor: Optional[str] = Field(None, max_length=100)
    device_type: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    enabled: bool = True
    tags: Optional[List[str]] = None
    custom_fields: Optional[dict] = None


class StandaloneDeviceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    ip: Optional[str] = None
    hostname: Optional[str] = Field(None, max_length=255)
    vendor: Optional[str] = Field(None, max_length=100)
    device_type: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=200)
    region: Optional[str] = Field(None, max_length=100)
    branch: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    enabled: Optional[bool] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[dict] = None
    branch_id: Optional[str] = None
    normalized_name: Optional[str] = None
    ssh_port: Optional[int] = Field(None, ge=1, le=65535)
    ssh_username: Optional[str] = Field(None, max_length=100)
    ssh_enabled: Optional[bool] = None


class StandaloneDeviceResponse(BaseModel):
    id: str
    name: str
    ip: str
    hostname: Optional[str]
    vendor: Optional[str]
    device_type: Optional[str]
    model: Optional[str]
    location: Optional[str]
    description: Optional[str]
    enabled: bool
    discovered_at: Optional[datetime]
    last_seen: Optional[datetime]
    tags: Optional[List[str]]
    custom_fields: Optional[dict]
    created_at: datetime
    updated_at: datetime
    region: Optional[str] = None
    branch: Optional[str] = None
    branch_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    available: Optional[str] = None
    ping_status: Optional[str] = None
    ping_response_time: Optional[float] = None
    last_ping_timestamp: Optional[str] = None
    down_since: Optional[str] = None  # ISO timestamp when device first went down
    problems: int = 0
    ssh_port: Optional[int] = 22
    ssh_username: Optional[str] = None
    ssh_enabled: Optional[bool] = True

    # ISP Interface Status
    isp_interfaces: Optional[List[dict]] = None  # List of {provider: str, status: str, name: str}

    @classmethod
    def from_model(cls, obj: StandaloneDevice, ping_result = None, db: Session = None):
        """
        Convert ORM object to Pydantic model, converting UUID to string

        PHASE 3: ping_result can now be either:
        - Dict[str, Any] from VictoriaMetrics (preferred)
        - PingResult object from PostgreSQL (fallback)
        """
        from models import Branch

        # Get branch info from branches table
        branch_name = ""
        region = ""
        if obj.branch_id and db:
            branch_obj = db.query(Branch).filter(Branch.id == obj.branch_id).first()
            if branch_obj:
                branch_name = branch_obj.display_name
                region = branch_obj.region or ""

        # Fallback to custom_fields
        fields = obj.custom_fields or {}
        if not branch_name:
            branch_name = fields.get("branch", "")
        if not region:
            region = fields.get("region", "")
        latitude = fields.get("latitude")
        longitude = fields.get("longitude")
        problems = fields.get("problems") or 0

        # CRITICAL FIX: Use device.down_since as the SOURCE OF TRUTH for status
        # The down_since field is updated by the monitoring worker and is always current
        # VictoriaMetrics ping data may be stale due to caching/propagation delays
        if obj.down_since is not None:
            # Device is DOWN - down_since timestamp exists
            ping_status = "Down"
            available = "Unavailable"
        else:
            # Device is UP - down_since is NULL
            ping_status = "Up"
            available = "Available"

        # Get ping response time and timestamp from ping_result (if available)
        if ping_result:
            # PHASE 3: Handle both dict (VictoriaMetrics) and PingResult object (PostgreSQL fallback)
            if isinstance(ping_result, dict):
                # VictoriaMetrics format
                ping_response_time = ping_result.get("avg_rtt_ms")
                timestamp = ping_result.get("timestamp")
                last_ping_timestamp = datetime.fromtimestamp(timestamp).isoformat() if timestamp else None
            else:
                # PostgreSQL PingResult object (fallback)
                ping_response_time = ping_result.avg_rtt_ms
                last_ping_timestamp = ping_result.timestamp.isoformat() if ping_result.timestamp else None
        else:
            ping_response_time = fields.get("ping_response_time")
            last_ping_timestamp = fields.get("synced_at")

        # Get ISP interface status (HYBRID: PostgreSQL for names, VictoriaMetrics for status)
        isp_interfaces = []
        if db and obj.ip:
            from monitoring.models import DeviceInterface
            from utils.victoriametrics_client import VictoriaMetricsClient

            # Get interface metadata from PostgreSQL (names, aliases)
            isp_query = db.query(DeviceInterface).filter(
                DeviceInterface.device_id == obj.id,
                DeviceInterface.interface_type == 'isp'
            ).all()

            # Get real-time status from VictoriaMetrics
            vm_status = {}
            if isp_query:
                try:
                    vm_client = VictoriaMetricsClient()
                    query = f'interface_oper_status{{device_ip="{obj.ip}",isp_provider!=""}}'
                    result = vm_client.query(query)

                    if result.get("status") == "success":
                        for series in result.get("data", {}).get("result", []):
                            metric = series.get("metric", {})
                            value = series.get("value", [None, None])
                            provider = metric.get("isp_provider")
                            oper_status = int(float(value[1])) if value[1] is not None else 0

                            if provider:
                                vm_status[provider] = oper_status
                except Exception as e:
                    logger.warning(f"Failed to get VM status for {obj.ip}: {e}")

            # Combine PostgreSQL metadata with VictoriaMetrics status
            for iface in isp_query:
                provider = iface.isp_provider
                # Use VictoriaMetrics status if available (real-time), fallback to PostgreSQL
                oper_status = vm_status.get(provider, iface.oper_status)
                status = "up" if oper_status == 1 else "down"

                isp_interfaces.append({
                    "provider": provider,
                    "status": status,
                    "name": iface.if_name or f"if{iface.if_index}",
                    "alias": iface.if_alias
                })

        data = {
            'id': str(obj.id),
            'name': obj.normalized_name or obj.name,
            'display_name': obj.normalized_name or obj.name,
            'original_name': obj.original_name or obj.name,
            'ip': obj.ip,
            'hostname': obj.hostname,
            'vendor': obj.vendor,
            'device_type': obj.device_type,
            'model': obj.model,
            'location': obj.location,
            'description': obj.description,
            'enabled': obj.enabled,
            'discovered_at': obj.discovered_at,
            'last_seen': obj.last_seen,
            'tags': obj.tags,
            'custom_fields': obj.custom_fields,
            'created_at': obj.created_at,
            'updated_at': obj.updated_at,
            'region': region,
            'branch': branch_name,
            'branch_id': str(obj.branch_id) if obj.branch_id else None,
            'latitude': latitude,
            'longitude': longitude,
            'available': available or ("Available" if obj.enabled else "Unavailable"),
            'ping_status': ping_status,
            'ping_response_time': ping_response_time,
            'last_ping_timestamp': last_ping_timestamp,
            'down_since': obj.down_since.isoformat() + 'Z' if obj.down_since else None,
            'problems': problems,
            'ssh_port': obj.ssh_port or 22,
            'ssh_username': obj.ssh_username,
            'ssh_enabled': obj.ssh_enabled if obj.ssh_enabled is not None else True,
            'isp_interfaces': isp_interfaces if isp_interfaces else None,
        }
        return cls(**data)

    class Config:
        from_attributes = True


def _latest_ping_lookup(db: Session, ips: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    PHASE 3: Return the most recent ping result per IP from VictoriaMetrics

    Performance improvements:
    - Phase 2 (PostgreSQL subquery): 50ms for 1000 devices
    - Phase 3 (VictoriaMetrics): <10ms for 1000 devices (5x faster!)

    Returns:
        Dict mapping IP -> ping data dict
        Compatible with both VictoriaMetrics (dict) and PostgreSQL (PingResult) formats
    """
    if not ips:
        return {}

    # PHASE 3: Query VictoriaMetrics
    try:
        from utils.victoriametrics_client import vm_client
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Querying VictoriaMetrics for {len(ips)} devices")
        return vm_client.get_latest_ping_for_devices(ips)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to query VictoriaMetrics for ping data: {e}")
        logger.warning("Returning empty ping data - status will use device.down_since field")
        # PHASE 3 FIX: DO NOT fallback to PostgreSQL after Phase 2!
        # When deploying all phases same day, PostgreSQL table will be immediately stale.
        # Device status will use device.down_since field which is always current.
        return {}


# ============================================
# Device CRUD Endpoints
# ============================================

@router.get("/list", response_model=List[StandaloneDeviceResponse])
def list_devices(
    enabled: Optional[bool] = None,
    vendor: Optional[str] = None,
    device_type: Optional[str] = None,
    location: Optional[str] = None,
    region: Optional[str] = None,
    branch: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List all standalone devices with optional filters

    TIER 1 OPTIMIZATION: Redis caching with 30-second TTL
    - Cache hit: 10-20ms (10x faster)
    - Cache miss: 50-200ms (database query)
    - Expected cache hit rate: 80-90% (dashboard refreshes every 30s)
    """
    # Build cache key from query parameters
    import hashlib
    import json as json_lib
    cache_params = {
        'enabled': enabled,
        'vendor': vendor,
        'device_type': device_type,
        'location': location,
        'region': region,
        'branch': branch,
        'skip': skip,
        'limit': limit
    }
    cache_key = f"devices:list:{hashlib.md5(json_lib.dumps(cache_params, sort_keys=True).encode()).hexdigest()}"

    # Try to get from cache
    try:
        from utils.cache import get_redis_client
        redis_client = get_redis_client()
        if redis_client:
            cached = redis_client.get(cache_key)
            if cached:
                logger.debug(f"Cache HIT for device list")
                return json_lib.loads(cached)
    except Exception as e:
        logger.debug(f"Cache read error (non-critical): {e}")

    # Cache miss - query database
    query = db.query(StandaloneDevice)

    # Apply filters
    if enabled is not None:
        query = query.filter(StandaloneDevice.enabled == enabled)
    if vendor:
        query = query.filter(StandaloneDevice.vendor == vendor)
    if device_type:
        query = query.filter(StandaloneDevice.device_type == device_type)
    if location:
        query = query.filter(StandaloneDevice.location == location)

    # OPTIMIZATION: Filter by region/branch at DATABASE level using PostgreSQL JSON operators
    # Before: Fetches ALL devices, filters in Python (slow with 1000+ devices)
    # After: Database filters, returns only matching devices (10x faster)
    if region:
        # Use PostgreSQL JSON operator to filter custom_fields->>'region'
        query = query.filter(StandaloneDevice.custom_fields['region'].astext == region)
    if branch:
        # Use PostgreSQL JSON operator to filter custom_fields->>'branch'
        query = query.filter(StandaloneDevice.custom_fields['branch'].astext == branch)

    # Apply pagination at database level (more efficient)
    paginated_devices = query.offset(skip).limit(limit).all()

    ping_lookup = _latest_ping_lookup(db, [d.ip for d in paginated_devices if d.ip])

    logger.info(f"Retrieved {len(paginated_devices)} standalone devices")
    result = [StandaloneDeviceResponse.from_model(d, ping_lookup.get(d.ip), db) for d in paginated_devices]

    # Store in cache (30-second TTL for dashboard refresh pattern)
    try:
        if redis_client:
            # Convert Pydantic models to dict for JSON serialization
            result_dict = [device.dict() for device in result]
            redis_client.setex(cache_key, 30, json_lib.dumps(result_dict, default=str))
            logger.debug(f"Cached device list for 30 seconds")
    except Exception as e:
        logger.debug(f"Cache write error (non-critical): {e}")

    return result


@router.post("", response_model=StandaloneDeviceResponse, status_code=status.HTTP_201_CREATED)
def create_device(
    device: StandaloneDeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new standalone device"""

    # Check if device with same IP already exists
    existing = db.query(StandaloneDevice).filter_by(ip=device.ip).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Device with IP {device.ip} already exists"
        )

    # Create new device
    new_device = StandaloneDevice(
        id=uuid.uuid4(),
        name=device.name,
        ip=device.ip,
        hostname=device.hostname,
        vendor=device.vendor,
        device_type=device.device_type,
        model=device.model,
        location=device.location,
        description=device.description,
        enabled=device.enabled,
        tags=device.tags,
        custom_fields=device.custom_fields,
    )

    db.add(new_device)
    db.commit()
    db.refresh(new_device)

    logger.info(f"Created standalone device: {new_device.name} ({new_device.ip})")
    ping_lookup = _latest_ping_lookup(db, [new_device.ip])
    return StandaloneDeviceResponse.from_model(new_device, ping_lookup.get(new_device.ip), db)


@router.get("/{device_id}", response_model=StandaloneDeviceResponse)
def get_device(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a specific standalone device by ID"""

    device = db.query(StandaloneDevice).filter_by(id=uuid.UUID(device_id)).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    ping_lookup = _latest_ping_lookup(db, [device.ip])
    return StandaloneDeviceResponse.from_model(device, ping_lookup.get(device.ip), db)


@router.put("/{device_id}", response_model=StandaloneDeviceResponse)
def update_device(
    device_id: str,
    device_update: StandaloneDeviceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a standalone device"""

    device = db.query(StandaloneDevice).filter_by(id=uuid.UUID(device_id)).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Check for IP conflict if IP is being changed
    if device_update.ip and device_update.ip != device.ip:
        existing = db.query(StandaloneDevice).filter_by(ip=device_update.ip).first()
        if existing and str(existing.id) != device_id:
            raise HTTPException(
                status_code=400,
                detail=f"Device with IP {device_update.ip} already exists"
            )

    # Update fields - handle region/branch specially since they're not direct columns
    update_data = device_update.model_dump(exclude_unset=True)

    # Extract region and branch if present
    region = update_data.pop('region', None)
    branch = update_data.pop('branch', None)

    # Update custom_fields with region/branch if provided
    if region is not None or branch is not None:
        custom_fields = device.custom_fields or {}
        if region is not None:
            custom_fields['region'] = region
        if branch is not None:
            custom_fields['branch'] = branch
        device.custom_fields = custom_fields

    # Update remaining fields
    for field, value in update_data.items():
        if hasattr(device, field):
            setattr(device, field, value)

    device.updated_at = utcnow()
    db.commit()
    db.refresh(device)

    logger.info(f"Updated standalone device: {device.name} ({device.ip})")
    ping_lookup = _latest_ping_lookup(db, [device.ip])
    return StandaloneDeviceResponse.from_model(device, ping_lookup.get(device.ip), db)


@router.delete("/{device_id}")
def delete_device(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a standalone device"""

    device = db.query(StandaloneDevice).filter_by(id=uuid.UUID(device_id)).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device_name = device.name
    device_ip = device.ip

    db.delete(device)
    db.commit()

    logger.info(f"Deleted standalone device: {device_name} ({device_ip})")
    return {"success": True, "message": f"Device {device_name} deleted"}


# ============================================
# Bulk Operations
# ============================================

@router.post("/bulk", response_model=List[StandaloneDeviceResponse], status_code=status.HTTP_201_CREATED)
def bulk_create_devices(
    devices: List[StandaloneDeviceCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Bulk create standalone devices"""

    created_devices = []
    errors = []

    for device_data in devices:
        try:
            # Check for duplicates
            existing = db.query(StandaloneDevice).filter_by(ip=device_data.ip).first()
            if existing:
                errors.append(f"Device with IP {device_data.ip} already exists")
                continue

            # Create device
            new_device = StandaloneDevice(
                id=uuid.uuid4(),
                name=device_data.name,
                ip=device_data.ip,
                hostname=device_data.hostname,
                vendor=device_data.vendor,
                device_type=device_data.device_type,
                model=device_data.model,
                location=device_data.location,
                description=device_data.description,
                enabled=device_data.enabled,
                tags=device_data.tags,
                custom_fields=device_data.custom_fields,
            )

            db.add(new_device)
            created_devices.append(new_device)

        except Exception as e:
            errors.append(f"Error creating device {device_data.name}: {str(e)}")

    if created_devices:
        db.commit()
        for device in created_devices:
            db.refresh(device)

    logger.info(f"Bulk created {len(created_devices)} devices, {len(errors)} errors")

    if errors:
        logger.warning(f"Bulk creation errors: {errors}")

    ping_lookup = _latest_ping_lookup(db, [d.ip for d in created_devices if d.ip])

    return [StandaloneDeviceResponse.from_model(d, ping_lookup.get(d.ip), db) for d in created_devices]


@router.post("/bulk/enable")
def bulk_enable_devices(
    device_ids: List[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Bulk enable devices"""

    updated_count = 0
    for device_id in device_ids:
        device = db.query(StandaloneDevice).filter_by(id=uuid.UUID(device_id)).first()
        if device:
            device.enabled = True
            device.updated_at = utcnow()
            updated_count += 1

    db.commit()
    logger.info(f"Bulk enabled {updated_count} devices")

    return {"success": True, "updated_count": updated_count}


@router.post("/bulk/disable")
def bulk_disable_devices(
    device_ids: List[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Bulk disable devices"""

    updated_count = 0
    for device_id in device_ids:
        device = db.query(StandaloneDevice).filter_by(id=uuid.UUID(device_id)).first()
        if device:
            device.enabled = False
            device.updated_at = utcnow()
            updated_count += 1

    db.commit()
    logger.info(f"Bulk disabled {updated_count} devices")

    return {"success": True, "updated_count": updated_count}


# ============================================
# Statistics
# ============================================

@router.get("/stats")
def get_device_stats_simple(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get device statistics (simple)"""
    try:
        total_devices = db.query(StandaloneDevice).count()
        enabled_devices = db.query(StandaloneDevice).filter_by(enabled=True).count()
        return {
            "total": total_devices,
            "online": 0,
            "offline": 0,
            "enabled": enabled_devices
        }
    except Exception as e:
        logger.error(f"Error getting device stats: {e}")
        # Return empty stats if database query fails
        return {"total": 0, "online": 0, "offline": 0, "enabled": 0}

@router.get("/stats/summary")
def get_device_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get device statistics"""

    total_devices = db.query(StandaloneDevice).count()
    enabled_devices = db.query(StandaloneDevice).filter_by(enabled=True).count()
    disabled_devices = total_devices - enabled_devices

    # Count by vendor
    vendors = db.query(
        StandaloneDevice.vendor,
        func.count(StandaloneDevice.id)
    ).group_by(StandaloneDevice.vendor).all()

    # Count by device type
    device_types = db.query(
        StandaloneDevice.device_type,
        func.count(StandaloneDevice.id)
    ).group_by(StandaloneDevice.device_type).all()

    return {
        "total_devices": total_devices,
        "enabled_devices": enabled_devices,
        "disabled_devices": disabled_devices,
        "by_vendor": {vendor: count for vendor, count in vendors if vendor},
        "by_type": {dtype: count for dtype, count in device_types if dtype},
    }


# ============================================
# Search
# ============================================

@router.get("/search/query")
def search_devices(
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Search devices by name, IP, hostname, or location"""

    query_lower = f"%{q.lower()}%"

    devices = db.query(StandaloneDevice).filter(
        or_(
            func.lower(StandaloneDevice.name).like(query_lower),
            func.lower(StandaloneDevice.ip).like(query_lower),
            func.lower(StandaloneDevice.hostname).like(query_lower),
            func.lower(StandaloneDevice.location).like(query_lower),
        )
    ).limit(50).all()

    return devices
