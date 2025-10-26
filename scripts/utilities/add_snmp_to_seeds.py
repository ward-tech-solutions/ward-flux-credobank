#!/usr/bin/env python3
"""
Add SNMP v2c credentials to network devices in seed data.
Community string: XoNaz-<h
"""

import json
from pathlib import Path

# SNMP Configuration
SNMP_COMMUNITY = "XoNaz-<h"
SNMP_VERSION = "2c"

# Network device types that should have SNMP
NETWORK_DEVICE_TYPES = [
    "Switch", "Router", "Core Switch", "Access Switch",
    "Distribution Switch", "Firewall", "Load Balancer",
    "Access Point", "AP"
]

def should_have_snmp(device_type: str) -> bool:
    """Check if device type should have SNMP enabled."""
    device_type_lower = device_type.lower()
    return any(keyword.lower() in device_type_lower for keyword in NETWORK_DEVICE_TYPES)

def add_snmp_to_devices():
    """Add SNMP credentials to network devices."""
    seeds_dir = Path(__file__).parent / "seeds" / "credobank"
    devices_file = seeds_dir / "devices.json"

    print(f"📂 Loading devices from: {devices_file}")

    with open(devices_file, 'r', encoding='utf-8') as f:
        devices = json.load(f)

    total_devices = len(devices)
    snmp_added = 0

    print(f"📊 Total devices: {total_devices}")

    for device in devices:
        device_type = device.get('device_type', '')

        if should_have_snmp(device_type):
            device['snmp_community'] = SNMP_COMMUNITY
            device['snmp_version'] = SNMP_VERSION
            snmp_added += 1
            print(f"  ✅ Added SNMP to: {device.get('hostname', device.get('name', 'Unknown'))} ({device_type})")
        else:
            # Ensure non-network devices don't have SNMP fields or have them as null
            device['snmp_community'] = None
            device['snmp_version'] = None

    print(f"\n📝 Saving updated devices...")
    with open(devices_file, 'w', encoding='utf-8') as f:
        json.dump(devices, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Done!")
    print(f"   Total devices: {total_devices}")
    print(f"   SNMP enabled: {snmp_added}")
    print(f"   ICMP only: {total_devices - snmp_added}")
    print(f"\n   SNMP Community: {SNMP_COMMUNITY}")
    print(f"   SNMP Version: {SNMP_VERSION}")

if __name__ == "__main__":
    add_snmp_to_devices()
