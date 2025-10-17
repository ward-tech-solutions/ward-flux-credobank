# Deploy CredoBank on Ubuntu 24.04 LTS - EXACT Copy of Local Setup

## 🚀 One-Command Deployment

This deploys the **EXACT** same Docker setup currently running locally with 875 devices and 128 branches.

### Method 1: Automated Script (Recommended)

```bash
# Clone repository
git clone https://github.com/ward-tech-solutions/ward-flux-credobank.git
cd ward-flux-credobank

# Run deployment script
./deploy-exact-copy.sh
```

**That's it!** The script will:
- ✅ Install Docker if needed
- ✅ Create production environment
- ✅ Build and start all containers
- ✅ Seed 875 devices across 128 branches
- ✅ Start SNMP monitoring

---

### Method 2: Manual Steps (3 commands)

```bash
# 1. Install Docker (if not already installed)
sudo apt update && sudo apt install -y docker.io docker-compose

# 2. Clone and deploy
git clone https://github.com/ward-tech-solutions/ward-flux-credobank.git
cd ward-flux-credobank
cp .env.production .env

# 3. Start everything
sudo docker-compose -f docker-compose.production-local.yml up -d --build
```

---

## 🎯 What Gets Deployed

Your **exact** local setup:
```
wardops-postgres-prod   → PostgreSQL with 875 devices, 128 branches
wardops-redis-prod      → Redis cache on port 6379
wardops-api-prod        → FastAPI backend on port 5001
wardops-worker-prod     → 60 concurrent SNMP workers
wardops-beat-prod       → Celery scheduler
```

## 🌐 Access

- **URL**: `http://YOUR_SERVER_IP:5001`
- **Username**: `admin`
- **Password**: `admin123`

## 📊 Useful Commands

```bash
# View all logs
sudo docker-compose -f docker-compose.production-local.yml logs -f

# View specific service logs
sudo docker-compose -f docker-compose.production-local.yml logs -f api

# Check container status
sudo docker ps

# Restart services
sudo docker-compose -f docker-compose.production-local.yml restart

# Stop (data preserved)
sudo docker-compose -f docker-compose.production-local.yml down

# Start again
sudo docker-compose -f docker-compose.production-local.yml up -d
```

## 🔄 Update Later

```bash
cd ward-flux-credobank
git pull origin main
sudo docker-compose -f docker-compose.production-local.yml down
sudo docker-compose -f docker-compose.production-local.yml up -d --build
```

## 🔒 Production Hardening (Optional)

```bash
# Enable firewall
sudo ufw allow 5001/tcp
sudo ufw enable

# For HTTPS, install Nginx reverse proxy
sudo apt install nginx certbot python3-certbot-nginx
# Configure Nginx to proxy port 5001
# Get SSL: sudo certbot --nginx -d your-domain.com
```

---

**Same containers, same ports, same data as your local setup!** 🎉

See [DEPLOY_TO_CREDOBANK_SERVER.md](DEPLOY_TO_CREDOBANK_SERVER.md) for detailed documentation.
