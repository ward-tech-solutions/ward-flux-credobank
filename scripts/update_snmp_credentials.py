#!/usr/bin/env python3
"""
Update SNMP credentials in standalone_devices table from seed file

This script reads the devices.json seed file and updates the snmp_community
and snmp_version fields for all devices that have SNMP configured.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from monitoring.models import StandaloneDevice

def main():
    print("=" * 80)
    print("SNMP Credentials Updater for CredoBank")
    print("=" * 80)

    # Load seed file
    seed_file = Path(__file__).parent.parent / "seeds" / "credobank" / "devices.json"

    if not seed_file.exists():
        print(f"ERROR: Seed file not found: {seed_file}")
        return 1

    print(f"\nLoading devices from: {seed_file}")

    with open(seed_file, 'r', encoding='utf-8') as f:
        devices_data = json.load(f)

    print(f"Loaded {len(devices_data)} devices from seed file")

    # Connect to database
    db = SessionLocal()

    try:
        updated_count = 0
        snmp_count = 0

        for device_data in devices_data:
            # Get SNMP fields from seed data
            snmp_community = device_data.get('snmp_community')
            snmp_version = device_data.get('snmp_version')
            device_ip = device_data.get('ip')
            device_name = device_data.get('name')

            if not device_ip:
                continue

            # Find device in database by IP
            device = db.query(StandaloneDevice).filter_by(ip=device_ip).first()

            if not device:
                print(f"  Device not found in DB: {device_name} ({device_ip})")
                continue

            # Update SNMP fields if present in seed data
            if snmp_community and snmp_community.strip():
                device.snmp_community = snmp_community
                device.snmp_version = snmp_version or 'v2c'
                updated_count += 1
                snmp_count += 1
                print(f"  Updated SNMP for: {device_name} ({device_ip}) - {snmp_version}")
            else:
                # Explicitly set to None for non-SNMP devices
                device.snmp_community = None
                device.snmp_version = None
                updated_count += 1

        # Commit changes
        db.commit()

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total devices in seed file: {len(devices_data)}")
        print(f"Devices updated: {updated_count}")
        print(f"Devices with SNMP: {snmp_count}")
        print(f"Devices without SNMP: {updated_count - snmp_count}")
        print("\n✅ SNMP credentials updated successfully!")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        db.rollback()
        raise

    finally:
        db.close()

    return 0

if __name__ == "__main__":
    sys.exit(main())
