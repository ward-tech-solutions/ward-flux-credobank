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


@router.get("/isp-status/vm")
def get_isp_status_from_victoriametrics(
    device_ips: str = Query(..., description="Comma-separated list of device IPs"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get ISP status from VictoriaMetrics (OPTIMIZED - NO PostgreSQL!)

    This is the CORRECT implementation following architecture:
    - Queries VictoriaMetrics time-series database
    - No PostgreSQL load
    - Fast (<100ms for 100+ devices)
    - Real-time data from SNMP polling

    Query: GET /api/v1/interfaces/isp-status/vm?device_ips=10.195.57.5,10.195.110.5

    Returns:
    {
        "10.195.57.5": {
            "magti": {"status": "up", "oper_status": 1},
            "silknet": {"status": "down", "oper_status": 2}
        }
    }
    """
    try:
        from utils.victoriametrics_client import VictoriaMetricsClient

        # Parse device IPs
        ip_list = [ip.strip() for ip in device_ips.split(',') if ip.strip()]

        if not ip_list:
            raise HTTPException(status_code=400, detail="No device IPs provided")

        if len(ip_list) > 200:
            raise HTTPException(status_code=400, detail="Too many devices requested (max 200)")

        # Initialize VM client
        vm_client = VictoriaMetricsClient()

        # Build PromQL query for ISP interface status
        # Query last value of oper_status for each ISP interface
        ip_regex = '|'.join([ip.replace('.', '\\.') for ip in ip_list])
        query = f'interface_oper_status{{device_ip=~"{ip_regex}",isp_provider!=""}}'

        # Execute instant query to get current status
        result = vm_client.query(query)

        if result.get("status") != "success":
            logger.error(f"VictoriaMetrics query failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail="Failed to query VictoriaMetrics")

        # Parse results into response format
        isp_status = {}
        data = result.get("data", {}).get("result", [])

        for series in data:
            metric = series.get("metric", {})
            value = series.get("value", [None, None])

            device_ip = metric.get("device_ip")
            isp_provider = metric.get("isp_provider")
            oper_status_value = int(float(value[1])) if value[1] is not None else 0

            if device_ip and isp_provider:
                if device_ip not in isp_status:
                    isp_status[device_ip] = {}

                # Convert oper_status to status string
                if oper_status_value == 1:
                    status = "up"
                elif oper_status_value == 2:
                    status = "down"
                else:
                    status = "unknown"

                isp_status[device_ip][isp_provider] = {
                    "status": status,
                    "oper_status": oper_status_value
                }

        # Add empty entries for devices with no data
        for ip in ip_list:
            if ip not in isp_status:
                isp_status[ip] = {}

        return isp_status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ISP status from VictoriaMetrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get ISP status: {str(e)}")


@router.get("/isp-status/bulk")
def get_bulk_isp_status(
    device_ips: str = Query(..., description="Comma-separated list of device IPs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get ISP status for multiple devices in a single query (DEPRECATED - Use /isp-status/vm)

    ⚠️  WARNING: This endpoint queries PostgreSQL and causes database load.
    Use /isp-status/vm instead which queries VictoriaMetrics directly.

    Query: GET /api/v1/interfaces/isp-status/bulk?device_ips=10.195.57.5,10.195.110.5

    Returns:
    {
        "10.195.57.5": {
            "magti": {"status": "up", "oper_status": 1, "if_name": "FastEthernet3", "last_seen": "..."},
            "silknet": {"status": "up", "oper_status": 1, "if_name": "FastEthernet4", "last_seen": "..."}
        },
        "10.195.110.5": { ... }
    }
    """
    try:
        # Parse device IPs
        ip_list = [ip.strip() for ip in device_ips.split(',') if ip.strip()]

        if not ip_list:
            raise HTTPException(status_code=400, detail="No device IPs provided")

        if len(ip_list) > 200:
            raise HTTPException(status_code=400, detail="Too many devices requested (max 200)")

        # OPTIMIZATION: Single bulk query for all devices and their ISP interfaces
        # Replaces N queries with 1 query
        query = select(
            StandaloneDevice.ip,
            DeviceInterface.isp_provider,
            DeviceInterface.oper_status,
            DeviceInterface.if_name,
            DeviceInterface.if_alias,
            DeviceInterface.last_seen,
            DeviceInterface.last_status_change
        ).join(
            DeviceInterface,
            StandaloneDevice.id == DeviceInterface.device_id
        ).where(
            and_(
                StandaloneDevice.ip.in_(ip_list),
                DeviceInterface.interface_type == 'isp',
                DeviceInterface.isp_provider.isnot(None)
            )
        ).order_by(
            StandaloneDevice.ip,
            DeviceInterface.if_index
        )

        results = db.execute(query).all()

        # Build response dictionary
        isp_status = {}
        for ip, isp_provider, oper_status, if_name, if_alias, last_seen, last_status_change in results:
            if ip not in isp_status:
                isp_status[ip] = {}

            # Determine status string
            if oper_status == 1:
                status = "up"
            elif oper_status == 2:
                status = "down"
            else:
                status = "unknown"

            isp_status[ip][isp_provider] = {
                "status": status,
                "oper_status": oper_status,
                "if_name": if_name,
                "if_alias": if_alias,
                "last_seen": last_seen.isoformat() if last_seen else None,
                "last_status_change": last_status_change.isoformat() if last_status_change else None
            }

        # Add empty entries for devices with no ISP interfaces discovered
        for ip in ip_list:
            if ip not in isp_status:
                isp_status[ip] = {}

        return isp_status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get bulk ISP status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get bulk ISP status: {str(e)}")


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


@router.get("/by-devices")
def get_interfaces_by_devices(
    device_ips: str = Query(..., description="Comma-separated list of device IPs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get ALL interfaces for specified device IPs (for topology visualization)

    Used by topology page to display all interfaces with bandwidth metrics.

    Query: GET /api/v1/interfaces/by-devices?device_ips=10.195.57.5,10.195.110.62

    Returns:
    {
        "10.195.57.5": [
            {
                "id": "uuid",
                "if_index": 3,
                "if_name": "FastEthernet3",
                "if_descr": "FastEthernet3",
                "if_alias": "ISP Magti Primary",
                "interface_type": "isp",
                "isp_provider": "magti",
                "oper_status": 1,
                "admin_status": 1,
                "speed": 100000000,
                "is_critical": true
            },
            ...
        ]
    }
    """
    try:
        # Parse device IPs
        ip_list = [ip.strip() for ip in device_ips.split(',') if ip.strip()]

        if not ip_list:
            raise HTTPException(status_code=400, detail="No device IPs provided")

        if len(ip_list) > 200:
            raise HTTPException(status_code=400, detail="Too many devices requested (max 200)")

        # Query devices
        devices = db.execute(
            select(StandaloneDevice).where(StandaloneDevice.ip.in_(ip_list))
        ).scalars().all()

        result = {}
        for device in devices:
            # Query all interfaces for this device
            interfaces = db.execute(
                select(DeviceInterface).where(
                    and_(
                        DeviceInterface.device_id == device.id,
                        DeviceInterface.enabled == True
                    )
                ).order_by(DeviceInterface.if_index)
            ).scalars().all()

            result[device.ip] = [
                {
                    "id": str(iface.id),
                    "if_index": iface.if_index,
                    "if_name": iface.if_name,
                    "if_descr": iface.if_descr,
                    "if_alias": iface.if_alias,
                    "interface_type": iface.interface_type,
                    "isp_provider": iface.isp_provider,
                    "oper_status": iface.oper_status,
                    "admin_status": iface.admin_status,
                    "speed": iface.speed,
                    "is_critical": iface.is_critical,
                }
                for iface in interfaces
            ]

        # Add empty arrays for devices with no interfaces discovered
        for ip in ip_list:
            if ip not in result:
                result[ip] = []

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get interfaces by devices: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get interfaces by devices: {str(e)}")


@router.get("/bandwidth/realtime")
def get_interface_bandwidth_realtime(
    device_ips: str = Query(..., description="Comma-separated list of device IPs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get real-time bandwidth for all interfaces from VictoriaMetrics

    Uses rate() function to calculate bytes/sec from counter metrics.
    Queries VictoriaMetrics for interface_if_hc_in_octets and interface_if_hc_out_octets.

    Query: GET /api/v1/interfaces/bandwidth/realtime?device_ips=10.195.57.5,10.195.110.62

    Returns:
    {
        "10.195.57.5": {
            "FastEthernet3": {
                "bandwidth_in_bps": 15234567,
                "bandwidth_out_bps": 8123456,
                "bandwidth_in_formatted": "15.2 Mbps",
                "bandwidth_out_formatted": "8.1 Mbps",
                "utilization_in_percent": 15.2,
                "utilization_out_percent": 8.1,
                "interface_speed_bps": 100000000,
                "last_updated": "2025-10-27T10:30:00Z"
            },
            ...
        }
    }
    """
    try:
        from utils.victoriametrics_client import VictoriaMetricsClient

        # Parse device IPs
        ip_list = [ip.strip() for ip in device_ips.split(',') if ip.strip()]

        if not ip_list:
            raise HTTPException(status_code=400, detail="No device IPs provided")

        if len(ip_list) > 200:
            raise HTTPException(status_code=400, detail="Too many devices requested (max 200)")

        # Get devices and their interfaces from PostgreSQL
        devices = db.execute(
            select(StandaloneDevice).where(StandaloneDevice.ip.in_(ip_list))
        ).scalars().all()

        # Initialize VictoriaMetrics client
        vm_client = VictoriaMetricsClient()

        result = {}
        for device in devices:
            interfaces = db.execute(
                select(DeviceInterface).where(
                    and_(
                        DeviceInterface.device_id == device.id,
                        DeviceInterface.enabled == True
                    )
                )
            ).scalars().all()

            device_bandwidth = {}
            for iface in interfaces:
                # Query VictoriaMetrics for bandwidth
                # rate() calculates per-second change over 1 minute window
                # Multiply by 8 to convert octets/sec to bits/sec
                query_in = f'rate(interface_if_hc_in_octets{{device_ip="{device.ip}",if_name="{iface.if_name}"}}[1m]) * 8'
                query_out = f'rate(interface_if_hc_out_octets{{device_ip="{device.ip}",if_name="{iface.if_name}"}}[1m]) * 8'

                try:
                    result_in = vm_client.query(query_in)
                    result_out = vm_client.query(query_out)

                    bw_in_bps = 0
                    bw_out_bps = 0

                    # Extract bandwidth values from VictoriaMetrics response
                    if result_in and result_in.get("status") == "success":
                        data_in = result_in.get("data", {}).get("result", [])
                        if data_in and len(data_in) > 0:
                            value_in = data_in[0].get("value", [None, None])
                            if value_in[1] is not None:
                                bw_in_bps = float(value_in[1])

                    if result_out and result_out.get("status") == "success":
                        data_out = result_out.get("data", {}).get("result", [])
                        if data_out and len(data_out) > 0:
                            value_out = data_out[0].get("value", [None, None])
                            if value_out[1] is not None:
                                bw_out_bps = float(value_out[1])

                    # Calculate utilization percentage
                    util_in = (bw_in_bps / iface.speed * 100) if iface.speed and iface.speed > 0 else 0
                    util_out = (bw_out_bps / iface.speed * 100) if iface.speed and iface.speed > 0 else 0

                    device_bandwidth[iface.if_name] = {
                        "bandwidth_in_bps": bw_in_bps,
                        "bandwidth_out_bps": bw_out_bps,
                        "bandwidth_in_formatted": format_bandwidth(bw_in_bps),
                        "bandwidth_out_formatted": format_bandwidth(bw_out_bps),
                        "utilization_in_percent": round(util_in, 1),
                        "utilization_out_percent": round(util_out, 1),
                        "interface_speed_bps": iface.speed,
                        "last_updated": datetime.utcnow().isoformat()
                    }

                except Exception as e:
                    logger.warning(f"Failed to get bandwidth for {device.ip} {iface.if_name}: {e}")
                    # Return zero bandwidth instead of failing
                    device_bandwidth[iface.if_name] = {
                        "bandwidth_in_bps": 0,
                        "bandwidth_out_bps": 0,
                        "bandwidth_in_formatted": "0 bps",
                        "bandwidth_out_formatted": "0 bps",
                        "utilization_in_percent": 0,
                        "utilization_out_percent": 0,
                        "interface_speed_bps": iface.speed,
                        "last_updated": datetime.utcnow().isoformat()
                    }

            result[device.ip] = device_bandwidth

        # Add empty objects for devices with no interfaces
        for ip in ip_list:
            if ip not in result:
                result[ip] = {}

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get interface bandwidth: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get interface bandwidth: {str(e)}")


def format_bandwidth(bps: float) -> str:
    """Format bandwidth in human-readable form"""
    if bps >= 1_000_000_000:  # Gbps
        return f"{bps / 1_000_000_000:.1f} Gbps"
    elif bps >= 1_000_000:  # Mbps
        return f"{bps / 1_000_000:.1f} Mbps"
    elif bps >= 1_000:  # Kbps
        return f"{bps / 1_000:.1f} Kbps"
    else:  # bps
        return f"{bps:.0f} bps"


@router.get("/isp-interface-history/{device_ip}")
async def get_isp_interface_history(
    device_ip: str,
    time_range: str = Query("1h", regex="^(30m|1h|3h|6h|12h|24h|7d|30d)$"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get historical metrics for ISP interfaces (Magti, Silknet) on .5 routers

    This endpoint retrieves historical interface metrics for ISP connections
    to help identify ISP-side vs customer-side issues.

    Args:
        device_ip: IP address of the .5 router
        time_range: Time range for historical data (30m, 1h, 3h, 6h, 12h, 24h, 7d, 30d)

    Returns:
        Dictionary with magti and silknet interface history data
    """
    from datetime import timedelta

    # Validate .5 device
    if not device_ip.endswith('.5'):
        raise HTTPException(
            status_code=400,
            detail="Only .5 routers have ISP interfaces. This device does not end with .5"
        )

    # Time range mapping
    time_deltas = {
        '30m': timedelta(minutes=30),
        '1h': timedelta(hours=1),
        '3h': timedelta(hours=3),
        '6h': timedelta(hours=6),
        '12h': timedelta(hours=12),
        '24h': timedelta(hours=24),
        '7d': timedelta(days=7),
        '30d': timedelta(days=30),
    }
    cutoff = datetime.utcnow() - time_deltas.get(time_range, timedelta(hours=1))

    # Find device
    device = db.query(StandaloneDevice).filter_by(ip=device_ip).first()
    if not device:
        raise HTTPException(
            status_code=404,
            detail=f"Device with IP {device_ip} not found"
        )

    # Get ISP interfaces
    isp_interfaces = db.query(DeviceInterface).filter(
        DeviceInterface.device_id == device.id,
        DeviceInterface.isp_name.in_(['magti', 'silknet']),
        DeviceInterface.enabled == True
    ).all()

    if not isp_interfaces:
        logger.warning(f"No ISP interfaces found for device {device_ip}")
        return {"magti": None, "silknet": None}

    # Initialize VictoriaMetrics client for time-series queries
    from utils.victoriametrics_client import VictoriaMetricsClient
    vm_client = VictoriaMetricsClient()

    result = {"magti": None, "silknet": None}

    for iface in isp_interfaces:
        # Query VictoriaMetrics for historical interface metrics (NOT PostgreSQL!)
        # Your VM has: interface_oper_status, interface_if_in_errors, interface_if_out_errors, etc.

        # Build PromQL queries for this interface
        device_filter = f'device_ip="{device_ip}",if_name="{iface.if_name}"'

        # Query oper_status for time-series data
        start_time = f"-{time_range}"
        query = f'interface_oper_status{{{device_filter}}}'

        result_vm = vm_client.query_range(
            query=query,
            start=start_time,
            end="now",
            step="1m"  # 1-minute resolution
        )

        history = []
        if result_vm.get("status") == "success":
            data = result_vm.get("data", {}).get("result", [])
            if data and len(data) > 0:
                # Extract values array [[timestamp, value], [timestamp, value], ...]
                values = data[0].get("values", [])

                # Query errors and discards for the same time range
                error_queries = {
                    "in_errors": f'interface_if_in_errors{{{device_filter}}}',
                    "out_errors": f'interface_if_out_errors{{{device_filter}}}',
                    "in_discards": f'interface_if_in_discards{{{device_filter}}}',
                    "out_discards": f'interface_if_out_discards{{{device_filter}}}',
                }

                error_data = {}
                for metric_name, error_query in error_queries.items():
                    error_result = vm_client.query_range(
                        query=error_query,
                        start=start_time,
                        end="now",
                        step="1m"
                    )
                    if error_result.get("status") == "success":
                        error_results = error_result.get("data", {}).get("result", [])
                        if error_results:
                            error_data[metric_name] = {str(t): float(v) for t, v in error_results[0].get("values", [])}

                # Transform to history format
                for timestamp, status_value in values:
                    timestamp_str = str(timestamp)
                    history.append({
                        "timestamp": int(timestamp),
                        "status": 1 if int(float(status_value)) == 1 else 0,  # 1=up, 2=down
                        "in_errors": int(error_data.get("in_errors", {}).get(timestamp_str, 0)),
                        "out_errors": int(error_data.get("out_errors", {}).get(timestamp_str, 0)),
                        "in_discards": int(error_data.get("in_discards", {}).get(timestamp_str, 0)),
                        "out_discards": int(error_data.get("out_discards", {}).get(timestamp_str, 0)),
                    })

        if not history:
            logger.info(f"No VictoriaMetrics data found for interface {iface.if_name} in time range {time_range}")
            continue

        # Store in result
        isp_name = iface.isp_name.lower() if iface.isp_name else 'unknown'

        # Map status integers to strings (1=up, 2=down)
        oper_status_map = {1: 'up', 2: 'down', 3: 'testing', 4: 'unknown', 5: 'dormant', 6: 'notPresent', 7: 'lowerLayerDown'}
        admin_status_map = {1: 'up', 2: 'down', 3: 'testing'}

        result[isp_name] = {
            "interface_name": iface.if_name,
            "interface_description": iface.if_descr,
            "interface_alias": iface.if_alias,
            "current_status": oper_status_map.get(iface.oper_status, 'unknown'),
            "current_admin_status": admin_status_map.get(iface.admin_status, 'unknown'),
            "total_points": len(history),
            "time_range": time_range,
            "history": history
        }

    logger.info(f"Retrieved ISP interface history for {device_ip}: Magti={result['magti'] is not None}, Silknet={result['silknet'] is not None}")

    return result
