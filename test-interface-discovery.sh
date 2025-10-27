#!/bin/bash
# Test Interface Discovery Diagnostic Script
# Run on production server to diagnose why discovery is failing

echo "=========================================="
echo "Interface Discovery Diagnostic"
echo "=========================================="
echo ""

# Test 1: Check if task is registered
echo "Test 1: Checking if interface discovery task is registered..."
docker exec wardops-worker-snmp-prod celery -A celery_app inspect registered | grep -i interface || echo "❌ Task NOT registered!"
echo ""

# Test 2: Check SNMP connectivity
echo "Test 2: Testing SNMP connectivity to 10.195.57.5..."
docker exec wardops-worker-snmp-prod snmpwalk -v 2c -c "XoNaz-<h" 10.195.57.5 1.3.6.1.2.1.1.5.0 2>&1 | head -5
echo ""

# Test 3: Check if snmpwalk is installed
echo "Test 3: Checking if snmpwalk is available in container..."
docker exec wardops-worker-snmp-prod which snmpwalk || echo "❌ snmpwalk NOT installed!"
echo ""

# Test 4: Check Python imports
echo "Test 4: Testing Python imports..."
docker exec wardops-worker-snmp-prod python3 -c "
import sys
sys.path.insert(0, '/app')
try:
    from monitoring.tasks_interface_discovery import discover_device_interfaces_task
    print('✅ Interface discovery task imports successfully')
except Exception as e:
    print(f'❌ Import failed: {e}')
"
echo ""

# Test 5: Run manual discovery with verbose output
echo "Test 5: Running manual interface discovery with verbose output..."
docker exec wardops-worker-snmp-prod python3 << 'EOF'
import sys
import logging
sys.path.insert(0, '/app')

# Enable verbose logging
logging.basicConfig(level=logging.DEBUG)

from monitoring.tasks_interface_discovery import discover_device_interfaces_task
from database import SessionLocal
from monitoring.models import StandaloneDevice

db = SessionLocal()

# Get test device
device = db.query(StandaloneDevice).filter(
    StandaloneDevice.ip == '10.195.57.5'
).first()

if device:
    print(f"Found device: {device.name} ({device.ip})")
    print(f"SNMP community: {device.snmp_community}")
    print(f"SNMP version: {device.snmp_version}")
    print(f"Device enabled: {device.enabled}")
    print("")
    print("Triggering discovery...")

    try:
        result = discover_device_interfaces_task(str(device.id))
        print(f"\n✅ Discovery result: {result}")
    except Exception as e:
        print(f"\n❌ Discovery failed: {e}")
        import traceback
        traceback.print_exc()
else:
    print("❌ Device not found!")

db.close()
EOF
echo ""

# Test 6: Check worker logs
echo "Test 6: Recent SNMP worker logs (last 50 lines)..."
docker logs --tail 50 wardops-worker-snmp-prod
echo ""

echo "=========================================="
echo "Diagnostic Complete"
echo "=========================================="
