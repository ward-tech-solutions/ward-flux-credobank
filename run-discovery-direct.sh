#!/bin/bash

echo "Running interface discovery directly via Python..."
echo ""

docker exec wardops-worker-snmp-prod python3 << 'PYEOF'
import sys
sys.path.insert(0, '/app')

from database import SessionLocal
from monitoring.models import StandaloneDevice, SNMPCredential
from monitoring.snmp.credentials import decrypt_credential
from monitoring.tasks_interface_discovery import InterfaceDiscovery
import asyncio

async def test_discovery():
    db = SessionLocal()
    
    # Get device 10.195.57.5
    device = db.query(StandaloneDevice).filter(
        StandaloneDevice.ip == '10.195.57.5'
    ).first()
    
    if not device:
        print("❌ Device 10.195.57.5 not found")
        return
    
    print(f"✅ Found device: {device.ip} (ID: {device.id})")
    
    # Get SNMP credentials
    snmp_cred = db.query(SNMPCredential).filter(
        SNMPCredential.device_id == device.id
    ).first()
    
    if not snmp_cred:
        print("❌ No SNMP credentials found")
        return
    
    print(f"✅ Found SNMP credentials (version: {snmp_cred.version})")
    
    # Decrypt community
    try:
        community = decrypt_credential(snmp_cred.community_encrypted)
        print(f"✅ Decrypted community string: {community[:5]}...")
    except Exception as e:
        print(f"❌ Failed to decrypt: {e}")
        return
    
    # Run discovery
    print(f"\nStarting interface discovery...")
    discovery = InterfaceDiscovery()
    
    result = await discovery.discover_device_interfaces(
        device_ip=device.ip,
        device_id=str(device.id),
        snmp_community=community,
        snmp_version=snmp_cred.version,
        snmp_port=161
    )
    
    print(f"\n{'='*60}")
    print(f"DISCOVERY RESULT:")
    print(f"{'='*60}")
    print(f"Success: {result.get('success')}")
    print(f"Interfaces found: {result.get('interfaces_found', 0)}")
    print(f"Interfaces saved: {result.get('interfaces_saved', 0)}")
    print(f"Critical interfaces: {result.get('critical_interfaces', 0)}")
    
    if result.get('error'):
        print(f"Error: {result['error']}")
    
    if result.get('interface_summary'):
        print(f"\nInterface Summary:")
        for itype, count in result['interface_summary'].items():
            print(f"  {itype}: {count}")
    
    db.close()

asyncio.run(test_discovery())
PYEOF

echo ""
echo "Checking database for discovered interfaces..."
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT if_index, if_name, if_alias, isp_provider, interface_type, oper_status
FROM device_interfaces
WHERE device_id = (SELECT id FROM standalone_devices WHERE ip = '10.195.57.5')
ORDER BY if_index;
"
