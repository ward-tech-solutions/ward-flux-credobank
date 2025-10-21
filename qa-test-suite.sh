#!/bin/bash

# ================================================================
# WARD OPS CredoBank - Automated QA Test Suite
# ================================================================
# This script tests all critical functionality after deployment
# Run on production server: ./qa-test-suite.sh
# ================================================================

set -e

API_URL="http://localhost:5001"
FAILED_TESTS=0
PASSED_TESTS=0
TOTAL_TESTS=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test result tracking
declare -a FAILED_TEST_NAMES=()

echo "================================================================"
echo "  WARD OPS CredoBank - QA Test Suite"
echo "================================================================"
echo "API URL: $API_URL"
echo "Date: $(date)"
echo ""

# Function to log test results
log_test() {
    local test_name="$1"
    local result="$2"
    local details="$3"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ "$result" = "PASS" ]; then
        echo -e "${GREEN}✓${NC} TEST $TOTAL_TESTS: $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗${NC} TEST $TOTAL_TESTS: $test_name"
        echo -e "  ${YELLOW}Details:${NC} $details"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        FAILED_TEST_NAMES+=("$test_name")
    fi
}

# Get auth token
echo "================================================================"
echo "Phase 1: Authentication"
echo "================================================================"

TOKEN_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" 2>/dev/null)

TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -n "$TOKEN" ]; then
    log_test "Admin login successful" "PASS" ""
else
    log_test "Admin login successful" "FAIL" "No token received"
    echo "Cannot proceed without authentication. Exiting."
    exit 1
fi

echo ""

# ================================================================
# Phase 2: Critical API Endpoints
# ================================================================

echo "================================================================"
echo "Phase 2: Critical API Endpoints"
echo "================================================================"

# Test 1: Health Check
HEALTH=$(curl -s "$API_URL/api/v1/health" 2>/dev/null)
if echo "$HEALTH" | grep -q "status"; then
    log_test "API health check responds" "PASS" ""
else
    log_test "API health check responds" "FAIL" "No status in response"
fi

# Test 2: Get All Devices
DEVICES=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/devices" 2>/dev/null)
DEVICE_COUNT=$(echo "$DEVICES" | grep -o '"hostid"' | wc -l | tr -d ' ')

if [ "$DEVICE_COUNT" -gt 0 ]; then
    log_test "Get all devices (found $DEVICE_COUNT)" "PASS" ""
else
    log_test "Get all devices" "FAIL" "No devices returned"
fi

# Test 3: Verify down_since field exists
DOWN_SINCE_COUNT=$(echo "$DEVICES" | grep -c '"down_since"' || true)
if [ "$DOWN_SINCE_COUNT" -gt 0 ]; then
    log_test "API returns down_since field" "PASS" "Found in $DOWN_SINCE_COUNT devices"
else
    log_test "API returns down_since field" "FAIL" "down_since not found in API response"
fi

# Test 4: Check for down devices with down_since set
DOWN_DEVICES=$(echo "$DEVICES" | grep -A 20 '"ping_status": "Down"' | grep -c '"down_since": "[^n]' || true)
if [ "$DOWN_DEVICES" -gt 0 ]; then
    log_test "Down devices have down_since timestamp" "PASS" "$DOWN_DEVICES devices tracked"
else
    log_test "Down devices have down_since timestamp" "FAIL" "No down devices with timestamps"
fi

# Test 5: Get Regions
REGIONS=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/branches/regions" 2>/dev/null)
REGION_COUNT=$(echo "$REGIONS" | grep -o '"region"' | wc -l | tr -d ' ')

if [ "$REGION_COUNT" -gt 0 ]; then
    log_test "Get regions (found $REGION_COUNT)" "PASS" ""
else
    log_test "Get regions" "FAIL" "No regions returned"
fi

# Test 6: Get Branches
BRANCHES=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/branches" 2>/dev/null)
BRANCH_COUNT=$(echo "$BRANCHES" | grep -o '"id"' | wc -l | tr -d ' ')

if [ "$BRANCH_COUNT" -gt 0 ]; then
    log_test "Get branches (found $BRANCH_COUNT)" "PASS" ""
