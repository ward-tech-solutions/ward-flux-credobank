#!/bin/bash

# WARD FLUX - Deploy Complete Topology with ALL Interfaces
# Deploys topology visualization with bandwidth display

set -e

echo "==========================================================="
echo "WARD FLUX - Topology with ALL Interfaces - FULL DEPLOYMENT"
echo "==========================================================="
echo ""
echo "This deployment includes:"
echo "  ✅ Backend API endpoints (/by-devices, /bandwidth/realtime)"
echo "  ✅ Topology visualization with ALL interfaces"
echo "  ✅ Real-time bandwidth from VictoriaMetrics"
echo "  ✅ ISP status from PostgreSQL"
echo ""
echo "Prerequisites:"
echo "  ⚠️  Celery Beat fix must be deployed FIRST"
echo "  ⚠️  VictoriaMetrics must have interface metrics"
echo ""

# Check if VictoriaMetrics has data
echo "Checking VictoriaMetrics for interface metrics..."
METRIC_COUNT=$(curl -s 'http://localhost:8428/api/v1/query?query=count(interface_if_hc_in_octets)' | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "0")

if [ "$METRIC_COUNT" == "0" ] || [ -z "$METRIC_COUNT" ]; then
  echo ""
  echo "⚠️  WARNING: VictoriaMetrics has NO interface metrics!"
  echo ""
  echo "Bandwidth display will show '↓ --' and '↑ --' until metrics are available."
  echo ""
  echo "To fix this:"
  echo "  1. Deploy Celery Beat fix: bash deploy-celery-beat-queue-fix.sh"
  echo "  2. Wait 2-3 minutes for metrics collection"
  echo "  3. Re-run this deployment"
  echo ""
  read -p "Continue anyway? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 1
  fi
else
  echo "✅ VictoriaMetrics has $METRIC_COUNT interface metric series"
  echo ""
fi

read -p "Press ENTER to deploy or CTRL+C to cancel..."

# Stop API container
echo ""
echo "1. Stopping API container..."
docker-compose -f docker-compose.production-priority-queues.yml stop api

# Remove old container
echo "2. Removing old API container..."
docker-compose -f docker-compose.production-priority-queues.yml rm -f api

# Rebuild API container (includes frontend)
echo "3. Building API container (includes frontend)..."
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache api

# Start API container
echo "4. Starting API container..."
docker-compose -f docker-compose.production-priority-queues.yml up -d api

# Wait for startup
echo "5. Waiting for API to start..."
sleep 15

# Check container status
echo "6. Checking API container status..."
docker-compose -f docker-compose.production-priority-queues.yml ps api

# Check API health
echo "7. Checking API health..."
sleep 5
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/api/v1/health || echo "000")

if [ "$HTTP_CODE" == "200" ]; then
  echo "✅ API is healthy (HTTP $HTTP_CODE)"
else
  echo "⚠️  API health check returned HTTP $HTTP_CODE"
  echo "Check logs: docker logs -f wardops-api-prod"
fi

echo ""
echo "==========================================================="
echo "Deployment Complete!"
echo "==========================================================="
echo ""
echo "Testing Checklist:"
echo ""
echo "1. Open Topology Page:"
echo "   http://10.30.25.46:5001/topology"
echo ""
echo "2. Verify:"
echo "   [ ] ONLY .5 routers are displayed (~93 devices)"
echo "   [ ] Each router has child nodes (interfaces)"
echo "   [ ] Interface status shows (🟢 UP or 🔴 DOWN)"
echo "   [ ] ISP interfaces show 'ISP: MAGTI' or 'ISP: SILKNET'"
echo "   [ ] Other interfaces show type (TRUNK, ACCESS, LAN)"
if [ "$METRIC_COUNT" != "0" ] && [ -n "$METRIC_COUNT" ]; then
  echo "   [ ] Bandwidth displays: ↓ X Mbps, ↑ Y Mbps"
  echo "   [ ] Bandwidth updates every 10 seconds"
else
  echo "   [ ] Bandwidth shows: ↓ --, ↑ -- (until Celery fix deployed)"
fi
echo "   [ ] No console errors in browser (F12)"
echo ""
echo "3. Test Navigation:"
echo "   - Click topology button on .5 router in Monitor page"
echo "   - Should navigate to topology and show that router"
echo ""
echo "4. Monitor Logs:"
echo "   docker logs -f wardops-api-prod"
echo ""

if [ "$METRIC_COUNT" == "0" ] || [ -z "$METRIC_COUNT" ]; then
  echo "⚠️  REMINDER: Deploy Celery Beat fix for bandwidth data:"
  echo "   bash deploy-celery-beat-queue-fix.sh"
  echo ""
fi

echo "Backend API Endpoints Available:"
echo "  GET /api/v1/interfaces/by-devices?device_ips=10.195.57.5"
echo "  GET /api/v1/interfaces/bandwidth/realtime?device_ips=10.195.57.5"
echo ""
