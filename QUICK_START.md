# 🚀 WARD OPS - Quick Start Guide

Welcome to WARD OPS Network Monitor! This guide will help you get started in minutes.

## 📦 Step 1: Install and Run

### Using Docker (Recommended)

```bash
# Pull and run the latest version
docker pull ghcr.io/ward-tech-solutions/ward-tech-solutions:latest

docker run -d \
  --name ward-ops \
  -p 5001:5001 \
  -v ward-ops-data:/app/data \
  -v ward-ops-logs:/app/logs \
  --restart unless-stopped \
  ghcr.io/ward-tech-solutions/ward-tech-solutions:latest
```

Wait 30 seconds for the application to start, then proceed to Step 2.

## 🔐 Step 2: First Login

1. **Open your browser** and navigate to:
   ```
   http://localhost:5001
   ```

   Or replace `localhost` with your server IP:
   ```
   http://your-server-ip:5001
   ```

2. **Login with default credentials:**
   - Username: `admin`
   - Password: `admin123`

3. **Change your password immediately!**
   - Click on your profile (top-right corner)
   - Select "Profile Settings"
   - Update your password in the security section

## ⚙️ Step 3: Connect to Zabbix

### 3.1 Navigate to Settings

1. Click **Settings** in the left sidebar
2. You'll see the Zabbix Integration section

### 3.2 Configure Zabbix Connection

Enter your Zabbix server details:

- **Zabbix URL**: Your Zabbix API endpoint
  ```
  http://your-zabbix-server/api_jsonrpc.php
  ```

- **Username**: Your Zabbix admin username
  ```
  Admin
  ```

- **Password**: Your Zabbix admin password
  ```
  zabbix
  ```

### 3.3 Test Connection

1. Click **"Test Connection"** button
2. Wait for the success message: ✅ "Connected successfully to Zabbix"
3. Click **"Save Configuration"**

## 📊 Step 4: Explore Your Network

### Dashboard
- Navigate to **Dashboard** to see network overview
- View total devices, branches, and availability metrics
- Monitor real-time status

### Topology Map
1. Click **Topology** in the left sidebar
2. Select a core device from the dropdown
3. View your network topology with:
   - Core devices (blue)
   - Distribution devices (green)
   - Access devices (yellow)
   - Edge devices (orange)
   - Connected hosts

### Branches
- Click **Branches** to see all branch locations
- View branch-wise device counts and health status
- Click on a branch to see detailed information

### Reports
- Navigate to **Reports** for availability reports
- Monitor ICMP ping availability for all devices
- Export reports for analysis

### Devices
- Click **Devices** to see all monitored devices
- Search and filter devices
- View device details and status

## 🔧 Step 5: Advanced Features

### SSH Terminal
1. Navigate to **Devices** page
2. Click on any device
3. Click **"Open Terminal"** button
4. Enter SSH credentials
5. Execute commands directly on the device

### Bulk Operations
1. Go to **Devices** page
2. Select multiple devices using checkboxes
3. Click **"Bulk Actions"** dropdown
4. Choose operation (Enable, Disable, Maintenance, etc.)
5. Confirm the action

### Zabbix Integration
- **Sync Hosts**: Automatically import hosts from Zabbix
- **Link Hosts**: Link devices to existing Zabbix hosts
- **Monitor Status**: Real-time availability from Zabbix data

## 📈 Understanding the Interface

### Status Icons
- 🟢 **Green**: Device is UP and available
- 🔴 **Red**: Device is DOWN or unavailable
- 🟡 **Yellow**: Device in maintenance or warning state
- ⚪ **Gray**: Unknown status or not monitored

### Device Types
- **Core**: Core network devices (routers, main switches)
- **Distribution**: Distribution layer switches
- **Access**: Access layer switches
- **Edge**: Edge devices (firewalls, gateways)
- **Host**: End devices (servers, workstations)

### Network Topology
- **Parent-Child Relationships**: Shows device hierarchy
- **Interactive Zoom**: Zoom in/out with mouse wheel
- **Drag and Pan**: Click and drag to move around
- **Device Details**: Click device for details

## 🔍 Health Monitoring

### System Health Check

Check application health anytime:
```bash
curl http://localhost:5001/health
```

Or visit: http://localhost:5001/health

Response shows:
- ✅ Database status
- ✅ Zabbix connection status
- ✅ API health
- 📌 Version information

### Application Logs

View logs from Docker:
```bash
# View real-time logs
docker logs -f ward-ops

# View last 100 lines
docker logs --tail 100 ward-ops
```

