#!/usr/bin/env bash
#
# CredoBank WARD OPS - Deployment Verification Script
# Verifies that all services are running correctly
#
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="${INSTALL_DIR:-/opt/wardops}"
FAILED_CHECKS=0

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    ((FAILED_CHECKS++))
}

check_docker() {
    log_info "Checking Docker..."
    if command -v docker &> /dev/null; then
        log_success "Docker is installed: $(docker --version)"
    else
        log_error "Docker is not installed"
    fi
}

check_compose() {
    log_info "Checking Docker Compose..."
    if docker compose version &> /dev/null; then
        log_success "Docker Compose is installed: $(docker compose version)"
    else
        log_error "Docker Compose is not installed"
    fi
}

check_installation_dir() {
    log_info "Checking installation directory..."
    if [[ -d "${INSTALL_DIR}" ]]; then
        log_success "Installation directory exists: ${INSTALL_DIR}"
    else
        log_error "Installation directory not found: ${INSTALL_DIR}"
        return
    fi

    # Check for required files
    if [[ -f "${INSTALL_DIR}/docker-compose.yml" ]]; then
        log_success "docker-compose.yml found"
    else
        log_error "docker-compose.yml not found"
    fi

    if [[ -f "${INSTALL_DIR}/.env.prod" ]]; then
        log_success ".env.prod found"
    else
        log_warning ".env.prod not found (required for deployment)"
    fi
}

check_services() {
    log_info "Checking service status..."
    cd "${INSTALL_DIR}"

    local services=("db" "redis" "api" "celery-worker" "celery-beat")

    for service in "${services[@]}"; do
        if docker compose ps | grep -q "${service}.*Up"; then
            log_success "Service '${service}' is running"
        else
            log_error "Service '${service}' is not running"
        fi
    done
}

check_health() {
    log_info "Checking service health..."
    cd "${INSTALL_DIR}"

    # Check database health
    if docker compose exec -T db pg_isready -U fluxdb &> /dev/null; then
        log_success "Database is healthy"
    else
        log_error "Database is not healthy"
    fi

    # Check Redis health
    if docker compose exec -T redis redis-cli ping &> /dev/null 2>&1 || \
       docker compose exec -T redis redis-cli --raw incr ping &> /dev/null; then
        log_success "Redis is healthy"
    else
        log_error "Redis is not healthy"
    fi

    # Check API health
    sleep 2  # Give API a moment
    if curl -f -s http://localhost:5001/api/v1/health > /dev/null; then
        log_success "API is healthy"

        # Show API response
        local api_response=$(curl -s http://localhost:5001/api/v1/health)
        echo "    Response: ${api_response}"
    else
        log_error "API is not responding at http://localhost:5001/api/v1/health"
    fi
}

check_ports() {
    log_info "Checking port availability..."

    if netstat -tuln 2>/dev/null | grep -q ":5001" || ss -tuln 2>/dev/null | grep -q ":5001"; then
        log_success "API port 5001 is listening"
    else
        log_error "API port 5001 is not listening"
    fi

    if netstat -tuln 2>/dev/null | grep -q ":5432" || ss -tuln 2>/dev/null | grep -q ":5432"; then
        log_success "Database port 5432 is listening"
    else
        log_warning "Database port 5432 is not exposed (this is OK if not needed)"
    fi
}

check_logs() {
    log_info "Checking for errors in recent logs..."
    cd "${INSTALL_DIR}"

    local error_count=$(docker compose logs --tail=100 2>&1 | grep -i "error\|exception\|failed" | wc -l)

    if [[ $error_count -eq 0 ]]; then
        log_success "No errors found in recent logs"
    else
        log_warning "Found ${error_count} error/exception messages in logs"
        echo "    Run 'docker compose logs -f' to investigate"
    fi
}

check_disk_space() {
    log_info "Checking disk space..."

    local available=$(df -h "${INSTALL_DIR}" | awk 'NR==2 {print $4}')
    local used_percent=$(df -h "${INSTALL_DIR}" | awk 'NR==2 {print $5}' | tr -d '%')

    if [[ $used_percent -lt 90 ]]; then
        log_success "Disk space OK: ${available} available (${used_percent}% used)"
    else
        log_warning "Disk space low: ${available} available (${used_percent}% used)"
    fi
}

check_database_connection() {
    log_info "Checking database connection and tables..."
    cd "${INSTALL_DIR}"

    # Count tables
    local table_count=$(docker compose exec -T db psql -U fluxdb -d ward_ops -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo "0")

    if [[ $table_count -gt 0 ]]; then
        log_success "Database has ${table_count} tables"
    else
        log_error "Database appears empty or inaccessible"
    fi
}

show_summary() {
    echo ""
    echo "======================================================================"
    if [[ $FAILED_CHECKS -eq 0 ]]; then
        echo -e "${GREEN}  ✓ All Checks Passed!${NC}"
        echo "======================================================================"
        echo ""
        echo "Your WARD OPS deployment is healthy and ready to use."
        echo ""
        echo "Access the application:"
        echo "  Web UI:  http://$(hostname -I | awk '{print $1}'):3000"
        echo "  API:     http://$(hostname -I | awk '{print $1}'):5001"
        echo ""
    else
        echo -e "${RED}  ✗ ${FAILED_CHECKS} Check(s) Failed${NC}"
        echo "======================================================================"
        echo ""
        echo "Some checks did not pass. Please review the errors above."
        echo ""
        echo "Common troubleshooting steps:"
        echo "  1. Check logs:    cd ${INSTALL_DIR} && docker compose logs -f"
        echo "  2. Restart:       cd ${INSTALL_DIR} && docker compose restart"
        echo "  3. Check status:  cd ${INSTALL_DIR} && docker compose ps"
        echo ""
    fi
    echo "======================================================================"
    echo ""
}

main() {
    echo ""
    echo "======================================================================"
    echo "         CredoBank WARD OPS - Deployment Verification"
    echo "======================================================================"
    echo ""

    check_docker
    check_compose
    check_installation_dir

    if [[ -d "${INSTALL_DIR}" ]]; then
        check_services
        check_health
        check_ports
        check_database_connection
        check_logs
        check_disk_space
    fi

    show_summary

    exit $FAILED_CHECKS
}

main "$@"
