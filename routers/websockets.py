"""
WARD Tech Solutions - WebSockets Router
Handles real-time WebSocket connections for device updates, router interfaces, and notifications
"""
import asyncio
import concurrent.futures
import json
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect

from routers.utils import run_in_executor

# Thread pool executor
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

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
            except:
                # Remove dead connections
                try:
                    self.disconnect(connection)
                except:
                    pass

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
            zabbix = app.state.zabbix
            # Note: sync client doesn't have use_cache param, just call get_all_hosts
            devices = await run_in_executor(zabbix.get_all_hosts)
            changes = []

            for device in devices:
                device_id = device['hostid']
                current_status = device.get('ping_status', 'Unknown')

                if device_id in last_state:
                    if last_state[device_id] != current_status:
                        changes.append({
                            'hostid': device_id,
                            'hostname': device['display_name'],
                            'old_status': last_state[device_id],
                            'new_status': current_status,
                            'timestamp': datetime.now().isoformat()
                        })

                last_state[device_id] = current_status

            # Broadcast changes to all connected clients
            if changes and app.state.websocket_connections:
                message = json.dumps({'type': 'status_change', 'changes': changes})

                disconnected = []
                for websocket in app.state.websocket_connections:
                    try:
                        await websocket.send_text(message)
                    except:
                        disconnected.append(websocket)

                # Remove disconnected clients
                for ws in disconnected:
                    app.state.websocket_connections.remove(ws)

            await asyncio.sleep(30)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Monitor error: {e}")
            await asyncio.sleep(30)


@router.websocket("/ws/router-interfaces/{hostid}")
async def websocket_router_interfaces(websocket: WebSocket, hostid: str):
    """WebSocket endpoint for live router interface monitoring - No Auth Required"""
    print(f"[WS] Router interface connection request for hostid: {hostid}")

    try:
        await websocket.accept()
        print(f"[WS] WebSocket accepted for router {hostid}")
    except Exception as e:
        print(f"[WS ERROR] Failed to accept WebSocket: {e}")
        return

    zabbix = websocket.app.state.zabbix

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            'type': 'connected',
            'hostid': hostid,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

        # Background task to fetch interface data every 5 seconds
        async def stream_interfaces():
            while True:
                try:
                    # Fetch interface data
                    loop = asyncio.get_event_loop()
                    interfaces = await loop.run_in_executor(executor, lambda: zabbix.get_router_interfaces(hostid))

                    # Ensure interfaces is a dict
                    if not isinstance(interfaces, dict):
                        print(f"[WS ERROR] Interfaces is not a dict: {type(interfaces)}")
                        interfaces = {}

                    # Calculate summary stats
                    total_interfaces = len(interfaces)
                    up_interfaces = sum(1 for iface in interfaces.values() if iface.get('status') == 'up')
                    total_bandwidth_in = sum(iface.get('bandwidth_in', 0) for iface in interfaces.values())
                    total_bandwidth_out = sum(iface.get('bandwidth_out', 0) for iface in interfaces.values())
                    total_errors_in = sum(iface.get('errors_in', 0) for iface in interfaces.values())
                    total_errors_out = sum(iface.get('errors_out', 0) for iface in interfaces.values())

                    # Send update
                    await websocket.send_json({
                        'type': 'interface_update',
                        'hostid': hostid,
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'summary': {
                            'total': total_interfaces,
                            'up': up_interfaces,
                            'down': total_interfaces - up_interfaces,
                            'bandwidth_in_mbps': round(total_bandwidth_in / 1000000, 2),
                            'bandwidth_out_mbps': round(total_bandwidth_out / 1000000, 2),
                            'errors_in': total_errors_in,
                            'errors_out': total_errors_out
                        },
                        'interfaces': [
                            {
                                'name': name,
                                'status': data.get('status', 'unknown'),
                                'bandwidth_in_mbps': round(data.get('bandwidth_in', 0) / 1000000, 2),
                                'bandwidth_out_mbps': round(data.get('bandwidth_out', 0) / 1000000, 2),
                                'errors_in': data.get('errors_in', 0),
                                'errors_out': data.get('errors_out', 0),
                                'description': data.get('description', '')
                            }
                            for name, data in sorted(interfaces.items())
                        ]
                    })

                    # Wait 5 seconds before next update
                    await asyncio.sleep(5)

                except Exception as e:
                    print(f"Error streaming interfaces for {hostid}: {e}")
                    await asyncio.sleep(5)

        # Start background task
        task = asyncio.create_task(stream_interfaces())

        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Echo back for ping/pong
            await websocket.send_json({'type': 'pong', 'timestamp': datetime.now(timezone.utc).isoformat()})

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for router {hostid}")
        task.cancel()
    except Exception as e:
        print(f"WebSocket error for router {hostid}: {e}")
        try:
            task.cancel()
        except:
            pass


@router.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time notifications"""
    await manager.connect(websocket)
    zabbix = websocket.app.state.zabbix

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            'type': 'connection',
            'message': 'Connected to notification service',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

        # Background task to check for problems periodically
        async def check_problems():
            while True:
                try:
                    # Fetch current problems from Zabbix
                    problems = await asyncio.to_thread(zabbix.get_problems)

                    if problems:
                        for problem in problems:
                            # Send notification for each problem
                            severity_map = {
                                '0': 'info',
                                '1': 'info',
                                '2': 'warning',
                                '3': 'warning',
                                '4': 'critical',
                                '5': 'critical'
                            }

                            await websocket.send_json({
                                'id': problem.get('eventid'),
                                'type': severity_map.get(str(problem.get('severity', 0)), 'info'),
                                'title': problem.get('name', 'Problem Detected'),
                                'message': f"{problem.get('hostname', 'Unknown Host')} - {problem.get('description', 'Issue detected')}",
                                'timestamp': datetime.now(timezone.utc).isoformat(),
                                'link': f"/devices?hostid={problem.get('hostid')}"
                            })

                    # Wait 30 seconds before next check
                    await asyncio.sleep(30)

                except Exception as e:
                    print(f"Error checking problems: {e}")
                    await asyncio.sleep(30)

        # Start background task
        task = asyncio.create_task(check_problems())

        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Echo back for ping/pong
            await websocket.send_json({'type': 'pong', 'timestamp': datetime.now(timezone.utc).isoformat()})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        task.cancel()
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)
        try:
            task.cancel()
        except:
            pass

