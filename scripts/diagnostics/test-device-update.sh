#!/bin/bash

# Test device update endpoint to diagnose 400 errors

echo "=========================================="
echo "Testing Device Update Endpoint"
echo "=========================================="
echo ""

echo "1. Check recent API errors:"
echo "--------------------------------------"
docker logs --tail=100 wardops-api-prod 2>&1 | grep -i "error\|400\|validation" | tail -20

echo ""
echo "2. Check API logs for device update attempts:"
echo "--------------------------------------"
docker logs --tail=100 wardops-api-prod 2>&1 | grep -i "PUT.*devices" | tail -10

echo ""
echo "3. Test a simple device update via API:"
echo "--------------------------------------"

# Get a test device ID
DEVICE_ID=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "SELECT id FROM standalone_devices LIMIT 1;" | xargs)

if [ -z "$DEVICE_ID" ]; then
    echo "❌ No devices found in database"
    exit 1
fi

echo "Testing with device ID: $DEVICE_ID"
echo ""

# Try to update with minimal payload
curl -X PUT http://localhost:5001/api/v1/devices/standalone/$DEVICE_ID \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(docker exec wardops-redis-prod redis-cli -a redispass GET admin_token 2>/dev/null)" \
  -d '{
    "description": "Test update"
  }' \
  -w "\nHTTP Status: %{http_code}\n" \
  -s

echo ""
echo "=========================================="
echo "If you see 400 error above, check the"
echo "error message for validation details"
echo "=========================================="
