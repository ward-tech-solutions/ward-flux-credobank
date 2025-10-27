"""
WARD FLUX - Interface Discovery Tasks
SNMP-based interface discovery using IF-MIB
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from celery import shared_task

from database import SessionLocal
from monitoring.models import StandaloneDevice, DeviceInterface, InterfaceMetricsSummary, SNMPCredential
from monitoring.interface_parser import classify_interface
from monitoring.snmp.poller import SNMPPoller, SNMPCredentialData, SNMPResult
from monitoring.snmp.credentials import decrypt_credential

logger = logging.getLogger(__name__)


# IF-MIB OIDs for interface discovery
IF_MIB_OIDS = {
    'if_index': '1.3.6.1.2.1.2.2.1.1',          # ifIndex
    'if_descr': '1.3.6.1.2.1.2.2.1.2',          # ifDescr (description)
    'if_type': '1.3.6.1.2.1.2.2.1.3',           # ifType
    'if_mtu': '1.3.6.1.2.1.2.2.1.4',            # ifMtu
    'if_speed': '1.3.6.1.2.1.2.2.1.5',          # ifSpeed (bits/sec)
    'if_phys_address': '1.3.6.1.2.1.2.2.1.6',   # ifPhysAddress (MAC)
    'if_admin_status': '1.3.6.1.2.1.2.2.1.7',   # ifAdminStatus
    'if_oper_status': '1.3.6.1.2.1.2.2.1.8',    # ifOperStatus
    'if_name': '1.3.6.1.2.1.31.1.1.1.1',        # ifName (from ifXTable)
    'if_alias': '1.3.6.1.2.1.31.1.1.1.18',      # ifAlias (user description - CRITICAL!)
    'if_hc_in_octets': '1.3.6.1.2.1.31.1.1.1.6',   # ifHCInOctets (64-bit counter)
    'if_hc_out_octets': '1.3.6.1.2.1.31.1.1.1.10', # ifHCOutOctets (64-bit counter)
}

# Interface type mappings (from IF-MIB)
IF_TYPE_NAMES = {
    6: 'ethernet-csmacd',
    24: 'softwareLoopback',
    131: 'tunnel',
    53: 'propVirtual',
    161: 'ieee8023adLag',
}


class InterfaceDiscovery:
    """
    SNMP Interface Discovery Engine

    Discovers network interfaces using IF-MIB (RFC 2863)
    Classifies interfaces using InterfaceParser
    Stores results in PostgreSQL
    """

    def __init__(self):
        """Initialize interface discovery"""
        self.poller = SNMPPoller()
        self.poller.timeout = 3  # 3 second timeout per OID
        self.poller.retries = 1  # 1 retry

    async def discover_device_interfaces(
        self,
        device_ip: str,
        device_id: str,
        snmp_community: str,
        snmp_version: str = 'v2c',
        snmp_port: int = 161
    ) -> Dict:
        """
        Discover all interfaces on a device using SNMP

        Args:
            device_ip: Device IP address
            device_id: Device UUID in database
            snmp_community: SNMP community string
            snmp_version: SNMP version (v2c or v3)
            snmp_port: SNMP port (default 161)

        Returns:
            Dict with discovery results:
            {
                'device_id': UUID,
                'device_ip': str,
                'success': bool,
                'interfaces_found': int,
                'interfaces_saved': int,
                'critical_interfaces': int,
                'isp_interfaces': List[str],
                'error': Optional[str]
            }
        """
        logger.info(f"Starting interface discovery for device {device_ip} (ID: {device_id})")

        result = {
            'device_id': str(device_id),
            'device_ip': device_ip,
            'success': False,
            'interfaces_found': 0,
            'interfaces_saved': 0,
            'critical_interfaces': 0,
            'isp_interfaces': [],
            'error': None,
            'skipped_loopback': 0,
        }

        try:
            # Build SNMP credentials
            credentials = SNMPCredentialData(
                version=snmp_version,
                community=snmp_community
            )

            # Discover interfaces using SNMP bulkwalk
            interfaces_data = await self._snmp_walk_interfaces(
                device_ip, credentials, snmp_port
            )

            if not interfaces_data:
                result['error'] = 'No interfaces found via SNMP'
                logger.warning(f"No interfaces found for {device_ip}")
                return result

            result['interfaces_found'] = len(interfaces_data)
            logger.info(f"Found {len(interfaces_data)} interfaces on {device_ip}")

            # Parse and classify each interface
            classified_interfaces = []
            for interface in interfaces_data:
                # Classify interface
                classification = classify_interface(
                    if_alias=interface.get('if_alias'),
                    if_descr=interface.get('if_descr'),
                    if_name=interface.get('if_name'),
                    if_type=interface.get('if_type_name')
                )

                # Skip loopback interfaces (optional - can be configured)
                if classification.interface_type == 'loopback':
                    result['skipped_loopback'] += 1
                    continue

                # Combine SNMP data with classification
                interface['classification'] = classification
                classified_interfaces.append(interface)

                # Track critical interfaces
                if classification.is_critical:
                    result['critical_interfaces'] += 1

                # Track ISP interfaces
                if classification.interface_type == 'isp' and classification.isp_provider:
                    isp_info = f"{interface.get('if_name', 'unknown')}: {classification.isp_provider}"
                    result['isp_interfaces'].append(isp_info)

            # Save to database
            saved_count = await self._save_interfaces_to_db(
                device_id, classified_interfaces
            )

            result['interfaces_saved'] = saved_count
            result['success'] = True

            logger.info(
                f"Interface discovery completed for {device_ip}: "
                f"{result['interfaces_found']} found, {saved_count} saved, "
                f"{result['critical_interfaces']} critical, "
                f"{len(result['isp_interfaces'])} ISP interfaces"
            )

        except Exception as e:
            logger.error(f"Interface discovery failed for {device_ip}: {str(e)}", exc_info=True)
            result['error'] = str(e)

        return result

    async def _snmp_walk_interfaces(
        self,
        device_ip: str,
        credentials: SNMPCredentialData,
        port: int = 161
    ) -> List[Dict]:
        """
        Walk IF-MIB table to discover all interfaces

        Args:
            device_ip: Device IP
            credentials: SNMP credentials
            port: SNMP port

        Returns:
            List of interface dictionaries with SNMP data
        """
        interfaces = {}

        # Walk ifTable and ifXTable to get all interface data
        oids_to_walk = [
            ('if_descr', IF_MIB_OIDS['if_descr']),
            ('if_type', IF_MIB_OIDS['if_type']),
            ('if_mtu', IF_MIB_OIDS['if_mtu']),
            ('if_speed', IF_MIB_OIDS['if_speed']),
            ('if_phys_address', IF_MIB_OIDS['if_phys_address']),
            ('if_admin_status', IF_MIB_OIDS['if_admin_status']),
            ('if_oper_status', IF_MIB_OIDS['if_oper_status']),
            ('if_name', IF_MIB_OIDS['if_name']),
            ('if_alias', IF_MIB_OIDS['if_alias']),
        ]

        for field_name, base_oid in oids_to_walk:
            try:
                walk_results = await self.poller.walk(device_ip, base_oid, credentials, port)

                for oid, value, value_type in walk_results:
                    # Extract interface index from OID (e.g., 1.3.6.1.2.1.2.2.1.2.1 -> index=1)
                    if_index = int(oid.split('.')[-1])

                    # Initialize interface dict if not exists
                    if if_index not in interfaces:
                        interfaces[if_index] = {'if_index': if_index}

                    # Store value
                    if field_name == 'if_type':
                        interfaces[if_index][field_name] = value
                        interfaces[if_index]['if_type_name'] = IF_TYPE_NAMES.get(value, f'type-{value}')
                    elif field_name == 'if_phys_address' and value:
                        # Convert bytes to MAC address format
                        mac = ':'.join(f'{b:02x}' for b in value) if isinstance(value, bytes) else str(value)
                        interfaces[if_index][field_name] = mac
                    else:
                        interfaces[if_index][field_name] = value

            except Exception as e:
                logger.warning(f"Failed to walk {field_name} on {device_ip}: {str(e)}")
                continue

        # Convert dict to list
        interfaces_list = list(interfaces.values())

        return interfaces_list

    async def _save_interfaces_to_db(
        self,
        device_id: str,
        interfaces: List[Dict]
    ) -> int:
        """
        Save discovered interfaces to PostgreSQL

        Uses UPSERT (INSERT ... ON CONFLICT) to update existing interfaces

        Args:
            device_id: Device UUID
            interfaces: List of interface dicts with SNMP data and classification

        Returns:
            Number of interfaces saved
        """
        if not interfaces:
            return 0

        db = SessionLocal()
        saved_count = 0

        try:
            for interface_data in interfaces:
                classification = interface_data.get('classification')

                # Prepare interface record
                interface_record = {
                    'device_id': device_id,
                    'if_index': interface_data['if_index'],
                    'if_name': interface_data.get('if_name'),
                    'if_descr': interface_data.get('if_descr'),
                    'if_alias': interface_data.get('if_alias'),
                    'if_type': interface_data.get('if_type_name'),
                    'admin_status': interface_data.get('if_admin_status'),
                    'oper_status': interface_data.get('if_oper_status'),
                    'speed': interface_data.get('if_speed'),
                    'mtu': interface_data.get('if_mtu'),
                    'phys_address': interface_data.get('if_phys_address'),
                    'last_seen': datetime.utcnow(),
                }

                # Add classification data
                if classification:
                    interface_record.update({
                        'interface_type': classification.interface_type,
                        'isp_provider': classification.isp_provider,
                        'is_critical': classification.is_critical,
                        'parser_confidence': classification.confidence,
                    })

                # UPSERT: Insert or update if exists
                stmt = insert(DeviceInterface).values(**interface_record)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['device_id', 'if_index'],
                    set_={
                        'if_name': stmt.excluded.if_name,
                        'if_descr': stmt.excluded.if_descr,
                        'if_alias': stmt.excluded.if_alias,
                        'if_type': stmt.excluded.if_type,
                        'admin_status': stmt.excluded.admin_status,
                        'oper_status': stmt.excluded.oper_status,
                        'speed': stmt.excluded.speed,
                        'mtu': stmt.excluded.mtu,
                        'phys_address': stmt.excluded.phys_address,
                        'interface_type': stmt.excluded.interface_type,
                        'isp_provider': stmt.excluded.isp_provider,
                        'is_critical': stmt.excluded.is_critical,
                        'parser_confidence': stmt.excluded.parser_confidence,
                        'last_seen': stmt.excluded.last_seen,
                        'updated_at': datetime.utcnow(),
                    }
                )

                db.execute(stmt)
                saved_count += 1

            db.commit()
            logger.info(f"Saved {saved_count} interfaces to database for device {device_id}")

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save interfaces to database: {str(e)}", exc_info=True)
            raise
        finally:
            db.close()

        return saved_count


# ============================================
# Celery Tasks
# ============================================

@shared_task(name="monitoring.tasks.discover_device_interfaces", bind=True)
def discover_device_interfaces_task(self, device_id: str):
    """
    Celery task: Discover interfaces for a single device

    Args:
        device_id: Device UUID (as string)

    Returns:
        Discovery result dict
    """
    logger.info(f"[Task {self.request.id}] Starting interface discovery for device {device_id}")

    db = SessionLocal()
    try:
        # Fetch device from database
        stmt = select(StandaloneDevice).where(StandaloneDevice.id == device_id)
        device = db.execute(stmt).scalar_one_or_none()

        if not device:
            logger.error(f"Device {device_id} not found in database")
            return {
                'success': False,
                'error': 'Device not found',
                'device_id': device_id
            }

        if not device.enabled:
            logger.info(f"Device {device_id} is disabled, skipping interface discovery")
            return {
                'success': False,
                'error': 'Device disabled',
                'device_id': device_id
            }

        # Get SNMP credentials from snmp_credentials table
        snmp_cred = db.query(SNMPCredential).filter(SNMPCredential.device_id == device_id).first()

        if not snmp_cred:
            logger.warning(f"No SNMP credentials found for device {device_id} ({device.ip}), skipping")
            return {
                'success': False,
                'error': 'No SNMP credentials',
                'device_id': device_id
            }

        # Decrypt community string
        snmp_community = decrypt_credential(snmp_cred.community_encrypted) if snmp_cred.community_encrypted else 'public'
        snmp_version = snmp_cred.version or 'v2c'
        snmp_port = 161

        # Run discovery (async)
        discovery = InterfaceDiscovery()
        result = asyncio.run(
            discovery.discover_device_interfaces(
                device_ip=device.ip,
                device_id=str(device.id),
                snmp_community=snmp_community,
                snmp_version=snmp_version,
                snmp_port=snmp_port
            )
        )

        return result

    except Exception as e:
        logger.error(f"Interface discovery task failed for device {device_id}: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'device_id': device_id
        }
    finally:
        db.close()


@shared_task(name="monitoring.tasks.discover_all_interfaces", bind=True)
def discover_all_interfaces_task(self):
    """
    Celery task: Discover interfaces for all enabled devices

    Runs periodically (every 1 hour via Celery Beat)

    Returns:
        Summary of discovery results
    """
    logger.info(f"[Task {self.request.id}] Starting interface discovery for all devices")

    db = SessionLocal()
    summary = {
        'total_devices': 0,
        'successful': 0,
        'failed': 0,
        'total_interfaces_found': 0,
        'total_interfaces_saved': 0,
        'total_critical_interfaces': 0,
        'errors': [],
        'started_at': datetime.utcnow().isoformat(),
    }

    try:
        # Fetch all enabled devices that have SNMP credentials
        stmt = select(StandaloneDevice).where(StandaloneDevice.enabled == True)
        devices = db.execute(stmt).scalars().all()

        # Filter devices with SNMP credentials
        devices_with_snmp = []
        for device in devices:
            snmp_cred = db.query(SNMPCredential).filter(SNMPCredential.device_id == device.id).first()
            if snmp_cred:
                devices_with_snmp.append((device, snmp_cred))

        summary['total_devices'] = len(devices_with_snmp)
        logger.info(f"Found {len(devices_with_snmp)} devices with SNMP credentials to discover interfaces")

        # Discover interfaces for each device
        discovery = InterfaceDiscovery()

        for device, snmp_cred in devices_with_snmp:
            try:
                # Decrypt community string
                snmp_community = decrypt_credential(snmp_cred.community_encrypted) if snmp_cred.community_encrypted else 'public'
                snmp_version = snmp_cred.version or 'v2c'
                snmp_port = 161

                result = asyncio.run(
                    discovery.discover_device_interfaces(
                        device_ip=device.ip,
                        device_id=str(device.id),
                        snmp_community=snmp_community,
                        snmp_version=snmp_version,
                        snmp_port=snmp_port
                    )
                )

                if result['success']:
                    summary['successful'] += 1
                    summary['total_interfaces_found'] += result['interfaces_found']
                    summary['total_interfaces_saved'] += result['interfaces_saved']
                    summary['total_critical_interfaces'] += result['critical_interfaces']
                else:
                    summary['failed'] += 1
                    summary['errors'].append({
                        'device_ip': device.ip,
                        'device_id': str(device.id),
                        'error': result.get('error', 'Unknown error')
                    })

            except Exception as e:
                logger.error(f"Failed to discover interfaces for device {device.ip}: {str(e)}")
                summary['failed'] += 1
                summary['errors'].append({
                    'device_ip': device.ip,
                    'device_id': str(device.id),
                    'error': str(e)
                })

        summary['completed_at'] = datetime.utcnow().isoformat()

        logger.info(
            f"Interface discovery completed: "
            f"{summary['successful']}/{summary['total_devices']} devices successful, "
            f"{summary['total_interfaces_saved']} interfaces saved, "
            f"{summary['total_critical_interfaces']} critical interfaces"
        )

        return summary

    except Exception as e:
        logger.error(f"Interface discovery task failed: {str(e)}", exc_info=True)
        summary['errors'].append({'error': str(e)})
        return summary
    finally:
        db.close()


@shared_task(name="monitoring.tasks.cleanup_old_interfaces", bind=True)
def cleanup_old_interfaces_task(self, days_threshold: int = 7):
    """
    Celery task: Cleanup interfaces not seen in X days

    Removes stale interfaces that haven't been seen during discovery

    Args:
        days_threshold: Number of days since last_seen to consider stale (default 7)

    Returns:
        Number of interfaces deleted
    """
    logger.info(f"[Task {self.request.id}] Starting cleanup of interfaces not seen in {days_threshold} days")

    db = SessionLocal()
    try:
        from sqlalchemy import delete
        from datetime import timedelta

        threshold_date = datetime.utcnow() - timedelta(days=days_threshold)

        # Delete interfaces not seen since threshold
        stmt = delete(DeviceInterface).where(
            DeviceInterface.last_seen < threshold_date
        )

        result = db.execute(stmt)
        db.commit()

        deleted_count = result.rowcount
        logger.info(f"Deleted {deleted_count} stale interfaces (not seen since {threshold_date})")

        return {
            'deleted_count': deleted_count,
            'threshold_days': days_threshold,
            'threshold_date': threshold_date.isoformat()
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Interface cleanup task failed: {str(e)}", exc_info=True)
        return {'error': str(e)}
    finally:
        db.close()
