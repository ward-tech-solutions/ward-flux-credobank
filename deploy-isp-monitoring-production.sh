#!/bin/bash
# ISP Monitoring Deployment Script for Production
# Run this on production server: 10.30.25.46

set -e

echo "=========================================="
echo "ISP Monitoring Deployment"
echo "$(date)"
echo "=========================================="
echo ""

# Step 1: Stop affected services
echo "Step 1: Stopping API and worker services..."
docker-compose -f docker-compose.production-priority-queues.yml stop api celery-worker-snmp celery-beat

# Step 2: Remove containers
echo "Step 2: Removing containers..."
docker-compose -f docker-compose.production-priority-queues.yml rm -f api celery-worker-snmp celery-beat

# Step 3: Build API (includes frontend)
echo "Step 3: Building API container with new ISP monitoring features..."
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache api

# Step 4: Start services
echo "Step 4: Starting services..."
docker-compose -f docker-compose.production-priority-queues.yml up -d \
    api \
    celery-worker-monitoring \
    celery-worker-alerts \
    celery-worker-snmp \
    celery-beat \
    celery-worker-maintenance

echo ""
echo "✅ Deployment complete!"
echo ""

# Step 5: Wait for API to be ready
echo "Step 5: Waiting for API to be ready..."
sleep 5

# Check API health
echo "Checking API health..."
curl -s http://localhost:5001/health || echo "Note: Health check endpoint may not exist"

echo ""
echo "=========================================="
echo "Services Status:"
echo "=========================================="
docker-compose -f docker-compose.production-priority-queues.yml ps api celery-worker-snmp celery-beat

echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo "1. Run interface discovery:"
echo "   ./deploy-isp-monitoring.sh"
echo ""
echo "2. Check logs:"
echo "   docker logs --tail 50 wardops-api-prod"
echo "   docker logs --tail 50 wardops-worker-snmp-prod"
echo ""
echo "3. Test ISP status API:"
echo "   curl http://localhost:5001/api/v1/interfaces/isp-status/bulk?device_ips=10.195.57.5"
echo ""
echo "=========================================="
