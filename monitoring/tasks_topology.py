"""
WARD FLUX - Topology Discovery Tasks
Celery tasks for network topology discovery using LLDP/CDP
"""

import logging
import asyncio
from datetime import datetime
from sqlalchemy import select
from celery import shared_task

from database import SessionLocal
from monitoring.models import StandaloneDevice
from monitoring.topology_discovery import topology_discovery

logger = logging.getLogger(__name__)


@shared_task(name="monitoring.tasks.discover_device_topology", bind=True)
def discover_device_topology_task(self, device_id: str):
    """
    Celery task: Discover topology for a single device

    Args:
        device_id: Device UUID (as string)

    Returns:
        Discovery result dict
    """
    logger.info(f"[Task {self.request.id}] Discovering topology for device {device_id}")

    db = SessionLocal()
    try:
        # Fetch device
        stmt = select(StandaloneDevice).where(StandaloneDevice.id == device_id)
        device = db.execute(stmt).scalar_one_or_none()

        if not device:
            logger.error(f"Device {device_id} not found")
            return {
                'success': False,
                'error': 'Device not found',
                'device_id': device_id
            }

        if not device.enabled:
            logger.info(f"Device {device_id} is disabled, skipping topology discovery")
            return {
                'success': False,
                'error': 'Device disabled',
                'device_id': device_id
            }

        # Get SNMP credentials
        snmp_community = device.snmp_community or 'XoNaz-<h'
        snmp_version = device.snmp_version or 'v2c'
        snmp_port = device.snmp_port or 161

        # Run topology discovery (async)
        result = asyncio.run(
            topology_discovery.discover_device_topology(
                device_ip=device.ip,
                device_id=str(device.id),
                device_name=device.name,
                snmp_community=snmp_community,
                snmp_version=snmp_version,
                snmp_port=snmp_port
            )
        )

        return result

    except Exception as e:
        logger.error(f"Topology discovery task failed for device {device_id}: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'device_id': device_id
        }
    finally:
        db.close()


@shared_task(name="monitoring.tasks.discover_all_topology", bind=True)
def discover_all_topology_task(self):
    """
    Celery task: Discover topology for all enabled devices

    Runs daily via Celery Beat

    Returns:
        Summary of discovery results
    """
    logger.info(f"[Task {self.request.id}] Starting topology discovery for all devices")

    db = SessionLocal()
    summary = {
        'total_devices': 0,
        'successful': 0,
        'failed': 0,
        'total_neighbors_found': 0,
        'total_connections_mapped': 0,
        'lldp_devices': 0,
        'cdp_devices': 0,
        'errors': [],
        'started_at': datetime.utcnow().isoformat(),
    }

    try:
        # Fetch all enabled devices with SNMP
        stmt = select(StandaloneDevice).where(
            StandaloneDevice.enabled == True,
            StandaloneDevice.snmp_community.isnot(None)
        )
        devices = db.execute(stmt).scalars().all()

        summary['total_devices'] = len(devices)
        logger.info(f"Found {len(devices)} devices for topology discovery")

        # Discover topology for each device
        for device in devices:
            try:
                snmp_community = device.snmp_community or 'XoNaz-<h'
                snmp_version = device.snmp_version or 'v2c'
                snmp_port = device.snmp_port or 161

                result = asyncio.run(
                    topology_discovery.discover_device_topology(
                        device_ip=device.ip,
                        device_id=str(device.id),
                        device_name=device.name,
                        snmp_community=snmp_community,
                        snmp_version=snmp_version,
                        snmp_port=snmp_port
                    )
                )

                if result['success']:
                    summary['successful'] += 1
                    summary['total_neighbors_found'] += result['neighbors_found']
                    summary['total_connections_mapped'] += result['connections_mapped']

                    if result['protocol_used'] == 'LLDP':
                        summary['lldp_devices'] += 1
                    elif result['protocol_used'] == 'CDP':
                        summary['cdp_devices'] += 1
                else:
                    summary['failed'] += 1
                    if result.get('error'):
                        summary['errors'].append({
                            'device_ip': device.ip,
                            'device_id': str(device.id),
                            'error': result['error']
                        })

            except Exception as e:
                logger.error(f"Failed to discover topology for device {device.ip}: {str(e)}")
                summary['failed'] += 1
                summary['errors'].append({
                    'device_ip': device.ip,
                    'device_id': str(device.id),
                    'error': str(e)
                })

        summary['completed_at'] = datetime.utcnow().isoformat()

        logger.info(
            f"Topology discovery completed: "
            f"{summary['successful']}/{summary['total_devices']} devices successful, "
            f"{summary['total_connections_mapped']} connections mapped, "
            f"LLDP: {summary['lldp_devices']}, CDP: {summary['cdp_devices']}"
        )

        return summary

    except Exception as e:
        logger.error(f"Topology discovery task failed: {str(e)}", exc_info=True)
        summary['errors'].append({'error': str(e)})
        return summary
    finally:
        db.close()


@shared_task(name="monitoring.tasks.build_topology_graph", bind=True)
def build_topology_graph_task(self):
    """
    Celery task: Build complete network topology graph

    Returns:
        Topology graph (nodes and edges)
    """
    logger.info(f"[Task {self.request.id}] Building topology graph")

    try:
        graph = topology_discovery.build_topology_graph()

        logger.info(
            f"Topology graph built: {graph['node_count']} nodes, {graph['edge_count']} edges"
        )

        return graph

    except Exception as e:
        logger.error(f"Failed to build topology graph: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }
