#!/bin/bash

# WARD FLUX - Deploy Topology Phase 1 (ISP Router Navigation)
# Rebuilds API container (includes frontend build)

set -e

echo "=========================================="
echo "WARD FLUX - Topology Phase 1 Deployment"
echo "=========================================="
echo ""
echo "Changes:"
echo "  ✅ Topology page shows ONLY .5 routers"
echo "  ✅ ISP status from PostgreSQL (Magti/Silknet)"
echo "  ✅ Navigation button ONLY on .5 routers in Monitor page"
echo "  ✅ Live status updates every 30 seconds"
echo ""
echo "Phase 2 (Bandwidth Display) - Pending:"
echo "  ⏳ Requires Celery Beat rebuild with queue fix"
echo "  ⏳ VictoriaMetrics bandwidth display"
echo ""

# Stop API container
echo "1. Stopping API container..."
docker-compose -f docker-compose.production-priority-queues.yml stop api

# Remove old container
echo "2. Removing old API container..."
docker-compose -f docker-compose.production-priority-queues.yml rm -f api

# Rebuild API container (includes frontend)
echo "3. Building new API container (includes frontend)..."
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache api

# Start API container
echo "4. Starting API container..."
docker-compose -f docker-compose.production-priority-queues.yml up -d api

# Wait for health check
echo "5. Waiting for API health check..."
sleep 10

# Check API status
echo "6. Checking API container status..."
docker-compose -f docker-compose.production-priority-queues.yml ps api

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Open Monitor page: http://localhost:5173/monitor"
echo "2. Find any .5 router (e.g., 10.195.57.5)"
echo "3. Click topology button (Network icon)"
echo "4. Verify topology shows ONLY .5 routers"
echo "5. Verify ISP status displays (Magti/Silknet)"
echo ""
echo "Phase 2 Deployment (After Testing):"
echo "  ./deploy-task-routing-fix.sh"
echo ""
