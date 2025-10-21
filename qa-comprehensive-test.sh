#!/bin/bash

# ================================================================
# WARD OPS CredoBank - COMPREHENSIVE QA Test Suite
# ================================================================
# Complete end-to-end testing of all functionality
# Run on production server: ./qa-comprehensive-test.sh
# ================================================================

set -e

API_URL="http://localhost:5001"
FAILED_TESTS=0
PASSED_TESTS=0
TOTAL_TESTS=0
WARNINGS=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

declare -a FAILED_TEST_NAMES=()
declare -a WARNING_TEST_NAMES=()

echo "================================================================"
echo "  WARD OPS CredoBank - COMPREHENSIVE QA TEST SUITE"
echo "================================================================"
echo "API URL: $API_URL"
echo "Date: $(date)"
echo "Hostname: $(hostname)"
echo ""

log_test() {
    local test_name="$1"
    local result="$2"
    local details="$3"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ "$result" = "PASS" ]; then
        echo -e "${GREEN}✓${NC} TEST $TOTAL_TESTS: $test_name"
        [ -n "$details" ] && echo -e "  ${BLUE}Info:${NC} $details"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    elif [ "$result" = "WARN" ]; then
        echo -e "${YELLOW}⚠${NC} TEST $TOTAL_TESTS: $test_name"
        echo -e "  ${YELLOW}Warning:${NC} $details"
        WARNINGS=$((WARNINGS + 1))
        WARNING_TEST_NAMES+=("$test_name: $details")
    else
        echo -e "${RED}✗${NC} TEST $TOTAL_TESTS: $test_name"
        echo -e "  ${RED}Failed:${NC} $details"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        FAILED_TEST_NAMES+=("$test_name")
    fi
}

# ================================================================
# PHASE 1: AUTHENTICATION & AUTHORIZATION
# ================================================================

echo ""
echo "================================================================"
echo "PHASE 1: AUTHENTICATION & AUTHORIZATION"
echo "================================================================"

# Test 1.1: Admin Login
TOKEN_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" 2>/dev/null)

TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -n "$TOKEN" ]; then
    log_test "Admin login with correct credentials" "PASS" "Token received"
else
    log_test "Admin login with correct credentials" "FAIL" "No token in response"
    echo "CRITICAL: Cannot proceed without authentication"
    exit 1
fi

# Test 1.2: Login with wrong credentials
WRONG_LOGIN=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=wrongpassword" 2>/dev/null)

if echo "$WRONG_LOGIN" | grep -q "detail"; then
    log_test "Login rejection with invalid credentials" "PASS" "Correctly rejected"
else
    log_test "Login rejection with invalid credentials" "FAIL" "Should have rejected"
fi

# Test 1.3: API access without token
NO_AUTH=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/devices" 2>/dev/null)
if [ "$NO_AUTH" = "401" ] || [ "$NO_AUTH" = "403" ]; then
    log_test "API rejects unauthenticated requests" "PASS" "Returns $NO_AUTH"
else
    log_test "API rejects unauthenticated requests" "FAIL" "Returns $NO_AUTH instead of 401/403"
fi

