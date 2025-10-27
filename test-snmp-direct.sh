#!/bin/bash

echo "Testing SNMP connectivity to 10.195.57.5..."
echo ""

# Test from host
echo "1. Test from HOST (should work if network is accessible):"
snmpwalk -v2c -c 'credo@bank' 10.195.57.5 1.3.6.1.2.1.1.1.0 -t 2 -r 1 2>&1 | head -5

echo ""
echo "2. Check if container can reach the router:"
docker exec wardops-worker-snmp-prod ping -c 2 10.195.57.5

echo ""
echo "3. Now testing SNMP from Python with correct community string..."
docker exec wardops-worker-snmp-prod python3 << 'PYEOF'
import sys
import asyncio
sys.path.insert(0, '/app')

from monitoring.snmp.poller import SNMPPoller, SNMPCredentialData

async def test():
    poller = SNMPPoller(timeout=10, retries=3)
    
    # Test with correct community string
    cred = SNMPCredentialData(
        version="2c",  # Will be normalized to v2c
        community="credo@bank"
    )
    
    print("Testing SNMP GET on 10.195.57.5...")
    result = await poller.get("10.195.57.5", "1.3.6.1.2.1.1.1.0", cred)
    
    if result.success:
        print(f"✅ SUCCESS: {result.value[:100]}")
    else:
        print(f"❌ FAILED: {result.error}")
    
    # Test interface walk
    print("\nTesting interface walk...")
    results = await poller.walk("10.195.57.5", "1.3.6.1.2.1.2.2.1.2", cred, max_results=5)
    print(f"Found {len(results)} interfaces")
    for r in results:
        if r.success:
            print(f"  - {r.value}")

asyncio.run(test())
PYEOF
