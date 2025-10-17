# Deploy to CredoBank Server - EXACT Copy of Local Setup

This will deploy the **EXACT** same Docker setup that's currently running locally.

## Current Local Setup (Running Now)

```
wardops-api-prod        → Port 5001
wardops-worker-prod     → 60 workers
wardops-beat-prod       → Scheduler
wardops-postgres-prod   → Port 5432 (875 devices, 128 branches)
wardops-redis-prod      → Port 6379
```

## Server Requirements

- **Ubuntu 24.04 LTS**
- **Docker & Docker Compose installed**
- **Ports available**: 5001, 5432, 6379

---

## 🚀 Deployment Steps

### Step 1: Install Docker (on CredoBank server)

```bash
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker

# Allow your user to run docker without sudo (optional)
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect
```

### Step 2: Transfer Files to Server

**Option A: Via Git (Recommended)**
```bash
# On CredoBank server
git clone https://github.com/ward-tech-solutions/ward-flux-credobank.git ward-ops
cd ward-ops
```

**Option B: Via SCP (if you prefer local files)**
```bash
# On your local machine
cd "/Users/g.jalabadze/Desktop/WARD OPS/CredoBranches"
tar -czf wardops-deploy.tar.gz \
  docker-compose.production-local.yml \
  Dockerfile \
  .dockerignore \
  routers/ \
  monitoring/ \
  frontend/ \
  seeds/ \
  scripts/ \
  migrations/ \
  requirements.txt \
  celery_app.py \
  main.py \
  models.py \
  database.py

# Copy to server (replace USER and SERVER_IP)
scp wardops-deploy.tar.gz user@SERVER_IP:/tmp/

# On CredoBank server
cd ~
mkdir -p ward-ops
cd ward-ops
tar -xzf /tmp/wardops-deploy.tar.gz
```

### Step 3: Create Environment File

```bash
# On CredoBank server
cd ward-ops
cat > .env << 'EOF'
# Database Configuration
DATABASE_URL=postgresql://ward_admin:ward_admin_password@postgres:5432/ward_ops

# Redis Configuration
REDIS_URL=redis://:redispass@redis:6379/0

# Security & Encryption
SECRET_KEY=local-prod-test-secret-key-change-me
ENCRYPTION_KEY=T8gn87i4YOSDqxFG2_Cx9U1UXzuZuPhwfXdE_wqBBY8=

# Admin Configuration
DEFAULT_ADMIN_PASSWORD=admin123

# Application Settings
ENVIRONMENT=production
MONITORING_MODE=snmp_only
API_HOST=0.0.0.0
API_PORT=5001
LOG_LEVEL=INFO

# Celery Worker Configuration
CELERY_WORKER_CONCURRENCY=60

# SNMP Polling Configuration
SNMP_TIMEOUT=5
SNMP_RETRIES=3
SNMP_MAX_BULK_SIZE=25
EOF
```

### Step 4: Deploy!

```bash
# On CredoBank server
cd ward-ops

# Pull images and build
sudo docker-compose -f docker-compose.production-local.yml pull postgres redis
sudo docker-compose -f docker-compose.production-local.yml build

# Start everything
sudo docker-compose -f docker-compose.production-local.yml up -d

# Watch logs (Ctrl+C to exit)
sudo docker-compose -f docker-compose.production-local.yml logs -f
```

### Step 5: Verify Deployment

```bash
# Check all containers are running
sudo docker ps

# Should see:
# - wardops-postgres-prod (healthy)
# - wardops-redis-prod (healthy)
# - wardops-api-prod
# - wardops-worker-prod
# - wardops-beat-prod

# Check API health
curl http://localhost:5001/api/v1/health

# Check logs
sudo docker-compose -f docker-compose.production-local.yml logs api
```

### Step 6: Access the System

- **URL**: `http://SERVER_IP:5001`
- **Username**: `admin`
- **Password**: `admin123`

---

## 📊 System Will Automatically:

✅ Create PostgreSQL database with 875 devices across 128 branches
✅ Start Redis cache
✅ Seed all CredoBank data (branches, devices, infrastructure)
✅ Start SNMP monitoring with 60 concurrent workers
✅ Start Celery Beat scheduler for periodic tasks
✅ Begin monitoring all devices

---

## 🔧 Management Commands

### View Logs
```bash
cd ward-ops

# All services
sudo docker-compose -f docker-compose.production-local.yml logs -f

# Specific service
sudo docker-compose -f docker-compose.production-local.yml logs -f api
sudo docker-compose -f docker-compose.production-local.yml logs -f celery-worker
sudo docker-compose -f docker-compose.production-local.yml logs -f postgres
```

### Restart Services
```bash
# Restart all
sudo docker-compose -f docker-compose.production-local.yml restart

# Restart specific service
sudo docker-compose -f docker-compose.production-local.yml restart api
sudo docker-compose -f docker-compose.production-local.yml restart celery-worker
```

### Stop/Start
```bash
# Stop all (data is preserved)
sudo docker-compose -f docker-compose.production-local.yml down

# Start again
sudo docker-compose -f docker-compose.production-local.yml up -d

# Stop and REMOVE all data (⚠️ WARNING: Deletes database!)
sudo docker-compose -f docker-compose.production-local.yml down -v
```

### Update Deployment
```bash
cd ward-ops
git pull origin main  # If using git
sudo docker-compose -f docker-compose.production-local.yml down
sudo docker-compose -f docker-compose.production-local.yml build
sudo docker-compose -f docker-compose.production-local.yml up -d
```

### Database Access
```bash
# Connect to PostgreSQL
sudo docker exec -it wardops-postgres-prod psql -U ward_admin -d ward_ops

# Backup database
sudo docker exec wardops-postgres-prod pg_dump -U ward_admin ward_ops > backup-$(date +%Y%m%d).sql

# Restore database
cat backup.sql | sudo docker exec -i wardops-postgres-prod psql -U ward_admin ward_ops
```

---

## 🔒 Security Notes

1. **Firewall**: Only expose port 5001
   ```bash
   sudo ufw allow 5001/tcp
   sudo ufw enable
   ```

2. **Change Default Password**: After first login, change admin password in UI

3. **HTTPS**: For production, set up Nginx reverse proxy with SSL:
   ```bash
   sudo apt install nginx certbot python3-certbot-nginx
   # Configure Nginx to proxy port 5001
   # Get SSL cert: sudo certbot --nginx -d your-domain.com
   ```

---

## 🎯 This Deployment Matches Your Local Setup EXACTLY

Same containers, same ports, same configuration, same data!
