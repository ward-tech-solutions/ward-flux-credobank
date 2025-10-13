# Local Development with Docker

Quick guide to run WARD OPS locally using Docker.

---

## Prerequisites

Make sure you have Docker installed:

```bash
# Install Docker Desktop (easiest option)
brew install --cask docker

# Launch Docker Desktop from Applications
# Wait for the whale icon to appear in menu bar
```

---

## Quick Start (Automated Script)

Use the provided setup script for an interactive menu:

```bash
./setup-local-docker.sh
```

**Menu Options:**
1. **Build and start** - First time setup or after code changes
2. **Start** - Start existing environment
3. **Stop** - Stop all containers
4. **Clean restart** - Remove data and rebuild (fresh start)
5. **View logs** - Stream container logs
6. **Shell into API** - Access API container terminal
7. **Shell into database** - Access PostgreSQL terminal

---

## Quick Start (Manual Commands)

### 1. Start the Environment

```bash
# Build and start all services
docker-compose -f docker-compose.local.yml up -d --build

# Check status
docker-compose -f docker-compose.local.yml ps
```

### 2. Access the Application

- **Frontend**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs
- **Default Login**: `admin` / `admin123`

### 3. View Logs

```bash
# All services
docker-compose -f docker-compose.local.yml logs -f

# Specific service
docker-compose -f docker-compose.local.yml logs -f api
docker-compose -f docker-compose.local.yml logs -f celery-worker
```

### 4. Stop the Environment

```bash
docker-compose -f docker-compose.local.yml down
```

---

## VS Code Integration

### Use the Command Palette:

1. Press `Cmd + Shift + P`
2. Type "Tasks: Run Task"
3. Select a Docker task:
   - **Docker: Build and Start Local**
   - **Docker: View Logs (All)**
   - **Docker: Stop Local**
   - And more...

### Use Keyboard Shortcuts:

- `Cmd + Shift + B` - Build and start (default build task)

### Use the Docker Extension:

1. Click **Docker icon** in the sidebar
2. Browse **Containers**, **Images**, **Volumes**
3. Right-click containers for actions:
   - View Logs
   - Attach Shell
   - Restart
   - Stop

---

## Common Tasks

### Rebuild After Code Changes

```bash
# Rebuild and restart all services
docker-compose -f docker-compose.local.yml up -d --build

# Rebuild specific service (faster)
docker-compose -f docker-compose.local.yml up -d --build api
```

### Access Container Shell

```bash
# API container (Python/FastAPI)
docker-compose -f docker-compose.local.yml exec api bash

# Database container
docker-compose -f docker-compose.local.yml exec postgres psql -U ward_admin -d ward_ops
```

### Run Database Migrations

```bash
docker-compose -f docker-compose.local.yml exec api python scripts/run_sql_migrations.py
```

### Reset Database (Fresh Start)

```bash
# Stop and remove volumes
docker-compose -f docker-compose.local.yml down -v

# Start again (will create fresh database)
docker-compose -f docker-compose.local.yml up -d --build
```

### Monitor Resource Usage

```bash
docker stats
```

---

## Service Details

| Service | Port | Description |
|---------|------|-------------|
| **api** | 8001 | FastAPI backend + Frontend |
| **postgres** | 5433 | PostgreSQL database |
| **redis** | 6380 | Redis cache |
| **celery-worker** | - | Background task worker |
| **celery-beat** | - | Task scheduler |

---

## Troubleshooting

### Containers Keep Restarting

```bash
# Check logs for errors
docker-compose -f docker-compose.local.yml logs api

# Common issue: Database not ready yet
# Wait 10-20 seconds and check again
```

### Port Already in Use

```bash
# Find what's using port 8001
lsof -i :8001

# Kill the process
kill -9 <PID>

# Or change port in docker-compose.local.yml
```

### Out of Disk Space

```bash
# Clean up Docker
docker system prune -a --volumes

# Warning: This removes all unused containers, images, and volumes!
```

### Database Connection Issues

```bash
# Make sure Postgres is healthy
docker-compose -f docker-compose.local.yml ps postgres

# Check Postgres logs
docker-compose -f docker-compose.local.yml logs postgres

# Try restarting
docker-compose -f docker-compose.local.yml restart postgres
```

---

## Development Workflow

### 1. Make Code Changes

Edit files in VS Code as normal. The following directories are mounted:

```yaml
volumes:
  - ./:/app  # Entire project is mounted in containers
```

### 2. Backend Changes (Python)

For backend changes, you have two options:

**Option A: Auto-reload (recommended for development)**
```bash
# API runs with --reload flag by default in docker-compose.local.yml
# Changes are automatically detected and server restarts
```

**Option B: Manual restart**
```bash
docker-compose -f docker-compose.local.yml restart api
```

### 3. Frontend Changes (React)

Frontend is pre-built into the Docker image. To see changes:

```bash
# Option 1: Run Vite dev server locally (fastest)
cd frontend
npm run dev
# Access at http://localhost:3000

# Option 2: Rebuild Docker image (slower)
docker-compose -f docker-compose.local.yml up -d --build api
```

### 4. Database Schema Changes

```bash
# Create migration SQL file in migrations/postgres/
# Then run migrations
docker-compose -f docker-compose.local.yml exec api python scripts/run_sql_migrations.py
```

---

## Comparing Local vs Production

| Aspect | Local (docker-compose.local.yml) | Production |
|--------|----------------------------------|------------|
| **Ports** | 8001 (API), 5433 (Postgres), 6380 (Redis) | 5001 (API), 5432 (Postgres), 6379 (Redis) |
| **Workers** | 10 Celery workers | 60 Celery workers |
| **Reload** | Auto-reload enabled | Disabled |
| **Volumes** | Mounts local code | Uses image code |
| **Resources** | Uses local Docker | Uses production server |

---

## Tips & Best Practices

### 1. Use VS Code Tasks

Press `Cmd + Shift + P` → "Tasks: Run Task" for quick access to Docker commands.

### 2. Monitor Logs in Separate Terminal

Keep a terminal open with logs streaming:
```bash
docker-compose -f docker-compose.local.yml logs -f
```

### 3. Test with Production-like Data

```bash
# Export from production
ssh user@10.30.25.39 "cd /opt/wardops && docker compose exec postgres pg_dump -U ward_admin -Fc ward_ops > /tmp/prod-backup.dump"
scp user@10.30.25.39:/tmp/prod-backup.dump ./

# Import to local
docker cp prod-backup.dump wardops-postgres-local:/tmp/
docker-compose -f docker-compose.local.yml exec postgres pg_restore -U ward_admin -d ward_ops -c /tmp/prod-backup.dump
```

### 4. Use Docker Extension

The VS Code Docker extension provides a great UI for managing containers, viewing logs, and more.

### 5. Clean Restart Regularly

Occasionally do a clean restart to ensure fresh state:
```bash
docker-compose -f docker-compose.local.yml down -v
docker-compose -f docker-compose.local.yml up -d --build
```

---

## Next Steps

- Read [DOCKER_SETUP_MACOS.md](DOCKER_SETUP_MACOS.md) for detailed Docker installation guide
- Check [README.md](README.md) for general project documentation
- View API documentation at http://localhost:8001/docs

---

**Happy Coding! 🚀**
