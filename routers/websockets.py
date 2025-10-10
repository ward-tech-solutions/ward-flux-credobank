"""
WARD Tech Solutions - WebSockets Router
Handles real-time WebSocket connections for device updates, router interfaces, and notifications
"""
import logging
import asyncio
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect

from database import SessionLocal
from monitoring.models import AlertHistory, NetworkTopology, StandaloneDevice
from database import PingResult

# Create router
router = APIRouter(tags=["websockets"])


class ConnectionManager:
    """Manage WebSocket connections for real-time notifications"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                # Remove dead connections
                logging.getLogger(__name__).warning(f"Failed to send message to client: {e}")
                try:
                    self.disconnect(connection)
                except Exception as disconnect_error:
                    logging.getLogger(__name__).error(f"Error disconnecting client: {disconnect_error}")


manager = ConnectionManager()


@router.websocket("/ws/updates")
async def websocket_updates(websocket: WebSocket):
    """WebSocket endpoint for real-time device status updates"""
    await websocket.accept()
    websocket.app.state.websocket_connections.append(websocket)

    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        websocket.app.state.websocket_connections.remove(websocket)


async def monitor_device_changes(app: FastAPI):
    """Background task to monitor device changes and broadcast via WebSocket"""
    last_state = {}

    while True:
        try:
            session = SessionLocal()
            devices = session.query(StandaloneDevice).all()

            ping_lookup: Dict[str, PingResult] = {}
            for ping in (
                session.query(PingResult)
                .order_by(PingResult.device_ip, PingResult.timestamp.desc())
                .all()
            ):
                if ping.device_ip not in ping_lookup:
                    ping_lookup[ping.device_ip] = ping

            changes = []

            for device in devices:
                device_id = str(device.id)
                ping = ping_lookup.get(device.ip)
                if ping:
                    current_status = "Up" if ping.is_reachable else "Down"
                else:
                    current_status = (device.custom_fields or {}).get("ping_status", "Unknown")

                if device_id in last_state:
                    if last_state[device_id] != current_status:
                        changes.append(
                            {
                                "hostid": device_id,
                                "hostname": device.name,
                                "old_status": last_state[device_id],
                                "new_status": current_status,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )

                last_state[device_id] = current_status

            session.close()

            # Broadcast changes to all connected clients
            if changes and app.state.websocket_connections:
                message = json.dumps({"type": "status_change", "changes": changes})

                disconnected = []
                for websocket in app.state.websocket_connections:
                    try:
                        await websocket.send_text(message)
                    except Exception as e:
                        logging.getLogger(__name__).error(f"Error: {e}")
                        disconnected.append(websocket)

                # Remove disconnected clients
                for ws in disconnected:
                    app.state.websocket_connections.remove(ws)

            await asyncio.sleep(30)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.info(f"Monitor error: {e}")
            await asyncio.sleep(30)


@router.websocket("/ws/router-interfaces/{hostid}")
async def websocket_router_interfaces(websocket: WebSocket, hostid: str):
    """WebSocket endpoint for streaming stored interface data."""
    logger.info(f"[WS] Router interface connection request for hostid: {hostid}")

    try:
        await websocket.accept()
        logger.info(f"[WS] WebSocket accepted for router {hostid}")
    except Exception as e:
        logger.info(f"[WS ERROR] Failed to accept WebSocket: {e}")
        return

    try:
        source_uuid = uuid.UUID(hostid)
    except ValueError:
        await websocket.send_json({"type": "error", "message": "Invalid device identifier"})
        await websocket.close()
        return

    try:
        # Send initial connection confirmation
        await websocket.send_json(
            {"type": "connected", "hostid": hostid, "timestamp": datetime.now(timezone.utc).isoformat()}
        )

        # Background task to fetch interface data every 5 seconds
        async def stream_interfaces():
            while True:
                session = SessionLocal()
                try:
                    topology_entries = (
                        session.query(NetworkTopology)
                        .filter(NetworkTopology.source_device_id == source_uuid)
                        .order_by(NetworkTopology.last_seen.desc())
                        .all()
                    )

                    interfaces = {}
                    for entry in topology_entries:
                        name = entry.interface_name or "unknown"
                        interface = interfaces.setdefault(name, {})
                        interface.update(
                            {
                                "status": "up" if entry.is_active else "down",
                                "target_ip": entry.target_ip,
                                "target_device_id": str(entry.target_device_id) if entry.target_device_id else None,
                                "description": entry.connection_type,
                                "last_seen": entry.last_seen.isoformat() if entry.last_seen else None,
                            }
                        )

                    await websocket.send_json(
                        {
                            "type": "interface_update",
                            "hostid": hostid,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "summary": {
                                "total": len(interfaces),
                                "up": sum(1 for data in interfaces.values() if data.get("status") == "up"),
                                "down": sum(1 for data in interfaces.values() if data.get("status") == "down"),
                            },
                            "interfaces": [
                                {
                                    "name": name,
                                    "status": data.get("status", "unknown"),
                                    "target_ip": data.get("target_ip"),
                                    "target_device_id": data.get("target_device_id"),
                                    "description": data.get("description", ""),
                                    "last_seen": data.get("last_seen"),
                                }
                                for name, data in sorted(interfaces.items())
                            ],
                        }
                    )

                    await asyncio.sleep(5)
                except Exception as e:
                    logger.info(f"Error streaming interfaces for {hostid}: {e}")
                    await asyncio.sleep(5)
                finally:
                    session.close()

        # Start background task
        task = asyncio.create_task(stream_interfaces())

        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Echo back for ping/pong
            await websocket.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for router {hostid}")
        task.cancel()
    except Exception as e:
        logger.info(f"WebSocket error for router {hostid}: {e}")
        try:
            task.cancel()
        except Exception as e:
            logging.getLogger(__name__).error(f"Error: {e}")
            pass


@router.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time notifications"""
    await manager.connect(websocket)

    task = None
    try:
        # Send initial connection confirmation
        await websocket.send_json(
            {
                "type": "connection",
                "message": "Connected to notification service",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        last_sent: Dict[str, str] = {}

        # Background task to check for problems periodically
        async def check_problems():
            while True:
                session = SessionLocal()
                try:
                    alerts = (
                        session.query(AlertHistory)
                        .filter(AlertHistory.resolved_at.is_(None))
                        .order_by(AlertHistory.triggered_at.desc())
                        .limit(50)
                        .all()
                    )

                    active_ids = set()
                    for alert in alerts:
                        alert_id = str(alert.id)
                        active_ids.add(alert_id)
                        fingerprint = f"{alert.severity}:{alert.message}:{alert.triggered_at}"
                        if last_sent.get(alert_id) == fingerprint:
                            continue

                        await websocket.send_json(
                            {
                                "id": alert_id,
                                "type": alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity),
                                "title": alert.message,
                                "message": f"Device {alert.device_id} reported an alert", 
                                "timestamp": (alert.triggered_at or datetime.now(timezone.utc)).isoformat(),
                                "link": f"/devices/{alert.device_id}" if alert.device_id else None,
                            }
                        )
                        last_sent[alert_id] = fingerprint

                    # Remove entries that are no longer active
                    for alert_id in list(last_sent.keys()):
                        if alert_id not in active_ids:
                            del last_sent[alert_id]

                    await asyncio.sleep(30)
                except Exception as e:
                    logger.info(f"Error checking problems: {e}")
                    await asyncio.sleep(30)
                finally:
                    session.close()

        # Start background task
        task = asyncio.create_task(check_problems())

        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Echo back for ping/pong
            await websocket.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        if task:
            task.cancel()
    except Exception as e:
        logger.info(f"WebSocket error: {e}")
        manager.disconnect(websocket)
        if task:
            try:
                task.cancel()
            except Exception as cancel_error:
                logging.getLogger(__name__).error(f"Error: {cancel_error}")
