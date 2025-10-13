# 🚀 WARD OPS - Quick Start Guide

Get WARD OPS running locally in 5 minutes!

---

## Step 1: Install Docker (First Time Only)

```bash
# Install Docker Desktop
brew install --cask docker

# Launch Docker Desktop
open -a Docker

# Wait for whale icon to appear in menu bar ✓
```

---

## Step 2: Run Local Environment

### Option A: Automated Script (Easiest) ⭐

```bash
cd "/Users/g.jalabadze/Desktop/WARD OPS/CredoBranches"
./setup-local-docker.sh
```

Choose option `1` to build and start.

### Option B: Manual Commands

```bash
cd "/Users/g.jalabadze/Desktop/WARD OPS/CredoBranches"

# Start everything
docker-compose -f docker-compose.local.yml up -d --build

# Check status
docker-compose -f docker-compose.local.yml ps
```

---

## Step 3: Access the Application

Open in your browser:

🌐 **http://localhost:8001**

**Login:**
- Username: `admin`
- Password: `admin123`

📚 **API Docs:** http://localhost:8001/docs

---

## Step 4: Make Changes and Test

### Edit Code

Just edit files in VS Code - changes are automatically mounted in containers!

### See Your Changes

**Frontend changes:**
```bash
# Run Vite dev server for instant updates
cd frontend
npm run dev
# Access at http://localhost:3000
```

**Backend changes:**
```bash
# Auto-reload is enabled by default
# Just edit Python files and save - server restarts automatically
```

### View Logs

```bash
# All services
docker-compose -f docker-compose.local.yml logs -f

# Just API
docker-compose -f docker-compose.local.yml logs -f api
```

---

## Step 5: Stop When Done

```bash
docker-compose -f docker-compose.local.yml down
```

---

## 🆘 Troubleshooting

### "Cannot connect to the Docker daemon"
→ Start Docker Desktop application

### "Port 8001 already in use"
→ `lsof -i :8001` then `kill -9 <PID>`

### "Containers keep restarting"
→ `docker-compose -f docker-compose.local.yml logs` to see errors

### Want to start fresh?
```bash
# Clean everything and rebuild
docker-compose -f docker-compose.local.yml down -v
docker-compose -f docker-compose.local.yml up -d --build
```

---

## 📚 More Information

- **Detailed Docker Setup**: [DOCKER_SETUP_MACOS.md](DOCKER_SETUP_MACOS.md)
- **Development Workflow**: [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)
- **VS Code Integration**: Use `.vscode/tasks.json` for quick commands

---

## 🎯 Common Commands

```bash
# Start
docker-compose -f docker-compose.local.yml up -d

# Stop
docker-compose -f docker-compose.local.yml down

# Rebuild
docker-compose -f docker-compose.local.yml up -d --build

# Logs
docker-compose -f docker-compose.local.yml logs -f

# Shell into API container
docker-compose -f docker-compose.local.yml exec api bash

# Shell into database
docker-compose -f docker-compose.local.yml exec postgres psql -U ward_admin -d ward_ops

# Status
docker-compose -f docker-compose.local.yml ps
```

---

## 🔥 VS Code Pro Tips

1. **Run Tasks**: `Cmd + Shift + P` → "Tasks: Run Task" → Select Docker task
2. **Quick Build**: `Cmd + Shift + B` (builds and starts)
3. **Docker Extension**: Click Docker icon in sidebar to manage containers
4. **Integrated Terminal**: View logs and shell into containers

---

## 📦 What Gets Installed?

- ✅ PostgreSQL 15 (port 5433)
- ✅ Redis 7 (port 6380)
- ✅ FastAPI Backend (port 8001)
- ✅ React Frontend (served by FastAPI)
- ✅ Celery Workers (10 workers)
- ✅ Celery Beat (task scheduler)

**Total Size**: ~2-3 GB (first build takes 5-10 minutes)

---

**That's it! You're ready to develop! 🎉**

Need help? Check the detailed guides or run `./setup-local-docker.sh` for interactive menu.