## 🎯 Common Tasks

### Add a New Branch
1. Go to **Branches** page
2. Click **"Add Branch"**
3. Enter branch details (name, city, address)
4. Click **"Save"**

### Configure Device
1. Navigate to **Devices**
2. Click on the device you want to configure
3. Edit device details (IP, type, branch, parent)
4. Click **"Save Changes"**

### Generate Availability Report
1. Go to **Reports** page
2. Select date range
3. Choose branches or devices
4. Click **"Generate Report"**
5. Export to CSV if needed

### Manage Users (Admin only)
1. Click **Users** in the left sidebar
2. Click **"Add User"** to create new users
3. Set role: ADMIN, USER, or VIEWER
4. Assign permissions appropriately

## 🛡️ Security Best Practices

1. ✅ **Change default password** immediately
2. ✅ **Use strong passwords** for all accounts
3. ✅ **Enable HTTPS** with reverse proxy (see DEPLOYMENT.md)
4. ✅ **Regular backups** of data volume
5. ✅ **Update regularly** to latest version
6. ✅ **Limit access** to port 5001 with firewall rules
7. ✅ **Monitor logs** for suspicious activity

## 🔄 Daily Operations

### Morning Checklist
- [ ] Check Dashboard for any red (DOWN) devices
- [ ] Review overnight alerts and events
- [ ] Verify Zabbix sync is working
- [ ] Check system health endpoint

### Weekly Tasks
- [ ] Review availability reports
- [ ] Update device configurations if needed
- [ ] Backup database (see DEPLOYMENT.md)
- [ ] Check for application updates

### Monthly Tasks
- [ ] Audit user accounts and permissions
- [ ] Review network topology for accuracy
- [ ] Clean up old logs
- [ ] Update documentation

## 🆘 Troubleshooting

### Issue: Cannot connect to Zabbix
**Solution:**
1. Verify Zabbix URL is correct (must include /api_jsonrpc.php)
2. Check username and password
3. Ensure Zabbix server is accessible from WARD OPS container
4. Test: `curl http://your-zabbix-server/api_jsonrpc.php`

### Issue: Devices not showing in Topology
**Solution:**
1. Ensure devices have correct parent-child relationships
2. Select appropriate core device from dropdown
3. Verify devices are linked to Zabbix hosts
4. Check Zabbix connection in Settings

### Issue: SSH Terminal not working
**Solution:**
1. Verify device IP address is correct
2. Check SSH credentials (username/password)
3. Ensure device is accessible from WARD OPS container
4. Check firewall rules allowing SSH (port 22)

### Issue: Reports showing 0% availability
**Solution:**
1. Verify Zabbix connection is active
2. Check that "Unavailable by ICMP ping" item exists in Zabbix
3. Ensure devices are linked to Zabbix hosts
4. Wait for Zabbix to collect data (may take 5-10 minutes)

### Issue: Application not starting
**Solution:**
```bash
# Check container logs
docker logs ward-ops

# Restart container
docker restart ward-ops

# If issue persists, recreate container
docker stop ward-ops
docker rm ward-ops
# Run docker run command again
```

## 📞 Getting Help

### Documentation
- Full deployment guide: See `DEPLOYMENT.md`
- GitHub repository: https://github.com/ward-tech-solutions/ward-tech-solutions

### Support Channels
- **Email**: support@wardops.tech
- **GitHub Issues**: Report bugs or request features
- **Documentation**: Check docs for detailed guides

### Useful Commands

```bash
# Check application version
curl http://localhost:5001/api/v1/health | jq '.version'

# Restart application
docker restart ward-ops

# View logs
docker logs -f ward-ops

# Backup database
docker run --rm -v ward-ops-data:/data -v $(pwd):/backup alpine tar czf /backup/ward-ops-backup.tar.gz /data

# Update to latest version
docker pull ghcr.io/ward-tech-solutions/ward-tech-solutions:latest
docker stop ward-ops && docker rm ward-ops
# Run docker run command again
```

## 🎉 You're All Set!

You've successfully set up WARD OPS Network Monitor!

**Next steps:**
1. ✅ Explore the dashboard
2. ✅ Configure your Zabbix integration
3. ✅ Add your network branches
4. ✅ View topology and devices
5. ✅ Generate availability reports

**Need more help?** Check `DEPLOYMENT.md` for advanced configuration and troubleshooting.

---

**Welcome to smarter network monitoring!** 🚀

*Copyright © 2025 WARD Tech Solutions*