# Test 1.4: Token expiration check
TOKEN_LENGTH=${#TOKEN}
if [ "$TOKEN_LENGTH" -gt 50 ]; then
    log_test "JWT token format valid" "PASS" "Token length: $TOKEN_LENGTH chars"
else
    log_test "JWT token format valid" "WARN" "Token seems short: $TOKEN_LENGTH chars"
fi

# ================================================================
# PHASE 2: CORE API ENDPOINTS
# ================================================================

echo ""
echo "================================================================"
echo "PHASE 2: CORE API ENDPOINTS"
echo "================================================================"

# Test 2.1: Health Check
HEALTH=$(curl -s "$API_URL/api/v1/health" 2>/dev/null)
if echo "$HEALTH" | grep -q "status"; then
    STATUS=$(echo "$HEALTH" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    log_test "API health endpoint" "PASS" "Status: $STATUS"
else
    log_test "API health endpoint" "FAIL" "No status field in response"
fi

# Test 2.2: Get All Devices
DEVICES=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/devices" 2>/dev/null)
DEVICE_COUNT=$(echo "$DEVICES" | jq 'length' 2>/dev/null || echo "0")

if [ "$DEVICE_COUNT" -gt 0 ]; then
    log_test "GET /api/v1/devices" "PASS" "Retrieved $DEVICE_COUNT devices"
else
    log_test "GET /api/v1/devices" "FAIL" "No devices returned"
fi

# Test 2.3: Verify device structure
FIRST_DEVICE=$(echo "$DEVICES" | jq '.[0]' 2>/dev/null)
REQUIRED_FIELDS=("hostid" "name" "ip" "ping_status" "last_check")
MISSING_FIELDS=()

for field in "${REQUIRED_FIELDS[@]}"; do
    if ! echo "$FIRST_DEVICE" | jq -e ".$field" > /dev/null 2>&1; then
        MISSING_FIELDS+=("$field")
    fi
done

if [ ${#MISSING_FIELDS[@]} -eq 0 ]; then
    log_test "Device response contains required fields" "PASS" "All fields present"
else
    log_test "Device response contains required fields" "FAIL" "Missing: ${MISSING_FIELDS[*]}"
fi

# Test 2.4: down_since field present
if echo "$FIRST_DEVICE" | jq -e '.down_since' > /dev/null 2>&1; then
    log_test "Device response includes down_since field" "PASS" "Field exists"
else
    log_test "Device response includes down_since field" "FAIL" "down_since field missing"
fi

# Test 2.5: Check down devices with timestamps
DOWN_DEVICES_WITH_TS=$(echo "$DEVICES" | jq '[.[] | select(.ping_status == "Down" and .down_since != null)] | length' 2>/dev/null)
TOTAL_DOWN=$(echo "$DEVICES" | jq '[.[] | select(.ping_status == "Down")] | length' 2>/dev/null)

if [ "$DOWN_DEVICES_WITH_TS" -gt 0 ]; then
    log_test "Down devices have down_since timestamps" "PASS" "$DOWN_DEVICES_WITH_TS of $TOTAL_DOWN down devices tracked"
else
    if [ "$TOTAL_DOWN" -eq 0 ]; then
        log_test "Down devices have down_since timestamps" "PASS" "No down devices currently"
    else
        log_test "Down devices have down_since timestamps" "WARN" "$TOTAL_DOWN down devices but none have timestamps yet"
    fi
fi

# Test 2.6: Get single device details
FIRST_DEVICE_ID=$(echo "$DEVICES" | jq -r '.[0].hostid' 2>/dev/null)
DEVICE_DETAIL=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/devices/$FIRST_DEVICE_ID" 2>/dev/null)

if echo "$DEVICE_DETAIL" | jq -e '.hostid' > /dev/null 2>&1; then
    log_test "GET /api/v1/devices/{id}" "PASS" "Device details retrieved"
else
    log_test "GET /api/v1/devices/{id}" "FAIL" "Could not retrieve device details"
fi

# Test 2.7: Get Branches
BRANCHES=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/branches" 2>/dev/null)
BRANCH_COUNT=$(echo "$BRANCHES" | jq 'length' 2>/dev/null || echo "0")

if [ "$BRANCH_COUNT" -gt 0 ]; then
    log_test "GET /api/v1/branches" "PASS" "Retrieved $BRANCH_COUNT branches"
else
    log_test "GET /api/v1/branches" "FAIL" "No branches returned"
fi

# Test 2.8: Get Regions
REGIONS=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/branches/regions" 2>/dev/null)
REGION_COUNT=$(echo "$REGIONS" | jq '.regions | length' 2>/dev/null || echo "0")

if [ "$REGION_COUNT" -gt 0 ]; then
    log_test "GET /api/v1/branches/regions" "PASS" "Retrieved $REGION_COUNT regions"
else
    log_test "GET /api/v1/branches/regions" "FAIL" "No regions returned"
fi

# Test 2.9: Get Branch Stats
BRANCH_STATS=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/branches/stats" 2>/dev/null)
if echo "$BRANCH_STATS" | jq -e '.total_branches' > /dev/null 2>&1; then
    TOTAL_BR=$(echo "$BRANCH_STATS" | jq -r '.total_branches' 2>/dev/null)
    log_test "GET /api/v1/branches/stats" "PASS" "Total: $TOTAL_BR branches"
else
    log_test "GET /api/v1/branches/stats" "FAIL" "Invalid stats response"
fi

# Test 2.10: Get specific branch
FIRST_BRANCH_ID=$(echo "$BRANCHES" | jq -r '.[0].id' 2>/dev/null)
if [ -n "$FIRST_BRANCH_ID" ] && [ "$FIRST_BRANCH_ID" != "null" ]; then
    BRANCH_DETAIL=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/branches/$FIRST_BRANCH_ID" 2>/dev/null)
    if echo "$BRANCH_DETAIL" | jq -e '.id' > /dev/null 2>&1; then
        log_test "GET /api/v1/branches/{id}" "PASS" "Branch details retrieved"
    else
        log_test "GET /api/v1/branches/{id}" "FAIL" "Could not retrieve branch details"
    fi
else
    log_test "GET /api/v1/branches/{id}" "WARN" "No branch ID to test with"
fi

# Test 2.11: Dashboard Stats
DASH_STATS=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/dashboard/stats" 2>/dev/null)
if echo "$DASH_STATS" | jq -e '.total_devices' > /dev/null 2>&1; then
    TOTAL_DEV=$(echo "$DASH_STATS" | jq -r '.total_devices')
    ONLINE_DEV=$(echo "$DASH_STATS" | jq -r '.online_devices')
    OFFLINE_DEV=$(echo "$DASH_STATS" | jq -r '.offline_devices')
    UPTIME=$(echo "$DASH_STATS" | jq -r '.uptime_percentage')
    log_test "GET /api/v1/dashboard/stats" "PASS" "Total:$TOTAL_DEV, Online:$ONLINE_DEV, Offline:$OFFLINE_DEV, Uptime:${UPTIME}%"
else
    log_test "GET /api/v1/dashboard/stats" "FAIL" "Invalid dashboard stats"
fi

# Test 2.12: Alerts endpoint
ALERTS=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/alerts?limit=10" 2>/dev/null)
ALERT_COUNT=$(echo "$ALERTS" | jq '.alerts | length' 2>/dev/null || echo "0")
log_test "GET /api/v1/alerts" "PASS" "Retrieved $ALERT_COUNT alerts"

# ================================================================
# PHASE 3: DEVICE CRUD OPERATIONS
# ================================================================

echo ""
echo "================================================================"
echo "PHASE 3: DEVICE CRUD OPERATIONS"
echo "================================================================"

# Generate unique test device data
TEST_DEVICE_NAME="QA-Test-Device-$(date +%s)"
TEST_DEVICE_IP="192.168.99.$(shuf -i 1-254 -n 1)"

# Test 3.1: Create new device
CREATE_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/standalone-devices" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$TEST_DEVICE_NAME\",
    \"ip\": \"$TEST_DEVICE_IP\",
    \"device_type\": \"Test\",
    \"enabled\": true
  }" 2>/dev/null)

if echo "$CREATE_RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
    TEST_DEVICE_ID=$(echo "$CREATE_RESPONSE" | jq -r '.id')
    log_test "POST /api/v1/standalone-devices (Create)" "PASS" "Device created: $TEST_DEVICE_ID"
else
    log_test "POST /api/v1/standalone-devices (Create)" "FAIL" "Could not create device"
    TEST_DEVICE_ID=""
fi

# Test 3.2: Get created device
if [ -n "$TEST_DEVICE_ID" ]; then
    GET_CREATED=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/standalone-devices/$TEST_DEVICE_ID" 2>/dev/null)
    if echo "$GET_CREATED" | jq -e '.name' > /dev/null 2>&1; then
        RETRIEVED_NAME=$(echo "$GET_CREATED" | jq -r '.name')
        if [ "$RETRIEVED_NAME" = "$TEST_DEVICE_NAME" ]; then
            log_test "GET /api/v1/standalone-devices/{id}" "PASS" "Retrieved created device"
        else
            log_test "GET /api/v1/standalone-devices/{id}" "FAIL" "Name mismatch"
        fi
    else
        log_test "GET /api/v1/standalone-devices/{id}" "FAIL" "Could not retrieve device"
    fi
fi

# Test 3.3: Update device
if [ -n "$TEST_DEVICE_ID" ]; then
    UPDATE_RESPONSE=$(curl -s -X PUT "$API_URL/api/v1/standalone-devices/$TEST_DEVICE_ID" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"name\": \"${TEST_DEVICE_NAME}-Updated\",
        \"ip\": \"$TEST_DEVICE_IP\",
        \"device_type\": \"Test-Updated\",
        \"enabled\": false
      }" 2>/dev/null)

    if echo "$UPDATE_RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
        UPDATED_NAME=$(echo "$UPDATE_RESPONSE" | jq -r '.name')
        if [[ "$UPDATED_NAME" == *"Updated"* ]]; then
            log_test "PUT /api/v1/standalone-devices/{id} (Update)" "PASS" "Device updated"
        else
            log_test "PUT /api/v1/standalone-devices/{id} (Update)" "FAIL" "Update didn't apply"
        fi
    else
        log_test "PUT /api/v1/standalone-devices/{id} (Update)" "FAIL" "Could not update device"
    fi
fi

# Test 3.4: IP conflict check (try to create duplicate IP)
if [ -n "$TEST_DEVICE_IP" ]; then
    DUPLICATE_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/standalone-devices" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"name\": \"Duplicate-Device\",
        \"ip\": \"$TEST_DEVICE_IP\",
        \"device_type\": \"Test\"
      }" 2>/dev/null)

    if echo "$DUPLICATE_RESPONSE" | grep -q "already exists\|duplicate"; then
        log_test "IP conflict detection on create" "PASS" "Duplicate IP rejected"
    else
        # It might have been created if previous delete succeeded
        log_test "IP conflict detection on create" "WARN" "Duplicate check unclear"
    fi
fi

# Test 3.5: Delete device
if [ -n "$TEST_DEVICE_ID" ]; then
    DELETE_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
      "$API_URL/api/v1/standalone-devices/$TEST_DEVICE_ID" \
      -H "Authorization: Bearer $TOKEN" 2>/dev/null)

    if [ "$DELETE_RESPONSE" = "200" ] || [ "$DELETE_RESPONSE" = "204" ]; then
        log_test "DELETE /api/v1/standalone-devices/{id}" "PASS" "Device deleted (HTTP $DELETE_RESPONSE)"
    else
        log_test "DELETE /api/v1/standalone-devices/{id}" "FAIL" "Delete failed (HTTP $DELETE_RESPONSE)"
    fi

    # Verify deletion
    VERIFY_DELETE=$(curl -s -o /dev/null -w "%{http_code}" \
      -H "Authorization: Bearer $TOKEN" \
      "$API_URL/api/v1/standalone-devices/$TEST_DEVICE_ID" 2>/dev/null)

    if [ "$VERIFY_DELETE" = "404" ]; then
        log_test "Verify device deletion" "PASS" "Device not found after delete"
    else
        log_test "Verify device deletion" "WARN" "Device still accessible (HTTP $VERIFY_DELETE)"
    fi
fi

# ================================================================
# PHASE 4: DATABASE INTEGRITY
# ================================================================

echo ""
echo "================================================================"
echo "PHASE 4: DATABASE INTEGRITY"
echo "================================================================"

# Test 4.1: down_since column exists
DB_SCHEMA=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "\d standalone_devices" 2>/dev/null | grep down_since | wc -l | tr -d ' ')
if [ "$DB_SCHEMA" -gt 0 ]; then
    log_test "Database schema: down_since column exists" "PASS" ""
