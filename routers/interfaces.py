"""
WARD FLUX - Interface Management API
REST API for network interface discovery and monitoring
"""

import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database import get_db, User
from monitoring.models import DeviceInterface, InterfaceMetricsSummary, StandaloneDevice
from monitoring.tasks_interface_discovery import discover_device_interfaces_task, discover_all_interfaces_task
from auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/interfaces", tags=["interfaces"])


# ============================================
# Pydantic Models (Request/Response schemas)
# ============================================

class InterfaceResponse(BaseModel):
    """Interface response model"""
    id: str
    device_id: str
    device_name: Optional[str] = None
    device_ip: Optional[str] = None

    # SNMP data
    if_index: int
    if_name: Optional[str] = None
    if_descr: Optional[str] = None
    if_alias: Optional[str] = None
    if_type: Optional[str] = None

    # Classification
    interface_type: Optional[str] = None
    isp_provider: Optional[str] = None
    is_critical: bool = False
    parser_confidence: Optional[float] = None

    # Status
    admin_status: Optional[int] = None
    oper_status: Optional[int] = None
    speed: Optional[int] = None
    mtu: Optional[int] = None
    phys_address: Optional[str] = None

    # Metadata
    discovered_at: datetime
    last_seen: datetime
    last_status_change: Optional[datetime] = None
    enabled: bool = True
    monitoring_enabled: bool = True

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InterfaceSummaryResponse(BaseModel):
    """Interface summary statistics"""
    total_interfaces: int
    critical_interfaces: int
    isp_interfaces: int
    trunk_interfaces: int
    interfaces_up: int
    interfaces_down: int
    interfaces_by_type: dict
    isp_providers: List[str]


class DiscoveryTriggerResponse(BaseModel):
    """Discovery trigger response"""
    task_id: str
    status: str
    message: str


# ============================================
# API Endpoints
# ============================================

