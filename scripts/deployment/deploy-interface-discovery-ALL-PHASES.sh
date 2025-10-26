#!/bin/bash
# ============================================
# WARD FLUX - Interface Discovery ALL PHASES Deployment
# ============================================
# Deploys complete interface discovery and monitoring system
# Phases: 1 (Discovery) + 2 (Metrics) + 3 (Topology/Analytics - optional)
# Server: Flux (10.30.25.46)
# Date: 2025-10-26
# ============================================

set -e  # Exit on error

echo "============================================"
echo "Interface Discovery - ALL PHASES Deployment"
echo "============================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/home/wardops/ward-flux-credobank"
COMPOSE_FILE="docker-compose.production-priority-queues.yml"
DB_CONTAINER="wardops-postgres-prod"
API_CONTAINER="wardops-api-prod"
WORKER_SNMP_CONTAINER="wardops-worker-snmp-prod"
BEAT_CONTAINER="wardops-beat-prod"
VM_CONTAINER="wardops-victoriametrics-prod"

# Deployment options
DEPLOY_PHASE1=${DEPLOY_PHASE1:-true}
DEPLOY_PHASE2=${DEPLOY_PHASE2:-true}
DEPLOY_PHASE3=${DEPLOY_PHASE3:-true}  # Topology & baselines (fully implemented)

echo "Deployment Configuration:"
echo "  Phase 1 (Discovery):     $DEPLOY_PHASE1"
echo "  Phase 2 (Metrics):       $DEPLOY_PHASE2"
echo "  Phase 3 (Topology):      $DEPLOY_PHASE3"
echo ""

echo -e "${YELLOW}Step 1: Prerequisites Check${NC}"
echo "=========================================="

# Check if on production server
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ Error: Project directory not found at $PROJECT_DIR${NC}"
    echo "   This script must be run on the Flux server"
    exit 1
fi

cd "$PROJECT_DIR"
echo -e "${GREEN}✅ Found project directory${NC}"

# Check Docker
if ! docker ps > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker is not running${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker is running${NC}"

# Check containers
for container in $DB_CONTAINER $VM_CONTAINER; do
    if ! docker ps | grep -q "$container"; then
        echo -e "${RED}❌ Error: Container $container is not running${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Container $container is running${NC}"
done

echo ""
echo -e "${YELLOW}Step 2: Pull Latest Code${NC}"
echo "=========================================="
git fetch origin main
git pull origin main
echo -e "${GREEN}✅ Code updated to latest version${NC}"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}PHASE 1: Interface Discovery${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ "$DEPLOY_PHASE1" = "true" ]; then
    echo ""
    echo -e "${YELLOW}Step 3: Run Phase 1 Database Migration${NC}"
    echo "=========================================="
    echo "Creating device_interfaces table..."

    # Run migration SQL directly via psql in container
    docker exec $DB_CONTAINER psql -U ward_admin -d ward_ops -f /tmp/010_migration.sql 2>&1 | tee /tmp/migration_010.log

    # Copy migration file to container first if needed
    if [ ! -f /tmp/010_migration.sql ]; then
        docker cp migrations/010_add_device_interfaces.sql $DB_CONTAINER:/tmp/010_migration.sql
        docker exec $DB_CONTAINER psql -U ward_admin -d ward_ops -f /tmp/010_migration.sql 2>&1 | tee /tmp/migration_010.log
    fi

    if grep -q "ERROR" /tmp/migration_010.log; then
        # Check if error is "already exists" which is OK
        if grep -q "already exists" /tmp/migration_010.log; then
            echo -e "${YELLOW}⚠️  Tables already exist (skipping)${NC}"
        else
            echo -e "${RED}❌ Phase 1 migration failed${NC}"
            cat /tmp/migration_010.log
            exit 1
        fi
    else
        echo -e "${GREEN}✅ Phase 1 migration completed${NC}"
    fi

    # Verify tables
    TABLES=$(docker exec $DB_CONTAINER psql -U ward_admin -d ward_ops -t -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name IN ('device_interfaces', 'interface_metrics_summary')")

    if [ "$TABLES" -ge 2 ]; then
        echo -e "${GREEN}✅ Phase 1 tables verified ($TABLES tables)${NC}"
    else
        echo -e "${RED}❌ Table verification failed${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⏭  Phase 1 skipped (already deployed)${NC}"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}PHASE 2: VictoriaMetrics Integration${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ "$DEPLOY_PHASE2" = "true" ]; then
    echo ""
    echo -e "${YELLOW}Step 4: Verify VictoriaMetrics${NC}"
    echo "=========================================="

    # Check VictoriaMetrics API
    VM_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8428/health || echo "000")

    if [ "$VM_HEALTH" = "200" ]; then
        echo -e "${GREEN}✅ VictoriaMetrics is healthy${NC}"
    else
        echo -e "${RED}❌ VictoriaMetrics health check failed (HTTP $VM_HEALTH)${NC}"
        exit 1
    fi

    # Check if VM has storage
    VM_SIZE=$(docker exec $VM_CONTAINER du -sh /victoria-metrics-data 2>/dev/null || echo "N/A")
    echo -e "${GREEN}✅ VictoriaMetrics storage: $VM_SIZE${NC}"