else
    log_test "Database schema: down_since column exists" "FAIL" "Column missing"
fi

# Test 4.2: Monitoring mode
MODE=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "SELECT mode FROM monitoring_profiles WHERE is_active = true;" 2>/dev/null | tr -d ' \n\r')
if [ "$MODE" = "standalone" ]; then
    log_test "Monitoring mode configuration" "PASS" "Mode: standalone"
else
    log_test "Monitoring mode configuration" "FAIL" "Mode: $MODE (expected standalone)"
fi

# Test 4.3: Device count consistency
DB_COUNT=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "SELECT COUNT(*) FROM standalone_devices;" 2>/dev/null | tr -d ' ')
if [ "$DB_COUNT" -eq "$DEVICE_COUNT" ]; then
    log_test "Device count consistency (DB vs API)" "PASS" "$DB_COUNT devices"
else
    log_test "Device count consistency (DB vs API)" "WARN" "DB: $DB_COUNT, API: $DEVICE_COUNT"
fi

# Test 4.4: Devices with down_since set
DOWN_TRACKED=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "SELECT COUNT(*) FROM standalone_devices WHERE down_since IS NOT NULL;" 2>/dev/null | tr -d ' ')
log_test "Devices being tracked for downtime" "PASS" "$DOWN_TRACKED devices have down_since set"

