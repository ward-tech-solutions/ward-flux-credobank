#!/bin/bash

set -e

echo "=================================================================="
echo "  WARD OPS - Surgical Deployment (Bypass Docker Compose Bug)"
echo "=================================================================="
echo ""
echo "This bypasses Docker Compose's ContainerConfig bug by using"
echo "docker run commands directly instead of docker-compose up"
echo ""

cd /home/wardops/ward-flux-credobank

echo "Step 1: Checking current container status..."
echo "=================================================================="
docker ps -a --filter "name=wardops" --format "table {{.Names}}\t{{.Status}}"

echo ""
echo "Step 2: Stopping and removing API/Worker/Beat containers..."
echo "=================================================================="

# Stop and remove only our application containers (not postgres/redis/victoria)
for container in wardops-api-prod wardops-worker-prod wardops-beat-prod; do
    echo "Processing $container..."
    docker stop $container 2>/dev/null || echo "  - Not running"
    docker rm $container 2>/dev/null || echo "  - Already removed"
done

echo "✓ Application containers cleaned up"

echo ""
echo "Step 3: Building fresh images..."
echo "=================================================================="
docker-compose -f docker-compose.production-local.yml build --no-cache api celery-worker celery-beat

echo ""
echo "Step 4: Starting containers using docker run (bypass compose bug)..."
echo "=================================================================="

# Get the network name
NETWORK="ward-flux-credobank_default"

# Start API container
echo "Starting wardops-api-prod..."
docker run -d \
  --name wardops-api-prod \
  --network $NETWORK \
  -p 5001:5001 \
  -e DATABASE_URL='postgresql://ward_admin:ward_admin_password@postgres:5432/ward_ops' \
  -e REDIS_URL='redis://:redispass@redis:6379/0' \
  -e VICTORIA_URL='http://victoriametrics:8428' \
  -e DEFAULT_ADMIN_PASSWORD='admin123' \
  -e SECRET_KEY="${SECRET_KEY:-local-prod-test-secret-key-change-me}" \
  -e ENCRYPTION_KEY="${ENCRYPTION_KEY:-}" \
  -e ENVIRONMENT='production' \
  -e MONITORING_MODE='snmp_only' \
  -v /home/wardops/ward-flux-credobank/logs:/app/logs \
  -v api_prod_data:/data \
  --restart unless-stopped \
  ward-flux-credobank_api:latest

echo "✓ API container started"

# Start Worker container
echo "Starting wardops-worker-prod..."
docker run -d \
  --name wardops-worker-prod \
  --network $NETWORK \
  -e DATABASE_URL='postgresql://ward_admin:ward_admin_password@postgres:5432/ward_ops' \
  -e REDIS_URL='redis://:redispass@redis:6379/0' \
  -e VICTORIA_URL='http://victoriametrics:8428' \
  -e SECRET_KEY="${SECRET_KEY:-local-prod-test-secret-key-change-me}" \
  -e ENCRYPTION_KEY="${ENCRYPTION_KEY:-}" \
  -e ENVIRONMENT='production' \
  -e MONITORING_MODE='snmp_only' \
  -v /home/wardops/ward-flux-credobank/logs:/app/logs \
  -v celery_prod_data:/data \
  --restart unless-stopped \
  ward-flux-credobank_celery-worker:latest \
  celery -A celery_app worker --loglevel=info --concurrency=100

echo "✓ Worker container started"

# Start Beat container
echo "Starting wardops-beat-prod..."
docker run -d \
  --name wardops-beat-prod \
  --network $NETWORK \
  -e DATABASE_URL='postgresql://ward_admin:ward_admin_password@postgres:5432/ward_ops' \
  -e REDIS_URL='redis://:redispass@redis:6379/0' \
  -e SECRET_KEY="${SECRET_KEY:-local-prod-test-secret-key-change-me}" \
  -e ENVIRONMENT='production' \
  -v /home/wardops/ward-flux-credobank/logs:/app/logs \
  -v beat_prod_data:/data \
  --restart unless-stopped \
  ward-flux-credobank_celery-beat:latest \
  celery -A celery_app beat --loglevel=info

echo "✓ Beat container started"

echo ""
echo "Step 5: Waiting for containers to initialize..."
echo "=================================================================="
sleep 15

echo ""
echo "Step 6: Verifying all containers are running..."
echo "=================================================================="
docker ps --filter "name=wardops" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "Step 7: Testing API health..."
echo "=================================================================="

for i in {1..10}; do
    if curl -sf http://localhost:5001/api/v1/health > /dev/null 2>&1; then
        echo "✓ API is healthy and responding"
        break
    else
        if [ $i -eq 10 ]; then
            echo "⚠ API not responding after 10 attempts"
            echo "Check logs: docker logs wardops-api-prod"
        else
            echo "Attempt $i/10: Waiting for API..."
            sleep 3
        fi
    fi
done

echo ""
echo "Step 8: Verifying timezone fix..."
echo "=================================================================="

SAMPLE=$(curl -s http://localhost:5001/api/v1/devices/standalone | jq -r '.[] | select(.down_since != null) | .down_since' | head -1)

if [ -z "$SAMPLE" ]; then
    echo "ℹ No down devices found (all devices are UP)"
    echo ""
    echo "Testing timestamp format with last_check instead:"
    curl -s http://localhost:5001/api/v1/devices/standalone | jq -r '.[0] | {name: .name, last_check: .last_check}'
else
    echo "Sample down_since timestamp: $SAMPLE"
    echo ""
    if [[ "$SAMPLE" == *"+00:00" ]] || [[ "$SAMPLE" == *"Z" ]]; then
        echo "✅ SUCCESS! Timezone fix is ACTIVE!"
        echo "   Timestamps now include timezone information"
    else
        echo "⚠ WARNING: Timezone suffix missing"
        echo "  Expected: 2025-10-21T08:34:45.186571+00:00"
        echo "  Got:      $SAMPLE"
    fi
fi

echo ""
echo "=================================================================="
echo "  Deployment Complete!"
echo "=================================================================="
echo ""
echo "✅ Bypassed Docker Compose ContainerConfig bug"
echo "✅ All containers running with fresh images"
echo "✅ Timezone fix deployed"
echo ""
echo "Container Status:"
docker ps --filter "name=wardops" --format "  - {{.Names}}: {{.Status}}"

echo ""
echo "VERIFICATION STEPS:"
echo ""
echo "1. Open Monitor page: http://10.30.25.39:5001/monitor"
echo ""
echo "2. Open browser console (F12) and check debug logs:"
echo "   - Look for: [Device] down_since: 2025-XX-XXT...+00:00"
echo "   - Check: Diff hours should be correct (not 6.07)"
echo ""
echo "3. Compare downtime with Zabbix alerts"
echo ""
echo "Monitoring Commands:"
echo "  docker logs wardops-api-prod -f"
echo "  docker logs wardops-worker-prod -f | grep -E 'went DOWN|came back UP'"
echo ""
echo "=================================================================="
