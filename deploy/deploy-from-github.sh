#!/usr/bin/env bash
#
# CredoBank WARD OPS - Deploy from GitHub
# This script allows deployment directly from GitHub repository
# Perfect for scenarios where you access servers via jump hosts
#
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
GITHUB_REPO="${GITHUB_REPO:-https://github.com/ward-tech-solutions/ward-flux-v2.git}"
GITHUB_BRANCH="${GITHUB_BRANCH:-client/credo-bank}"
INSTALL_DIR="/opt/wardops"
TEMP_DIR="/tmp/wardops-deploy-$$"
REGISTRY_URL="${REGISTRY_URL:-ghcr.io}"
APP_IMAGE="${APP_IMAGE:-ghcr.io/ward-tech-solutions/ward-flux-v2/credobank:latest}"
DB_IMAGE="${DB_IMAGE:-ghcr.io/ward-tech-solutions/ward-flux-v2/credobank-postgres:latest}"

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

    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run with sudo or as root"
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        echo "Run: curl -fsSL https://get.docker.com | sh"
        exit 1
    fi

    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose plugin is not installed."
        exit 1
    fi

    if ! command -v git &> /dev/null; then
        log_error "Git is not installed. Please install git."
        echo "Run: apt-get install -y git (Ubuntu/Debian) or yum install -y git (RHEL/CentOS)"
        exit 1
    fi

    if ! command -v python3 &> /dev/null; then
        log_error "Python3 is required for secret generation"
        echo "Run: apt-get install -y python3 python3-pip"
        exit 1
    fi

    # Check if cryptography module is available
    if ! python3 -c "from cryptography.fernet import Fernet" 2>/dev/null; then
        log_warning "Python cryptography module not found. Installing..."
        pip3 install cryptography || {
            log_error "Failed to install cryptography module"
            exit 1
        }
    fi

    log_success "All prerequisites met"
}

clone_repository() {
    log_info "Cloning repository from GitHub..."

    # Clean up any existing temp directory
    rm -rf "${TEMP_DIR}"
    mkdir -p "${TEMP_DIR}"

    # Clone the repository
    if git clone --branch "${GITHUB_BRANCH}" --single-branch --depth 1 "${GITHUB_REPO}" "${TEMP_DIR}"; then
        log_success "Repository cloned successfully"
    else
        log_error "Failed to clone repository from ${GITHUB_REPO}"
        log_info "Make sure:"
        log_info "  1. The repository URL is correct"
        log_info "  2. The branch '${GITHUB_BRANCH}' exists"
        log_info "  3. You have network access to GitHub"
        log_info "  4. For private repos, set up SSH keys or use HTTPS with credentials"
        exit 1
    fi

    # Check if deploy directory exists
    if [[ ! -d "${TEMP_DIR}/deploy" ]]; then
        log_error "Deploy directory not found in repository"
        exit 1
    fi

    log_success "Found deployment files"
}

setup_installation() {
    log_info "Setting up installation directory..."

    # Create installation directory
    mkdir -p "${INSTALL_DIR}"
    mkdir -p "${INSTALL_DIR}/logs"
    mkdir -p "${INSTALL_DIR}/backups"

    # Copy deployment files
    cp "${TEMP_DIR}/deploy/docker-compose.yml" "${INSTALL_DIR}/"
    cp "${TEMP_DIR}/deploy/verify.sh" "${INSTALL_DIR}/"
    chmod +x "${INSTALL_DIR}/verify.sh"

    log_success "Installation directory prepared"
}

generate_env_file() {
    log_info "Generating environment configuration..."

    ENV_FILE="${INSTALL_DIR}/.env.prod"

    if [[ -f "${ENV_FILE}" ]]; then
        log_warning "Environment file already exists at ${ENV_FILE}"
        read -p "Do you want to regenerate it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Keeping existing environment file"
            return
        fi
        cp "${ENV_FILE}" "${ENV_FILE}.backup.$(date +%Y%m%d-%H%M%S)"
    fi

    log_info "Generating secure random secrets..."
    SECRET_KEY=$(generate_secret)
    ENCRYPTION_KEY=$(generate_fernet_key)
    REDIS_PASSWORD=$(openssl rand -base64 24)

    # Ask for admin password
    echo ""
    read -sp "Enter admin password (default: admin123): " ADMIN_PASSWORD
    echo
    ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin123}

    cat > "${ENV_FILE}" <<EOF
# CredoBank WARD OPS - Production Configuration
# Generated: $(date)
# Deployed from: ${GITHUB_REPO} (${GITHUB_BRANCH})

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