else
    log_test "Get branches" "FAIL" "No branches returned"
fi

# Test 7: Dashboard Stats
STATS=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/dashboard/stats" 2>/dev/null)
if echo "$STATS" | grep -q "total_devices"; then
    TOTAL=$(echo "$STATS" | grep -o '"total_devices":[0-9]*' | cut -d':' -f2)
    ONLINE=$(echo "$STATS" | grep -o '"online_devices":[0-9]*' | cut -d':' -f2)
    OFFLINE=$(echo "$STATS" | grep -o '"offline_devices":[0-9]*' | cut -d':' -f2)
    log_test "Dashboard stats (Total: $TOTAL, Online: $ONLINE, Offline: $OFFLINE)" "PASS" ""
else
    log_test "Dashboard stats" "FAIL" "total_devices not found"
fi

echo ""

# ================================================================
# Phase 3: Database Integrity
# ================================================================

echo "================================================================"
echo "Phase 3: Database Integrity"
echo "================================================================"

# Test 8: Check down_since column exists
DB_COLUMN=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "\d standalone_devices" 2>/dev/null | grep -c "down_since" || true)
if [ "$DB_COLUMN" -gt 0 ]; then
    log_test "Database down_since column exists" "PASS" ""
else
    log_test "Database down_since column exists" "FAIL" "Column not found in schema"
fi

# Test 9: Check monitoring mode
MODE=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "SELECT mode FROM monitoring_profiles WHERE is_active = true;" 2>/dev/null | tr -d ' \n')
if [ "$MODE" = "standalone" ]; then
    log_test "Monitoring mode is standalone" "PASS" ""
else
    log_test "Monitoring mode is standalone" "FAIL" "Current mode: $MODE"
fi

# Test 10: Count devices with down_since set
DOWN_TRACKED=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "SELECT COUNT(*) FROM standalone_devices WHERE down_since IS NOT NULL;" 2>/dev/null | tr -d ' ')
if [ "$DOWN_TRACKED" -gt 0 ]; then
    log_test "Devices being tracked for downtime ($DOWN_TRACKED devices)" "PASS" ""
else
    log_test "Devices being tracked for downtime" "FAIL" "No devices have down_since set"
fi

echo ""

# ================================================================
# Phase 4: Worker Health
# ================================================================

echo "================================================================"
echo "Phase 4: Worker Health"
echo "================================================================"

# Test 11: Worker container running
WORKER_STATUS=$(docker ps --filter "name=wardops-worker-prod" --format "{{.Status}}" 2>/dev/null)
if echo "$WORKER_STATUS" | grep -q "Up"; then
    log_test "Celery worker container running" "PASS" "$WORKER_STATUS"
else
    log_test "Celery worker container running" "FAIL" "Worker not running"
fi

# Test 12: Worker has down_since tracking code
WORKER_CODE=$(docker exec wardops-worker-prod grep -c "went DOWN" /app/monitoring/tasks.py 2>/dev/null || echo "0")
if [ "$WORKER_CODE" -gt 0 ]; then
    log_test "Worker has state transition tracking code" "PASS" ""
else
    log_test "Worker has state transition tracking code" "FAIL" "Code not found"
fi

# Test 13: Recent worker activity
RECENT_TASKS=$(docker logs --since 5m wardops-worker-prod 2>&1 | grep -c "Task monitoring.tasks.ping_device" || true)
if [ "$RECENT_TASKS" -gt 10 ]; then
    log_test "Worker processing ping tasks ($RECENT_TASKS in last 5 min)" "PASS" ""
else
    log_test "Worker processing ping tasks" "FAIL" "Only $RECENT_TASKS tasks in 5 minutes"
fi

echo ""

# ================================================================
# Phase 5: Container Health
# ================================================================

echo "================================================================"
echo "Phase 5: Container Health"
echo "================================================================"

# Test 14: All containers running
EXPECTED_CONTAINERS=("wardops-api-prod" "wardops-worker-prod" "wardops-beat-prod" "wardops-postgres-prod" "wardops-redis-prod" "wardops-victoriametrics-prod")
RUNNING_COUNT=0

