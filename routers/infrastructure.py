"""
WARD Tech Solutions - Infrastructure Router
Standalone topology and interface inventory
"""
import logging
import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_active_user
from database import PingResult, User, UserRole, get_db
from monitoring.models import NetworkTopology, StandaloneDevice

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["infrastructure"])


def _filter_devices_for_user(devices: List[StandaloneDevice], user: User) -> List[StandaloneDevice]:
    if user.role == UserRole.ADMIN:
        return devices

    allowed_branches = [
        b.strip() for b in (user.branches or "").split(",") if b.strip()
    ] if user.branches else []

    filtered: List[StandaloneDevice] = []
    for device in devices:
        fields = device.custom_fields or {}
        if user.region and fields.get("region") != user.region:
            continue
        if allowed_branches and fields.get("branch") not in allowed_branches:
            continue
        filtered.append(device)
    return filtered


def _serialize_device(device: StandaloneDevice, latest_ping: Optional[PingResult]) -> Dict:
    fields = device.custom_fields or {}
    status = "Unknown"
    if latest_ping:
        status = "Up" if latest_ping.is_reachable else "Down"
    elif fields.get("ping_status"):
        status = fields.get("ping_status")

    return {
        "id": str(device.id),
        "label": device.name,
        "ip": device.ip,
        "vendor": device.vendor,
        "device_type": device.device_type,
        "status": status,
        "branch": fields.get("branch"),
        "region": fields.get("region"),
        "latitude": fields.get("latitude"),
        "longitude": fields.get("longitude"),
        "title": f"{device.name}\n{device.ip}\nType: {device.device_type or 'Unknown'}\nStatus: {status}",
    }


@router.get("/router/{hostid}/interfaces")
async def get_router_interfaces(
    hostid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return stored interface statistics for the requested standalone device."""
    try:
        device_uuid = uuid.UUID(hostid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid device identifier")

    device = db.query(StandaloneDevice).filter(StandaloneDevice.id == device_uuid).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if current_user.role != UserRole.ADMIN:
        fields = device.custom_fields or {}
        if current_user.region and fields.get("region") != current_user.region:
            raise HTTPException(status_code=403, detail="Forbidden")
        if current_user.branches:
            allowed = [b.strip() for b in current_user.branches.split(",") if b.strip()]
            if allowed and fields.get("branch") not in allowed:
                raise HTTPException(status_code=403, detail="Forbidden")

    topology_entries = (
        db.query(NetworkTopology)
        .filter(NetworkTopology.source_device_id == device_uuid)
        .order_by(NetworkTopology.last_seen.desc())
        .all()
    )

    interfaces: Dict[str, Dict] = {}
    for entry in topology_entries:
        name = entry.interface_name or "unknown"
        interface = interfaces.setdefault(name, {})
        interface.update(
            {
                "description": entry.connection_type,
                "status": "up" if entry.is_active else "down",
                "target_ip": entry.target_ip,
                "target_device_id": str(entry.target_device_id) if entry.target_device_id else None,
                "last_seen": entry.last_seen.isoformat() if entry.last_seen else None,
            }
        )

    return {"device_id": hostid, "interfaces": interfaces}


@router.get("/topology")
async def get_topology(
    view: str = "discovery",
    limit: int = 200,
    region: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return network topology graph derived from standalone discovery data."""
    devices = db.query(StandaloneDevice).all()
    devices = _filter_devices_for_user(devices, current_user)

    if region:
        devices = [
            d for d in devices
            if (d.custom_fields or {}).get("region") == region
        ]

    if len(devices) > limit:
        devices = devices[:limit]

    device_map = {str(device.id): device for device in devices}
    device_ids = [device.id for device in devices]
    ips = {device.ip for device in devices if device.ip}

    ping_lookup: Dict[str, PingResult] = {}
    for ping in (
        db.query(PingResult)
        .filter(PingResult.device_ip.in_(ips))
        .order_by(PingResult.device_ip, PingResult.timestamp.desc())
        .all()
    ):
        if ping.device_ip not in ping_lookup:
            ping_lookup[ping.device_ip] = ping

    nodes = [
        _serialize_device(device, ping_lookup.get(device.ip))
        for device in devices
    ]

    topology_edges = db.query(NetworkTopology).filter(
        NetworkTopology.source_device_id.in_(device_ids)
    ).all()

    edges = []
    seen = set()
    for edge in topology_edges:
        if edge.target_device_id and str(edge.target_device_id) not in device_map:
            continue

        edge_key = tuple(sorted([str(edge.source_device_id), str(edge.target_device_id)]))
        if edge_key in seen:
            continue
        seen.add(edge_key)

        edges.append(
            {
                "from": str(edge.source_device_id),
                "to": str(edge.target_device_id) if edge.target_device_id else edge.target_ip,
                "label": edge.connection_type or "",
                "title": f"{edge.interface_name or ''} → {edge.target_interface or ''}\nStatus: {'active' if edge.is_active else 'inactive'}",
                "color": "#14b8a6" if edge.is_active else "#dc3545",
            }
        )

    stats = {
        "total_devices": len(nodes),
        "links": len(edges),
        "active_links": sum(1 for e in edges if e["color"] == "#14b8a6"),
    }

    return {"view": view, "nodes": nodes, "edges": edges, "stats": stats}