else
    echo -e "${YELLOW}⏭  Phase 2 skipped${NC}"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}PHASE 3: Topology & Baselines${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ "$DEPLOY_PHASE3" = "true" ]; then
    echo ""
    echo -e "${YELLOW}Step 4: Run Phase 3 Database Migration${NC}"
    echo "=========================================="
    echo "Creating interface_baselines table..."

    # Copy migration file to container
    docker cp migrations/011_add_phase3_tables.sql $DB_CONTAINER:/tmp/011_migration.sql

    # Run migration
    docker exec $DB_CONTAINER psql -U ward_admin -d ward_ops -f /tmp/011_migration.sql 2>&1 | tee /tmp/migration_011.log

    if grep -q "ERROR" /tmp/migration_011.log; then
        # Check if error is "already exists" which is OK
        if grep -q "already exists" /tmp/migration_011.log; then
            echo -e "${YELLOW}⚠️  Tables already exist (skipping)${NC}"
        else
            echo -e "${RED}❌ Phase 3 migration failed${NC}"
            cat /tmp/migration_011.log
            exit 1
        fi
    else
        echo -e "${GREEN}✅ Phase 3 migration completed${NC}"
    fi

    # Verify table
    TABLE_EXISTS=$(docker exec $DB_CONTAINER psql -U ward_admin -d ward_ops -t -c \
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'interface_baselines')")

    if echo "$TABLE_EXISTS" | grep -q "t"; then
        echo -e "${GREEN}✅ interface_baselines table verified${NC}"
    else
        echo -e "${RED}❌ interface_baselines table not found${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⏭  Phase 3 skipped${NC}"
fi

echo ""
echo -e "${YELLOW}Step 5: Rebuild API Container${NC}"
echo "=========================================="

echo "Building new API image (includes all phases)..."
docker-compose -f $COMPOSE_FILE build api

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ API image built successfully${NC}"
else
    echo -e "${RED}❌ API image build failed${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 6: Restart Containers${NC}"
echo "=========================================="

# Stop and restart API
echo "Restarting API container..."
docker stop $API_CONTAINER || true
docker rm $API_CONTAINER || true
docker-compose -f $COMPOSE_FILE up -d api

# Wait for API
echo "Waiting for API to start..."
sleep 5

# Check API health
if docker ps | grep -q "$API_CONTAINER"; then
    echo -e "${GREEN}✅ API container started${NC}"

    API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/api/v1/health || echo "000")
    if [ "$API_HEALTH" = "200" ]; then
        echo -e "${GREEN}✅ API is healthy (HTTP $API_HEALTH)${NC}"
    else
        echo -e "${YELLOW}⚠️  API health check: HTTP $API_HEALTH (may still be starting)${NC}"
    fi
else
    echo -e "${RED}❌ API container failed to start${NC}"
    exit 1
fi

# Restart SNMP worker
echo "Restarting SNMP worker..."
docker-compose -f $COMPOSE_FILE restart celery-worker-snmp
echo -e "${GREEN}✅ SNMP worker restarted${NC}"

# Restart Celery Beat
echo "Restarting Celery Beat..."
docker-compose -f $COMPOSE_FILE restart celery-beat
echo -e "${GREEN}✅ Celery Beat restarted${NC}"

sleep 3

echo ""
echo -e "${YELLOW}Step 7: Verify Deployment${NC}"
echo "=========================================="

# Verify Phase 1 endpoints
echo "Testing Phase 1 endpoints..."
SUMMARY_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/api/v1/interfaces/summary || echo "000")

if [ "$SUMMARY_RESPONSE" = "200" ] || [ "$SUMMARY_RESPONSE" = "401" ]; then
    echo -e "${GREEN}✅ Phase 1 API endpoints accessible (HTTP $SUMMARY_RESPONSE)${NC}"
else
    echo -e "${YELLOW}⚠️  Phase 1 API: HTTP $SUMMARY_RESPONSE${NC}"
fi

# Verify Celery Beat schedule
echo "Verifying Celery Beat schedule..."
docker logs --tail 100 $BEAT_CONTAINER 2>&1 | grep -i "discover\|collect\|interface" > /tmp/beat_schedule.txt || true

