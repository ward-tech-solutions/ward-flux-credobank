#!/bin/bash

echo "Testing if we can use easysnmp (net-snmp wrapper for Python)..."
echo ""

echo "Step 1: Install easysnmp in container..."
docker exec wardops-worker-snmp-prod pip install easysnmp

echo ""
echo "Step 2: Test SNMP walk with easysnmp..."
docker exec wardops-worker-snmp-prod python3 << 'PYEOF'
from easysnmp import Session

# Create session
session = Session(hostname='10.195.57.5', community='XoNaz-<h', version=2)

# Walk interfaces
print("Walking ifDescr (1.3.6.1.2.1.2.2.1.2)...")
items = session.walk('1.3.6.1.2.1.2.2.1.2')

print(f"Found {len(items)} interfaces:")
for item in items[:10]:
    print(f"  {item.oid} = {item.value}")

if len(items) > 10:
    print(f"  ... and {len(items) - 10} more")

print("")
print("✅ easysnmp works perfectly!")
PYEOF
