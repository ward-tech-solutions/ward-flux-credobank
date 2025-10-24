#!/bin/bash

# Check if timezone fix is deployed on Credobank server
# This script verifies that the API returns timestamps with 'Z' suffix

echo "Checking if timezone fix is deployed..."
echo ""

# Get API response and check for 'Z' in down_since timestamp
curl -s http://localhost:5001/api/v1/devices/standalone/list | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)

# Find device 10.195.5.17
device = None
for d in data:
    if d.get('ip') == '10.195.5.17':
        device = d
        break

if not device:
    print('❌ Device 10.195.5.17 not found in API response')
    sys.exit(1)

print('Device:', device.get('name'))
print('IP:', device.get('ip'))
print('Status:', device.get('ping_status'))
print('down_since:', device.get('down_since'))
print('')

down_since = device.get('down_since')
if down_since:
    if down_since.endswith('Z'):
        print('✅ TIMEZONE FIX DEPLOYED - timestamp has Z suffix')
    else:
        print('❌ TIMEZONE FIX NOT DEPLOYED - timestamp missing Z suffix')
        print('')
        print('Need to deploy:')
        print('  cd /home/wardops/ward-flux-credobank')
        print('  git pull origin main')
        print('  docker-compose -f docker-compose.production-priority-queues.yml build api')
        print('  docker-compose -f docker-compose.production-priority-queues.yml stop api')
        print('  docker-compose -f docker-compose.production-priority-queues.yml up -d api')
else:
    print('✅ Device is UP (down_since is null)')
"

echo ""
echo "Current server time:"
echo "  Tbilisi: $(date)"
echo "  UTC: $(date -u)"
