# 🚀 Quick Start Guide

## Automated Setup (Recommended)

Run the automated setup script:

```bash
cd "/Users/g.jalabadze/Desktop/WARD OPS/CredoBranches"
./setup.sh
```

This will:
- Create Python virtual environment
- Install Python dependencies (FastAPI, httpx, etc.)
- Install Node.js dependencies (React, Vite, TypeScript, etc.)

---

## Manual Setup

### 1. Backend Setup

```bash
# Navigate to project
cd "/Users/g.jalabadze/Desktop/WARD OPS/CredoBranches"

# Create & activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install
```

---

## Running the Application

### Development Mode (2 Terminals)

**Terminal 1 - Start Backend:**
```bash
cd "/Users/g.jalabadze/Desktop/WARD OPS/CredoBranches"
source venv/bin/activate
python main.py
```

**Terminal 2 - Start Frontend:**
```bash
cd "/Users/g.jalabadze/Desktop/WARD OPS/CredoBranches/frontend"
npm run dev
```

**Access:**
- 🌐 Application: http://localhost:3000
- 📡 API: http://localhost:5001
- 📚 API Docs: http://localhost:5001/docs

---

## Production Build

```bash
# Build frontend
cd frontend
npm run build

# Run production server
cd ..
source venv/bin/activate
pip install gunicorn
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:5001
```

---

## Key Commands Reference

### Backend
```bash
# Start dev server
python main.py

# Start with uvicorn
uvicorn main:app --reload --port 5001

# Production
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:5001
```

### Frontend
```bash
# Development
npm run dev

# Production build
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

---

## What Changed?

### API Endpoints (NEW)
All endpoints now use `/api/v1/` prefix:
- `/api/v1/dashboard/stats` - Dashboard statistics
- `/api/v1/devices` - Device list
- `/api/v1/devices/{id}` - Device details
- `/api/v1/search` - Advanced search
- `/api/v1/topology` - Network topology
- `/api/v1/reports/downtime` - Downtime reports
- `/ws/updates` - WebSocket for real-time updates

### Technology Stack

**Backend:**
- ❌ Flask → ✅ FastAPI (async)
- ❌ SSE → ✅ WebSocket
- ❌ Manual routing → ✅ Auto-generated API docs

**Frontend:**
- ❌ Vanilla JS → ✅ React + TypeScript
- ❌ No bundler → ✅ Vite
- ❌ Spinners → ✅ Skeleton loaders
- ❌ Generic errors → ✅ Error boundaries

---

## File Structure

```
CredoBranches/
├── main.py                  # FastAPI app (NEW)
├── zabbix_client_async.py   # Async Zabbix client (NEW)
├── setup.sh                 # Automated setup (NEW)
├── requirements.txt         # Updated dependencies
├── MODERNIZATION_GUIDE.md   # Full documentation
├── QUICK_START.md          # This file
└── frontend/               # React app (NEW)
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── components/     # Reusable components
        ├── pages/          # Page components
        ├── hooks/          # Custom hooks
        └── api/            # API client
```

---

## Troubleshooting

### "Port already in use"
```bash
# Kill process on port
lsof -ti:5001 | xargs kill -9  # Backend
lsof -ti:3000 | xargs kill -9  # Frontend
```

### "Module not found"
```bash
# Backend
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend && npm install
```

### "Cannot connect to WebSocket"
Ensure backend is running on port 5001 before starting frontend.

---

## Next Steps

1. ✅ Setup complete - Follow this guide
2. 📖 Read [MODERNIZATION_GUIDE.md](MODERNIZATION_GUIDE.md) for details
3. 🎨 Implement remaining pages (Devices, Map, Topology, Reports)
4. 🔒 Add authentication
5. 🐳 Docker deployment
6. 🚀 Deploy to production

---

## Need Help?

Check these files:
- `MODERNIZATION_GUIDE.md` - Full documentation
- `main.py` - FastAPI backend code
- `frontend/src/` - React components

Or visit:
- FastAPI Docs: http://localhost:5001/docs (when running)
- React Query: https://tanstack.com/query/latest
- Vite: https://vitejs.dev/
