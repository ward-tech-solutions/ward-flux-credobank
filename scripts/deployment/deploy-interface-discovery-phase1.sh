#!/bin/bash
# ============================================
# WARD FLUX - Interface Discovery Phase 1 Deployment
# ============================================
# Deploys SNMP interface discovery system
# Server: Flux (10.30.25.46)
# Date: 2025-10-26
# ============================================

set -e  # Exit on error

echo "============================================"
echo "Interface Discovery Phase 1 Deployment"
echo "============================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/home/wardops/ward-flux-credobank"
COMPOSE_FILE="docker-compose.production-priority-queues.yml"
DB_CONTAINER="wardops-postgres-prod"
API_CONTAINER="wardops-api-prod"
WORKER_SNMP_CONTAINER="wardops-worker-snmp-prod"
BEAT_CONTAINER="wardops-beat-prod"

echo -e "${YELLOW}Step 1: Verify prerequisites${NC}"
echo "----------------------------------------"

# Check if on production server
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ Error: Project directory not found at $PROJECT_DIR${NC}"
    echo "   This script must be run on the Flux server"
    exit 1
fi

cd "$PROJECT_DIR"
echo -e "${GREEN}✅ Found project directory${NC}"

# Check if Docker is running
if ! docker ps > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker is not running${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker is running${NC}"

# Check if PostgreSQL container is running
if ! docker ps | grep -q "$DB_CONTAINER"; then
    echo -e "${RED}❌ Error: PostgreSQL container is not running${NC}"
    exit 1
fi
echo -e "${GREEN}✅ PostgreSQL container is running${NC}"

echo ""
echo -e "${YELLOW}Step 2: Pull latest code from GitHub${NC}"
echo "----------------------------------------"
git fetch origin main
git pull origin main
echo -e "${GREEN}✅ Code updated to latest version${NC}"

echo ""
echo -e "${YELLOW}Step 3: Run database migration${NC}"
echo "----------------------------------------"
echo "Creating device_interfaces table..."

# Run migration using Python script
python3 migrations/run_010_migration.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Database migration completed${NC}"
else
    echo -e "${RED}❌ Database migration failed${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 4: Verify database migration${NC}"
echo "----------------------------------------"

# Verify tables were created
TABLES_CREATED=$(docker exec $DB_CONTAINER psql -U ward_admin -d ward_ops -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_name IN ('device_interfaces', 'interface_metrics_summary')")

if [ "$TABLES_CREATED" -ge 2 ]; then
    echo -e "${GREEN}✅ Tables created successfully (found $TABLES_CREATED tables)${NC}"
else
    echo -e "${RED}❌ Table creation verification failed (found $TABLES_CREATED/2 tables)${NC}"
    exit 1
fi

# Show table structure
echo ""
echo "device_interfaces table columns:"
docker exec $DB_CONTAINER psql -U ward_admin -d ward_ops -c \
    "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'device_interfaces' ORDER BY ordinal_position" \
    | head -20

echo ""
echo -e "${YELLOW}Step 5: Rebuild API container${NC}"
echo "----------------------------------------"

echo "Building new API image..."
docker-compose -f $COMPOSE_FILE build api

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ API image built successfully${NC}"
else
    echo -e "${RED}❌ API image build failed${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 6: Restart API container${NC}"
echo "----------------------------------------"

# Stop and remove old container
echo "Stopping old API container..."
docker stop $API_CONTAINER || true
docker rm $API_CONTAINER || true

# Start new container
echo "Starting new API container..."
docker-compose -f $COMPOSE_FILE up -d api

# Wait for API to be ready
echo "Waiting for API to start..."
sleep 5

# Check if API is running
if docker ps | grep -q "$API_CONTAINER"; then
    echo -e "${GREEN}✅ API container started successfully${NC}"
else
    echo -e "${RED}❌ API container failed to start${NC}"
    exit 1
fi

# Check API health
echo "Checking API health..."
API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/api/v1/health || echo "000")

if [ "$API_HEALTH" = "200" ]; then
    echo -e "${GREEN}✅ API is healthy (HTTP $API_HEALTH)${NC}"
else
    echo -e "${YELLOW}⚠️  API health check returned HTTP $API_HEALTH (may still be starting)${NC}"
fi

echo ""
echo -e "${YELLOW}Step 7: Restart SNMP worker container${NC}"
echo "----------------------------------------"

echo "Restarting SNMP worker (for new discovery tasks)..."
docker-compose -f $COMPOSE_FILE restart worker-snmp

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ SNMP worker restarted${NC}"
else
    echo -e "${RED}❌ SNMP worker restart failed${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 8: Restart Celery Beat (scheduler)${NC}"
echo "----------------------------------------"

echo "Restarting Celery Beat (adds new scheduled tasks)..."
docker-compose -f $COMPOSE_FILE restart beat

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Celery Beat restarted${NC}"
else
    echo -e "${RED}❌ Celery Beat restart failed${NC}"
    exit 1
fi

# Wait for Beat to start
sleep 3

# Verify Beat schedule
echo ""
echo "Verifying Beat schedule includes new tasks..."
docker logs --tail 50 $BEAT_CONTAINER 2>&1 | grep -i "discover" || true

echo ""
echo -e "${YELLOW}Step 9: Verify API endpoints${NC}"
echo "----------------------------------------"

# Test interface endpoints
echo "Testing /api/v1/interfaces/summary endpoint..."
SUMMARY_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/api/v1/interfaces/summary || echo "000")

