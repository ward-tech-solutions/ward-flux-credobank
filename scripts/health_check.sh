#!/bin/bash
# ==================================================
# WARD FLUX - Docker Services Health Check
# ==================================================
# Checks health status of all Docker services and
# provides detailed diagnostics

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
API_URL="http://localhost:5001"
GRAFANA_URL="http://localhost:3000"
VICTORIA_URL="http://localhost:8428"

# Functions
print_header() {
    echo -e "${BLUE}${NC}"
    echo -e "${BLUE}  WARD FLUX - Health Check Report${NC}"
    echo -e "${BLUE}  $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo -e "${BLUE}${NC}"
    echo ""
}

print_service() {
    local service=$1
    local status=$2
    local details=$3

    if [ "$status" = "healthy" ] || [ "$status" = "running" ]; then
        echo -e "${GREEN}${NC} $service: ${GREEN}$status${NC} $details"
    elif [ "$status" = "unhealthy" ]; then
        echo -e "${RED}${NC} $service: ${RED}$status${NC} $details"
    else
        echo -e "${YELLOW} ${NC} $service: ${YELLOW}$status${NC} $details"
    fi
}

check_http() {
    local url=$1
    local timeout=${2:-5}

    if curl -sf --max-time $timeout "$url" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Main health check
print_header

# 1. Check Docker
echo -e "${BLUE}[1/8]${NC} Checking Docker..."
if command -v docker &> /dev/null; then
    if docker ps &> /dev/null; then
        print_service "Docker Engine" "running" ""
    else
        print_service "Docker Engine" "error" "(not responding)"
        exit 1
    fi
else
    print_service "Docker" "not found" "(install Docker first)"
    exit 1
fi

# 2. Check PostgreSQL
echo -e "${BLUE}[2/8]${NC} Checking PostgreSQL..."
POSTGRES_STATUS=$(docker inspect ward-postgres --format='{{.State.Health.Status}}' 2>/dev/null || echo "not running")
if [ "$POSTGRES_STATUS" = "healthy" ]; then
    # Check connection
    if docker exec ward-postgres pg_isready -U ward &> /dev/null; then
        print_service "PostgreSQL" "healthy" "(accepting connections)"
    else
        print_service "PostgreSQL" "unhealthy" "(not accepting connections)"
    fi
else
    print_service "PostgreSQL" "$POSTGRES_STATUS" ""
fi

# 3. Check Redis
echo -e "${BLUE}[3/8]${NC} Checking Redis..."
REDIS_STATUS=$(docker inspect ward-redis --format='{{.State.Health.Status}}' 2>/dev/null || echo "not running")
if [ "$REDIS_STATUS" = "healthy" ]; then
    # Check connection
    REDIS_PING=$(docker exec ward-redis redis-cli --raw incr ping 2>/dev/null || echo "FAIL")
    if [ "$REDIS_PING" != "FAIL" ]; then
        print_service "Redis" "healthy" "(responding to commands)"
    else
        print_service "Redis" "unhealthy" "(not responding)"
    fi
else
    print_service "Redis" "$REDIS_STATUS" ""
fi

# 4. Check VictoriaMetrics
echo -e "${BLUE}[4/8]${NC} Checking VictoriaMetrics..."
VICTORIA_STATUS=$(docker inspect ward-victoriametrics --format='{{.State.Health.Status}}' 2>/dev/null || echo "not running")
if [ "$VICTORIA_STATUS" = "healthy" ]; then
    if check_http "$VICTORIA_URL/health"; then
        print_service "VictoriaMetrics" "healthy" "(API responding)"
    else
        print_service "VictoriaMetrics" "unhealthy" "(API not responding)"
    fi
else
    print_service "VictoriaMetrics" "$VICTORIA_STATUS" ""
fi

# 5. Check API Server
echo -e "${BLUE}[5/8]${NC} Checking API Server..."
API_STATUS=$(docker inspect ward-api --format='{{.State.Health.Status}}' 2>/dev/null || echo "not running")
if [ "$API_STATUS" = "healthy" ]; then
    if check_http "$API_URL/api/v1/health"; then
        # Get detailed health info
        HEALTH_JSON=$(curl -s "$API_URL/api/v1/health")
        print_service "API Server" "healthy" "(all systems operational)"
    else
        print_service "API Server" "unhealthy" "(health endpoint failed)"
    fi
else
    print_service "API Server" "$API_STATUS" ""
fi

# 6. Check Celery Worker
echo -e "${BLUE}[6/8]${NC} Checking Celery Worker..."
WORKER_STATUS=$(docker inspect ward-celery-worker --format='{{.State.Status}}' 2>/dev/null || echo "not running")
if [ "$WORKER_STATUS" = "running" ]; then
    # Check worker stats
    WORKER_STATS=$(docker exec ward-celery-worker celery -A celery_app inspect stats 2>/dev/null || echo "{}")
    if [ "$WORKER_STATS" != "{}" ]; then
        print_service "Celery Worker" "running" "(processing tasks)"
    else
        print_service "Celery Worker" "running" "(no active workers)"
    fi
else
    print_service "Celery Worker" "$WORKER_STATUS" ""
fi

# 7. Check Celery Beat
echo -e "${BLUE}[7/8]${NC} Checking Celery Beat..."
BEAT_STATUS=$(docker inspect ward-celery-beat --format='{{.State.Status}}' 2>/dev/null || echo "not running")
if [ "$BEAT_STATUS" = "running" ]; then
    print_service "Celery Beat" "running" "(scheduler active)"
else
    print_service "Celery Beat" "$BEAT_STATUS" ""
fi

# 8. Check Grafana
echo -e "${BLUE}[8/8]${NC} Checking Grafana..."
GRAFANA_STATUS=$(docker inspect ward-grafana --format='{{.State.Status}}' 2>/dev/null || echo "not running")
if [ "$GRAFANA_STATUS" = "running" ]; then
    if check_http "$GRAFANA_URL/api/health"; then
        print_service "Grafana" "running" "(dashboard available)"
    else
        print_service "Grafana" "running" "(dashboard not ready)"
    fi
else
    print_service "Grafana" "$GRAFANA_STATUS" ""
fi

# Resource usage summary
echo ""
echo -e "${BLUE}${NC}"
echo -e "${BLUE}  Resource Usage${NC}"
echo -e "${BLUE}${NC}"

docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
    ward-postgres ward-redis ward-victoriametrics ward-api ward-celery-worker ward-celery-beat ward-grafana 2>/dev/null || \
    echo "Unable to retrieve container stats"

# Disk usage
echo ""
echo -e "${BLUE}${NC}"
echo -e "${BLUE}  Docker Disk Usage${NC}"
echo -e "${BLUE}${NC}"
docker system df

# Network connectivity
echo ""
echo -e "${BLUE}${NC}"
echo -e "${BLUE}  Network Connectivity${NC}"
echo -e "${BLUE}${NC}"

# Check if ward-network exists
if docker network inspect ward-network &> /dev/null; then
    print_service "Docker Network" "running" "(ward-network active)"

    # List connected containers
    CONNECTED=$(docker network inspect ward-network --format='{{range .Containers}}{{.Name}} {{end}}' 2>/dev/null)
    echo -e "  Connected: $CONNECTED"
else
    print_service "Docker Network" "not found" "(ward-network missing)"
fi

# Volume status
echo ""
echo -e "${BLUE}${NC}"
echo -e "${BLUE}  Persistent Volumes${NC}"
echo -e "${BLUE}${NC}"

for volume in ward-postgres-data ward-redis-data ward-victoria-data ward-grafana-data; do
    if docker volume inspect "$volume" &> /dev/null; then
        SIZE=$(docker volume inspect "$volume" --format='{{.Mountpoint}}' | xargs du -sh 2>/dev/null | cut -f1)
        print_service "$volume" "exists" "($SIZE)"
    else
        print_service "$volume" "not found" ""
    fi
done

# Recent logs check
echo ""
echo -e "${BLUE}${NC}"
echo -e "${BLUE}  Recent Errors (Last 10 minutes)${NC}"
echo -e "${BLUE}${NC}"

ERROR_COUNT=$(docker-compose logs --since 10m 2>/dev/null | grep -i "error\|exception\|failed" | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    print_service "Error Logs" "clean" "(no errors in last 10 minutes)"
else
    print_service "Error Logs" "warnings" "($ERROR_COUNT errors found)"
    echo ""
    echo "Recent errors:"
    docker-compose logs --since 10m 2>/dev/null | grep -i "error\|exception\|failed" | tail -5
fi

# Summary
echo ""
echo -e "${BLUE}${NC}"
echo -e "${BLUE}  Quick Actions${NC}"
echo -e "${BLUE}${NC}"
echo ""
echo "View logs:         docker-compose logs -f [service-name]"
echo "Restart service:   docker-compose restart [service-name]"
echo "Restart all:       docker-compose restart"
echo "View API docs:     $API_URL/docs"
echo "View Grafana:      $GRAFANA_URL"
echo ""
echo -e "${BLUE}${NC}"
echo ""
