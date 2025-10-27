#!/bin/bash

echo "Testing discovery step by step..."
docker exec wardops-worker-snmp-prod python3 << 'PYEOF'
import sys
import traceback
sys.path.insert(0, '/app')

try:
    print("Step 1: Import database...")
    from database import SessionLocal
    print("✅ Database imported")
    
    print("\nStep 2: Import models...")
    from monitoring.models import StandaloneDevice, SNMPCredential
    print("✅ Models imported")
    
    print("\nStep 3: Import credentials module...")
    from monitoring.snmp.credentials import decrypt_credential
    print("✅ Credentials module imported")
    
    print("\nStep 4: Import InterfaceDiscovery...")
    from monitoring.tasks_interface_discovery import InterfaceDiscovery
    print("✅ InterfaceDiscovery imported")
    
    print("\nStep 5: Create database session...")
    db = SessionLocal()
    print("✅ Database session created")
    
    print("\nStep 6: Query device 10.195.57.5...")
    device = db.query(StandaloneDevice).filter(
        StandaloneDevice.ip == '10.195.57.5'
    ).first()
    
    if not device:
        print("❌ Device not found")
        sys.exit(1)
    
    print(f"✅ Device found: {device.ip} (ID: {device.id})")
    
    print("\nStep 7: Query SNMP credentials...")
    snmp_cred = db.query(SNMPCredential).filter(
        SNMPCredential.device_id == device.id
    ).first()
    
    if not snmp_cred:
        print("❌ No SNMP credentials")
        sys.exit(1)
    
    print(f"✅ SNMP cred found (version: {snmp_cred.version})")
    print(f"   Community encrypted: {snmp_cred.community_encrypted[:10]}...")
    
    print("\nStep 8: Decrypt community...")
    community = decrypt_credential(snmp_cred.community_encrypted)
    print(f"✅ Decrypted: {community}")
    
    print("\nStep 9: Test SNMP with pysnmp...")
    import asyncio
    from monitoring.snmp.poller import SNMPPoller, SNMPCredentialData
    
    async def test_snmp():
        poller = SNMPPoller(timeout=10, retries=3)
        cred = SNMPCredentialData(version=snmp_cred.version, community=community)
        
        print(f"   Querying sysDescr...")
        result = await poller.get(device.ip, "1.3.6.1.2.1.1.1.0", cred)
        
        if result.success:
            print(f"   ✅ SNMP works: {result.value[:50]}...")
            return True
        else:
            print(f"   ❌ SNMP failed: {result.error}")
            return False
    
    snmp_works = asyncio.run(test_snmp())
    
    if snmp_works:
        print("\n✅ ALL CHECKS PASSED - SNMP is working!")
        print("\nNow testing interface discovery...")
        
        async def test_discovery():
            discovery = InterfaceDiscovery()
            result = await discovery.discover_device_interfaces(
                device_ip=device.ip,
                device_id=str(device.id),
                snmp_community=community,
                snmp_version=snmp_cred.version,
                snmp_port=161
            )
            return result
        
        result = asyncio.run(test_discovery())
        print(f"\nDiscovery result: {result}")
    else:
        print("\n❌ SNMP not working - cannot proceed")
    
    db.close()

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
PYEOF