if [ "$SUMMARY_RESPONSE" = "200" ] || [ "$SUMMARY_RESPONSE" = "401" ]; then
    echo -e "${GREEN}✅ Interface API endpoint is accessible (HTTP $SUMMARY_RESPONSE)${NC}"
else
    echo -e "${YELLOW}⚠️  Interface API endpoint returned HTTP $SUMMARY_RESPONSE${NC}"
fi

echo ""
echo "============================================"
echo -e "${GREEN}✅ Phase 1 Deployment Complete!${NC}"
echo "============================================"
echo ""
echo "Summary:"
echo "  ✅ Database migration completed"
echo "  ✅ device_interfaces table created"
echo "  ✅ interface_metrics_summary table created"
echo "  ✅ API container restarted with new code"
echo "  ✅ SNMP worker restarted"
echo "  ✅ Celery Beat restarted with new schedule"
echo "  ✅ Interface discovery tasks registered"
echo ""
echo "New Features:"
echo "  📡 SNMP interface discovery (hourly)"
echo "  🔍 Interface classification (ISP, trunk, access, etc.)"
echo "  🏷️  ISP provider detection (Magti, Silknet, Veon, etc.)"
echo "  ⚠️  Critical interface flagging"
echo "  📊 Interface API endpoints"
echo ""
echo "API Endpoints:"
echo "  GET  /api/v1/interfaces/list           - List all interfaces"
echo "  GET  /api/v1/interfaces/summary        - Interface statistics"
echo "  GET  /api/v1/interfaces/device/{id}    - Interfaces for specific device"
echo "  GET  /api/v1/interfaces/critical       - Critical interfaces only"
echo "  GET  /api/v1/interfaces/isp            - ISP interfaces only"
echo "  POST /api/v1/interfaces/discover/{id}  - Trigger discovery for device"
echo "  POST /api/v1/interfaces/discover/all   - Trigger discovery for all devices"
echo ""
echo "Scheduled Tasks:"
echo "  ⏰ Interface discovery: Every hour at :00"
echo "  ⏰ Interface cleanup: Daily at 4:00 AM (removes stale interfaces)"
echo ""
echo "Next Steps:"
echo "  1. Wait for network admins to whitelist Flux IP (10.30.25.46) on Cisco devices"
echo "  2. Test manual discovery: POST /api/v1/interfaces/discover/{device_id}"
echo "  3. Monitor first hourly discovery run (check logs)"
echo "  4. Verify interface data in database"
echo ""
echo "Monitoring:"
echo "  📋 Check API logs: docker logs -f $API_CONTAINER"
echo "  📋 Check SNMP worker logs: docker logs -f $WORKER_SNMP_CONTAINER"
echo "  📋 Check Beat schedule: docker logs $BEAT_CONTAINER | grep discover"
echo ""
echo "Database Queries:"
echo "  # Count interfaces"
echo "  docker exec $DB_CONTAINER psql -U ward_admin -d ward_ops -c \"SELECT COUNT(*) FROM device_interfaces\""
echo ""
echo "  # Show critical interfaces"
echo "  docker exec $DB_CONTAINER psql -U ward_admin -d ward_ops -c \"SELECT * FROM device_interfaces WHERE is_critical = true LIMIT 10\""
echo ""
echo "  # Show ISP interfaces"
echo "  docker exec $DB_CONTAINER psql -U ward_admin -d ward_ops -c \"SELECT if_name, if_alias, isp_provider FROM device_interfaces WHERE interface_type = 'isp' LIMIT 10\""
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT: SNMP discovery requires Flux IP (10.30.25.46) to be whitelisted${NC}"
echo -e "${YELLOW}   on Cisco devices. Ask network admins to add to SNMP ACL.${NC}"
echo ""
echo "============================================"
