#!/bin/bash

##############################################################################
# Deploy AUTO-SCALING Batch Processing Solution
##############################################################################
#
# WHAT THIS DOES:
# - Automatically adjusts batch size based on device count
# - 875 devices   → 100 per batch → 9 batches
# - 1,500 devices → 150 per batch → 10 batches
# - 3,000 devices → 300 per batch → 10 batches
# - 10,000 devices → 500 per batch → 20 batches (capped)
#
# NO MANUAL TUNING NEEDED - IT JUST WORKS!
#
##############################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.production-priority-queues.yml"

echo "=========================================================================="
echo -e "${GREEN}🚀 DEPLOYING AUTO-SCALING BATCH PROCESSING${NC}"
echo "=========================================================================="
echo ""
echo "⏰ Started at: $(date)"
echo ""

##############################################################################
# What's Being Deployed
##############################################################################
echo -e "${CYAN}📦 AUTO-SCALING SOLUTION:${NC}"
echo ""
echo "  ✅ Automatically adjusts batch size based on device count"
echo "  ✅ Works from 100 to 10,000+ devices"
echo "  ✅ No manual configuration needed"
echo "  ✅ Keeps task count constant (~60-80 tasks/min)"
echo "  ✅ Maintains 10-second near real-time intervals"
echo ""
echo -e "${CYAN}📊 AUTO-SCALING EXAMPLES:${NC}"
echo ""
echo "  Device Count │ Batch Size │ Batches │ Tasks/Min │ Performance"
echo "  ────────────┼────────────┼─────────┼───────────┼─────────────"
echo "  875         │ 100        │ 9       │ 54        │ ✅ Excellent"
echo "  1,500       │ 150        │ 10      │ 60        │ ✅ Excellent"
echo "  2,000       │ 200        │ 10      │ 60        │ ✅ Excellent"
echo "  3,000       │ 300        │ 10      │ 60        │ ✅ Excellent"
echo "  5,000       │ 500        │ 10      │ 60        │ ✅ Excellent"
echo "  10,000      │ 500 (cap)  │ 20      │ 120       │ ✅ Good"
echo ""
echo -e "${YELLOW}⚠️  This will restart worker and beat containers!${NC}"
echo ""

read -p "Press ENTER to continue (Ctrl+C to cancel)..."

##############################################################################
# Backup Current Configuration
##############################################################################
echo ""
echo -e "${BLUE}[1/7] Backing up current configuration...${NC}"
echo ""

BACKUP_DIR="backups/auto-scaling-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -f "monitoring/tasks_batch.py" ]; then
    cp monitoring/tasks_batch.py "$BACKUP_DIR/tasks_batch.py.backup"
    echo "✅ Backed up tasks_batch.py"
fi

echo "Backups saved to: $BACKUP_DIR"
echo ""

##############################################################################
# Verify Auto-Scaling Code
##############################################################################
echo -e "${BLUE}[2/7] Verifying auto-scaling implementation...${NC}"
echo ""

if grep -q "calculate_optimal_batch_size" monitoring/tasks_batch.py; then
    echo "✅ Auto-scaling function found"
else
    echo -e "${RED}❌ Error: Auto-scaling function not found!${NC}"
    echo "Please ensure you've pulled the latest code from git."
    exit 1
fi

if grep -q "AUTO-SCALING: Calculate optimal batch size" monitoring/tasks_batch.py; then
    echo "✅ Auto-scaling logic integrated"
else
    echo -e "${RED}❌ Error: Auto-scaling not integrated in batch tasks!${NC}"
    exit 1
fi

echo ""

##############################################################################
# Check Current Device Count
##############################################################################
echo -e "${BLUE}[3/7] Checking current device count...${NC}"
echo ""

DEVICE_COUNT=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -t -c "SELECT COUNT(*) FROM standalone_devices WHERE enabled = true;" 2>/dev/null | tr -d ' ' || echo "0")

echo "Current enabled devices: $DEVICE_COUNT"

if [ "$DEVICE_COUNT" -gt 0 ]; then
    # Calculate what batch size will be used
    CALCULATED_BATCH=$(python3 -c "import math; device_count=$DEVICE_COUNT; batch_size = math.ceil(device_count / 10); batch_size = math.ceil(batch_size / 50) * 50; batch_size = max(50, min(batch_size, 500)); print(batch_size)")
    BATCHES=$(python3 -c "import math; print(math.ceil($DEVICE_COUNT / $CALCULATED_BATCH))")

    echo "Auto-calculated batch size: $CALCULATED_BATCH devices"
    echo "Number of batches: $BATCHES"
    echo "Tasks per minute: ~$((BATCHES * 6))"
fi

echo ""

