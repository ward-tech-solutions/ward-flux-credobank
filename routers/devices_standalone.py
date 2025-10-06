"""
WARD FLUX - Standalone Device Management API
CRUD operations for standalone devices (no Zabbix dependency)
"""

import logging
import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel, Field, IPvAnyAddress

from database import get_db, User
from auth import get_current_active_user
from monitoring.models import StandaloneDevice

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/devices/standalone", tags=["standalone-devices"])


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
    description: Optional[str] = None
    enabled: Optional[bool] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[dict] = None


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

    @classmethod
    def from_orm(cls, obj):
        """Convert ORM object to Pydantic model, converting UUID to string"""
        data = {
            'id': str(obj.id),
            'name': obj.name,
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
        }
        return cls(**data)

    class Config:
        from_attributes = True
        from_attributes = True


# ============================================
# Device CRUD Endpoints
# ============================================

@router.get("/list", response_model=List[StandaloneDeviceResponse])
def list_devices(
    enabled: Optional[bool] = None,
    vendor: Optional[str] = None,
    device_type: Optional[str] = None,
    location: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all standalone devices with optional filters"""
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

    # Apply pagination
    devices = query.offset(skip).limit(limit).all()

    logger.info(f"Retrieved {len(devices)} standalone devices")
    return [StandaloneDeviceResponse.from_orm(d) for d in devices]


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
    return StandaloneDeviceResponse.from_orm(new_device)


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

    return StandaloneDeviceResponse.from_orm(device)


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
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Device with IP {device_update.ip} already exists"
            )

    # Update fields
    update_data = device_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(device, field, value)

    device.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(device)

    logger.info(f"Updated standalone device: {device.name} ({device.ip})")
    return StandaloneDeviceResponse.from_orm(device)


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

    return [StandaloneDeviceResponse.from_orm(d) for d in created_devices]


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
            device.updated_at = datetime.utcnow()
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
            device.updated_at = datetime.utcnow()
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
