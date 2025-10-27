#!/bin/bash
# Debug SNMP Discovery

echo "=========================================="
echo "SNMP Discovery Debug"
echo "=========================================="
echo ""

echo "Step 1: Check worker logs for SNMP errors..."
echo "----------------------------------------------------------------------"
docker logs wardops-worker-snmp-prod --tail 100 | grep -i -E "(snmp|interface|error|exception|traceback)" || echo "No SNMP errors found"

echo ""
echo ""
echo "Step 2: Check if SNMP credentials exist..."
echo "----------------------------------------------------------------------"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT id, name, version, priority, is_default, community IS NOT NULL as has_community
FROM snmp_credentials
ORDER BY priority;
"

echo ""
echo "Step 3: Test SNMP discovery manually on one router..."
echo "----------------------------------------------------------------------"
docker exec wardops-worker-snmp-prod python3 << 'EOF'
import sys
import asyncio
sys.path.insert(0, '/app')

from database import SessionLocal
from monitoring.models import StandaloneDevice, SNMPCredential
from monitoring.snmp.poller import SNMPPoller, SNMPCredentialData
from monitoring.snmp.credentials import decrypt_credential

async def test_snmp():
    db = SessionLocal()

    # Get test router
    device = db.query(StandaloneDevice).filter(
        StandaloneDevice.ip == '10.195.57.5'
    ).first()

    if not device:
        print("❌ Device 10.195.57.5 not found")
        return

    print(f"✅ Device found: {device.ip} (ID: {device.id})")

    # Get SNMP credentials
    creds = db.query(SNMPCredential).order_by(SNMPCredential.priority).all()
    print(f"✅ Found {len(creds)} SNMP credential sets")

    if not creds:
        print("❌ No SNMP credentials configured!")
        return

    # Try first credential
    cred = creds[0]
    print(f"\nTesting with credential: {cred.name} (v{cred.version})")

    # Decrypt community string
    community = decrypt_credential(cred.community) if cred.community else None

    cred_data = SNMPCredentialData(
        version=cred.version,
        community=community
    )

    # Test SNMP
    poller = SNMPPoller(timeout=5, retries=2)

    print(f"\nQuerying sysDescr (1.3.6.1.2.1.1.1.0)...")
    result = await poller.get(device.ip, '1.3.6.1.2.1.1.1.0', cred_data)

    if result.success:
        print(f"✅ SNMP GET successful!")
        print(f"   Value: {result.value[:100]}...")
    else:
        print(f"❌ SNMP GET failed: {result.error}")

    # Test interface walk
    print(f"\nWalking ifDescr (1.3.6.1.2.1.2.2.1.2)...")
    results = await poller.walk(device.ip, '1.3.6.1.2.1.2.2.1.2', cred_data, max_results=10)

    print(f"Found {len(results)} interfaces:")
    for r in results[:5]:
        if r.success:
            print(f"   {r.oid} = {r.value}")

    db.close()

asyncio.run(test_snmp())
EOF

echo ""
echo "=========================================="
echo "Debug Complete"
echo "=========================================="
