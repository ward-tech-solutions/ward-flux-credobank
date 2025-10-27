#!/usr/bin/env python3
"""
Trigger interface discovery for a specific device
Usage: python3 trigger_discovery.py <device_ip>
"""
import asyncio
import sys

from database import SessionLocal
from monitoring.models import StandaloneDevice, SNMPCredential
from monitoring.tasks_interface_discovery import InterfaceDiscovery


async def discover_device(device_ip: str):
    """Discover interfaces for a device by IP address"""
    db = SessionLocal()
    try:
        # Find device
        device = db.query(StandaloneDevice).filter(StandaloneDevice.ip == device_ip).first()
        if not device:
            print(f"❌ Device {device_ip} not found in database")
            return False

        print(f"✅ Found device: {device.ip} (ID: {device.id})")

        # Find SNMP credentials
        cred = db.query(SNMPCredential).filter(SNMPCredential.device_id == device.id).first()
        if not cred:
            print(f"❌ No SNMP credentials for device {device_ip}")
            return False

        print(f"✅ SNMP credentials: version={cred.version}")

        # Run discovery
        discovery = InterfaceDiscovery()
        result = await discovery.discover_device_interfaces(
            device_ip=device.ip,
            device_id=str(device.id),
            snmp_community=cred.community_encrypted or 'public',
            snmp_version=cred.version or 'v2c',
            snmp_port=161
        )

        # Print results
        print("\n" + "="*70)
        print("DISCOVERY RESULTS")
        print("="*70)
        print(f"Success: {result['success']}")
        print(f"Interfaces found: {result['interfaces_found']}")
        print(f"Interfaces saved: {result['interfaces_saved']}")
        print(f"Critical interfaces: {result['critical_interfaces']}")
        print(f"Skipped loopback: {result.get('skipped_loopback', 0)}")

        if result.get('isp_interfaces'):
            print(f"\n🎯 ISP Interfaces ({len(result['isp_interfaces'])}):")
            for isp_info in result['isp_interfaces']:
                print(f"   - {isp_info}")

        if result.get('error'):
            print(f"\n❌ Error: {result['error']}")

        print("="*70)

        return result['success']

    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 trigger_discovery.py <device_ip>")
        print("Example: python3 trigger_discovery.py 10.195.57.5")
        sys.exit(1)

    device_ip = sys.argv[1]
    print(f"Starting interface discovery for {device_ip}...")

    success = asyncio.run(discover_device(device_ip))

    if success:
        print("\n✅ Discovery completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Discovery failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