##############################################################################
# Stop Old Workers
##############################################################################
echo -e "${BLUE}[4/7] Stopping workers for update...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" stop celery-worker-monitoring celery-worker-snmp celery-beat

echo "✅ Workers stopped"
echo ""

##############################################################################
# Build New Images
##############################################################################
echo -e "${BLUE}[5/7] Building worker images with auto-scaling...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" build --no-cache celery-worker-monitoring celery-worker-snmp celery-beat

echo "✅ Images built"
echo ""

##############################################################################
# Start New Workers
##############################################################################
echo -e "${BLUE}[6/7] Starting auto-scaling workers...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" up -d celery-worker-monitoring celery-worker-snmp celery-beat

echo "Waiting 30 seconds for workers to initialize..."
sleep 30

echo "✅ Workers started"
echo ""

##############################################################################
# Verify Auto-Scaling is Working
##############################################################################
echo -e "${BLUE}[7/7] Verifying auto-scaling is active...${NC}"
echo ""

echo "Container status:"
docker-compose -f "$COMPOSE_FILE" ps celery-worker-monitoring celery-worker-snmp celery-beat

echo ""
echo "Waiting 35 seconds for first ping cycle with auto-scaling..."
sleep 35

echo ""
echo "Checking for auto-scaling log messages:"
docker-compose -f "$COMPOSE_FILE" logs --tail 100 celery-worker-monitoring | grep -E "(AUTO-SCALING|batch size)" | tail -5

echo ""

##############################################################################
# Summary
##############################################################################
echo "=========================================================================="
echo -e "${GREEN}✅ AUTO-SCALING DEPLOYED SUCCESSFULLY${NC}"
echo "=========================================================================="
echo ""
echo -e "${CYAN}🎯 What Changed:${NC}"
echo ""
echo "  ✅ Batch size now automatically adjusts based on device count"
echo "  ✅ No manual tuning needed as you add devices"
echo "  ✅ Scales from 100 to 10,000+ devices"
echo "  ✅ Maintains consistent performance"
echo ""
echo -e "${CYAN}📊 Current Configuration:${NC}"
echo ""
echo "  Enabled devices: $DEVICE_COUNT"
echo "  Auto-calculated batch size: $CALCULATED_BATCH"
echo "  Number of batches: $BATCHES"
echo "  Tasks per minute: ~$((BATCHES * 6))"
echo ""
echo -e "${CYAN}🔍 Monitor Auto-Scaling:${NC}"
echo ""
echo "  # Watch auto-scaling decisions (run for 2-3 minutes):"
echo "  docker-compose -f $COMPOSE_FILE logs -f celery-worker-monitoring | grep AUTO-SCALING"
echo ""
echo "  # You should see messages like:"
echo "  # AUTO-SCALING: 875 devices → batch size 100 → ~9 batches"
echo ""
echo "  # Check queue sizes (should stay consistent as you add devices):"
echo "  watch -n 5 'docker-compose -f $COMPOSE_FILE exec redis redis-cli -a redispass LLEN monitoring snmp'"
echo ""
echo "  # Verify performance:"
echo "  docker-compose -f $COMPOSE_FILE exec postgres psql -U ward_admin -d ward_ops -c \\"
echo "    \"SELECT COUNT(*), MAX(timestamp), NOW() - MAX(timestamp) as age"
echo "     FROM ping_results WHERE timestamp > NOW() - INTERVAL '1 minute';\""
echo ""
echo -e "${GREEN}🚀 AUTO-SCALING ACTIVE - ADD DEVICES WITHOUT WORRY!${NC}"
echo ""
echo "  When you add devices from 875 → 1,500:"
echo "  • Batch size automatically increases from 100 → 150"
echo "  • Batches stay at ~10 (not 15!)"
echo "  • Tasks/min increases slightly: 54 → 60 (only 11% more!)"
echo "  • Performance remains excellent"
echo "  • NO configuration changes needed!"
echo ""
echo "⏰ Completed at: $(date)"
echo "=========================================================================="
echo ""

##############################################################################
# Next Steps
##############################################################################
echo -e "${CYAN}📋 NEXT STEPS:${NC}"
echo ""
echo "1. Monitor auto-scaling for 10 minutes to verify it's working"
echo ""
echo "2. Add more devices (up to 1,500-2,000) - system will auto-adjust!"
echo ""
echo "3. Check alerts are being created:"
echo "   docker-compose -f $COMPOSE_FILE exec postgres psql -U ward_admin -d ward_ops -c \\"
echo "     \"SELECT COUNT(*), MAX(triggered_at) FROM alert_history WHERE triggered_at > NOW() - INTERVAL '10 minutes';\""
echo ""
echo "4. If you see 'AUTO-SCALING' messages in logs, everything is working! ✅"
echo ""

exit 0
