# 👥 WARD TECH SOLUTIONS - Customer Onboarding Guide

**For Service Providers & Sales Teams**

---

## 📋 Overview

This guide helps you onboard new customers quickly and efficiently. Follow this proven workflow to deploy WARD TECH SOLUTIONS for any company in **under 20 minutes**.

---

## 🎯 Pre-Sales Checklist

Before selling to a customer, verify they have:

### Technical Requirements
- [ ] **Zabbix Server** (version 5.0+)
- [ ] **API Access** enabled on Zabbix
- [ ] **User Account** with permissions to:
  - View hosts
  - View host groups
  - View items/triggers
  - View events

### Infrastructure Requirements
- [ ] Server/VM to run Docker
- [ ] 4GB RAM minimum
- [ ] 10GB disk space
- [ ] Port 5001 available (or alternative)
- [ ] Network access from server to Zabbix

### Decision Makers
- [ ] IT Manager approval
- [ ] Network Admin contact (for Zabbix credentials)
- [ ] Budget approval (if applicable)

---

## 💼 Sales Pitch Template

### Value Proposition

> **"WARD TECH SOLUTIONS transforms your existing Zabbix monitoring into a modern, user-friendly platform with geographic visualization, advanced reporting, and real-time dashboards - all in under 20 minutes."**

### Key Benefits

1. **Instant ROI**
   - Uses existing Zabbix infrastructure
   - No additional sensors needed
   - Deploy in minutes, not days

2. **Enhanced Visibility**
   - See all devices on interactive map
   - Real-time status updates
   - Beautiful, professional dashboards

3. **Executive Reporting**
   - One-click Excel reports
   - Custom branding
   - Scheduled exports

4. **Ease of Use**
   - Web-based (no client installation)
   - Mobile-responsive
   - Dark/Light modes

### Pricing Models

**Option 1: Perpetual License**
- One-time fee
- Unlimited devices
- 1 year support included

**Option 2: Subscription**
- Monthly/Annual billing
- Per-device pricing tiers:
  - 1-100 devices: $X/month
  - 101-500 devices: $Y/month
  - 501+ devices: Custom pricing

**Option 3: Managed Service**
- We host + configure
- Monthly SLA-backed service
- 24/7 support

---

## 🚀 Deployment Workflow

### Phase 1: Pre-Deployment (15 minutes)

**Step 1: Gather Customer Information**

Fill out the onboarding form:

```
┌─────────────────────────────────────────────┐
│ CUSTOMER ONBOARDING FORM                    │
├─────────────────────────────────────────────┤
│ Company Name: _____________________________  │
│ Industry: __________________________________  │
│ Primary Contact: ___________________________  │
│ Email: _____________________________________  │
│ Phone: _____________________________________  │
│                                             │
│ Zabbix Server URL: ________________________  │
│ Zabbix Version: ____________________________  │
│ Number of Devices: _________________________  │
│ Host Groups to Monitor: ____________________  │
│ ___________________________________________ │
│                                             │
│ Deployment Server IP: ______________________  │
│ Preferred URL: _____________________________  │
│ SSL Required: [ ] Yes [ ] No                 │
│                                             │
│ Logo File: _________________________________  │
│ Primary Color: _____________________________  │
└─────────────────────────────────────────────┘
```

**Step 2: Obtain Zabbix Credentials**

Send this email template to customer's Network Admin:

```
Subject: WARD Monitoring Platform - Zabbix API Access Needed

Hi [Name],

We're setting up the WARD TECH SOLUTIONS monitoring platform for
[Company Name]. To connect it to your Zabbix server, we need:

1. Zabbix API URL (usually http://your-server/api_jsonrpc.php)
2. A read-only user account with permissions:
   - View hosts
   - View host groups
   - View items and triggers

Please create a dedicated user (e.g., "ward_monitor") with these
permissions and reply with the credentials.

Security Note: We'll only have READ access - we cannot modify
your Zabbix configuration or devices.

Thank you!
```

**Step 3: Prepare Deployment Server**

```bash
# SSH into deployment server
ssh user@deployment-server

# Install Docker if not present
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify
docker --version
docker-compose --version
```

---

### Phase 2: Deployment (5 minutes)

**Step 1: Deploy Container**

```bash
# Create deployment directory
mkdir -p /opt/ward-monitor
cd /opt/ward-monitor

# Download docker-compose.yml
wget https://your-repo/docker-compose.yml

# Or create it manually:
cat > docker-compose.yml <<EOF
version: '3.8'

services:
  ward-app:
    image: wardtechsolutions/network-monitor:latest
    container_name: ward-${CUSTOMER_NAME}
    ports:
      - "5001:5001"
    volumes:
      - ward-data:/app/data
      - ward-logs:/app/logs
    environment:
      - SETUP_MODE=enabled
    restart: unless-stopped

volumes:
  ward-data:
  ward-logs:
EOF

# Start the container
docker-compose up -d

# Check status
docker ps
docker logs ward-${CUSTOMER_NAME}
```

