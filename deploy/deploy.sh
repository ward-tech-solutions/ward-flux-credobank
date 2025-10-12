#!/usr/bin/env bash
#
# CredoBank WARD OPS - One-Command Deployment Script
# This script automates the deployment of the WARD OPS monitoring platform
#
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/wardops"
ENV_FILE="${INSTALL_DIR}/.env.prod"
COMPOSE_FILE="${INSTALL_DIR}/docker-compose.yml"
REGISTRY_URL="${REGISTRY_URL:-docker.io}"
APP_IMAGE="${APP_IMAGE:-ward_flux/wardops-app:credobank-latest}"
DB_IMAGE="${DB_IMAGE:-ward_flux/wardops-postgres-seeded:credobank-latest}"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

generate_secret() {
    python3 - <<'PY'
import secrets, base64
print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
PY
}

generate_fernet_key() {
    python3 - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if running as root or with sudo
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run with sudo or as root"
        exit 1
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/engine/install/"
        exit 1
    fi

    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose plugin is not installed."
        exit 1
    fi

    # Check Python3
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 is required for secret generation"
        exit 1
    fi

    log_success "All prerequisites met"
}

setup_directories() {
    log_info "Setting up directories..."

    mkdir -p "${INSTALL_DIR}"
    mkdir -p "${INSTALL_DIR}/logs"
    mkdir -p "${INSTALL_DIR}/backups"

    log_success "Directories created"
}

generate_env_file() {
    log_info "Generating environment configuration..."

    if [[ -f "${ENV_FILE}" ]]; then
        log_warning "Environment file already exists at ${ENV_FILE}"
        read -p "Do you want to regenerate it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Keeping existing environment file"
            return
        fi
        # Backup existing file
        cp "${ENV_FILE}" "${ENV_FILE}.backup.$(date +%Y%m%d-%H%M%S)"
    fi

    log_info "Generating secure random secrets..."
    SECRET_KEY=$(generate_secret)
    ENCRYPTION_KEY=$(generate_fernet_key)
    REDIS_PASSWORD=$(openssl rand -base64 24)

    # Ask for admin password
    read -sp "Enter admin password (default: admin123): " ADMIN_PASSWORD
    echo
    ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin123}

    cat > "${ENV_FILE}" <<EOF
# CredoBank WARD OPS - Production Configuration
# Generated: $(date)

# Database Configuration
DATABASE_URL=postgresql://fluxdb:FluxDB@db:5432/ward_ops

# Redis Configuration
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
REDIS_PASSWORD=${REDIS_PASSWORD}

# Security Keys (DO NOT SHARE)
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# Admin Credentials
DEFAULT_ADMIN_PASSWORD=${ADMIN_PASSWORD}

# Application Settings
LOG_LEVEL=INFO
MONITORING_MODE=hybrid
CORS_ORIGINS=*

# Optional: VictoriaMetrics (uncomment if needed)
# VICTORIA_URL=http://victoriametrics:8428

# Optional: Zabbix Integration (configure via UI after deployment)
# ZABBIX_URL=
# ZABBIX_USER=
# ZABBIX_PASSWORD=
EOF

    chmod 600 "${ENV_FILE}"
    log_success "Environment file created at ${ENV_FILE}"
    log_warning "IMPORTANT: Backup this file securely - it contains sensitive credentials"
}

copy_compose_file() {
    log_info "Copying docker-compose configuration..."

    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

    if [[ -f "${SCRIPT_DIR}/docker-compose.yml" ]]; then
        cp "${SCRIPT_DIR}/docker-compose.yml" "${COMPOSE_FILE}"
        log_success "Docker Compose file copied"
    else
        log_error "docker-compose.yml not found in ${SCRIPT_DIR}"
        exit 1
    fi
}

docker_login() {
    log_info "Logging into Docker registry..."

    if [[ "${REGISTRY_URL}" != "docker.io" ]]; then
        read -p "Registry username: " REGISTRY_USER
        read -sp "Registry password: " REGISTRY_PASS
        echo

        echo "${REGISTRY_PASS}" | docker login "${REGISTRY_URL}" --username "${REGISTRY_USER}" --password-stdin
        log_success "Logged into registry"
    else
        log_info "Using Docker Hub - no login required for public images"
    fi
}

pull_images() {
    log_info "Pulling Docker images..."
    log_info "This may take several minutes depending on your connection..."

    docker pull "${APP_IMAGE}"
    docker pull "${DB_IMAGE}"
    docker pull redis:7-alpine

    log_success "All images pulled successfully"
}

start_services() {
    log_info "Starting services..."

    cd "${INSTALL_DIR}"

    # Start services
    docker compose up -d

    log_info "Waiting for services to be healthy..."
    sleep 10

    # Check health
    if docker compose ps | grep -q "unhealthy"; then
        log_warning "Some services are unhealthy. Checking logs..."
        docker compose ps
    else
        log_success "All services started successfully"
    fi
}

show_summary() {
    echo ""
    echo "======================================================================"
    echo -e "${GREEN}  CredoBank WARD OPS - Deployment Complete!${NC}"
    echo "======================================================================"
    echo ""
    echo "Services are now running:"
    echo ""
    echo "  API:        http://$(hostname -I | awk '{print $1}'):5001"
    echo "  Frontend:   http://$(hostname -I | awk '{print $1}'):3000"
    echo "  Health:     http://$(hostname -I | awk '{print $1}'):5001/api/v1/health"
    echo ""
    echo "Default Credentials:"
    echo "  Username: admin"
    echo "  Password: ${ADMIN_PASSWORD:-admin123}"
    echo ""
    echo "IMPORTANT: Change the admin password immediately after first login!"
    echo ""
    echo "Useful Commands:"
    echo "  View logs:        cd ${INSTALL_DIR} && docker compose logs -f"
    echo "  Restart:          cd ${INSTALL_DIR} && docker compose restart"
    echo "  Stop:             cd ${INSTALL_DIR} && docker compose down"
    echo "  Update:           cd ${INSTALL_DIR} && docker compose pull && docker compose up -d"
    echo ""
    echo "Configuration:"
    echo "  Install dir:      ${INSTALL_DIR}"
    echo "  Environment:      ${ENV_FILE}"
    echo "  Docker Compose:   ${COMPOSE_FILE}"
    echo ""
    echo "======================================================================"
    echo ""
}

enable_systemd() {
    log_info "Setting up systemd service for auto-start..."

    cat > /etc/systemd/system/wardops.service <<EOF
[Unit]
Description=WARD OPS Monitoring Stack
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${INSTALL_DIR}
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable wardops.service

    log_success "Systemd service enabled - will auto-start on boot"
}

# Main deployment flow
main() {
    echo ""
    echo "======================================================================"
    echo "         CredoBank WARD OPS - Automated Deployment"
    echo "======================================================================"
    echo ""

    check_prerequisites
    setup_directories
    generate_env_file
    copy_compose_file
    docker_login
    pull_images
    start_services

    # Ask about systemd
    read -p "Enable auto-start on boot? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        enable_systemd
    fi

    show_summary

    log_success "Deployment complete!"
}

# Run main function
main "$@"