@router.get("/list", response_model=List[InterfaceResponse])
def list_interfaces(
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    interface_type: Optional[str] = Query(None, description="Filter by type (isp, trunk, access, etc.)"),
    isp_provider: Optional[str] = Query(None, description="Filter by ISP provider (magti, silknet, etc.)"),
    is_critical: Optional[bool] = Query(None, description="Filter critical interfaces only"),
    oper_status: Optional[int] = Query(None, description="Filter by operational status (1=up, 2=down)"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List network interfaces with optional filtering

    Supports filtering by:
    - Device ID
    - Interface type (isp, trunk, access, server_link, branch_link, etc.)
    - ISP provider (magti, silknet, veon, etc.)
    - Critical status
    - Operational status

    Returns list of interfaces with device information
    """
    try:
        # Build query
        query = select(DeviceInterface, StandaloneDevice).join(
            StandaloneDevice,
            DeviceInterface.device_id == StandaloneDevice.id
        )

        # Apply filters
        filters = []
        if device_id:
            filters.append(DeviceInterface.device_id == device_id)
        if interface_type:
            filters.append(DeviceInterface.interface_type == interface_type)
        if isp_provider:
            filters.append(DeviceInterface.isp_provider == isp_provider)
        if is_critical is not None:
            filters.append(DeviceInterface.is_critical == is_critical)
        if oper_status is not None:
            filters.append(DeviceInterface.oper_status == oper_status)

        if filters:
            query = query.where(and_(*filters))

        # Order by critical first, then device name, then interface name
        query = query.order_by(
            DeviceInterface.is_critical.desc(),
            StandaloneDevice.name,
            DeviceInterface.if_index
        )

        # Pagination
        query = query.offset(offset).limit(limit)

        # Execute query
        results = db.execute(query).all()

        # Build response
        response = []
        for interface, device in results:
            interface_dict = InterfaceResponse.from_orm(interface).dict()
            interface_dict['device_name'] = device.name
            interface_dict['device_ip'] = device.ip
            response.append(interface_dict)

        return response

    except Exception as e:
        logger.error(f"Failed to list interfaces: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list interfaces: {str(e)}")


@router.get("/summary", response_model=InterfaceSummaryResponse)
def get_interface_summary(
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get interface statistics summary

    Returns counts and breakdowns by type, status, ISP provider, etc.
    """
    try:
        # Base query
        query = select(DeviceInterface)
        if device_id:
            query = query.where(DeviceInterface.device_id == device_id)

        # Total interfaces
        total_interfaces = db.execute(
            select(func.count()).select_from(query.subquery())
        ).scalar()

        # Critical interfaces
        critical_interfaces = db.execute(
            select(func.count()).select_from(query.subquery()).where(
                DeviceInterface.is_critical == True
            )
        ).scalar()

        # ISP interfaces
        isp_interfaces = db.execute(
            select(func.count()).select_from(query.subquery()).where(
                DeviceInterface.interface_type == 'isp'
            )
        ).scalar()

        # Trunk interfaces
        trunk_interfaces = db.execute(
            select(func.count()).select_from(query.subquery()).where(
                DeviceInterface.interface_type == 'trunk'
            )
        ).scalar()

        # Interfaces up/down
        interfaces_up = db.execute(
            select(func.count()).select_from(query.subquery()).where(
                DeviceInterface.oper_status == 1
            )
        ).scalar()

        interfaces_down = db.execute(
            select(func.count()).select_from(query.subquery()).where(
                DeviceInterface.oper_status == 2
            )
        ).scalar()

        # Interfaces by type
        type_counts = db.execute(
            select(
                DeviceInterface.interface_type,
                func.count(DeviceInterface.id)
            ).group_by(DeviceInterface.interface_type)
        ).all()
        interfaces_by_type = {row[0] or 'unknown': row[1] for row in type_counts}

        # ISP providers
        isp_providers = db.execute(
            select(DeviceInterface.isp_provider).where(
                DeviceInterface.isp_provider.isnot(None)
            ).distinct()
        ).scalars().all()

        return InterfaceSummaryResponse(
            total_interfaces=total_interfaces,
            critical_interfaces=critical_interfaces,
            isp_interfaces=isp_interfaces,
            trunk_interfaces=trunk_interfaces,
            interfaces_up=interfaces_up,
            interfaces_down=interfaces_down,
            interfaces_by_type=interfaces_by_type,
            isp_providers=list(isp_providers)
        )

    except Exception as e:
        logger.error(f"Failed to get interface summary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get interface summary: {str(e)}")


@router.get("/device/{device_id}", response_model=List[InterfaceResponse])
def get_device_interfaces(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all interfaces for a specific device

    Returns interfaces ordered by:
    1. Critical interfaces first
    2. Interface type (ISP, trunk, access, etc.)
    3. Interface index
    """
    try:
        # Check if device exists
        device = db.execute(
            select(StandaloneDevice).where(StandaloneDevice.id == device_id)
        ).scalar_one_or_none()

        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

        # Fetch interfaces
        query = select(DeviceInterface).where(
            DeviceInterface.device_id == device_id
        ).order_by(
            DeviceInterface.is_critical.desc(),
            DeviceInterface.interface_type,
            DeviceInterface.if_index
        )

        interfaces = db.execute(query).scalars().all()

        # Build response
        response = []
        for interface in interfaces:
            interface_dict = InterfaceResponse.from_orm(interface).dict()
            interface_dict['device_name'] = device.name
            interface_dict['device_ip'] = device.ip
            response.append(interface_dict)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get device interfaces: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get device interfaces: {str(e)}")


@router.get("/critical", response_model=List[InterfaceResponse])
def get_critical_interfaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all critical interfaces (ISP uplinks, core trunks, etc.)

    Returns interfaces marked as critical, ordered by device name
    """
    try:
        query = select(DeviceInterface, StandaloneDevice).join(
            StandaloneDevice,
            DeviceInterface.device_id == StandaloneDevice.id
        ).where(
            DeviceInterface.is_critical == True
        ).order_by(
            StandaloneDevice.name,
            DeviceInterface.if_index
        )

        results = db.execute(query).all()

        # Build response
        response = []
        for interface, device in results:
            interface_dict = InterfaceResponse.from_orm(interface).dict()
            interface_dict['device_name'] = device.name
            interface_dict['device_ip'] = device.ip
            response.append(interface_dict)

        return response

    except Exception as e:
        logger.error(f"Failed to get critical interfaces: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get critical interfaces: {str(e)}")


@router.get("/isp", response_model=List[InterfaceResponse])
def get_isp_interfaces(
    isp_provider: Optional[str] = Query(None, description="Filter by ISP (magti, silknet, etc.)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all ISP interfaces

    Optionally filter by ISP provider (magti, silknet, veon, etc.)

    Returns ISP interfaces ordered by device name
    """
    try:
        query = select(DeviceInterface, StandaloneDevice).join(
            StandaloneDevice,
            DeviceInterface.device_id == StandaloneDevice.id
        ).where(
            DeviceInterface.interface_type == 'isp'
        )

        if isp_provider:
            query = query.where(DeviceInterface.isp_provider == isp_provider)

        query = query.order_by(
            StandaloneDevice.name,
            DeviceInterface.if_index
        )

        results = db.execute(query).all()

        # Build response
        response = []
        for interface, device in results:
            interface_dict = InterfaceResponse.from_orm(interface).dict()
            interface_dict['device_name'] = device.name
            interface_dict['device_ip'] = device.ip
            response.append(interface_dict)

        return response

    except Exception as e:
        logger.error(f"Failed to get ISP interfaces: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get ISP interfaces: {str(e)}")


@router.post("/discover/{device_id}", response_model=DiscoveryTriggerResponse)
def trigger_device_discovery(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Trigger interface discovery for a single device

    Queues a Celery task to discover interfaces via SNMP

    Returns task ID for tracking
    """
    try:
        # Check if device exists
        device = db.execute(
            select(StandaloneDevice).where(StandaloneDevice.id == device_id)
        ).scalar_one_or_none()

        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

        if not device.enabled:
            raise HTTPException(status_code=400, detail=f"Device {device_id} is disabled")

        # Trigger discovery task
        task = discover_device_interfaces_task.delay(str(device_id))

        logger.info(f"Triggered interface discovery for device {device_id} (task {task.id})")

        return DiscoveryTriggerResponse(
            task_id=task.id,
            status="queued",
            message=f"Interface discovery queued for device {device.name} ({device.ip})"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger discovery: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to trigger discovery: {str(e)}")


@router.post("/discover/all", response_model=DiscoveryTriggerResponse)
def trigger_all_discovery(
    current_user: User = Depends(get_current_active_user)
):
    """
    Trigger interface discovery for ALL enabled devices

    Queues a Celery task to discover interfaces on all devices

    Returns task ID for tracking
    """
    try:
        # Trigger discovery task
        task = discover_all_interfaces_task.delay()

        logger.info(f"Triggered interface discovery for all devices (task {task.id})")

        return DiscoveryTriggerResponse(
            task_id=task.id,
            status="queued",
            message="Interface discovery queued for all enabled devices"
        )

    except Exception as e:
        logger.error(f"Failed to trigger discovery: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to trigger discovery: {str(e)}")


@router.patch("/{interface_id}", response_model=InterfaceResponse)
def update_interface(
    interface_id: str,
    is_critical: Optional[bool] = None,
    enabled: Optional[bool] = None,
    monitoring_enabled: Optional[bool] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update interface configuration

    Allows updating:
    - is_critical: Mark interface as critical
    - enabled: Enable/disable interface
    - monitoring_enabled: Enable/disable metrics collection
    - notes: User notes
    """
    try:
        # Fetch interface
        interface = db.execute(
            select(DeviceInterface).where(DeviceInterface.id == interface_id)
        ).scalar_one_or_none()

        if not interface:
            raise HTTPException(status_code=404, detail=f"Interface {interface_id} not found")

        # Update fields
        if is_critical is not None:
            interface.is_critical = is_critical
        if enabled is not None:
            interface.enabled = enabled
        if monitoring_enabled is not None:
            interface.monitoring_enabled = monitoring_enabled
        if notes is not None:
            interface.notes = notes

        interface.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(interface)

        logger.info(f"Updated interface {interface_id}")

        return InterfaceResponse.from_orm(interface)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update interface: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update interface: {str(e)}")
