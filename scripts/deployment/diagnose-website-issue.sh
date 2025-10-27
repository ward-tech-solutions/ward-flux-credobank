#!/bin/bash

echo "=========================================="
echo "Website Issue Diagnostics"
echo "=========================================="
echo ""

echo "1. Check API Container Status:"
echo "--------------------------------------"
docker ps | grep wardops-api-prod

echo ""
echo "2. Check API Logs for Errors (last 50 lines):"
echo "--------------------------------------"
docker logs --tail=50 wardops-api-prod 2>&1 | grep -i "error\|exception\|traceback\|failed" || echo "No errors found in recent logs"

echo ""
echo "3. Check if API is responding:"
echo "--------------------------------------"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:5001/health || echo "API not responding"

echo ""
echo "4. Check API startup logs:"
echo "--------------------------------------"
docker logs --tail=100 wardops-api-prod 2>&1 | head -50

echo ""
echo "5. Check for Python syntax errors:"
echo "--------------------------------------"
docker exec wardops-api-prod python -m py_compile /app/routers/devices_standalone.py 2>&1 || echo "Syntax error detected!"

echo ""
echo "6. Test devices endpoint:"
echo "--------------------------------------"
curl -s http://localhost:5001/api/v1/devices 2>&1 | head -c 200 || echo "Devices endpoint failed"

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo "If you see errors above, the issue is identified."
echo "If no errors, the frontend may be the issue."
echo ""
