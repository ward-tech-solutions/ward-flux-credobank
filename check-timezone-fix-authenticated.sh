#!/bin/bash

# Check if timezone fix is deployed (with authentication)
# This script logs in first, then checks the API response

echo "Checking if timezone fix is deployed..."
echo ""

# Get admin credentials from docker-compose or use defaults
ADMIN_USER="admin"
ADMIN_PASS="admin"  # Change if different

# Login and get token
echo "Logging in to API..."
TOKEN=$(curl -s -X POST "http://localhost:5001/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$ADMIN_USER&password=$ADMIN_PASS" | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to authenticate"
    echo "Please check admin credentials"
    exit 1
fi

echo "✅ Authenticated"
echo ""

# Get device list with authentication
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:5001/api/v1/devices/standalone/list" | \
  python3 -c "
import json, sys

try:
    data = json.load(sys.stdin)

    # Debug: Check data type
    if not isinstance(data, list):
        print(f'❌ Unexpected API response type: {type(data)}')
        if isinstance(data, dict) and 'detail' in data:
            print(f'Error: {data[\"detail\"]}')
        sys.exit(1)

    # Find device 10.195.5.17
    device = None
    for d in data:
        if not isinstance(d, dict):
            continue
        if d.get('ip') == '10.195.5.17':
            device = d
            break

    if not device:
        print('❌ Device 10.195.5.17 not found in API response')
        print(f'Total devices in response: {len(data)}')

        # Show first device as example
        if len(data) > 0:
            print('')
            print('Example device from response:')
            print(f'  IP: {data[0].get(\"ip\")}')
            print(f'  Name: {data[0].get(\"name\")}')
            print(f'  down_since: {data[0].get(\"down_since\")}')
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
            print('')
            print('Downtime calculation should now be accurate!')
        else:
            print('❌ TIMEZONE FIX NOT DEPLOYED - timestamp missing Z suffix')
            print('')
            print('The API container may not have the latest code.')
            print('Check API logs: docker logs wardops-api-prod --tail 50')
    else:
        print('✅ Device is UP (down_since is null)')
        print('')
        print('Find a DOWN device to verify timezone fix.')

except json.JSONDecodeError as e:
    print(f'❌ Failed to parse JSON: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

echo ""
echo "Current server time:"
echo "  Tbilisi: $(date)"
echo "  UTC: $(date -u)"
echo ""

# Also check database for comparison
echo "Database timestamp for comparison:"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c \
  "SELECT name, down_since FROM standalone_devices WHERE ip = '10.195.5.17';" 2>/dev/null || echo "  (Database query failed)"
