#!/bin/bash
# Verify all fixes are working

echo "🔍 Verifying CredoBank Deployment"
echo "===================================="
echo ""

# 1. Check container status
echo "📦 Container Status:"
docker-compose -f docker-compose.production-local.yml ps | grep -E "api-prod|worker-prod|beat-prod"
echo ""

# 2. Check API health
echo "🏥 API Health Check:"
curl -s http://localhost:5001/api/v1/health | jq . || echo "API not responding yet"
echo ""

# 3. Check if SNMP polling is working
echo "📊 SNMP Polling Status (last 10 lines):"
docker logs --tail=10 wardops-worker-prod 2>&1 | grep -E "Polling device|SNMP|poll_device_snmp" || echo "No SNMP polling logs yet"
echo ""

# 4. Check PostgreSQL connections
echo "🗄️  PostgreSQL Connection Status:"
docker-compose -f docker-compose.production-local.yml exec -T postgres psql -U ward_admin -d ward_ops -c "SELECT count(*) as active_connections FROM pg_stat_activity WHERE state = 'active';"
echo ""

# 5. Check max_connections
echo "📊 PostgreSQL max_connections:"
docker-compose -f docker-compose.production-local.yml exec -T postgres psql -U ward_admin -d ward_ops -c 'SHOW max_connections;'
echo ""

# 6. Test device update endpoint
echo "🧪 Testing Device Update Endpoint:"
echo "   Making test API call to verify backend accepts region/branch fields..."
DEVICE_ID=$(docker-compose -f docker-compose.production-local.yml exec -T postgres psql -U ward_admin -d ward_ops -t -c "SELECT id FROM standalone_devices LIMIT 1;" | xargs)
if [ -n "$DEVICE_ID" ]; then
    echo "   Test device ID: $DEVICE_ID"
    curl -s -X PUT http://localhost:5001/api/v1/devices/standalone/$DEVICE_ID \
        -H "Content-Type: application/json" \
        -d '{"region":"Tbilisi"}' 2>&1 | head -3 || echo "   Note: Auth required for actual update (expected)"
else
    echo "   Could not get test device ID"
fi
echo ""

echo "✅ Verification complete!"
echo ""
echo "🌐 Access points:"
echo "   - Frontend: http://10.30.25.39:5001/devices"
echo "   - VictoriaMetrics: http://10.30.25.39:8428"
echo ""
echo "🔄 Remember to hard refresh browser (Ctrl+Shift+R) to see UI changes!"
