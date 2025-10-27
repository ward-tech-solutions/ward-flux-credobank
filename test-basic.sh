#!/bin/bash

echo "Test 1: Can we run Python?"
docker exec wardops-worker-snmp-prod python3 -c "print('Python works')"

echo ""
echo "Test 2: Can we import sys?"
docker exec wardops-worker-snmp-prod python3 -c "import sys; print('sys works')"

echo ""
echo "Test 3: Can we add to path?"
docker exec wardops-worker-snmp-prod python3 -c "import sys; sys.path.insert(0, '/app'); print('path works')"

echo ""
echo "Test 4: Can we import database?"
docker exec wardops-worker-snmp-prod python3 -c "import sys; sys.path.insert(0, '/app'); from database import SessionLocal; print('database import works')"

echo ""
echo "Test 5: Can we query device?"
docker exec wardops-worker-snmp-prod python3 -c "
import sys
sys.path.insert(0, '/app')
from database import SessionLocal
from monitoring.models import StandaloneDevice
db = SessionLocal()
device = db.query(StandaloneDevice).filter(StandaloneDevice.ip == '10.195.57.5').first()
if device:
    print(f'Device found: {device.ip}')
else:
    print('Device NOT found')
db.close()
"

echo ""
echo "Test 6: Check SNMP credentials exist?"
docker exec wardops-worker-snmp-prod python3 -c "
import sys
sys.path.insert(0, '/app')
from database import SessionLocal
from monitoring.models import StandaloneDevice, SNMPCredential
db = SessionLocal()
device = db.query(StandaloneDevice).filter(StandaloneDevice.ip == '10.195.57.5').first()
if device:
    cred = db.query(SNMPCredential).filter(SNMPCredential.device_id == device.id).first()
    if cred:
        print(f'SNMP cred found: version={cred.version}')
    else:
        print('NO SNMP credentials for this device')
else:
    print('Device not found')
db.close()
"

echo ""
echo "Test 7: Can we decrypt?"
docker exec wardops-worker-snmp-prod python3 -c "
import sys
sys.path.insert(0, '/app')
from database import SessionLocal
from monitoring.models import StandaloneDevice, SNMPCredential
from monitoring.snmp.credentials import decrypt_credential
db = SessionLocal()
device = db.query(StandaloneDevice).filter(StandaloneDevice.ip == '10.195.57.5').first()
if device:
    cred = db.query(SNMPCredential).filter(SNMPCredential.device_id == device.id).first()
    if cred:
        try:
            community = decrypt_credential(cred.community_encrypted)
            print(f'Decrypted community: {community}')
        except Exception as e:
            print(f'Decryption failed: {e}')
    else:
        print('No cred')
db.close()
"