**Step 2: Verify Deployment**

```bash
# Health check
curl http://localhost:5001/api/v1/health

# Expected output:
# {"status":"healthy","timestamp":"2025-10-04..."}

# Setup wizard available
curl -I http://localhost:5001/setup

# Expected: HTTP/1.1 200 OK
```

---

### Phase 3: Configuration (10 minutes)

**Step 1: Access Setup Wizard**

Share this link with customer (or do it together on screen share):

```
http://DEPLOYMENT_SERVER_IP:5001/setup
```

**Step 2: Walk Through Setup**

**Screen 1: Welcome**
- Review features
- Click "Next"

**Screen 2: Zabbix Configuration**
- Company Name: `[Customer Company Name]`
- Zabbix URL: `[From Step 2]`
- Username: `[From Step 2]`
- Password: `[From Step 2]`
- Click "Test Connection"
- ✅ Verify success message
- Click "Next"

**Screen 3: Host Groups**
- Review all available groups
- Select desired groups (help customer choose)
- Recommended: Start with 1-2 groups for testing
- Click "Next"

**Screen 4: Admin Account**
- Username: `admin` (or customer preference)
- Email: `[Customer admin email]`
- Password: `[Generate strong password]`
- **IMPORTANT:** Save credentials securely!
- Click "Next"

**Screen 5: Complete**
- Review summary
- Click "Go to Dashboard"

**Step 3: First Login**

```
URL: http://DEPLOYMENT_SERVER_IP:5001
Username: admin
Password: [From Step 4]
```

---

### Phase 4: Handoff (5 minutes)

**Step 1: Quick Tour**

Show customer these features:

1. **Dashboard**
   - Total devices
   - Online/offline status
   - Quick stats

2. **Devices Page**
   - List view
   - Search/filter
   - Status indicators

3. **Map Page**
   - Geographic visualization
   - Click devices for details

4. **Reports Page**
   - Generate Excel reports
   - One-click export

5. **Settings Page**
   - Change logo
   - Update colors
   - Manage users

**Step 2: Provide Documentation**

Email customer these documents:
- User Guide (basic usage)
- Admin Guide (user management)
- FAQ
- Support contact

**Step 3: Record Deployment**

Fill out deployment record:

```
DEPLOYMENT RECORD

Customer: ________________________________
Deployment Date: _________________________
Server IP: _______________________________
Container Name: __________________________
Admin Username: __________________________
Admin Password: __________ (stored in vault)

Zabbix Connection:
  URL: ___________________________________
  User: __________________________________
  Groups: ________________________________

Notes:
_________________________________________
_________________________________________
```

---

## 📞 Customer Training Script

### 5-Minute Quick Start

**For Customer Admin:**

> "Let me show you the three things you'll use most:
>
> **1. Dashboard (Home Page)**
> This shows you at-a-glance status of all your monitored devices.
> Green = online, Red = offline. Updates in real-time.
>
> **2. Devices Page**
> Here's your complete device list. You can search by name, filter
> by type, and click any device for detailed information.
>
> **3. Reports**
> Click 'Generate Report' and you'll get an Excel file with all
> device information. Perfect for management meetings.
>
> That's it! Those three features will cover 90% of your daily use.
> Everything else is bonus features you can explore."

### Common Questions & Answers

**Q: Can I add more users?**
A: Yes! Go to Settings → Users → Add User

**Q: How often does data refresh?**
A: Real-time via WebSocket. You'll see changes within seconds.

**Q: Can I change which groups are monitored?**
A: Yes! Go to Settings → Zabbix Configuration → Edit Groups

**Q: Is my Zabbix data safe?**
A: Yes. We only READ data from Zabbix. We cannot make any changes to your Zabbix server or devices.

**Q: What if a device shows wrong location?**
A: Click the device → Edit → Update coordinates. We auto-detect from hostname but you can override.

**Q: Can I customize the dashboard?**
A: Currently no, but it's on our roadmap. Let us know your specific needs!

---

## 🎨 Custom Branding (Optional)

### Add Customer Logo

```bash
# On deployment server
docker cp /path/to/logo.png ward-CUSTOMER:/ app/static/img/custom-logo.png

# Then in UI: Settings → Branding → Upload Logo
```

### Change Primary Color

Settings → Branding → Primary Color
- Use customer brand color
- Preview before saving

---

## 🔒 Security Hardening (Production)

### Step 1: Enable HTTPS

