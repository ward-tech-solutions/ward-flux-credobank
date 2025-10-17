# Deploy WARD OPS CredoBank on Ubuntu 24.04 LTS

Complete guide to deploy CredoBank monitoring tool on Ubuntu server using Docker.

## 🚀 Quick Start (5 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/ward-tech-solutions/ward-flux-credobank.git
cd ward-flux-credobank

# 2. Install Docker (if not installed)
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker

# 3. Create environment file
cp .env.example .env
nano .env  # Edit with your settings

# 4. Deploy
sudo docker-compose -f docker-compose.production-local.yml up -d

# 5. Access
# Web UI: http://YOUR_SERVER_IP:5001
# Default login: admin / admin123
```

## 📋 Detailed Installation Steps

### Step 1: Prepare Ubuntu Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y git curl wget nano

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install -y docker-compose

# Add current user to docker group (optional, to run without sudo)
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker-compose --version
```

### Step 2: Clone Repository

```bash
# Clone from GitHub (requires authentication)
git clone https://github.com/ward-tech-solutions/ward-flux-credobank.git
cd ward-flux-credobank

# Or if using SSH
git clone git@github.com:ward-tech-solutions/ward-flux-credobank.git
cd ward-flux-credobank
```

### Step 3: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Required environment variables:**

```env
# Database
DATABASE_URL=postgresql://ward_admin:CHANGE_THIS_PASSWORD@postgres:5432/ward_ops

# Redis
REDIS_URL=redis://:CHANGE_THIS_PASSWORD@redis:6379/0

# Security (IMPORTANT: Change these!)
SECRET_KEY=your-secret-key-here-change-me
ENCRYPTION_KEY=your-fernet-encryption-key-here

# Admin
DEFAULT_ADMIN_PASSWORD=CHANGE_THIS_PASSWORD

# Environment
ENVIRONMENT=production
MONITORING_MODE=snmp_only
```

**Generate secure keys:**

```bash
# Generate SECRET_KEY
python3 -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"

# Generate ENCRYPTION_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Step 4: Deploy with Docker Compose

```bash
# Build and start all services
docker-compose -f docker-compose.production-local.yml up -d --build

# Check status
docker-compose -f docker-compose.production-local.yml ps

# View logs
docker-compose -f docker-compose.production-local.yml logs -f api

# Stop services
docker-compose -f docker-compose.production-local.yml down
```

### Step 5: Verify Deployment

```bash
# Check if containers are running
docker ps

# You should see:
# - wardops-postgres-prod
# - wardops-redis-prod
# - wardops-api-prod
# - wardops-worker-prod
# - wardops-beat-prod

# Check API health
curl http://localhost:5001/api/v1/health

# Access web UI
# http://YOUR_SERVER_IP:5001
# Login: admin / admin123 (or your configured password)
```

## 🔧 Configuration

### Ports

The application uses these ports:
- **5001** - Web UI & API
- **5432** - PostgreSQL (internal)
- **6379** - Redis (internal)

### Firewall Configuration

```bash
# Allow web UI access
sudo ufw allow 5001/tcp

# If accessing from specific IP only
sudo ufw allow from YOUR_IP_ADDRESS to any port 5001

# Enable firewall
sudo ufw enable
```

### SSL/HTTPS Setup (Optional but Recommended)

```bash
# Install nginx
sudo apt install -y nginx certbot python3-certbot-nginx

# Create nginx config
sudo nano /etc/nginx/sites-available/ward-ops
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://localhost:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/ward-ops /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

## 📊 Database Seeding

The CredoBank edition automatically seeds:
- ✅ 875 devices across all branches
- ✅ 128 branches
- ✅ Georgian regions and cities
- ✅ Alert rules
- ✅ Admin user

To re-seed:
```bash
# Enter the container
docker exec -it wardops-api-prod bash

# Run seeding script
python scripts/seed_credobank.py --database-url $DATABASE_URL --seeds-dir seeds/credobank

# Exit
exit
```

## 🔄 Updates & Maintenance

### Update to Latest Version

```bash
cd ward-flux-credobank

# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.production-local.yml down
docker-compose -f docker-compose.production-local.yml up -d --build
```

### Backup Database

```bash
# Backup PostgreSQL
docker exec wardops-postgres-prod pg_dump -U ward_admin ward_ops > backup_$(date +%Y%m%d).sql

# Restore backup
cat backup_20251016.sql | docker exec -i wardops-postgres-prod psql -U ward_admin -d ward_ops
```

### View Logs

```bash
# All services
docker-compose -f docker-compose.production-local.yml logs -f

# Specific service
docker-compose -f docker-compose.production-local.yml logs -f api

# Last 100 lines
docker-compose -f docker-compose.production-local.yml logs --tail=100 api
```

### Restart Services

```bash
# Restart all
docker-compose -f docker-compose.production-local.yml restart

# Restart specific service
docker-compose -f docker-compose.production-local.yml restart api
```

## 🛠️ Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose -f docker-compose.production-local.yml logs api

# Check container status
docker ps -a

# Remove and recreate
docker-compose -f docker-compose.production-local.yml down -v
docker-compose -f docker-compose.production-local.yml up -d --build
```

### Database connection issues

```bash
# Check if PostgreSQL is running
docker exec wardops-postgres-prod pg_isready -U ward_admin

# Check database exists
docker exec -it wardops-postgres-prod psql -U ward_admin -d ward_ops -c "\dt"
```

### Port already in use

```bash
# Check what's using port 5001
sudo lsof -i :5001

# Change port in docker-compose.yml
nano docker-compose.production-local.yml
# Change "5001:5001" to "8080:5001" or any available port
```

### Reset admin password

```bash
docker exec -it wardops-api-prod bash
python -c "
from database import SessionLocal
from models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
db = SessionLocal()
admin = db.query(User).filter(User.username == 'admin').first()
admin.hashed_password = pwd_context.hash('newpassword123')
db.commit()
print('Password reset to: newpassword123')
"
exit
```

## 📈 Performance Tuning

### For Production Server

```bash
# Edit docker-compose.production-local.yml
nano docker-compose.production-local.yml
```

Recommended changes for production:

```yaml
services:
  postgres:
    command: postgres -c max_connections=200 -c shared_buffers=256MB
    
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
          
  celery-worker:
    command: celery -A celery_app worker --loglevel=info --concurrency=4
```

## 🔐 Security Checklist

- ✅ Change default admin password
- ✅ Use strong SECRET_KEY and ENCRYPTION_KEY
- ✅ Change PostgreSQL password
- ✅ Change Redis password
- ✅ Enable firewall (ufw)
- ✅ Use HTTPS/SSL
- ✅ Regular backups
- ✅ Keep system updated
- ✅ Restrict port 5432 and 6379 (only internal access)

## 📞 Support

For issues:
- Check logs: `docker-compose -f docker-compose.production-local.yml logs`
- GitHub Issues: https://github.com/ward-tech-solutions/ward-flux-credobank/issues

---

**Deployment complete!** Access your monitoring dashboard at `http://YOUR_SERVER_IP:5001` 🎉
