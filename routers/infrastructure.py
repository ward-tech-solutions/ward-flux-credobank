"""
WARD Tech Solutions - Infrastructure Router
Handles network topology visualization and router interface monitoring
"""
import logging
import asyncio
import concurrent.futures
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, Request

from auth import get_current_active_user
from database import User, UserRole
from routers.utils import get_monitored_groupids

logger = logging.getLogger(__name__)

# Thread pool executor
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

# Create router
router = APIRouter(prefix="/api/v1", tags=["infrastructure"])


@router.get("/router/{hostid}/interfaces")
async def get_router_interfaces(request: Request, hostid: str, current_user: User = Depends(get_current_active_user)):
    """Get router interface statistics"""
    zabbix = request.app.state.zabbix
    loop = asyncio.get_event_loop()
    interfaces = await loop.run_in_executor(executor, lambda: zabbix.get_router_interfaces(hostid))
    return {"hostid": hostid, "interfaces": interfaces}


@router.get("/topology")
async def get_topology(
    request: Request,
    view: str = "discovery",  # Changed default to discovery mode
    limit: int = 200,
    region: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
):
    """Get network topology data discovered from interface descriptions"""
    zabbix = request.app.state.zabbix
    groupids = get_monitored_groupids()
    loop = asyncio.get_event_loop()
    devices = await loop.run_in_executor(executor, lambda: zabbix.get_all_hosts(group_ids=groupids))

    # Apply user permission filtering (non-admin users)
    if current_user.role != UserRole.ADMIN:
        # Filter by region if user has regional restriction
        if current_user.region:
            devices = [d for d in devices if d.get("region") == current_user.region]

        # Filter by branches if user has branch restrictions
        if current_user.branches:
            allowed_branches = [b.strip() for b in current_user.branches.split(",")]
            devices = [d for d in devices if d.get("branch") in allowed_branches]

    if region:
        devices = [d for d in devices if d["region"] == region]

    if len(devices) > limit:
        devices = devices[:limit]

    nodes = []
    edges = []
    edges_set = set()  # Track edges to avoid duplicates

    # Build device name mapping for connection discovery
    device_name_map = {}  # Maps normalized device names to hostids
    for device in devices:
        display_name = device.get("display_name", "").lower().strip()
        # Store multiple name variations for matching
        device_name_map[display_name] = device["hostid"]
        # Also store without suffixes like "-881", "-1111"
        base_name = display_name.split("-")[0].strip()
        if base_name and base_name != display_name:
            device_name_map[base_name] = device["hostid"]

    logger.info(f"[Topology] Built device name map with {len(device_name_map)} entries")

    # Create nodes for all devices
    for device in devices:
        status = device.get("ping_status", "Unknown")
        device_type = device.get("device_type", "Unknown")
        ip = device.get("ip", "")

        # Determine device type based on IP if not set
        if ip and device_type in ["Switch", "L3 Switch", "Branch Switch"]:
            last_octet = ip.split(".")[-1] if "." in ip else ""
            if last_octet == "5":
                device_type = "Router"
            elif last_octet in ["245", "246"]:
                device_type = "Switch"

        # Color and size based on device type
        if device_type == "Core Router":
            color = "#FF6B35" if status == "Up" else "#dc3545"
            size = 35
            shape = "diamond"
        elif device_type in ["Router", "Switch", "L3 Switch", "Branch Switch"]:
            color = "#14b8a6" if status == "Up" else "#dc3545"
            size = 25
            shape = "box"
        else:
            color = "#6B7280" if status == "Up" else "#dc3545"
            size = 15
            shape = "dot"

        nodes.append({
            "id": device["hostid"],
            "label": device["display_name"],
            "title": f"{device['display_name']}\n{ip}\nType: {device_type}\nStatus: {status}",
            "color": color,
            "size": size,
            "shape": shape,
            "deviceType": device_type,
            "branch": device.get("branch", "Unknown"),
        })

    logger.info(f"[Topology] Created {len(nodes)} nodes")

    # Discover connections from interface descriptions
    connection_count = 0
    for device in devices:
        try:
            # Fetch interfaces for this device
            interfaces = await loop.run_in_executor(
                executor, lambda d=device: zabbix.get_router_interfaces(d["hostid"])
            )

            # Parse interface descriptions to find connections
            for iface_name, iface_data in interfaces.items():
                description = iface_data.get("description", "").lower().strip()
                if not description or len(description) < 3:
                    continue

                # Skip management interfaces
                if any(skip in description for skip in ["mgmt", "loopback", "null", "vlan"]):
                    continue

                # Try to match description to device names
                matched_hostid = None
                for device_name, hostid in device_name_map.items():
                    if device_name in description or description in device_name:
                        # Don't connect device to itself
                        if hostid != device["hostid"]:
                            matched_hostid = hostid
                            break

                if matched_hostid:
                    # Create edge (avoid duplicates)
                    edge_key = tuple(sorted([device["hostid"], matched_hostid]))
                    if edge_key not in edges_set:
                        edges_set.add(edge_key)

                        # Get bandwidth info
                        bw_in_mbps = iface_data.get("bandwidth_in", 0) / 1000000
                        bw_out_mbps = iface_data.get("bandwidth_out", 0) / 1000000
                        iface_status = iface_data.get("status", "unknown")

                        edge_label = f"↓{bw_in_mbps:.1f}M ↑{bw_out_mbps:.1f}M" if bw_in_mbps > 0 else ""

                        edges.append({
                            "from": device["hostid"],
                            "to": matched_hostid,
                            "label": edge_label,
                            "title": f"Interface: {iface_name}\nDescription: {iface_data.get('description', '')}\n↓ {bw_in_mbps:.2f} Mbps\n↑ {bw_out_mbps:.2f} Mbps\nStatus: {iface_status}",
                            "color": "#14b8a6" if iface_status == "up" else "#dc3545",
                            "width": 3 if bw_in_mbps > 100 else 2,
                            "font": {"size": 10, "color": "#00d9ff"},
                        })
                        connection_count += 1

        except Exception as e:
            logger.debug(f"[Topology] Could not fetch interfaces for {device.get('display_name', 'unknown')}: {e}")
            continue

    logger.info(f"[Topology] Discovered {connection_count} connections from interface descriptions")

    # Count device types for stats
    core_routers = [d for d in devices if d.get("device_type") == "Core Router"]
    branch_switches = [d for d in devices if d.get("device_type") in ["Switch", "L3 Switch", "Branch Switch", "Router"]]
    end_devices = [d for d in devices if d not in core_routers and d not in branch_switches]

    # Legacy hierarchical view support removed - now using discovery mode only

    if False and view == "hierarchical":
        # Level 0: Core Routers (LEGACY CODE - DISABLED)
        for router in core_routers:
            status = router.get("ping_status", "Unknown")
            # Fetch interface statistics for core routers
            try:
                interfaces = await loop.run_in_executor(
                    executor, lambda r=router: zabbix.get_router_interfaces(r["hostid"])
                )
                total_interfaces = len(interfaces)
                up_interfaces = sum(1 for iface in interfaces.values() if iface.get("status") == "up")
                total_bandwidth_in = sum(iface.get("bandwidth_in", 0) for iface in interfaces.values())
                total_bandwidth_out = sum(iface.get("bandwidth_out", 0) for iface in interfaces.values())

                interface_info = f"\n{up_interfaces}/{total_interfaces} interfaces up"
                bandwidth_info = (
                    f"\nIn: {total_bandwidth_in/1000000:.1f} Mbps | Out: {total_bandwidth_out/1000000:.1f} Mbps"
                )
            except Exception as e:
                logger.info(f"[ERROR] Failed to get interfaces for {router['display_name']}: {e}")
                interface_info = ""
                bandwidth_info = ""
                interfaces = {}

            nodes.append(
                {
                    "id": router["hostid"],
                    "label": router["display_name"],
                    "title": f"{router['display_name']}\n{router['ip']}\nStatus: {status}{interface_info}{bandwidth_info}",
                    "group": "core",
                    "level": 0,
                    "size": 35,
                    "color": "#FF6B35" if status == "Up" else "#dc3545",
                    "shape": "diamond",
                    "deviceType": "Core Router",
                    "interfaces": interfaces,
                }
            )

        # Level 1: Branch Switches (connect to core routers)
        branches_by_region = defaultdict(list)
        for switch in branch_switches:
            branches_by_region[switch.get("branch", "Unknown")].append(switch)

        for branch_name, switches in branches_by_region.items():
            for switch in switches:
                status = switch.get("ping_status", "Unknown")

                # Determine device type based on IP address last octet
                ip = switch.get("ip", "")
                device_type = "Switch"  # Default
                if ip:
                    last_octet = ip.split(".")[-1] if "." in ip else ""
                    if last_octet == "5":
                        device_type = "Router"
                    elif last_octet in ["245", "246"]:
                        device_type = "Switch"

                nodes.append(
                    {
                        "id": switch["hostid"],
                        "label": switch["display_name"][:20],
                        "title": f"{switch['display_name']}\n{switch['ip']}\nBranch: {branch_name}\nStatus: {status}",
                        "group": "branch",
                        "level": 1,
                        "size": 20,
                        "color": "#14b8a6" if status == "Up" else "#dc3545",
                        "shape": "box",
                        "branch": branch_name,
                        "deviceType": device_type,  # Add deviceType field
                    }
                )

                # Connect branch switches to core routers
                # In a real deployment, you'd determine actual connections via LLDP/CDP
                # For now, distribute evenly across core routers
                if core_routers:
                    core_router = core_routers[hash(switch["hostid"]) % len(core_routers)]

                    # Try to find matching interface on core router for this branch
                    edge_label = ""
                    edge_title = f"Link: {core_router['display_name']} → {switch['display_name']}"

                    # Get interfaces for this core router to find bandwidth for this connection
                    try:
                        router_interfaces = core_router.get("interfaces", {})
                        # Look for interface connected to this branch
                        branch_name_clean = switch.get("branch", "").lower().replace(" ", "_")

                        for iface_name, iface_data in router_interfaces.items():
                            iface_desc = iface_data.get("description", "").lower()
                            # Match if interface description contains branch name
                            if branch_name_clean and branch_name_clean in iface_desc:
                                bw_in_mbps = iface_data.get("bandwidth_in", 0) / 1000000
                                bw_out_mbps = iface_data.get("bandwidth_out", 0) / 1000000
                                edge_label = f"↓{bw_in_mbps:.1f}M ↑{bw_out_mbps:.1f}M"
                                edge_title += (
                                    f"\nInterface: {iface_name}\n↓ {bw_in_mbps:.2f} Mbps\n↑ {bw_out_mbps:.2f} Mbps"
                                )
                                break
                    except Exception as e:
                        logger.info(f"[WARN] Could not get interface bandwidth: {e}")

                    edges.append(
                        {
                            "from": core_router["hostid"],
                            "to": switch["hostid"],
                            "color": "#14b8a6" if status == "Up" else "#dc3545",
                            "width": 2,
                            "label": edge_label,
                            "title": edge_title,
                            "font": {"size": 10, "color": "#00d9ff", "strokeWidth": 2, "strokeColor": "#000"},
                        }
                    )

        # Level 2: End Devices (connect to branch switches)
        device_types = defaultdict(list)
        for device in end_devices[:100]:  # Limit to 100 end devices for performance
            device_types[device.get("device_type", "Unknown")].append(device)

        for device_type, type_devices in device_types.items():
            for device in type_devices[:20]:  # Max 20 devices per type
                status = device.get("ping_status", "Unknown")
                branch = device.get("branch", "Unknown")

                # Determine icon shape based on device type
                if "ATM" in device_type:
                    shape = "triangle"
                    color = "#9333EA" if status == "Up" else "#dc3545"
                elif "NVR" in device_type or "Camera" in device_type:
                    shape = "star"
                    color = "#3B82F6" if status == "Up" else "#dc3545"
                elif "Access Point" in device_type or "WiFi" in device_type:
                    shape = "dot"
                    color = "#10B981" if status == "Up" else "#dc3545"
                else:
                    shape = "dot"
                    color = "#6B7280" if status == "Up" else "#dc3545"

                nodes.append(
                    {
                        "id": device["hostid"],
                        "label": "",  # No label to reduce clutter
                        "title": f"{device['display_name']}\n{device['ip']}\nType: {device_type}\nBranch: {branch}\nStatus: {status}",
                        "group": device_type,
                        "level": 2,
                        "size": 10,
                        "color": color,
                        "shape": shape,
                        "deviceType": device_type,
                    }
                )

                # Connect to branch switch in same branch
                branch_switch_in_branch = [s for s in branch_switches if s.get("branch") == branch]
                if branch_switch_in_branch:
                    target_switch = branch_switch_in_branch[hash(device["hostid"]) % len(branch_switch_in_branch)]
                    edges.append(
                        {
                            "from": target_switch["hostid"],
                            "to": device["hostid"],
                            "color": color,
                            "width": 0.5,
                            "dashes": status != "Up",
                        }
                    )
                elif branch_switches:
                    # Fallback: connect to any branch switch
                    target_switch = branch_switches[hash(device["hostid"]) % len(branch_switches)]
                    edges.append(
                        {
                            "from": target_switch["hostid"],
                            "to": device["hostid"],
                            "color": color,
                            "width": 0.5,
                            "dashes": True,
                        }
                    )

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "core_routers": len(core_routers),
            "branch_switches": len(branch_switches),
            "end_devices": len(end_devices),
            "total_devices": len(devices),
        },
    }


# ============================================
# WebSocket for Real-Time Updates
# ============================================
# EXTRACTED TO: routers/websockets.py
# @router.websocket("/ws/updates")
# async def monitor_device_changes()


# ============================================
# Backward Compatibility Routes (for old frontend)
# ============================================
