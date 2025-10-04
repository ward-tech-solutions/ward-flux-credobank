# 🚀 WARD TECH SOLUTIONS - Quick Start Guide

**Network Monitoring Platform v2.0.0**

---

## ⚡ Prerequisites

```bash
# Required
Python 3.10+
Zabbix Server (External)
SQLite 3.x

# Recommended
Git
Docker (for production)
```

---

## 📦 Installation

### **1. Clone & Setup**
```bash
# Navigate to project
cd "/Users/g.jalabadze/Desktop/WARD OPS/CredoBranches"

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### **2. Environment Configuration**
```bash
# Create .env file
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Required Environment Variables:**
```env
# Zabbix Connection
ZABBIX_URL=http://10.30.25.34:8080
ZABBIX_USER=Python
ZABBIX_PASSWORD=Ward123Ops

# Database
DATABASE_URL=sqlite:///data/ward_ops.db

# Security
SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32
JWT_SECRET_KEY=your-jwt-secret    # Generate with: openssl rand -hex 32

# Application
DEBUG=False
HOST=0.0.0.0
PORT=5001
```

### **3. Database Initialization**
```bash
# Initialize database and create admin user
python init_db.py
```

**Default Admin Credentials:**
```
Username: admin
Password: Ward@2025!
```
⚠️ **Change these immediately after first login!**

---

## 🎬 Running the Application

### **Development Mode**
```bash
# Method 1: Using run.py
python run.py

# Method 2: Using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 5001

# Method 3: Using FastAPI CLI
fastapi dev main.py --port 5001
```

**Access the application:**
```
🌐 Web Interface: http://localhost:5001
📚 API Docs: http://localhost:5001/docs
📖 ReDoc: http://localhost:5001/redoc
```

### **Production Mode**
```bash
# Using uvicorn with workers
uvicorn main:app --host 0.0.0.0 --port 5001 --workers 4

# Using gunicorn + uvicorn workers
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:5001
```

---

## 🎨 Features Overview

### **Dashboard** (`/`)
- Real-time device statistics
- Regional breakdown
- Device type distribution
- Active alerts summary
- KPI metrics

### **Devices** (`/devices`)
- Comprehensive device list
- Advanced filtering
- Table and card views
- Bulk operations (CSV/Excel import/export)
- SSH terminal access

### **Map View** (`/map`)
- Georgian regions visualization
- Interactive markers
- Device clustering
- Real-time status updates

### **Topology** (`/topology`)
- Network graph visualization
- Hierarchical layout
- Core router bandwidth monitoring
- Interactive node exploration

### **Reports** (`/reports`)
- Downtime reports
- MTTR statistics
- Availability metrics
- Custom date ranges

### **Configuration** (`/config`) - Admin Only
- Host group management
- City coordinate configuration
- Regional settings

### **User Management** (`/users`) - Admin Only
- User CRUD operations
- Role assignment
- Regional/branch restrictions

---

## 👥 User Roles & Permissions

| Role | Permissions |
|------|-------------|
| **Admin** | Full access to all features, user management, configuration |
| **Regional Manager** | View and manage devices in assigned region |
| **Technician** | View devices, create/edit/delete hosts, bulk operations |
| **Viewer** | Read-only access to dashboard and devices |

---

## 🎨 Theme & Appearance

### **Dark Mode Toggle**
- Click the moon icon (🌙) in the top navigation
- Preference saved in localStorage
- Automatic persistence across sessions

### **Ward Theme Colors**
- **Primary:** #5EBBA8 (WARD Green)
- **Light:** #72CFB8
- **Dark:** #4A9D8A

### **Font**
- **Primary:** Roboto (all weights: 300-900)
- Professional, clean, highly readable

---

## 🔑 API Authentication

### **Login**
```bash
curl -X POST http://localhost:5001/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=Ward@2025!"
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### **Authenticated Request**
```bash
curl -X GET http://localhost:5001/api/v1/devices \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## 🛠️ Common Tasks