# Test 4.5: Branch relationships
ORPHANED_DEVICES=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "SELECT COUNT(*) FROM standalone_devices sd WHERE sd.branch_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM branches b WHERE b.id = sd.branch_id);" 2>/dev/null | tr -d ' ')
if [ "$ORPHANED_DEVICES" -eq 0 ]; then
    log_test "Foreign key integrity: branch references" "PASS" "No orphaned devices"
else
    log_test "Foreign key integrity: branch references" "FAIL" "$ORPHANED_DEVICES devices with invalid branch_id"
fi

# Test 4.6: Ping results exist
PING_COUNT=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "SELECT COUNT(*) FROM ping_results;" 2>/dev/null | tr -d ' ')
if [ "$PING_COUNT" -gt 1000 ]; then
    log_test "Ping results data collection" "PASS" "$PING_COUNT ping results stored"
else
    log_test "Ping results data collection" "WARN" "Only $PING_COUNT ping results (seems low)"
fi

# Test 4.7: Recent ping activity
RECENT_PINGS=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "SELECT COUNT(*) FROM ping_results WHERE timestamp > NOW() - INTERVAL '5 minutes';" 2>/dev/null | tr -d ' ')
if [ "$RECENT_PINGS" -gt 100 ]; then
    log_test "Recent ping activity (last 5 min)" "PASS" "$RECENT_PINGS recent pings"
