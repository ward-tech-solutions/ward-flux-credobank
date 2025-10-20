#!/usr/bin/env python3
"""
Create SNMP Monitoring Items for CredoBank Devices

This script creates monitoring items (OID polling configurations) for all
devices that have SNMP credentials in the database.

For each SNMP-enabled device, it creates monitoring items for:
- System information (sysDescr, sysUpTime, sysName)
- CPU usage (vendor-specific)
- Memory usage (vendor-specific)
- Network interfaces (ifOperStatus, ifInOctets, ifOutOctets)

Usage:
    python3 scripts/create_snmp_monitoring_items.py

Requirements:
    - Database connection configured via DATABASE_URL
    - Devices must have snmp_community set
"""

import sys
import os
import logging
from pathlib import Path
from uuid import uuid4
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from monitoring.models import StandaloneDevice, SNMPCredential, MonitoringItem
from monitoring.snmp.oids import UNIVERSAL_OIDS, get_vendor_oids, detect_vendor_from_oid

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_critical_oids_for_device(vendor: str = None) -> list:
    """
    Get list of critical OIDs to monitor for a device

    Args:
        vendor: Optional vendor name for vendor-specific OIDs

    Returns:
        List of (oid_key, OIDDefinition) tuples
    """
    critical_oids = []

    # Always include universal OIDs
    universal_keys = [
        "sysDescr",
        "sysObjectID",
        "sysUpTime",
        "sysName",
        "ifNumber",
    ]

    for key in universal_keys:
        if key in UNIVERSAL_OIDS:
            critical_oids.append((key, UNIVERSAL_OIDS[key]))

    # Add vendor-specific OIDs if vendor detected
    if vendor:
        vendor_oids = get_vendor_oids(vendor)

        # Add CPU metrics
        cpu_keys = ["cpmCPUTotal5sec", "fgSysCpuUsage", "jnxOperatingCPU", "hpSwitchCpuStat", "mtxrCPULoad"]
        for key in cpu_keys:
            if key in vendor_oids:
                critical_oids.append((key, vendor_oids[key]))
                break  # Only add one CPU metric

        # Add memory metrics
        mem_keys = ["ciscoMemoryPoolUsed", "fgSysMemUsage", "jnxOperatingBuffer", "hpLocalMemFreeBytes", "mtxrMemoryUsed"]
        for key in mem_keys:
            if key in vendor_oids:
                critical_oids.append((key, vendor_oids[key]))
                break  # Only add one memory metric

    return critical_oids


def create_monitoring_items_for_device(db, device: StandaloneDevice, snmp_cred: SNMPCredential):
    """
    Create monitoring items for a single device

    Args:
        db: Database session
        device: StandaloneDevice instance
        snmp_cred: SNMPCredential instance
    """
    try:
        # Check if device already has monitoring items
        existing_items = db.query(MonitoringItem).filter_by(device_id=device.id).count()

        if existing_items > 0:
            logger.info(f"  Device {device.name} already has {existing_items} monitoring items, skipping")
            return 0

        # Detect vendor (we'll need to query sysObjectID in a real scenario)
        # For now, use device_type as a hint
        vendor = None
        device_type_lower = device.device_type.lower() if device.device_type else ""

        if "cisco" in device_type_lower or "catalyst" in device_type_lower:
            vendor = "Cisco"
        elif "fortinet" in device_type_lower or "fortigate" in device_type_lower:
            vendor = "Fortinet"
        elif "juniper" in device_type_lower:
            vendor = "Juniper"
        elif "hp" in device_type_lower or "aruba" in device_type_lower:
            vendor = "HP"
        elif "mikrotik" in device_type_lower:
            vendor = "MikroTik"

        # Get OIDs to monitor
        oids_to_monitor = get_critical_oids_for_device(vendor)

        if not oids_to_monitor:
            logger.warning(f"  No OIDs configured for device {device.name}")
            return 0

        # Create monitoring items
        items_created = 0
        for oid_key, oid_def in oids_to_monitor:
            try:
                monitoring_item = MonitoringItem(
                    id=uuid4(),
                    device_id=device.id,
                    name=oid_def.name,
                    oid=oid_def.oid,
                    value_type=oid_def.value_type,
                    units=oid_def.units,
                    description=oid_def.description,
                    enabled=True,
                    poll_interval=60,  # Poll every 60 seconds
                    created_at=datetime.utcnow(),
                )
                db.add(monitoring_item)
                items_created += 1

            except Exception as item_error:
                logger.error(f"    Error creating item {oid_def.name}: {item_error}")

        db.commit()
        logger.info(f"  Created {items_created} monitoring items for {device.name}")
        return items_created

    except Exception as e:
        logger.error(f"  Error creating monitoring items for {device.name}: {e}")
        db.rollback()
        return 0


def main():
    """Main function"""
    logger.info("=" * 80)
    logger.info("SNMP Monitoring Items Creator for CredoBank")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # Get all devices with SNMP credentials
        devices_with_snmp = (
            db.query(StandaloneDevice)
            .filter(
                StandaloneDevice.snmp_community.isnot(None),
                StandaloneDevice.snmp_community != "",
                StandaloneDevice.enabled == True
            )
            .all()
        )

        logger.info(f"\nFound {len(devices_with_snmp)} devices with SNMP credentials")

        if not devices_with_snmp:
            logger.warning("No devices with SNMP credentials found!")
            return

        # Process each device
        total_items_created = 0
        devices_processed = 0

        for device in devices_with_snmp:
            logger.info(f"\nProcessing device: {device.name} ({device.ip})")
            logger.info(f"  Type: {device.device_type}")
            logger.info(f"  SNMP Version: {device.snmp_version}")

            # Get or create SNMP credential
            snmp_cred = db.query(SNMPCredential).filter_by(device_id=device.id).first()

            if not snmp_cred:
                # Create SNMPCredential from device data
                snmp_cred = SNMPCredential(
                    id=uuid4(),
                    device_id=device.id,
                    version=device.snmp_version or "v2c",
                    community_encrypted=device.snmp_community,  # Will be encrypted by the API
                    created_at=datetime.utcnow(),
                )
                db.add(snmp_cred)
                db.commit()
                db.refresh(snmp_cred)
                logger.info(f"  Created SNMP credential for {device.name}")

            # Create monitoring items
            items_created = create_monitoring_items_for_device(db, device, snmp_cred)
            total_items_created += items_created

            if items_created > 0:
                devices_processed += 1

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Devices with SNMP: {len(devices_with_snmp)}")
        logger.info(f"Devices processed: {devices_processed}")
        logger.info(f"Monitoring items created: {total_items_created}")
        logger.info("")
        logger.info("✅ SNMP monitoring items setup complete!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Start Celery workers: docker-compose up celery-worker")
        logger.info("  2. Start Celery beat: docker-compose up celery-beat")
        logger.info("  3. Monitor SNMP polling in logs")
        logger.info("  4. Check VictoriaMetrics for incoming metrics: http://localhost:8428")
        logger.info("")

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    main()
