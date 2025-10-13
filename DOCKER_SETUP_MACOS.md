# Docker Setup Guide for macOS (M1/M2/Intel)

Complete guide to install and use Docker on macOS using Homebrew and VS Code.

---

## Prerequisites

- macOS 10.15 or later (Catalina, Big Sur, Monterey, Ventura, Sonoma)
- Homebrew installed
- VS Code installed
- At least 4GB RAM available for Docker

---

## Step 1: Install Homebrew (if not installed)

If you don't have Homebrew, install it first:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

After installation, follow the instructions to add Homebrew to your PATH.

---

## Step 2: Install Docker Desktop via Homebrew

### Option A: Install Docker Desktop (Recommended - includes GUI)

```bash
# Install Docker Desktop
brew install --cask docker

# Wait for installation to complete
# Docker Desktop will appear in your Applications folder
```

**Launch Docker Desktop:**
1. Open **Spotlight** (Cmd + Space)
2. Type "Docker" and press Enter
3. Accept the terms and conditions
4. Docker will start (you'll see the whale icon in your menu bar)

### Option B: Install Docker CLI + Colima (Lightweight alternative)

If you prefer a lightweight setup without Docker Desktop:

```bash
# Install Docker CLI and Colima
brew install docker docker-compose colima

# Start Colima (lightweight Docker runtime)
colima start --cpu 4 --memory 8 --disk 50

# Verify installation
docker --version
docker-compose --version
```

---

## Step 3: Verify Docker Installation

```bash
# Check Docker version
docker --version
# Expected output: Docker version 24.x.x, build xxxxx

# Check Docker Compose version
docker-compose --version
# Expected output: Docker Compose version v2.x.x

# Test Docker with hello-world
docker run hello-world
# Should download and run successfully
```

---

## Step 4: Configure Docker Resources (Docker Desktop)

**For optimal performance with WARD OPS:**

1. Click the **Docker icon** in the menu bar
2. Select **Settings** (or **Preferences**)
3. Go to **Resources** tab:
   - **CPUs**: 4-6 cores (for 60 Celery workers)
   - **Memory**: 8-12 GB
   - **Swap**: 2 GB
   - **Disk**: 50 GB
4. Click **Apply & Restart**

---

## Step 5: Install VS Code Docker Extension

### Install Docker Extension:

1. Open **VS Code**
2. Press `Cmd + Shift + X` (Extensions)
3. Search for **"Docker"** by Microsoft
4. Click **Install**

**Or install via command line:**
```bash
code --install-extension ms-azuretools.vscode-docker
```

### Other Useful VS Code Extensions:

```bash
# Remote - Containers (for dev containers)
code --install-extension ms-vscode-remote.remote-containers

# YAML support (for docker-compose.yml)
code --install-extension redhat.vscode-yaml

# Python (for backend development)
code --install-extension ms-python.python

# ESLint (for React frontend)
code --install-extension dbaeumer.vscode-eslint
```

---

## Step 6: Set Up WARD OPS Local Development

### Navigate to project:

```bash
cd "/Users/g.jalabadze/Desktop/WARD OPS/CredoBranches"
```

### Open in VS Code:

```bash
code .
```

---

## Step 7: Build and Run Local Docker Environment

### Using docker-compose.local.yml:

```bash
# Build images
docker-compose -f docker-compose.local.yml build

# Start all services
docker-compose -f docker-compose.local.yml up -d

# View logs
docker-compose -f docker-compose.local.yml logs -f

# Access the application
open http://localhost:8001
```

### VS Code Docker Extension Usage:

1. Click the **Docker icon** in the left sidebar (or press `Cmd + Shift + D`)
2. You'll see:
   - **Containers**: Running/stopped containers
   - **Images**: Built images
   - **Volumes**: Data volumes
   - **Networks**: Docker networks

3. **Right-click on a container** to:
   - View Logs
   - Attach Shell
   - Inspect
   - Stop/Start/Restart
   - Remove

---

## Step 8: Useful Docker Commands

### Container Management:

```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# View logs
docker-compose -f docker-compose.local.yml logs -f api
docker-compose -f docker-compose.local.yml logs -f celery-worker

# Execute commands in running container
docker-compose -f docker-compose.local.yml exec api bash
docker-compose -f docker-compose.local.yml exec postgres psql -U ward_admin -d ward_ops

# Stop all services
docker-compose -f docker-compose.local.yml down

# Stop and remove volumes (clean slate)
docker-compose -f docker-compose.local.yml down -v

# Restart specific service
docker-compose -f docker-compose.local.yml restart api
```

### Image Management:

```bash
# List images
docker images

# Remove unused images
docker image prune

# Remove all unused images, containers, networks
docker system prune -a

# Build without cache
docker-compose -f docker-compose.local.yml build --no-cache
```

### Debugging:

```bash
# Check container resource usage
docker stats

# Inspect container details
docker inspect wardops-api-local

# View container processes
docker top wardops-api-local

# Copy files from container
docker cp wardops-api-local:/app/logs/app.log ./local-logs.txt
```

---

## Step 9: VS Code Development Workflow

### Recommended VS Code Settings:

Create or update `.vscode/settings.json`:

```json
{
  "docker.commands.build": "${containerCommand} build --pull --rm -f \"${dockerfile}\" -t ${tag} \"${context}\"",
  "docker.commands.run": "${containerCommand} run --rm -d ${exposedPorts} ${tag}",
  "docker.dockerComposeBuild": true,
  "docker.dockerComposeDetached": true,
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "editor.formatOnSave": true
}
```

### Keyboard Shortcuts:

| Action | Shortcut |
|--------|----------|
| Open Command Palette | `Cmd + Shift + P` |
| Docker: Compose Up | Type "Docker: Compose Up" in palette |
| Docker: Compose Down | Type "Docker: Compose Down" in palette |
| View Container Logs | Right-click container → "View Logs" |
| Attach Shell | Right-click container → "Attach Shell" |

---

## Step 10: Initialize Database and Seed Data

### First-time setup:

```bash
# Start services
docker-compose -f docker-compose.local.yml up -d

# Wait for Postgres to be ready (check logs)
docker-compose -f docker-compose.local.yml logs postgres

# Run migrations
docker-compose -f docker-compose.local.yml exec api python scripts/run_sql_migrations.py

# Create admin user (if needed)
docker-compose -f docker-compose.local.yml exec api python -c "
from database import SessionLocal
from models import User
from passlib.context import CryptContext

db = SessionLocal()
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

admin = User(
    username='admin',
    email='admin@wardops.local',
    hashed_password=pwd_context.hash('admin123'),
    is_superuser=True
)
db.add(admin)
db.commit()
print('Admin user created!')
"
```

---

## Step 11: Access Services

Once running, access these URLs:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend** | http://localhost:8001 | admin / admin123 |
| **API Docs** | http://localhost:8001/docs | - |
| **PostgreSQL** | localhost:5433 | ward_admin / ward_admin_password |
| **Redis** | localhost:6380 | Password: redispass |

### Database Connection (DBeaver/TablePlus):

- **Host**: localhost
- **Port**: 5433
- **Database**: ward_ops
- **User**: ward_admin
- **Password**: ward_admin_password

---

## Step 12: Troubleshooting

### Docker Desktop Not Starting:

```bash
# Reset Docker Desktop
rm -rf ~/Library/Group\ Containers/group.com.docker
rm -rf ~/Library/Containers/com.docker.docker
rm -rf ~/.docker

# Restart Docker Desktop
```

### Port Already in Use:

```bash
# Find process using port 8001
lsof -i :8001

# Kill process
kill -9 <PID>

# Or change port in docker-compose.local.yml
ports:
  - "8002:8000"  # Change 8001 to 8002
```

### Containers Exiting Immediately:

```bash
# Check logs for errors
docker-compose -f docker-compose.local.yml logs api

# Common issues:
# 1. Database not ready → Wait longer or check postgres logs
# 2. Missing environment variables → Check .env file
# 3. Port conflicts → Change ports in docker-compose.local.yml
```

### Out of Disk Space:

```bash
# Clean up Docker
docker system prune -a --volumes

# Remove all stopped containers
docker container prune

# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune
```

### Colima Issues (if using Colima instead of Docker Desktop):

```bash
# Stop Colima
colima stop

# Start with more resources
colima start --cpu 6 --memory 12 --disk 60

# Check status
colima status

# Restart Colima
colima restart
```

---

## Step 13: VS Code Docker Development Tips

### 1. Attach to Running Container:

In VS Code:
1. Click **Docker** icon in sidebar
2. Expand **Containers**
3. Right-click **wardops-api-local**
4. Select **Attach Shell**
5. A new terminal opens inside the container!

### 2. View Real-time Logs:

1. Right-click container → **View Logs**
2. Logs stream in VS Code terminal
3. Use `Cmd + F` to search logs

### 3. Rebuild After Code Changes:

```bash
# Rebuild specific service
docker-compose -f docker-compose.local.yml up -d --build api

# Or rebuild all
docker-compose -f docker-compose.local.yml up -d --build
```

### 4. Debug Python in Docker:

Add to `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Docker: Python Attach",
      "type": "python",
      "request": "attach",
      "connect": {
        "host": "localhost",
        "port": 5678
      },
      "pathMappings": [
        {
          "localRoot": "${workspaceFolder}",
          "remoteRoot": "/app"
        }
      ]
    }
  ]
}
```

---

## Step 14: Production Deployment Workflow

### Test locally → Push to Git → CI/CD → Deploy to Production:

```bash
# 1. Develop and test locally
docker-compose -f docker-compose.local.yml up -d

# 2. Test changes at http://localhost:8001
# Make sure everything works!

# 3. Commit changes
git add .
git commit -m "Feature: XYZ"
git push origin client/credo-bank

# 4. Wait for CI/CD to build images
# Check GitHub Actions

# 5. Deploy to production
ssh user@10.30.25.39 "cd /opt/wardops && docker compose pull && docker compose up -d"
```

---

## Quick Reference

### Essential Commands:

```bash
# Start
docker-compose -f docker-compose.local.yml up -d

# Stop
docker-compose -f docker-compose.local.yml down

# Logs
docker-compose -f docker-compose.local.yml logs -f

# Rebuild
docker-compose -f docker-compose.local.yml up -d --build

# Clean restart
docker-compose -f docker-compose.local.yml down -v && docker-compose -f docker-compose.local.yml up -d --build

# Shell into API container
docker-compose -f docker-compose.local.yml exec api bash

# Shell into database
docker-compose -f docker-compose.local.yml exec postgres psql -U ward_admin -d ward_ops
```

---

## Additional Resources

- **Docker Desktop Documentation**: https://docs.docker.com/desktop/
- **Docker Compose Reference**: https://docs.docker.com/compose/
- **VS Code Docker Extension**: https://code.visualstudio.com/docs/containers/overview
- **Colima (Docker Desktop alternative)**: https://github.com/abiosoft/colima

---

## Support

If you encounter issues:

1. Check Docker Desktop is running (whale icon in menu bar)
2. Verify Docker version: `docker --version`
3. Check available resources: `docker system df`
4. Review container logs: `docker-compose -f docker-compose.local.yml logs`
5. Clean and restart: `docker system prune -a`

---

**Happy Dockerizing! 🐳**
