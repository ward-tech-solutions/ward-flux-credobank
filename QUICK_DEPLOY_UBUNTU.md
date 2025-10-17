# Deploy CredoBank on Ubuntu 24.04 LTS - Quick Guide

## 🚀 Simple 3-Step Deployment

### Step 1: Install Docker (if not already installed)

```bash
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker
```

### Step 2: Clone and Deploy

```bash
# Clone repository
git clone https://github.com/ward-tech-solutions/ward-flux-credobank.git
cd ward-flux-credobank

# Copy production environment
cp .env.production .env

# Deploy!
sudo docker-compose -f docker-compose.production-local.yml up -d --build
```

### Step 3: Access

- **URL**: `http://YOUR_SERVER_IP:5001`
- **Username**: `admin`
- **Password**: `admin123`

## ✅ That's It!

The system will automatically:
- ✅ Start PostgreSQL database
- ✅ Start Redis cache
- ✅ Seed 875 devices across 128 branches
- ✅ Start SNMP monitoring
- ✅ Start background workers

## 📊 Check Status

```bash
# View running containers
sudo docker ps

# View logs
sudo docker-compose -f docker-compose.production-local.yml logs -f api

# Restart if needed
sudo docker-compose -f docker-compose.production-local.yml restart
```

## 🔄 Update Later

```bash
cd ward-flux-credobank
git pull origin main
sudo docker-compose -f docker-compose.production-local.yml down
sudo docker-compose -f docker-compose.production-local.yml up -d --build
```

---

**Ready to monitor your CredoBank infrastructure!** 🎉
