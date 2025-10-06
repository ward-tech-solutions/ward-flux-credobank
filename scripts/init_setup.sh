#!/bin/bash
# ==================================================
# WARD FLUX - First-Time Setup Script
# ==================================================
# This script initializes the database and creates
# the initial admin user for WARD FLUX.

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}${NC}"
    echo -e "${BLUE}  WARD FLUX - Initial Setup${NC}"
    echo -e "${BLUE}${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}${NC} $1"
}

print_error() {
    echo -e "${RED}${NC} $1"
}

print_warning() {
    echo -e "${YELLOW} ${NC} $1"
}

print_info() {
    echo -e "${BLUE}9${NC} $1"
}

# Main setup
print_header

# Step 1: Check if running in Docker
if [ -f /.dockerenv ]; then
    print_info "Running inside Docker container"
    DOCKER_MODE=true
else
    print_info "Running in local environment"
    DOCKER_MODE=false
fi

# Step 2: Check environment variables
print_info "Checking environment configuration..."

if [ -z "$DATABASE_URL" ]; then
    print_warning "DATABASE_URL not set, using default SQLite"
    export DATABASE_URL="sqlite:///./data/ward_ops.db"
fi

if [ -z "$ENCRYPTION_KEY" ]; then
    print_error "ENCRYPTION_KEY not set in environment!"
    print_info "Generate one with: python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    exit 1
fi

if [ -z "$SECRET_KEY" ]; then
    print_error "SECRET_KEY not set in environment!"
    print_info "Generate one with: openssl rand -base64 32"
    exit 1
fi

print_success "Environment variables validated"

# Step 3: Initialize database
print_info "Initializing database schema..."

python3 -c "
from database import init_db
try:
    init_db()
    print(' Database initialized successfully')
except Exception as e:
    print(f' Database initialization failed: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    print_success "Database schema created"
else
    print_error "Database initialization failed"
    exit 1
fi

# Step 4: Create admin user
print_info "Creating admin user..."

# Prompt for admin credentials
read -p "Enter admin username [admin]: " ADMIN_USERNAME
ADMIN_USERNAME=${ADMIN_USERNAME:-admin}

read -p "Enter admin email [admin@wardflux.local]: " ADMIN_EMAIL
ADMIN_EMAIL=${ADMIN_EMAIL:-admin@wardflux.local}

read -p "Enter admin full name [System Administrator]: " ADMIN_FULLNAME
ADMIN_FULLNAME=${ADMIN_FULLNAME:-System Administrator}

# Password with confirmation
while true; do
    read -sp "Enter admin password: " ADMIN_PASSWORD
    echo ""
    read -sp "Confirm admin password: " ADMIN_PASSWORD2
    echo ""

    if [ "$ADMIN_PASSWORD" = "$ADMIN_PASSWORD2" ]; then
        if [ ${#ADMIN_PASSWORD} -lt 8 ]; then
            print_error "Password must be at least 8 characters"
            continue
        fi
        break
    else
        print_error "Passwords do not match, try again"
    fi
done

# Create admin user in database
python3 -c "
import sys
from database import SessionLocal, User, UserRole
from auth import get_password_hash
from datetime import datetime

db = SessionLocal()
try:
    # Check if admin already exists
    existing = db.query(User).filter_by(username='$ADMIN_USERNAME').first()
    if existing:
        print(' User \"$ADMIN_USERNAME\" already exists')
        sys.exit(1)

    # Create admin user
    admin = User(
        username='$ADMIN_USERNAME',
        email='$ADMIN_EMAIL',
        full_name='$ADMIN_FULLNAME',
        hashed_password=get_password_hash('$ADMIN_PASSWORD'),
        role=UserRole.ADMIN,
        is_superuser=True,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.add(admin)
    db.commit()
    print(' Admin user created successfully')
    sys.exit(0)
except Exception as e:
    print(f' Failed to create admin user: {e}')
    db.rollback()
    sys.exit(1)
finally:
    db.close()
"

if [ $? -eq 0 ]; then
    print_success "Admin user created: $ADMIN_USERNAME"
else
    print_error "Failed to create admin user"
    exit 1
fi

# Step 5: Import default templates
print_info "Importing default monitoring templates..."

python3 -c "
import sys
from pathlib import Path
import json
import uuid
from database import SessionLocal
from models import MonitoringTemplate

db = SessionLocal()
try:
    templates_dir = Path(__file__).parent.parent / 'monitoring' / 'templates'
    if not templates_dir.exists():
        print('  Templates directory not found, skipping')
        sys.exit(0)

    imported = []
    for template_file in templates_dir.glob('*.json'):
        with open(template_file, 'r') as f:
            template_data = json.load(f)

        # Check if template already exists
        existing = db.query(MonitoringTemplate).filter_by(name=template_data['name']).first()
        if existing:
            continue

        new_template = MonitoringTemplate(
            id=uuid.uuid4(),
            name=template_data['name'],
            description=template_data.get('description', ''),
            vendor=template_data.get('vendor'),
            device_types=template_data.get('device_types', []),
            items=template_data.get('items', []),
            triggers=template_data.get('triggers', []),
            is_default=True
        )
        db.add(new_template)
        imported.append(template_data['name'])

    db.commit()
    print(f' Imported {len(imported)} templates')
    for name in imported:
        print(f'  - {name}')
    sys.exit(0)
except Exception as e:
    print(f' Failed to import templates: {e}')
    db.rollback()
    sys.exit(1)
finally:
    db.close()
"

if [ $? -eq 0 ]; then
    print_success "Default templates imported"
else
    print_warning "Template import failed (non-critical)"
fi

# Step 6: Create default monitoring profile
print_info "Creating default monitoring profile..."

python3 -c "
import sys
import uuid
from database import SessionLocal
from models import MonitoringProfile, MonitoringMode

db = SessionLocal()
try:
    # Check if profile already exists
    existing = db.query(MonitoringProfile).filter_by(is_active=True).first()
    if existing:
        print('  Active monitoring profile already exists')
        sys.exit(0)

    # Create STANDALONE profile
    profile = MonitoringProfile(
        id=uuid.uuid4(),
        name='Default Standalone Profile',
        mode=MonitoringMode.STANDALONE,
        polling_interval=60,
        is_active=True
    )
    db.add(profile)
    db.commit()
    print(' Default monitoring profile created (STANDALONE mode)')
    sys.exit(0)
except Exception as e:
    print(f' Failed to create monitoring profile: {e}')
    db.rollback()
    sys.exit(1)
finally:
    db.close()
"

if [ $? -eq 0 ]; then
    print_success "Default monitoring profile created"
else
    print_warning "Monitoring profile creation failed (non-critical)"
fi

# Step 7: Summary
echo ""
echo -e "${GREEN}${NC}"
echo -e "${GREEN}  Setup Complete!${NC}"
echo -e "${GREEN}${NC}"
echo ""
print_success "Database initialized"
print_success "Admin user created: $ADMIN_USERNAME"
print_success "Default templates imported"
print_success "Monitoring profile configured"
echo ""
print_info "Next steps:"
echo "  1. Start the API server: uvicorn main:app --host 0.0.0.0 --port 5001"
echo "  2. Start Celery worker: celery -A celery_app worker --loglevel=info"
echo "  3. Start Celery beat: celery -A celery_app beat --loglevel=info"
echo "  4. Access API docs: http://localhost:5001/docs"
echo "  5. Login with username: $ADMIN_USERNAME"
echo ""
print_info "Or use Docker Compose: docker-compose up -d"
echo ""
