#!/usr/bin/env python3
"""Full interface discovery test with detailed logging"""
import sys
import asyncio
sys.path.insert(0, '/app')

from database import SessionLocal
from monitoring.models import StandaloneDevice, SNMPCredential
from monitoring.tasks_interface_discovery import InterfaceDiscovery

async def main():
    db = SessionLocal()

    # Get device
    device = db.query(StandaloneDevice).filter(
        StandaloneDevice.ip == '10.195.57.5'
    ).first()

    if not device:
        print("❌ Device not found")
        return

    print(f"✅ Device: {device.ip} (ID: {device.id})")

    # Get credentials
    cred = db.query(SNMPCredential).filter(
        SNMPCredential.device_id == device.id
    ).first()

    if not cred:
        print("❌ No SNMP credentials")
        return

    print(f"✅ SNMP credentials: version={cred.version}, community={cred.community_encrypted}")

    # Run discovery
    print("\n" + "="*60)
    print("STARTING INTERFACE DISCOVERY")
    print("="*60 + "\n")

    discovery = InterfaceDiscovery()

    result = await discovery.discover_device_interfaces(
        device_ip=device.ip,
        device_id=str(device.id),
        snmp_community=cred.community_encrypted,
        snmp_version=cred.version,
        snmp_port=161
    )

    print("\n" + "="*60)
    print("DISCOVERY RESULT")
    print("="*60)
    print(f"Success: {result.get('success')}")
    print(f"Device ID: {result.get('device_id')}")
    print(f"Device IP: {result.get('device_ip')}")
    print(f"Interfaces Found: {result.get('interfaces_found', 0)}")
    print(f"Interfaces Saved: {result.get('interfaces_saved', 0)}")
    print(f"Critical Interfaces: {result.get('critical_interfaces', 0)}")

    if result.get('error'):
        print(f"\n❌ Error: {result['error']}")

    if result.get('interface_summary'):
        print("\nInterface Summary by Type:")
        for itype, count in result['interface_summary'].items():
            print(f"  {itype}: {count}")

    if result.get('interface_details'):
        print(f"\nInterface Details ({len(result['interface_details'])} total):")
        for i, iface in enumerate(result['interface_details'][:10], 1):
            print(f"\n  Interface {i}:")
            print(f"    Index: {iface.get('if_index')}")
            print(f"    Name: {iface.get('if_name')}")
            print(f"    Alias: {iface.get('if_alias')}")
            print(f"    Type: {iface.get('interface_type')}")
            print(f"    ISP: {iface.get('isp_provider')}")
            print(f"    Status: {iface.get('oper_status')}")

        if len(result['interface_details']) > 10:
            print(f"\n  ... and {len(result['interface_details']) - 10} more")

    db.close()
    print("\n" + "="*60)

try:
    asyncio.run(main())
except Exception as e:
    print(f"\n❌ EXCEPTION: {e}")
    import traceback
    traceback.print_exc()