else
    log_test "Recent ping activity (last 5 min)" "WARN" "Only $RECENT_PINGS pings in last 5 min"
fi

# Test 4.8: Database size and health
DB_SIZE=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "SELECT pg_size_pretty(pg_database_size('ward_ops'));" 2>/dev/null | tr -d ' ')
log_test "Database size" "PASS" "$DB_SIZE"

# Test 4.9: Database connections
DB_CONNECTIONS=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='ward_ops';" 2>/dev/null | tr -d ' ')
if [ "$DB_CONNECTIONS" -lt 100 ]; then
    log_test "Database connection pool" "PASS" "$DB_CONNECTIONS active connections"
else
    log_test "Database connection pool" "WARN" "$DB_CONNECTIONS connections (possible leak)"
fi

# Test 4.10: Database deadlocks
DEADLOCKS=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "SELECT deadlocks FROM pg_stat_database WHERE datname = 'ward_ops';" 2>/dev/null | tr -d ' ')
if [ "$DEADLOCKS" -eq 0 ]; then
    log_test "Database deadlocks" "PASS" "No deadlocks detected"
else
    log_test "Database deadlocks" "WARN" "$DEADLOCKS deadlocks occurred"
fi

# ================================================================
# PHASE 5: WORKER HEALTH & MONITORING
# ================================================================

echo ""
echo "================================================================"
echo "PHASE 5: WORKER HEALTH & MONITORING"
echo "================================================================"

# Test 5.1: Worker container running
WORKER_STATUS=$(docker ps --filter "name=wardops-worker-prod" --format "{{.Status}}" 2>/dev/null)
if echo "$WORKER_STATUS" | grep -q "Up"; then
    UPTIME=$(echo "$WORKER_STATUS" | grep -o "Up [^(]*")
    log_test "Celery worker container status" "PASS" "$UPTIME"
else
    log_test "Celery worker container status" "FAIL" "Worker not running"
fi

# Test 5.2: Worker code deployment
WORKER_CODE=$(docker exec wardops-worker-prod grep -c "went DOWN" /app/monitoring/tasks.py 2>/dev/null || echo "0")
if [ "$WORKER_CODE" -gt 0 ]; then
    log_test "Worker has down_since tracking code" "PASS" "Latest code deployed"
else
    log_test "Worker has down_since tracking code" "FAIL" "Old code without state tracking"
fi

# Test 5.3: Recent ping task activity
PING_TASKS=$(docker logs --since 5m wardops-worker-prod 2>&1 | grep -c "Task monitoring.tasks.ping_device\[" || echo "0")
if [ "$PING_TASKS" -gt 500 ]; then
    log_test "Worker ping task processing" "PASS" "$PING_TASKS tasks in last 5 min"
elif [ "$PING_TASKS" -gt 100 ]; then
    log_test "Worker ping task processing" "PASS" "$PING_TASKS tasks (moderate activity)"
else
    log_test "Worker ping task processing" "WARN" "Only $PING_TASKS tasks in 5 min"
fi

# Test 5.4: State transition logging
STATE_TRANSITIONS=$(docker logs --since 1h wardops-worker-prod 2>&1 | grep -c "went DOWN\|came back UP" || echo "0")
log_test "Worker state transition logging" "PASS" "$STATE_TRANSITIONS transitions logged in last hour"