if grep -q "discover-all-interfaces" /tmp/beat_schedule.txt; then
    echo -e "${GREEN}✅ Phase 1 tasks scheduled (interface discovery)${NC}"
fi

if [ "$DEPLOY_PHASE2" = "true" ]; then
    if grep -q "collect-interface-metrics" /tmp/beat_schedule.txt; then
        echo -e "${GREEN}✅ Phase 2 tasks scheduled (metrics collection)${NC}"
    fi
fi

rm -f /tmp/beat_schedule.txt

echo ""
echo "============================================"
echo -e "${GREEN}✅ DEPLOYMENT COMPLETE!${NC}"
echo "============================================"
echo ""

echo -e "${BLUE}📦 Deployed Components:${NC}"
if [ "$DEPLOY_PHASE1" = "true" ]; then
    echo "  ✅ Phase 1: Interface Discovery"
    echo "     - Database schema (device_interfaces, interface_metrics_summary)"
    echo "     - Interface parser (9 types, 7 ISP providers)"
    echo "     - Discovery tasks (hourly)"
    echo "     - API endpoints (8 endpoints)"
fi

if [ "$DEPLOY_PHASE2" = "true" ]; then
    echo "  ✅ Phase 2: VictoriaMetrics Integration"
    echo "     - Metrics collector (8 counters per interface)"
    echo "     - Collection tasks (every 5 min)"
    echo "     - Summary caching (every 15 min)"
    echo "     - Threshold alerts (every 1 min)"
fi

if [ "$DEPLOY_PHASE3" = "true" ]; then
    echo "  ✅ Phase 3: Topology & Analytics"
    echo "     - LLDP/CDP topology discovery"
    echo "     - Baseline learning"
    echo "     - Anomaly detection"
fi

echo ""
echo -e "${BLUE}📊 Scheduled Tasks:${NC}"
echo "  ⏰ Interface discovery:     Every hour at :00"
echo "  ⏰ Interface cleanup:        Daily at 4:00 AM"

if [ "$DEPLOY_PHASE2" = "true" ]; then
    echo "  ⏰ Metrics collection:       Every 5 minutes"
    echo "  ⏰ Summary updates:          Every 15 minutes"
    echo "  ⏰ Threshold checks:         Every 1 minute"
fi

echo ""
echo -e "${BLUE}🔗 API Endpoints:${NC}"
echo "  GET  /api/v1/interfaces/list"
echo "  GET  /api/v1/interfaces/summary"
echo "  GET  /api/v1/interfaces/device/{id}"
echo "  GET  /api/v1/interfaces/critical"
echo "  GET  /api/v1/interfaces/isp"
echo "  POST /api/v1/interfaces/discover/{id}"
echo "  POST /api/v1/interfaces/discover/all"

echo ""
echo -e "${YELLOW}⚠️  IMPORTANT: SNMP Whitelist Required${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Network admins must whitelist Flux IP (10.30.25.46)"
echo "on ALL Cisco devices for SNMP access:"
echo ""
echo "  access-list <acl_number> permit 10.30.25.46"
echo "  snmp-server community XoNaz-<h RO <acl_number>"
echo ""
echo "Without this, discovery and metrics collection will NOT work!"
echo ""

echo -e "${BLUE}📋 Monitoring Commands:${NC}"
echo ""
echo "# Check API logs"
echo "docker logs -f $API_CONTAINER | grep interface"
echo ""
echo "# Check SNMP worker logs"
echo "docker logs -f $WORKER_SNMP_CONTAINER | grep -i discover"
echo ""
echo "# Check Celery Beat schedule"
echo "docker logs $BEAT_CONTAINER | grep -i discover"
echo ""
echo "# Count interfaces in database"
echo "docker exec $DB_CONTAINER psql -U ward_admin -d ward_ops -c \"SELECT COUNT(*) FROM device_interfaces\""
echo ""
echo "# Show critical interfaces"
echo "docker exec $DB_CONTAINER psql -U ward_admin -d ward_ops -c \"SELECT * FROM device_interfaces WHERE is_critical = true LIMIT 5\""
echo ""

if [ "$DEPLOY_PHASE2" = "true" ]; then
    echo "# Query VictoriaMetrics (metrics count)"
    echo "curl 'http://localhost:8428/api/v1/query?query=count(interface_if_hc_in_octets)'"
    echo ""
    echo "# Query interface traffic (last 5 min rate)"
    echo "curl 'http://localhost:8428/api/v1/query?query=rate(interface_if_hc_in_octets\{interface_type=\"isp\"\}[5m])*8'"
    echo ""
fi

echo "============================================"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo "============================================"