Install nginx:
```bash
sudo apt install nginx certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d monitor.customer.com

# Nginx config
sudo nano /etc/nginx/sites-available/ward-monitor

server {
    listen 443 ssl;
    server_name monitor.customer.com;

    ssl_certificate /etc/letsencrypt/live/monitor.customer.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/monitor.customer.com/privkey.pem;

    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Enable
sudo ln -s /etc/nginx/sites-available/ward-monitor /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 2: Firewall

```bash
# Allow only HTTPS
sudo ufw allow 443/tcp
sudo ufw deny 5001/tcp  # Block direct access
sudo ufw enable
```

---

## 📊 Success Metrics

Track these for each customer:

### Immediate (Day 1)
- [ ] Platform deployed
- [ ] Setup wizard completed
- [ ] Devices visible
- [ ] Admin can login
- [ ] Reports generated

### Week 1
- [ ] Multiple users added
- [ ] Custom branding applied
- [ ] First support ticket (if any)
- [ ] Customer satisfaction survey sent

### Month 1
- [ ] Usage analytics reviewed
- [ ] Upsell opportunities identified
- [ ] Renewal/expansion discussion

---

## 🆘 Troubleshooting Common Issues

### Issue: "Cannot connect to Zabbix"

**Diagnosis:**
```bash
# Test from container
docker exec -it ward-CUSTOMER curl http://ZABBIX_URL

# If fails, test from host
curl http://ZABBIX_URL
```

**Solutions:**
1. Verify Zabbix URL is correct
2. Check firewall allows connection
3. Verify Zabbix user has API access
4. Check Zabbix API is enabled

### Issue: "No devices showing"

**Diagnosis:**
1. Check selected host groups have devices
2. Verify Zabbix user can see these groups
3. Check logs: `docker logs ward-CUSTOMER`

**Solutions:**
1. Re-run setup wizard
2. Add more host groups
3. Check Zabbix permissions

### Issue: "Setup wizard loops back to start"

**Solution:**
```bash
# Reset setup state
docker exec -it ward-CUSTOMER python <<EOF
from database import SessionLocal
from models import SetupWizardState

db = SessionLocal()
state = db.query(SetupWizardState).first()
if state:
    state.is_complete = False
    db.commit()
db.close()
EOF

# Restart container
docker restart ward-CUSTOMER
```

---

## 📋 Customer Acceptance Checklist

Before considering deployment "complete":

### Technical Verification
- [ ] Platform accessible via URL
- [ ] HTTPS enabled (production)
- [ ] All monitored devices visible
- [ ] Map showing device locations
- [ ] Reports generating successfully
- [ ] Real-time updates working
- [ ] Dark/light mode switching works

### Customer Satisfaction
- [ ] Admin trained on basic features
- [ ] Documentation provided
- [ ] Support contact shared
- [ ] Customer can login independently
- [ ] Customer confirms satisfaction

### Business Closure
- [ ] Invoice sent/payment received
- [ ] SLA signed (if applicable)
- [ ] Deployment record filed
- [ ] Customer added to CRM
- [ ] First check-in scheduled

---

## 🎁 Customer Welcome Email Template

```
Subject: Welcome to WARD TECH SOLUTIONS! 🎉

Hi [Customer Name],

Your WARD TECH SOLUTIONS network monitoring platform is now live!

🔗 Access URL: https://monitor.yourcomain.com
👤 Username: admin
🔑 Password: [Provided separately]

Quick Start Guide:
1. Login with credentials above
2. Explore your dashboard (all devices visible!)
3. Try generating a report (Reports tab)
4. Check out the geographic map (Map tab)

Need help?
📧 Email: support@wardops.tech
📞 Phone: [Your support number]
📚 Docs: https://docs.wardops.tech

We'll check in next week to see how things are going!

Best regards,
[Your Name]
WARD TECH SOLUTIONS Team
```

---

## 🚀 Next Steps

After successful onboarding:

1. **Schedule 1-week check-in**
2. **Send satisfaction survey**
3. **Identify expansion opportunities**
4. **Add customer to success stories** (with permission)
5. **Request testimonial** (after 30 days)

---

## 📈 Upsell Opportunities

After initial deployment, consider:

### Add-On Services
- Custom report templates
- Integration with ticketing systems
- Advanced alerting
- White-label mobile app
- Dedicated support SLA

### Expansion
- Monitor additional host groups
- Multi-site deployment
- Training for additional users
- Custom feature development

---

## ✅ Onboarding Success Rate Target

**Goal:** 95% successful deployments within 20 minutes

**Track:**
- Average deployment time
- Issues encountered (categorize)
- Customer satisfaction score
- Time to first value (when they see their devices)

---

*WARD TECH SOLUTIONS - Making Network Monitoring Simple for Everyone*