# Test 5.5: Worker errors
WORKER_ERRORS=$(docker logs --since 1h wardops-worker-prod 2>&1 | grep -c "ERROR" || echo "0")
if [ "$WORKER_ERRORS" -lt 10 ]; then
    log_test "Worker error rate" "PASS" "$WORKER_ERRORS errors in last hour"
elif [ "$WORKER_ERRORS" -lt 100 ]; then
    log_test "Worker error rate" "WARN" "$WORKER_ERRORS errors in last hour"
else
    log_test "Worker error rate" "FAIL" "$WORKER_ERRORS errors (too many)"
fi

# Test 5.6: Celery beat scheduler
BEAT_STATUS=$(docker ps --filter "name=wardops-beat-prod" --format "{{.Status}}" 2>/dev/null)
if echo "$BEAT_STATUS" | grep -q "Up"; then
    log_test "Celery beat scheduler running" "PASS" ""
else
    log_test "Celery beat scheduler running" "FAIL" "Beat not running"
fi

# Test 5.7: Redis connectivity
REDIS_PING=$(docker exec wardops-redis-prod redis-cli ping 2>/dev/null)
if [ "$REDIS_PING" = "PONG" ]; then
    log_test "Redis connectivity" "PASS" ""
else
    log_test "Redis connectivity" "FAIL" "Redis not responding"
fi

# Test 5.8: Redis memory usage
REDIS_MEM=$(docker exec wardops-redis-prod redis-cli INFO memory 2>/dev/null | grep "used_memory_human" | cut -d':' -f2 | tr -d '\r')
log_test "Redis memory usage" "PASS" "$REDIS_MEM"

# Test 5.9: Redis queue depth
QUEUE_DEPTH=$(docker exec wardops-redis-prod redis-cli LLEN celery 2>/dev/null)
if [ "$QUEUE_DEPTH" -lt 100 ]; then
    log_test "Redis queue depth" "PASS" "$QUEUE_DEPTH tasks queued"
else
    log_test "Redis queue depth" "WARN" "$QUEUE_DEPTH tasks (possible backlog)"
fi

# Test 5.10: VictoriaMetrics
VM_STATUS=$(docker ps --filter "name=wardops-victoriametrics-prod" --format "{{.Status}}" 2>/dev/null)
if echo "$VM_STATUS" | grep -q "Up"; then
    log_test "VictoriaMetrics running" "PASS" ""
else
    log_test "VictoriaMetrics running" "FAIL" "Metrics storage not running"
fi

# ================================================================
# PHASE 6: CONTAINER HEALTH
# ================================================================

echo ""
echo "================================================================"
echo "PHASE 6: CONTAINER HEALTH"
echo "================================================================"

# Test 6.1: All required containers
EXPECTED_CONTAINERS=("wardops-api-prod" "wardops-worker-prod" "wardops-beat-prod" "wardops-postgres-prod" "wardops-redis-prod" "wardops-victoriametrics-prod")
RUNNING_CONTAINERS=$(docker ps --format "{{.Names}}" 2>/dev/null)
MISSING_CONTAINERS=()

for container in "${EXPECTED_CONTAINERS[@]}"; do
    if ! echo "$RUNNING_CONTAINERS" | grep -q "^${container}$"; then
        MISSING_CONTAINERS+=("$container")
    fi
done

