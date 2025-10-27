"""
WARD FLUX - Network Topology Discovery
Discovers network topology using LLDP (IEEE 802.1AB) and CDP (Cisco Discovery Protocol)
Maps interface connections between devices
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select, and_

from database import SessionLocal
from monitoring.models import DeviceInterface, StandaloneDevice
from monitoring.snmp.poller import SNMPPoller, SNMPCredentialData

logger = logging.getLogger(__name__)


# LLDP MIB OIDs (IEEE 802.1AB-MIB)
LLDP_OIDS = {
    'lldp_rem_chassis_id': '1.0.8802.1.1.2.1.4.1.1.5',    # Neighbor device ID
    'lldp_rem_port_id': '1.0.8802.1.1.2.1.4.1.1.7',       # Neighbor port ID
    'lldp_rem_sys_name': '1.0.8802.1.1.2.1.4.1.1.9',      # Neighbor device name
    'lldp_rem_sys_desc': '1.0.8802.1.1.2.1.4.1.1.10',     # Neighbor description
    'lldp_rem_port_desc': '1.0.8802.1.1.2.1.4.1.1.8',     # Neighbor port description
}

# CDP MIB OIDs (CISCO-CDP-MIB)
CDP_OIDS = {
    'cdp_cache_device_id': '1.3.6.1.4.1.9.9.23.1.2.1.1.6',    # Neighbor device ID
    'cdp_cache_device_port': '1.3.6.1.4.1.9.9.23.1.2.1.1.7',  # Neighbor port
    'cdp_cache_platform': '1.3.6.1.4.1.9.9.23.1.2.1.1.8',     # Neighbor platform
    'cdp_cache_address': '1.3.6.1.4.1.9.9.23.1.2.1.1.4',      # Neighbor IP address
}


class TopologyDiscovery:
    """
    Network Topology Discovery Engine

    Discovers network connections using:
    - LLDP (IEEE 802.1AB) - Industry standard
    - CDP (Cisco Discovery Protocol) - Cisco proprietary

    Maps interface-to-interface connections
    Identifies neighbor devices
    Builds topology graph
    """

    def __init__(self):
        """Initialize topology discovery"""
        self.poller = SNMPPoller()
        self.poller.timeout = 5
        self.poller.retries = 2

    async def discover_device_topology(
        self,
        device_ip: str,
        device_id: str,
        device_name: str,
        snmp_community: str,
        snmp_version: str = 'v2c',
        snmp_port: int = 161
    ) -> Dict:
        """
        Discover topology for a single device

        Args:
            device_ip: Device IP address
            device_id: Device UUID
            device_name: Device name
            snmp_community: SNMP community string
            snmp_version: SNMP version
            snmp_port: SNMP port

        Returns:
            Dict with discovery results
        """
        result = {
            'device_id': str(device_id),
            'device_ip': device_ip,
            'device_name': device_name,
            'success': False,
            'neighbors_found': 0,
            'connections_mapped': 0,
            'protocol_used': None,
            'error': None
        }

        try:
            credentials = SNMPCredentialData(
                version=snmp_version,
                community=snmp_community
            )

            # Try LLDP first (industry standard)
            lldp_neighbors = await self._discover_lldp_neighbors(
                device_ip, credentials, snmp_port
            )

            if lldp_neighbors:
                result['protocol_used'] = 'LLDP'
                result['neighbors_found'] = len(lldp_neighbors)
                logger.info(f"Found {len(lldp_neighbors)} LLDP neighbors on {device_ip}")

            # If LLDP failed, try CDP (Cisco)
            if not lldp_neighbors:
                cdp_neighbors = await self._discover_cdp_neighbors(
                    device_ip, credentials, snmp_port
                )

                if cdp_neighbors:
                    result['protocol_used'] = 'CDP'
                    result['neighbors_found'] = len(cdp_neighbors)
                    logger.info(f"Found {len(cdp_neighbors)} CDP neighbors on {device_ip}")
                    lldp_neighbors = cdp_neighbors  # Use CDP data

            # Map connections to database
            if lldp_neighbors:
                mapped_count = await self._map_connections_to_database(
                    device_id, lldp_neighbors
                )
                result['connections_mapped'] = mapped_count

            result['success'] = True

        except Exception as e:
            logger.error(f"Topology discovery failed for {device_ip}: {str(e)}", exc_info=True)
            result['error'] = str(e)

        return result

    async def _discover_lldp_neighbors(
        self,
        device_ip: str,
        credentials: SNMPCredentialData,
        port: int = 161
    ) -> List[Dict]:
        """
        Discover neighbors using LLDP

        Args:
            device_ip: Device IP
            credentials: SNMP credentials
            port: SNMP port

        Returns:
            List of neighbor dicts
        """
        neighbors = []

        try:
            # Walk LLDP remote system name table
            sys_name_results = await self.poller.walk(
                device_ip,
                LLDP_OIDS['lldp_rem_sys_name'],
                credentials,
                port
            )

            if not sys_name_results:
                return []

            # Extract neighbors
            for result in sys_name_results:
                # Skip failed results
                if not result.success:
                    continue

                # OID format: base_oid.timeMark.local_port.neighbor_index
                # Example: 1.0.8802.1.1.2.1.4.1.1.9.0.1.1
                oid_parts = result.oid.split('.')

                if len(oid_parts) >= 3:
                    time_mark = oid_parts[-3]
                    local_port = oid_parts[-2]
                    neighbor_index = oid_parts[-1]

                    neighbor = {
                        'local_port_index': local_port,
                        'neighbor_name': str(result.value) if result.value else None,
                        'neighbor_chassis_id': None,
                        'neighbor_port_id': None,
                        'neighbor_port_desc': None,
                        'neighbor_sys_desc': None,
                    }

                    # Try to get additional neighbor info
                    suffix = f"{time_mark}.{local_port}.{neighbor_index}"

                    # Get chassis ID
                    try:
                        chassis_oid = f"{LLDP_OIDS['lldp_rem_chassis_id']}.{suffix}"
                        chassis_result = await self.poller.get(device_ip, chassis_oid, credentials, port)
                        if chassis_result.success:
                            neighbor['neighbor_chassis_id'] = str(chassis_result.value)
                    except:
                        pass

                    # Get port ID
                    try:
                        port_oid = f"{LLDP_OIDS['lldp_rem_port_id']}.{suffix}"
                        port_result = await self.poller.get(device_ip, port_oid, credentials, port)
                        if port_result.success:
                            neighbor['neighbor_port_id'] = str(port_result.value)
                    except:
                        pass

                    # Get port description
                    try:
                        port_desc_oid = f"{LLDP_OIDS['lldp_rem_port_desc']}.{suffix}"
                        port_desc_result = await self.poller.get(device_ip, port_desc_oid, credentials, port)
                        if port_desc_result.success:
                            neighbor['neighbor_port_desc'] = str(port_desc_result.value)
                    except:
                        pass

                    neighbors.append(neighbor)

        except Exception as e:
            logger.debug(f"LLDP discovery failed for {device_ip}: {str(e)}")
            return []

        return neighbors

    async def _discover_cdp_neighbors(
        self,
        device_ip: str,
        credentials: SNMPCredentialData,
        port: int = 161
    ) -> List[Dict]:
        """
        Discover neighbors using CDP (Cisco)

        Args:
            device_ip: Device IP
            credentials: SNMP credentials
            port: SNMP port

        Returns:
            List of neighbor dicts
        """
        neighbors = []

        try:
            # Walk CDP cache device ID table
            device_id_results = await self.poller.walk(
                device_ip,
                CDP_OIDS['cdp_cache_device_id'],
                credentials,
                port
            )

            if not device_id_results:
                return []

            # Extract neighbors
            for result in device_id_results:
                # Skip failed results
                if not result.success:
                    continue

                # OID format: base_oid.if_index.cache_index
                # Example: 1.3.6.1.4.1.9.9.23.1.2.1.1.6.10.1
                oid_parts = result.oid.split('.')

                if len(oid_parts) >= 2:
                    local_port = oid_parts[-2]
                    cache_index = oid_parts[-1]

                    neighbor = {
                        'local_port_index': local_port,
                        'neighbor_name': str(result.value) if result.value else None,
                        'neighbor_chassis_id': None,
                        'neighbor_port_id': None,
                        'neighbor_port_desc': None,
                        'neighbor_platform': None,
                        'neighbor_ip': None,
                    }

                    suffix = f"{local_port}.{cache_index}"

                    # Get device port
                    try:
                        port_oid = f"{CDP_OIDS['cdp_cache_device_port']}.{suffix}"
                        port_result = await self.poller.get(device_ip, port_oid, credentials, port)
                        if port_result.success:
                            neighbor['neighbor_port_id'] = str(port_result.value)
                            neighbor['neighbor_port_desc'] = str(port_result.value)
                    except:
                        pass

                    # Get platform
                    try:
                        platform_oid = f"{CDP_OIDS['cdp_cache_platform']}.{suffix}"
                        platform_result = await self.poller.get(device_ip, platform_oid, credentials, port)
                        if platform_result.success:
                            neighbor['neighbor_platform'] = str(platform_result.value)
                    except:
                        pass

                    # Get IP address
                    try:
                        addr_oid = f"{CDP_OIDS['cdp_cache_address']}.{suffix}"
                        addr_result = await self.poller.get(device_ip, addr_oid, credentials, port)
                        if addr_result.success:
                            neighbor['neighbor_ip'] = str(addr_result.value)
                    except:
                        pass

                    neighbors.append(neighbor)

        except Exception as e:
            logger.debug(f"CDP discovery failed for {device_ip}: {str(e)}")
            return []

        return neighbors

    async def _map_connections_to_database(
        self,
        device_id: str,
        neighbors: List[Dict]
    ) -> int:
        """
        Map discovered neighbors to database connections

        Args:
            device_id: Source device UUID
            neighbors: List of neighbor dicts

        Returns:
            Number of connections mapped
        """
        if not neighbors:
            return 0

        db = SessionLocal()
        mapped_count = 0

        try:
            for neighbor in neighbors:
                try:
                    local_port_index = neighbor.get('local_port_index')
                    neighbor_name = neighbor.get('neighbor_name')
                    neighbor_port = neighbor.get('neighbor_port_id') or neighbor.get('neighbor_port_desc')

                    if not local_port_index or not neighbor_name:
                        continue

                    # Find local interface
                    local_interface = db.execute(
                        select(DeviceInterface).where(
                            and_(
                                DeviceInterface.device_id == device_id,
                                DeviceInterface.if_index == int(local_port_index)
                            )
                        )
                    ).scalar_one_or_none()

                    if not local_interface:
                        logger.debug(f"Local interface not found: if_index={local_port_index}")
                        continue

                    # Try to find neighbor device in database
                    # Match by name (fuzzy match - remove common prefixes)
                    neighbor_device = await self._find_device_by_name(db, neighbor_name)

                    if neighbor_device:
                        # Update local interface with neighbor info
                        local_interface.connected_to_device_id = neighbor_device.id
                        local_interface.lldp_neighbor_name = neighbor_name
                        local_interface.lldp_neighbor_port = neighbor_port

                        # Try to find neighbor interface
                        if neighbor_port:
                            neighbor_interface = await self._find_interface_by_name(
                                db, neighbor_device.id, neighbor_port
                            )

                            if neighbor_interface:
                                local_interface.connected_to_interface_id = neighbor_interface.id

                        db.commit()
                        mapped_count += 1
                        logger.info(
                            f"Mapped connection: {local_interface.if_name} -> "
                            f"{neighbor_name} ({neighbor_port})"
                        )
                    else:
                        # Neighbor not in database (orphan)
                        local_interface.lldp_neighbor_name = neighbor_name
                        local_interface.lldp_neighbor_port = neighbor_port
                        db.commit()
                        logger.debug(f"Orphan neighbor found: {neighbor_name} (not in database)")

                except Exception as e:
                    logger.error(f"Failed to map neighbor: {str(e)}")
                    continue

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to map connections: {str(e)}", exc_info=True)
        finally:
            db.close()

        return mapped_count

    async def _find_device_by_name(self, db, neighbor_name: str) -> Optional[StandaloneDevice]:
        """
        Find device by name (fuzzy match)

        Args:
            db: Database session
            neighbor_name: Neighbor device name

        Returns:
            StandaloneDevice or None
        """
        # Clean neighbor name (remove common prefixes, domains, etc.)
        clean_name = neighbor_name.split('.')[0]  # Remove domain
        clean_name = clean_name.replace('_', '-').replace(' ', '-')

        # Try exact match first
        device = db.execute(
            select(StandaloneDevice).where(
                StandaloneDevice.name == neighbor_name
            )
        ).scalar_one_or_none()

        if device:
            return device

        # Try fuzzy match (name contains or starts with)
        device = db.execute(
            select(StandaloneDevice).where(
                StandaloneDevice.name.ilike(f"%{clean_name}%")
            )
        ).scalar_one_or_none()

        return device

    async def _find_interface_by_name(
        self,
        db,
        device_id: str,
        port_name: str
    ) -> Optional[DeviceInterface]:
        """
        Find interface by name on a device

        Args:
            db: Database session
            device_id: Device UUID
            port_name: Interface name (Gi0/0/0, etc.)

        Returns:
            DeviceInterface or None
        """
        # Clean port name
        clean_port = port_name.strip()

        # Try exact match on if_name
        interface = db.execute(
            select(DeviceInterface).where(
                and_(
                    DeviceInterface.device_id == device_id,
                    DeviceInterface.if_name == clean_port
                )
            )
        ).scalar_one_or_none()

        if interface:
            return interface

        # Try match on if_descr
        interface = db.execute(
            select(DeviceInterface).where(
                and_(
                    DeviceInterface.device_id == device_id,
                    DeviceInterface.if_descr.ilike(f"%{clean_port}%")
                )
            )
        ).scalar_one_or_none()

        return interface

    def build_topology_graph(self) -> Dict:
        """
        Build complete network topology graph

        Returns:
            Dict with nodes (devices) and edges (connections)
        """
        db = SessionLocal()

        try:
            # Get all devices
            devices = db.execute(select(StandaloneDevice)).scalars().all()

            # Get all interface connections
            connections = db.execute(
                select(DeviceInterface).where(
                    DeviceInterface.connected_to_device_id.isnot(None)
                )
            ).scalars().all()

            # Build graph
            nodes = []
            edges = []

            # Add nodes (devices)
            for device in devices:
                nodes.append({
                    'id': str(device.id),
                    'name': device.name,
                    'ip': device.ip,
                    'device_type': device.device_type,
                    'vendor': device.vendor,
                })

            # Add edges (connections)
            for interface in connections:
                if interface.connected_to_device_id:
                    edges.append({
                        'source_device_id': str(interface.device_id),
                        'source_interface_id': str(interface.id),
                        'source_interface_name': interface.if_name,
                        'target_device_id': str(interface.connected_to_device_id),
                        'target_interface_id': str(interface.connected_to_interface_id) if interface.connected_to_interface_id else None,
                        'target_interface_name': interface.lldp_neighbor_port,
                        'interface_type': interface.interface_type,
                        'is_critical': interface.is_critical,
                    })

            return {
                'nodes': nodes,
                'edges': edges,
                'node_count': len(nodes),
                'edge_count': len(edges),
            }

        finally:
            db.close()


# Singleton instance
topology_discovery = TopologyDiscovery()