for container in "${EXPECTED_CONTAINERS[@]}"; do
    if docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
        RUNNING_COUNT=$((RUNNING_COUNT + 1))
    fi
done

if [ "$RUNNING_COUNT" -eq "${#EXPECTED_CONTAINERS[@]}" ]; then
    log_test "All containers running (${RUNNING_COUNT}/${#EXPECTED_CONTAINERS[@]})" "PASS" ""
else
    log_test "All containers running" "FAIL" "Only ${RUNNING_COUNT}/${#EXPECTED_CONTAINERS[@]} running"
fi

# Test 15: API container health
API_HEALTH=$(docker inspect wardops-api-prod --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
if [ "$API_HEALTH" = "healthy" ]; then
    log_test "API container healthy" "PASS" ""
else
    log_test "API container healthy" "FAIL" "Status: $API_HEALTH"
fi

# Test 16: Database connections
DB_CONNECTIONS=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='ward_ops';" 2>/dev/null | tr -d ' ')
if [ "$DB_CONNECTIONS" -gt 0 ] && [ "$DB_CONNECTIONS" -lt 100 ]; then
    log_test "Database connections healthy ($DB_CONNECTIONS active)" "PASS" ""
else
    log_test "Database connections healthy" "FAIL" "$DB_CONNECTIONS connections (check for leaks)"
fi

echo ""

# ================================================================
# Phase 6: Performance Checks
# ================================================================

echo "================================================================"
echo "Phase 6: Performance Checks"
echo "================================================================"

# Test 17: API response time
START_TIME=$(date +%s%3N)
curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/devices" > /dev/null 2>&1
END_TIME=$(date +%s%3N)
RESPONSE_TIME=$((END_TIME - START_TIME))

if [ "$RESPONSE_TIME" -lt 1000 ]; then
    log_test "API response time < 1s (${RESPONSE_TIME}ms)" "PASS" ""
elif [ "$RESPONSE_TIME" -lt 2000 ]; then
    log_test "API response time" "PASS" "${RESPONSE_TIME}ms (acceptable)"
else
    log_test "API response time" "FAIL" "${RESPONSE_TIME}ms (too slow)"
fi

# Test 18: Database size
DB_SIZE=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "SELECT pg_size_pretty(pg_database_size('ward_ops'));" 2>/dev/null | tr -d ' ')
log_test "Database size: $DB_SIZE" "PASS" "Informational"

# Test 19: Redis memory
REDIS_MEM=$(docker exec wardops-redis-prod redis-cli INFO memory 2>/dev/null | grep "used_memory_human" | cut -d':' -f2 | tr -d '\r')
log_test "Redis memory usage: $REDIS_MEM" "PASS" "Informational"

echo ""

# ================================================================
# Final Report
# ================================================================

echo "================================================================"
echo "  TEST EXECUTION SUMMARY"
echo "================================================================"
echo ""
echo "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $FAILED_TESTS${NC}"
echo ""

if [ "$FAILED_TESTS" -gt 0 ]; then
    echo -e "${RED}FAILED TESTS:${NC}"
    for test_name in "${FAILED_TEST_NAMES[@]}"; do
        echo "  - $test_name"
    done
    echo ""
fi

SUCCESS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
echo "Success Rate: ${SUCCESS_RATE}%"
echo ""

if [ "$FAILED_TESTS" -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    echo ""
    echo "System Status: HEALTHY"
    echo "Production Ready: YES"
    exit 0
elif [ "$FAILED_TESTS" -lt 3 ]; then
    echo -e "${YELLOW}⚠ SOME TESTS FAILED (Minor Issues)${NC}"
    echo ""
    echo "System Status: FUNCTIONAL WITH ISSUES"
    echo "Production Ready: YES (with monitoring)"
    exit 0
else
    echo -e "${RED}✗ CRITICAL TESTS FAILED${NC}"
    echo ""
    echo "System Status: DEGRADED"
    echo "Production Ready: NO (requires fixes)"
    exit 1
fi