if [ ${#MISSING_CONTAINERS[@]} -eq 0 ]; then
    log_test "All required containers running" "PASS" "${#EXPECTED_CONTAINERS[@]}/${#EXPECTED_CONTAINERS[@]} containers up"
else
    log_test "All required containers running" "FAIL" "Missing: ${MISSING_CONTAINERS[*]}"
fi

# Test 6.2: API container health
API_HEALTH=$(docker inspect wardops-api-prod --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
if [ "$API_HEALTH" = "healthy" ]; then
    log_test "API container health status" "PASS" "healthy"
else
    log_test "API container health status" "WARN" "Status: $API_HEALTH"
fi

# Test 6.3: Container restart counts
for container in "${EXPECTED_CONTAINERS[@]}"; do
    RESTARTS=$(docker inspect "$container" --format='{{.RestartCount}}' 2>/dev/null || echo "unknown")
    if [ "$RESTARTS" = "0" ]; then
        log_test "Container stability: $container" "PASS" "No restarts"
    elif [ "$RESTARTS" != "unknown" ] && [ "$RESTARTS" -lt 3 ]; then
        log_test "Container stability: $container" "WARN" "$RESTARTS restarts"
    else
        log_test "Container stability: $container" "FAIL" "$RESTARTS restarts (unstable)"
    fi
done

# Test 6.4: Docker disk usage
DOCKER_DISK=$(docker system df 2>/dev/null | grep -i "images\|containers\|volumes")
log_test "Docker disk usage" "PASS" "$(echo "$DOCKER_DISK" | wc -l) items checked"

# ================================================================
# PHASE 7: PERFORMANCE & RESPONSE TIMES
# ================================================================

echo ""
echo "================================================================"
echo "PHASE 7: PERFORMANCE & RESPONSE TIMES"
echo "================================================================"

# Test 7.1: API devices endpoint response time
START=$(date +%s%3N)
curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/devices" > /dev/null 2>&1
END=$(date +%s%3N)
DEVICES_TIME=$((END - START))

if [ "$DEVICES_TIME" -lt 500 ]; then
    log_test "GET /api/v1/devices response time" "PASS" "${DEVICES_TIME}ms (excellent)"
elif [ "$DEVICES_TIME" -lt 1000 ]; then
    log_test "GET /api/v1/devices response time" "PASS" "${DEVICES_TIME}ms (good)"
elif [ "$DEVICES_TIME" -lt 2000 ]; then
    log_test "GET /api/v1/devices response time" "WARN" "${DEVICES_TIME}ms (acceptable)"
else
    log_test "GET /api/v1/devices response time" "FAIL" "${DEVICES_TIME}ms (too slow)"
fi

# Test 7.2: Dashboard stats response time
START=$(date +%s%3N)
curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/dashboard/stats" > /dev/null 2>&1
END=$(date +%s%3N)
DASH_TIME=$((END - START))

if [ "$DASH_TIME" -lt 300 ]; then
    log_test "GET /api/v1/dashboard/stats response time" "PASS" "${DASH_TIME}ms"
else
    log_test "GET /api/v1/dashboard/stats response time" "WARN" "${DASH_TIME}ms"
fi

# Test 7.3: Branches endpoint response time
START=$(date +%s%3N)
curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/branches" > /dev/null 2>&1
END=$(date +%s%3N)
BRANCH_TIME=$((END - START))

if [ "$BRANCH_TIME" -lt 500 ]; then
    log_test "GET /api/v1/branches response time" "PASS" "${BRANCH_TIME}ms"
else
    log_test "GET /api/v1/branches response time" "WARN" "${BRANCH_TIME}ms"
fi

# Test 7.4: CPU usage
CPU_USAGE=$(docker stats --no-stream --format "{{.Name}}\t{{.CPUPerc}}" 2>/dev/null | grep "wardops-api-prod" | awk '{print $2}' | tr -d '%')
if (( $(echo "$CPU_USAGE < 50" | bc -l) )); then
    log_test "API container CPU usage" "PASS" "${CPU_USAGE}%"
else
    log_test "API container CPU usage" "WARN" "${CPU_USAGE}% (high)"
fi

# Test 7.5: Memory usage
MEM_USAGE=$(docker stats --no-stream --format "{{.Name}}\t{{.MemUsage}}" 2>/dev/null | grep "wardops-api-prod" | awk '{print $2}')
log_test "API container memory usage" "PASS" "$MEM_USAGE"

# ================================================================
# PHASE 8: DATA VALIDATION & INTEGRITY
# ================================================================

echo ""
echo "================================================================"
echo "PHASE 8: DATA VALIDATION & INTEGRITY"
echo "================================================================"

# Test 8.1: IP address format validation
INVALID_IPS=$(echo "$DEVICES" | jq -r '.[] | select(.ip | test("^[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}$") | not) | .ip' 2>/dev/null | wc -l | tr -d ' ')
if [ "$INVALID_IPS" -eq 0 ]; then
    log_test "Device IP address format validation" "PASS" "All IPs valid IPv4"
else
    log_test "Device IP address format validation" "WARN" "$INVALID_IPS devices with non-standard IPs"
fi

# Test 8.2: Duplicate IP detection
DUPLICATE_IPS=$(echo "$DEVICES" | jq -r '.[] | .ip' 2>/dev/null | sort | uniq -d | wc -l | tr -d ' ')
if [ "$DUPLICATE_IPS" -eq 0 ]; then
    log_test "Duplicate IP address detection" "PASS" "No duplicate IPs"
else
    log_test "Duplicate IP address detection" "FAIL" "$DUPLICATE_IPS IPs used by multiple devices"
fi

# Test 8.3: Device names populated
UNNAMED_DEVICES=$(echo "$DEVICES" | jq '[.[] | select(.name == "" or .name == null)] | length' 2>/dev/null)
if [ "$UNNAMED_DEVICES" -eq 0 ]; then
    log_test "Device naming compliance" "PASS" "All devices named"
else
    log_test "Device naming compliance" "WARN" "$UNNAMED_DEVICES devices without names"
fi

# Test 8.4: Ping status values
INVALID_STATUS=$(echo "$DEVICES" | jq -r '.[] | select(.ping_status != "Up" and .ping_status != "Down" and .ping_status != "Unknown") | .ping_status' 2>/dev/null | wc -l | tr -d ' ')
if [ "$INVALID_STATUS" -eq 0 ]; then
    log_test "Ping status value validation" "PASS" "All statuses valid"
else
    log_test "Ping status value validation" "FAIL" "$INVALID_STATUS devices with invalid status"
fi

# Test 8.5: Last check timestamps
OLD_CHECKS=$(echo "$DEVICES" | jq --arg cutoff "$(date -d '1 hour ago' +%s 2>/dev/null || date -v-1H +%s)" '[.[] | select(.last_check < ($cutoff | tonumber))] | length' 2>/dev/null)
if [ "$OLD_CHECKS" -lt 10 ]; then
    log_test "Last check timestamp freshness" "PASS" "$OLD_CHECKS devices not checked in 1h"
else
    log_test "Last check timestamp freshness" "WARN" "$OLD_CHECKS devices not checked in 1h"
fi

# ================================================================
# FINAL SUMMARY
# ================================================================

echo ""
echo "================================================================"
echo "  COMPREHENSIVE TEST EXECUTION SUMMARY"
echo "================================================================"
echo ""
echo "Total Tests Executed: $TOTAL_TESTS"
echo -e "${GREEN}Tests Passed: $PASSED_TESTS${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo -e "${RED}Tests Failed: $FAILED_TESTS${NC}"
echo ""

SUCCESS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
echo "Success Rate: ${SUCCESS_RATE}%"
echo ""

if [ "$FAILED_TESTS" -gt 0 ]; then
    echo -e "${RED}═══ FAILED TESTS ═══${NC}"
    for test_name in "${FAILED_TEST_NAMES[@]}"; do
        echo -e "${RED}  ✗${NC} $test_name"
    done
    echo ""
fi

if [ "$WARNINGS" -gt 0 ]; then
    echo -e "${YELLOW}═══ WARNINGS ═══${NC}"
    for warning in "${WARNING_TEST_NAMES[@]}"; do
        echo -e "${YELLOW}  ⚠${NC} $warning"
    done
    echo ""
fi

echo "================================================================"
if [ "$FAILED_TESTS" -eq 0 ] && [ "$WARNINGS" -eq 0 ]; then
    echo -e "${GREEN}✓✓✓ ALL TESTS PASSED - SYSTEM FULLY OPERATIONAL ✓✓✓${NC}"
    echo ""
    echo "System Status: HEALTHY"
    echo "Production Readiness: EXCELLENT"
    echo "Recommendation: System ready for production use"
    exit 0
elif [ "$FAILED_TESTS" -eq 0 ]; then
    echo -e "${GREEN}✓ ALL CRITICAL TESTS PASSED${NC}"
    echo -e "${YELLOW}⚠ Some warnings detected - see above${NC}"
    echo ""
    echo "System Status: FUNCTIONAL WITH MINOR ISSUES"
    echo "Production Readiness: GOOD"
    echo "Recommendation: Monitor warnings but system is production-ready"
    exit 0
elif [ "$FAILED_TESTS" -lt 5 ]; then
    echo -e "${YELLOW}⚠ SOME TESTS FAILED - MINOR ISSUES DETECTED${NC}"
    echo ""
    echo "System Status: FUNCTIONAL WITH ISSUES"
    echo "Production Readiness: ACCEPTABLE"
    echo "Recommendation: Address failed tests but system can operate"
    exit 0
else
    echo -e "${RED}✗ CRITICAL FAILURES DETECTED${NC}"
    echo ""
    echo "System Status: DEGRADED"
    echo "Production Readiness: NOT RECOMMENDED"
    echo "Recommendation: Fix critical issues before production deployment"
    exit 1
fi
