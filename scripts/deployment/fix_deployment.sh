#!/bin/bash
# Fix deployment issues on CredoBank production server

set -e

echo "🔧 Fixing CredoBank Production Deployment..."
echo "=============================================="

# 1. Increase PostgreSQL max_connections
echo "📊 Step 1: Increasing PostgreSQL max_connections..."
docker-compose -f docker-compose.production-local.yml exec -T postgres psql -U ward_admin -d ward_ops -c "ALTER SYSTEM SET max_connections = 200;"
docker-compose -f docker-compose.production-local.yml restart postgres
sleep 10

# 2. Rebuild containers with latest code
echo "🔨 Step 2: Rebuilding containers with latest fixes..."
docker-compose -f docker-compose.production-local.yml build api celery-worker

# 3. Restart all services
echo "♻️  Step 3: Restarting services..."
docker-compose -f docker-compose.production-local.yml restart api celery-worker celery-beat

# Wait for services to stabilize
echo "⏳ Waiting for services to start..."
sleep 15

# 4. Verify SNMP polling
echo "✅ Step 4: Checking SNMP polling status..."
docker logs --tail=50 wardops-worker-prod 2>&1 | grep -i "poll" || echo "No polling logs yet"

echo ""
echo "✅ Deployment fix complete!"
echo ""
echo "📋 Next steps:"
echo "1. Monitor logs: docker logs -f --tail=100 wardops-worker-prod"
echo "2. Check VictoriaMetrics UI: http://10.30.25.39:8428"
echo "3. Test device edit in frontend UI"