### **Add a New Device**
1. Navigate to **Devices** page
2. Click **"Add Device"** button
3. Fill in device details:
   - Hostname
   - IP Address
   - Host Groups
   - Templates
4. Click **"Create Host"**

### **Bulk Import Devices**
1. Navigate to **Devices** page
2. Click **"Import CSV"**
3. Download template if needed
4. Upload your CSV file
5. Review and confirm import

### **Export Device List**
1. Navigate to **Devices** page
2. Click **"Export to CSV"** or **"Export to Excel"**
3. File downloads automatically

### **SSH into Device**
1. Click on any device card/row
2. Click **"SSH Terminal"** button
3. Enter credentials
4. Interactive terminal opens

### **Configure Monitored Host Groups**
1. Navigate to **Config** page (Admin only)
2. Select host groups to monitor
3. Click **"Save Configuration"**
4. Dashboard will update automatically

---

## 🔧 Troubleshooting

### **Common Issues**

#### **Issue: Can't connect to Zabbix**
```bash
# Check Zabbix connection
python test_zabbix.py

# Verify credentials in .env
cat .env | grep ZABBIX
```

#### **Issue: Database errors**
```bash
# Reinitialize database
rm data/ward_ops.db
python init_db.py
```

#### **Issue: Port already in use**
```bash
# Find process using port 5001
lsof -i :5001

# Kill the process
kill -9 <PID>

# Or use a different port
uvicorn main:app --port 8000
```

#### **Issue: Missing dependencies**
```bash
# Reinstall requirements
pip install -r requirements.txt --force-reinstall
```

---

## 📊 Monitoring & Logs

### **Application Logs**
```bash
# View logs in real-time
tail -f server_new.log

# Search for errors
grep "ERROR" server_new.log

# View specific time range
grep "2025-10-04" server_new.log
```

### **Health Check**
```bash
# Check application health
curl http://localhost:5001/api/v1/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-04T12:34:56"
}
```

---

## 🚀 Performance Tips

### **1. Enable Caching**
```python
# Already implemented in zabbix_client.py
# Default cache timeout: 30 seconds
```

### **2. Use Redis (Production)**
```bash
# Install Redis
pip install redis

# Uncomment in requirements.txt
# redis==5.0.1
# flask-caching==2.1.0
```

### **3. Database Optimization**
```bash
# Vacuum database periodically
sqlite3 data/ward_ops.db "VACUUM;"
```

---

## 🔒 Security Best Practices

### **1. Change Default Credentials**
```sql
-- After first login, change admin password
-- Do this through the web interface: Users > Edit Admin
```

### **2. Use Strong JWT Secret**
```bash
# Generate strong secret
openssl rand -hex 32
# Add to .env
```

### **3. Enable HTTPS (Production)**
```bash
# Use nginx or Apache as reverse proxy
# Example nginx config:

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### **4. Restrict Network Access**
```bash
# In production, bind to localhost only
uvicorn main:app --host 127.0.0.1 --port 5001

# Use nginx/Apache for public access
```

---

## 📚 Additional Resources

- **API Documentation:** http://localhost:5001/docs
- **Zabbix Docs:** https://docs.zabbix.com
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **Project README:** [README.md](README.md)
- **Refactoring Summary:** [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)

---

## 💡 Tips & Tricks

### **Keyboard Shortcuts**
- **Alt + D** - Focus search box
- **Ctrl + K** - Open command palette (if implemented)
- **D** - Toggle dark mode (when on devices page)

### **URL Parameters**
```
# Filter devices by region
/devices?region=Tbilisi

# Filter by device type
/devices?type=Router

# Combine filters
/devices?region=Tbilisi&type=Switch
```

---

## 🆘 Support

**Need Help?**
- 📧 Email: info@wardops.tech
- 🌐 Website: https://wardops.tech
- 📝 GitHub Issues: [Report a bug](https://github.com/wardops/network-monitoring/issues)

---

**Happy Monitoring! 🎉**

*© 2025 WARD Tech Solutions. All rights reserved.*