# Optional: VictoriaMetrics
# VICTORIA_URL=http://victoriametrics:8428

# Optional: Zabbix Integration
# ZABBIX_URL=
# ZABBIX_USER=
# ZABBIX_PASSWORD=
EOF

    chmod 600 "${ENV_FILE}"
    log_success "Environment file created at ${ENV_FILE}"
    log_warning "IMPORTANT: This file contains sensitive credentials!"
}

docker_login() {
    log_info "Checking Docker registry access..."

    if [[ "${REGISTRY_URL}" == "ghcr.io" ]]; then
        log_info "Using GitHub Container Registry (public images)"
        log_info "No authentication required for public packages"
    elif [[ "${REGISTRY_URL}" != "docker.io" ]]; then
        log_info "Private registry detected: ${REGISTRY_URL}"

        if [[ -n "${REGISTRY_USERNAME:-}" ]] && [[ -n "${REGISTRY_PASSWORD:-}" ]]; then
            log_info "Using credentials from environment variables"
            echo "${REGISTRY_PASSWORD}" | docker login "${REGISTRY_URL}" --username "${REGISTRY_USERNAME}" --password-stdin
        else
            read -p "Registry username: " REGISTRY_USER
            read -sp "Registry password: " REGISTRY_PASS
            echo
            echo "${REGISTRY_PASS}" | docker login "${REGISTRY_URL}" --username "${REGISTRY_USER}" --password-stdin
        fi
        log_success "Logged into registry"
    else
        log_info "Using Docker Hub (public images)"
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
    docker compose up -d

    log_info "Waiting for services to initialize..."
    sleep 15

    log_success "Services started"
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

    log_success "Systemd service enabled"
}

cleanup() {
    log_info "Cleaning up temporary files..."
    rm -rf "${TEMP_DIR}"
    log_success "Cleanup complete"
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
    echo "  Verify health:    cd ${INSTALL_DIR} && ./verify.sh"
    echo ""
    echo "Configuration:"
    echo "  Install dir:      ${INSTALL_DIR}"
    echo "  Environment:      ${INSTALL_DIR}/.env.prod"
    echo "  Deployed from:    ${GITHUB_REPO} (${GITHUB_BRANCH})"
    echo ""
    echo "======================================================================"
    echo ""
}

main() {
    echo ""
    echo "======================================================================"
    echo "    CredoBank WARD OPS - GitHub Deployment"
    echo "======================================================================"
    echo ""
    echo "Repository: ${GITHUB_REPO}"
    echo "Branch:     ${GITHUB_BRANCH}"
    echo ""

    check_prerequisites
    clone_repository
    setup_installation
    generate_env_file
    docker_login
    pull_images
    start_services

    # Ask about systemd
    echo ""
    read -p "Enable auto-start on boot? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        enable_systemd
    fi

    cleanup
    show_summary

    # Run verification
    echo ""
    read -p "Run health verification now? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        cd "${INSTALL_DIR}"
        ./verify.sh || true
    fi

    log_success "Deployment complete!"
}

# Handle script arguments
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    cat <<EOF
CredoBank WARD OPS - GitHub Deployment Script

Usage:
  sudo ./deploy-from-github.sh [OPTIONS]

Options:
  --help, -h                    Show this help message

Environment Variables:
  GITHUB_REPO                   GitHub repository URL
                                Default: https://github.com/ward-tech-solutions/ward-flux-v2.git

  GITHUB_BRANCH                 Branch to deploy from
                                Default: client/credo-bank

  REGISTRY_URL                  Docker registry URL
                                Default: ghcr.io

  REGISTRY_USERNAME             Registry username (for private registries)
  REGISTRY_PASSWORD             Registry password (for private registries)

  APP_IMAGE                     Application image name
                                Default: ghcr.io/ward-tech-solutions/ward-flux-v2/credobank:latest

  DB_IMAGE                      Database image name
                                Default: ghcr.io/ward-tech-solutions/ward-flux-v2/credobank-postgres:latest

Examples:
  # Deploy with default settings
  sudo ./deploy-from-github.sh

  # Deploy from custom repository
  sudo GITHUB_REPO=https://github.com/myorg/wardops.git ./deploy-from-github.sh

  # Deploy with private registry
  sudo REGISTRY_USERNAME=user REGISTRY_PASSWORD=pass ./deploy-from-github.sh

For more information, see the documentation at:
  ${INSTALL_DIR}/README.md (after deployment)

EOF
    exit 0
fi

# Run main function
main "$@"
