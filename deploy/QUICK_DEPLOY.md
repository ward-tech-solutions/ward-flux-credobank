# Quick Deployment for Private Repository

Since the repository is **private**, you need to authenticate before deploying.

## Method 1: Clone and Deploy (Easiest)

### Step 1: Set up SSH key on server

```bash
# On CredoBank server
ssh-keygen -t ed25519 -C "credobank-server" -f ~/.ssh/id_ed25519 -N ""

# Display public key
cat ~/.ssh/id_ed25519.pub
```

### Step 2: Add deploy key to GitHub

1. Copy the public key from above
2. Go to: https://github.com/ward-tech-solutions/ward-flux-v2/settings/keys
3. Click "Add deploy key"
4. Paste the key
5. Give it a name: "CredoBank Server"
6. **Leave "Allow write access" unchecked** (read-only is safer)
7. Click "Add key"

### Step 3: Clone and deploy

```bash
# Clone the repository
git clone --branch client/credo-bank --single-branch \
  git@github.com:ward-tech-solutions/ward-flux-v2.git /tmp/wardops

# Run deployment script
cd /tmp/wardops/deploy
sudo ./deploy-from-github.sh
```

---

## Method 2: Manual Deployment (Full Control)

If you can't use SSH keys, deploy manually:

### Step 1: Create deployment directory

```bash
sudo mkdir -p /opt/wardops
cd /opt/wardops
```

### Step 2: Create docker-compose.yml

```bash
sudo tee docker-compose.yml > /dev/null <<'EOF'
version: "3.8"

services:
  db:
    image: ghcr.io/ward-tech-solutions/ward-flux-v2/credobank-postgres:latest
    container_name: wardops-db
    environment:
      POSTGRES_USER: fluxdb
      POSTGRES_PASSWORD: FluxDB
      POSTGRES_DB: ward_ops
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - db-data:/var/lib/postgresql/data
      - ./backups:/backups
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U fluxdb -d ward_ops"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    restart: unless-stopped
    networks:
      - wardops-network

  redis:
    image: redis:7-alpine
    container_name: wardops-redis
    command:
      - redis-server
      - --requirepass
      - ${REDIS_PASSWORD}
      - --appendonly
      - "yes"
      - --appendfsync
      - everysec
    environment:
      REDIS_PASSWORD: ${REDIS_PASSWORD}
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    networks:
      - wardops-network

  api:
    image: ghcr.io/ward-tech-solutions/ward-flux-v2/credobank:latest
    container_name: wardops-api
    env_file: .env.prod
    volumes:
      - ./logs:/app/logs
      - api-data:/data
    ports:
      - "5001:5001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - wardops-network

  celery-worker:
    image: ghcr.io/ward-tech-solutions/ward-flux-v2/credobank:latest
    container_name: wardops-worker
    env_file: .env.prod
    command:
      - celery
      - -A
      - celery_app
      - worker
      - --loglevel=info
      - --concurrency=4
      - --max-tasks-per-child=1000
    volumes:
      - ./logs:/app/logs
      - worker-data:/data
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - wardops-network
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

  celery-beat:
    image: ghcr.io/ward-tech-solutions/ward-flux-v2/credobank:latest
    container_name: wardops-beat
    env_file: .env.prod
    command:
      - celery
      - -A
      - celery_app
      - beat
      - --loglevel=info
    volumes:
      - ./logs:/app/logs
      - beat-data:/data
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - wardops-network

volumes:
  db-data:
    driver: local
  redis-data:
    driver: local
  api-data:
    driver: local
  worker-data:
    driver: local
  beat-data:
    driver: local

networks:
  wardops-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
EOF
```

### Step 3: Generate secrets

```bash
# Generate random secrets
SECRET_KEY=$(openssl rand -base64 32)
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
REDIS_PASSWORD=$(openssl rand -base64 24)
ADMIN_PASSWORD="admin123"  # Change this!
```

### Step 4: Create .env.prod

```bash
sudo tee .env.prod > /dev/null <<EOF
# Database Configuration
DATABASE_URL=postgresql://fluxdb:FluxDB@db:5432/ward_ops

# Redis Configuration
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
REDIS_PASSWORD=${REDIS_PASSWORD}

# Security Keys
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# Admin Credentials
DEFAULT_ADMIN_PASSWORD=${ADMIN_PASSWORD}

# Application Settings
LOG_LEVEL=INFO
MONITORING_MODE=hybrid
CORS_ORIGINS=*
EOF

sudo chmod 600 .env.prod
```

### Step 5: Create directories

```bash
sudo mkdir -p logs backups
```

### Step 6: Pull images

```bash
sudo docker compose pull
```

### Step 7: Start services

```bash
sudo docker compose up -d
```

### Step 8: Verify deployment

```bash
# Wait for services to start
sleep 30

# Check status
sudo docker compose ps

# Test health endpoint
curl http://localhost:5001/api/v1/health
```

---

## Method 3: Use Personal Access Token

### Step 1: Create GitHub Personal Access Token

1. Go to: https://github.com/settings/tokens/new
2. Name: "CredoBank Deployment"
3. Scopes: Check `repo` (full control of private repositories)
4. Click "Generate token"
5. **Copy the token** (you won't see it again!)

### Step 2: Clone with token

```bash
# Replace YOUR_TOKEN with actual token
git clone --branch client/credo-bank --single-branch \
  https://YOUR_TOKEN@github.com/ward-tech-solutions/ward-flux-v2.git /tmp/wardops

# Run deployment
cd /tmp/wardops/deploy
sudo ./deploy-from-github.sh
```

---

## Verification

After deployment, verify everything is working:

```bash
# Check services
cd /opt/wardops
sudo docker compose ps

# Expected output:
# wardops-api       Up (healthy)
# wardops-beat      Up
# wardops-db        Up (healthy)
# wardops-redis     Up (healthy)
# wardops-worker    Up

# Test API
curl http://localhost:5001/api/v1/health

# View logs
sudo docker compose logs -f
```

---

## Accessing the Application

Open in browser:
```
http://<server-ip>:5001
```

**Default credentials:**
- Username: `admin`
- Password: `admin123` (or what you set)

**⚠️ Change the password immediately after first login!**

---

## Troubleshooting

### Can't pull images from GHCR

If you get authentication errors:

```bash
# The images are public, but you may need to authenticate
docker login ghcr.io -u YOUR_GITHUB_USERNAME
# Password: Use a personal access token
```

### Services won't start

```bash
# Check logs
cd /opt/wardops
sudo docker compose logs

# Check disk space
df -h

# Check Docker
sudo systemctl status docker
```

### Port 5001 already in use

```bash
# Check what's using it
sudo lsof -i :5001

# Change port in docker-compose.yml
sudo nano docker-compose.yml
# Change "5001:5001" to "5002:5001"
sudo docker compose up -d
```

---

## Quick Reference

```bash
# Status
cd /opt/wardops && sudo docker compose ps

# Logs
cd /opt/wardops && sudo docker compose logs -f

# Restart
cd /opt/wardops && sudo docker compose restart

# Stop
cd /opt/wardops && sudo docker compose down

# Start
cd /opt/wardops && sudo docker compose up -d

# Update
cd /opt/wardops && sudo docker compose pull && sudo docker compose up -d
```

---

**Need help?** Check the full deployment guide in the repository.
