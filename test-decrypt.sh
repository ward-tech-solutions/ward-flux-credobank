#!/bin/bash

echo "Testing decryption with current key..."
docker exec wardops-worker-snmp-prod python3 << 'PYEOF'
import sys
sys.path.insert(0, '/app')

from database import SessionLocal
from monitoring.models import StandaloneDevice, SNMPCredential
import os

db = SessionLocal()

# Get device
device = db.query(StandaloneDevice).filter(
    StandaloneDevice.ip == '10.195.57.5'
).first()

if not device:
    print("Device not found")
    sys.exit(1)

# Get credential
cred = db.query(SNMPCredential).filter(
    SNMPCredential.device_id == device.id
).first()

if not cred:
    print("No SNMP credential found")
    sys.exit(1)

print(f"Encrypted value in DB: {cred.community_encrypted}")
print(f"Length: {len(cred.community_encrypted)} bytes")
print(f"Current WARD_ENCRYPTION_KEY: {os.getenv('WARD_ENCRYPTION_KEY', 'NOT SET')[:20]}...")
print("")

# Try to decrypt with current key
try:
    from monitoring.snmp.credentials import decrypt_credential
    decrypted = decrypt_credential(cred.community_encrypted)
    print(f"✅ Decryption SUCCESS: {decrypted}")
except Exception as e:
    print(f"❌ Decryption FAILED: {e}")
    print("")
    print("The encrypted value might be:")
    print("1. Not encrypted (stored as plaintext)")
    print("2. Encrypted with a different key")
    print("3. Corrupted")
    print("")
    print("Testing if it's plaintext...")
    # Test if we can use it directly
    from monitoring.snmp.poller import SNMPPoller, SNMPCredentialData
    import asyncio
    
    async def test_plaintext():
        poller = SNMPPoller(timeout=5, retries=2)
        cred_data = SNMPCredentialData(
            version='2c',
            community=cred.community_encrypted  # Use as-is
        )
        result = await poller.get(device.ip, '1.3.6.1.2.1.1.1.0', cred_data)
        return result.success
    
    if asyncio.run(test_plaintext()):
        print("✅ The value IS plaintext - SNMP works with it directly!")
        print(f"Community string: {cred.community_encrypted}")
    else:
        print("❌ Not plaintext either - SNMP doesn't work")

db.close()
PYEOF
