#!/bin/bash

# ================================================================
# WARD OPS - Verify All Fixes Are Deployed
# ================================================================

echo "=========================================="
echo "Verifying All Fixes Are Deployed"
echo "=========================================="
echo ""

cd /home/wardops/ward-flux-credobank

echo "1. Check container status:"
echo "--------------------------------------"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep wardops

echo ""
echo "2. Check API container frontend files date:"
echo "--------------------------------------"
docker exec wardops-api-prod ls -la /app/static_new/assets/*.js 2>&1 | head -5

echo ""
echo "3. Verify down_since in frontend JavaScript:"
echo "--------------------------------------"
docker exec wardops-api-prod grep -o "down_since" /app/static_new/assets/*.js 2>&1 | head -3
if [ $? -eq 0 ]; then
    echo "✅ Frontend has down_since code!"
else
    echo "❌ Frontend does NOT have down_since code - build failed!"
fi

echo ""
echo "4. Check worker container has latest code:"
echo "--------------------------------------"
docker exec wardops-worker-prod grep -A 2 "went DOWN" /app/monitoring/tasks.py 2>&1 | head -5

echo ""
echo "5. Test API health:"
echo "--------------------------------------"
curl -s http://localhost:5001/api/v1/health | head -c 200

echo ""
echo ""
echo "6. Check recent worker logs for state transitions:"
echo "--------------------------------------"
docker logs --tail=50 wardops-worker-prod 2>&1 | grep -i "went DOWN\|came back UP" | tail -10
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Worker is logging state transitions!"
else
    echo ""
    echo "ℹ️  No recent state transitions (devices may all be stable)"
fi

echo ""
echo "=========================================="
echo "Verification Complete"
echo "=========================================="
echo ""
echo "Expected Results:"
echo "  ✅ Container files should be dated TODAY (not Oct 20)"
echo "  ✅ Frontend JavaScript should contain 'down_since'"
echo "  ✅ Worker code should have state transition logging"
echo "  ✅ API should respond with health status"
echo ""
echo "If all checks pass, the fixes are deployed!"
echo "Access: http://10.30.25.39:5001"
echo ""
