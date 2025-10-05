"""
WARD TECH SOLUTIONS - Network Monitoring Platform
Modern FastAPI-based Network Management System

Copyright © 2025 WARD Tech Solutions
Powered by FastAPI, Zabbix API, and modern async architecture
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, UploadFile, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from contextlib import asynccontextmanager
import asyncio
import json
import io
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from pydantic import BaseModel
from sqlalchemy.orm import Session

from zabbix_client import ZabbixClient
import concurrent.futures

# Authentication imports
from database import get_db, User, UserRole, init_db
from auth import (
    authenticate_user, create_access_token, get_current_active_user,
    create_user, UserCreate, UserResponse, Token,
    require_admin, require_manager_or_admin, require_tech_or_admin
)

# Bulk operations imports
from bulk_operations import (
    parse_csv_file, parse_excel_file, validate_bulk_import_data,
    process_bulk_import, bulk_update_devices, bulk_delete_devices,
    generate_csv_template, export_devices_to_csv, export_devices_to_excel,
    BulkOperationResult
)

# Thread pool for running sync Zabbix client in async context
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

# ============================================
# Helper Functions
# ============================================

def get_monitored_groupids():
    """Get list of monitored group IDs from database"""
    import sqlite3
    conn = sqlite3.connect('data/ward_ops.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT groupid FROM monitored_hostgroups WHERE is_active = 1
    """)
    groupids = [row['groupid'] for row in cursor.fetchall()]
    conn.close()
    return groupids if groupids else None

def extract_city_from_hostname(hostname):
    """Extract city name from hostname"""
    # Remove IP if present: "Batumi-ATM 10.199.96.163" -> "Batumi-ATM"
    name = hostname.split()[0]

    # Handle special prefixes: "PING-Kabali-AP" -> skip "PING", use "Kabali"
    parts = name.split('-')

    # Skip common prefixes (PING, TEST, PROD, etc.)
    common_prefixes = ['PING', 'TEST', 'PROD', 'DEV', 'SW', 'RTR']
    if len(parts) > 1 and parts[0].upper() in common_prefixes:
        city = parts[1]  # Use second part as city
    else:
        city = parts[0]  # Use first part as city

    # Remove numbers: "Batumi1" -> "Batumi"
    city = ''.join([c for c in city if not c.isdigit()])

    return city.strip()

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database
    init_db()

    # Create default admin user if it doesn't exist
    from database import SessionLocal, User, UserRole
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                email="admin@wardops.tech",
                full_name="Administrator",
                hashed_password=pwd_context.hash("admin123"),
                role=UserRole.ADMIN,
                is_active=True,
                is_superuser=True
            )
            db.add(admin_user)
            db.commit()
            print("✓ Default admin user created (username: admin, password: admin123)")
        else:
            # Update existing admin user to ensure ADMIN role
            if admin_user.role != UserRole.ADMIN:
                admin_user.role = UserRole.ADMIN
                admin_user.is_superuser = True
                db.commit()
                print("✓ Admin user role updated to ADMIN")
            else:
                print("✓ Admin user already exists")
    except Exception as e:
        print(f"Warning: Could not create default admin user: {e}")
    finally:
        db.close()

    # Startup - use the working synchronous client
    app.state.zabbix = ZabbixClient()
    app.state.websocket_connections: List[WebSocket] = []

    # Start background task for real-time updates
    app.state.monitor_task = asyncio.create_task(monitor_device_changes(app))

    yield

    # Shutdown
    app.state.monitor_task.cancel()
    executor.shutdown(wait=False)

app = FastAPI(
    title="WARD TECH SOLUTIONS - Network Monitoring Platform",
    description="""
## Enterprise-grade Network Monitoring & Management System

### Features:
* 🔐 **Secure Authentication** - JWT-based user authentication
* 📊 **Zabbix Integration** - Real-time monitoring data from Zabbix
* 🌐 **Network Diagnostics** - Ping, Traceroute, MTR tools
* 📈 **Performance Baselines** - Automated performance tracking
* 🗺️ **Network Topology** - Visual network mapping
* 👥 **Multi-user Support** - Role-based access control

### API Documentation:
* Interactive Swagger UI: `/docs`
* Alternative ReDoc: `/redoc`
* OpenAPI Schema: `/openapi.json`
    """,
    version="2.0.0",
    contact={
        "name": "WARD Tech Solutions",
        "url": "https://wardops.tech",
        "email": "info@wardops.tech"
    },
    license_info={
        "name": "Proprietary",
        "url": "https://wardops.tech/license"
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Allow all hosts (for Docker deployment with any IP/domain)
from starlette.middleware.trustedhost import TrustedHostMiddleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# ============================================
# Include Modular Routers
# ============================================
from routers import auth, bulk, config, dashboard, devices, diagnostics, infrastructure, pages, reports, websockets, zabbix

app.include_router(auth.router)
app.include_router(pages.router)
app.include_router(config.router)
app.include_router(bulk.router)
app.include_router(devices.router)
app.include_router(reports.router)
app.include_router(zabbix.router)
app.include_router(dashboard.router)
app.include_router(diagnostics.router)
app.include_router(websockets.router)
app.include_router(infrastructure.router)

# ============================================
# Security Middleware
# ============================================

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    return response

# CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# Rate Limiting Setup
# ============================================
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    RATE_LIMITING_ENABLED = True
except ImportError:
    print("Warning: slowapi not installed. Rate limiting disabled. Install with: pip install slowapi")
    RATE_LIMITING_ENABLED = False
    limiter = None

# ============================================
# Setup Wizard Integration
# ============================================
from setup_wizard import router as setup_router
from middleware_setup import setup_check_middleware

# Add setup middleware (redirects to wizard if not configured)
# DISABLED: Setup wizard not needed - use Settings page for Zabbix config
# app.middleware("http")(setup_check_middleware)

# Include setup wizard routes
app.include_router(setup_router)

# ============================================
# Static files and templates
# ============================================
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.auto_reload = True  # Force template reload for development

# Add Flask-compatible url_for to templates
def url_for(endpoint: str, **values):
    """Flask-compatible url_for function for Jinja2 templates"""
    if endpoint == 'static':
        filename = values.get('filename', '')
        return f"/static/{filename}"
    return f"/{endpoint}"

templates.env.globals['url_for'] = url_for

# Helper function to run sync code in thread pool
async def run_in_executor(func, *args):
    """Run synchronous function in thread pool"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)

# Pydantic models for request validation
class CreateHostRequest(BaseModel):
    hostname: str
    visible_name: str
    ip_address: str
    group_ids: List[str]
    template_ids: List[str]

class UpdateHostRequest(BaseModel):
    hostname: Optional[str] = None
    visible_name: Optional[str] = None
    ip_address: Optional[str] = None
    branch: Optional[str] = None

class SSHConnectRequest(BaseModel):
    host: str
    username: str
    password: str
    port: int = 22

# ============================================
# API v1 Routes
# ============================================

# EXTRACTED TO: routers/dashboard.py
# @app.get("/api/v1/health")
# @app.get("/health")
# @app.get("/api/v1/dashboard/stats")

# Legacy health endpoint (redirect to /api/v1/health)
@app.get("/health")
async def simple_health_check(request: Request):
    """Simple health check endpoint (returns 200 OK)"""
    from routers.dashboard import health_check
    return await health_check(request)

# EXTRACTED TO: routers/devices.py
# @app.get("/api/v1/devices")
# @app.get("/api/v1/devices/{hostid}")
# ============================================
# NETWORK DIAGNOSTICS - EXTRACTED TO routers/diagnostics.py
# ============================================
# @router.post("/ping")
# @router.post("/traceroute")
# @router.get("/ping/history/{ip}")
# @router.get("/traceroute/history/{ip}")
# @router.post("/mtr/store")
# @router.get("/mtr/history/{ip}")
# @router.get("/trends/{ip}")
# @router.post("/bulk/ping")
# @router.post("/export")
# @router.post("/dns/lookup")
# @router.post("/dns/reverse")
# @router.post("/portscan")
# @router.post("/baseline/calculate")
# @router.get("/baseline/{ip}")
# @router.post("/anomaly/detect")

# EXTRACTED TO: routers/zabbix.py
# @app.get("/api/v1/alerts")
# @app.get("/api/v1/mttr/stats")
# @app.get("/api/v1/groups")
# @app.get("/api/v1/templates")
# @app.post("/api/v1/hosts")
# @app.put("/api/v1/hosts/{hostid}")
# @app.delete("/api/v1/hosts/{hostid}")
# @app.get("/api/v1/search")

# EXTRACTED TO: routers/reports.py
# @app.get("/api/v1/reports/downtime")
# @app.get("/api/v1/reports/mttr-extended")
# EXTRACTED TO: routers/infrastructure.py
# @router.get("/router/{hostid}/interfaces")
# @router.get("/topology")


@app.get("/api/dashboard-stats")
async def api_dashboard_stats_legacy(request: Request, region: Optional[str] = None):
    """Legacy route - no auth for backward compatibility"""
    zabbix = request.app.state.zabbix

    # Run sync methods in thread pool
    if region:
        devices = await run_in_executor(zabbix.get_devices_by_region, region)
    else:
        devices = await run_in_executor(zabbix.get_all_hosts)

    alerts = await run_in_executor(zabbix.get_active_alerts)

    total_devices = len(devices)
    online_devices = len([h for h in devices if h.get('ping_status') == 'Up'])
    offline_devices = len([h for h in devices if h.get('ping_status') == 'Down'])
    warning_devices = len([h for h in devices if h.get('ping_status') == 'Unknown'])

    # Device types statistics
    device_types = {}
    for host in devices:
        dt = host['device_type']
        if dt not in device_types:
            device_types[dt] = {'total': 0, 'online': 0, 'offline': 0}
        device_types[dt]['total'] += 1
        if host.get('ping_status') == 'Up':
            device_types[dt]['online'] += 1
        elif host.get('ping_status') == 'Down':
            device_types[dt]['offline'] += 1

    # Region statistics
    regions_stats = {}
    for host in devices:
        region_name = host['region']
        if region_name not in regions_stats:
            regions_stats[region_name] = {'total': 0, 'online': 0, 'offline': 0}
        regions_stats[region_name]['total'] += 1
        if host.get('ping_status') == 'Up':
            regions_stats[region_name]['online'] += 1
        elif host.get('ping_status') == 'Down':
            regions_stats[region_name]['offline'] += 1

    return {
        'total_devices': total_devices,
        'online_devices': online_devices,
        'offline_devices': offline_devices,
        'warning_devices': warning_devices,
        'uptime_percentage': round((online_devices / total_devices * 100) if total_devices > 0 else 0, 2),
        'active_alerts': len(alerts),
        'critical_alerts': len([a for a in alerts if a['severity'] in ['High', 'Disaster']]),
        'device_types': device_types,
        'regions_stats': regions_stats
    }

@app.get("/api/devices")
async def api_devices_legacy(
    request: Request,
    region: Optional[str] = None,
    branch: Optional[str] = None,
    device_type: Optional[str] = None
):
    """Legacy route - no auth for backward compatibility"""
    zabbix = request.app.state.zabbix

    if region:
        devices = await run_in_executor(zabbix.get_devices_by_region, region)
    elif branch:
        devices = await run_in_executor(zabbix.get_devices_by_branch, branch)
    elif device_type:
        devices = await run_in_executor(zabbix.get_devices_by_type, device_type)
    else:
        devices = await run_in_executor(zabbix.get_all_hosts)

    return devices

@app.get("/api/device/{hostid}")
async def api_device_details_legacy(request: Request, hostid: str):
    """Legacy route - redirects to v1"""
    return await get_device_details(request, hostid)

@app.get("/api/alerts")
async def api_alerts_legacy(request: Request):
    """Legacy route - redirects to v1"""
    return await get_alerts(request)

@app.get("/api/mttr-stats")
async def api_mttr_stats_legacy(request: Request):
    """Legacy route - redirects to v1"""
    return await get_mttr_stats(request)

@app.get("/api/groups")
async def api_groups_legacy(request: Request):
    """Legacy route - redirects to v1"""
    return await get_groups(request)

@app.get("/api/templates")
async def api_templates_legacy(request: Request):
    """Legacy route - redirects to v1"""
    return await get_templates(request)

@app.get("/api/search")
async def api_search_legacy(
    request: Request,
    q: Optional[str] = None,
    region: Optional[str] = None,
    branch: Optional[str] = None,
    device_type: Optional[str] = None,
    status: Optional[str] = None
):
    """Legacy route - no auth for backward compatibility"""
    zabbix = request.app.state.zabbix
    devices = await run_in_executor(zabbix.get_all_hosts)

    # Apply text search
    if q:
        query = q.lower()
        devices = [d for d in devices if (
            query in d['display_name'].lower() or
            query in d['branch'].lower() or
            query in d['ip'].lower() or
            query in d['region'].lower()
        )]

    # Apply filters
    if region:
        devices = [d for d in devices if d['region'] == region]
    if branch:
        devices = [d for d in devices if branch.lower() in d['branch'].lower()]
    if device_type:
        devices = [d for d in devices if d['device_type'] == device_type]
    if status:
        devices = [d for d in devices if d['ping_status'] == status]

    return devices

@app.get("/api/topology")
async def api_topology_legacy(
    request: Request,
    view: str = 'hierarchical',
    limit: int = 200,
    region: Optional[str] = None
):
    """Legacy route - no auth, enhanced with core router hierarchy"""
    zabbix = request.app.state.zabbix
    groupids = get_monitored_groupids()
    loop = asyncio.get_event_loop()
    devices = await loop.run_in_executor(executor, lambda: zabbix.get_all_hosts(group_ids=groupids))

    if region:
        devices = [d for d in devices if d['region'] == region]

    if len(devices) > limit:
        devices = devices[:limit]

    nodes = []
    edges = []

    # Identify core routers and categorize devices
    from collections import defaultdict
    core_routers = [d for d in devices if d.get('device_type') == 'Core Router']
    branch_switches = [d for d in devices if d.get('device_type') in ['Switch', 'L3 Switch', 'Branch Switch']]
    end_devices = [d for d in devices if d not in core_routers and d not in branch_switches]

    if view == 'hierarchical':
        # Level 0: Core Routers
        for router in core_routers:
            status = router.get('ping_status', 'Unknown')
            # Fetch interface statistics for core routers
            try:
                interfaces = await loop.run_in_executor(executor, lambda r=router: zabbix.get_router_interfaces(r['hostid']))
                total_interfaces = len(interfaces)
                up_interfaces = sum(1 for iface in interfaces.values() if iface.get('status') == 'up')
                total_bandwidth_in = sum(iface.get('bandwidth_in', 0) for iface in interfaces.values())
                total_bandwidth_out = sum(iface.get('bandwidth_out', 0) for iface in interfaces.values())

                interface_info = f"\n{up_interfaces}/{total_interfaces} interfaces up"
                bandwidth_info = f"\nIn: {total_bandwidth_in/1000000:.1f} Mbps | Out: {total_bandwidth_out/1000000:.1f} Mbps"
            except Exception as e:
                print(f"[ERROR] Failed to get interfaces for {router['display_name']}: {e}")
                interface_info = ""
                bandwidth_info = ""
                interfaces = {}

            nodes.append({
                'id': router['hostid'],
                'label': router['display_name'],
                'title': f"{router['display_name']}\n{router['ip']}\nStatus: {status}{interface_info}{bandwidth_info}",
                'group': 'core',
                'level': 0,
                'size': 35,
                'color': '#FF6B35' if status == 'Up' else '#dc3545',
                'shape': 'diamond',
                'deviceType': 'Core Router',
                'interfaces': interfaces
            })

        # Level 1: Branch Switches (connect to core routers)
        branches_by_region = defaultdict(list)
        for switch in branch_switches:
            branches_by_region[switch.get('branch', 'Unknown')].append(switch)

        for branch_name, switches in branches_by_region.items():
            for switch in switches:
                status = switch.get('ping_status', 'Unknown')
                nodes.append({
                    'id': switch['hostid'],
                    'label': switch['display_name'][:20],
                    'title': f"{switch['display_name']}\n{switch['ip']}\nBranch: {branch_name}\nStatus: {status}",
                    'group': 'branch',
                    'level': 1,
                    'size': 20,
                    'color': '#14b8a6' if status == 'Up' else '#dc3545',
                    'shape': 'box',
                    'branch': branch_name
                })

                # Connect branch switches to core routers
                if core_routers:
                    core_router = core_routers[hash(switch['hostid']) % len(core_routers)]

                    # Try to find matching interface on core router for this branch
                    edge_label = ""
                    edge_title = f"Link: {core_router['display_name']} → {switch['display_name']}"

                    # Get interfaces for this core router to find bandwidth for this connection
                    try:
                        router_interfaces = core_router.get('interfaces', {})
                        # Look for interface connected to this branch
                        branch_name_clean = switch.get('branch', '').lower().replace(' ', '_')

                        for iface_name, iface_data in router_interfaces.items():
                            iface_desc = iface_data.get('description', '').lower()
                            # Match if interface description contains branch name
                            if branch_name_clean and branch_name_clean in iface_desc:
                                bw_in_mbps = iface_data.get('bandwidth_in', 0) / 1000000
                                bw_out_mbps = iface_data.get('bandwidth_out', 0) / 1000000
                                edge_label = f"↓{bw_in_mbps:.1f}M ↑{bw_out_mbps:.1f}M"
                                edge_title += f"\nInterface: {iface_name}\n↓ {bw_in_mbps:.2f} Mbps\n↑ {bw_out_mbps:.2f} Mbps"
                                break
                    except Exception as e:
                        print(f"[WARN] Could not get interface bandwidth: {e}")

                    edges.append({
                        'from': core_router['hostid'],
                        'to': switch['hostid'],
                        'color': '#14b8a6' if status == 'Up' else '#dc3545',
                        'width': 2,
                        'label': edge_label,
                        'title': edge_title,
                        'font': {'size': 10, 'color': '#00d9ff', 'strokeWidth': 2, 'strokeColor': '#000'}
                    })

        # Level 2: End Devices (connect to branch switches)
        device_types = defaultdict(list)
        for device in end_devices[:100]:
            device_types[device.get('device_type', 'Unknown')].append(device)

        for device_type, type_devices in device_types.items():
            for device in type_devices[:20]:
                status = device.get('ping_status', 'Unknown')
                branch = device.get('branch', 'Unknown')

                # Determine icon shape based on device type
                if 'ATM' in device_type:
                    shape = 'triangle'
                    color = '#9333EA' if status == 'Up' else '#dc3545'
                elif 'NVR' in device_type or 'Camera' in device_type:
                    shape = 'star'
                    color = '#3B82F6' if status == 'Up' else '#dc3545'
                elif 'Access Point' in device_type or 'WiFi' in device_type:
                    shape = 'dot'
                    color = '#10B981' if status == 'Up' else '#dc3545'
                else:
                    shape = 'dot'
                    color = '#6B7280' if status == 'Up' else '#dc3545'

                nodes.append({
                    'id': device['hostid'],
                    'label': '',
                    'title': f"{device['display_name']}\n{device['ip']}\nType: {device_type}\nBranch: {branch}\nStatus: {status}",
                    'group': device_type,
                    'level': 2,
                    'size': 10,
                    'color': color,
                    'shape': shape,
                    'deviceType': device_type
                })

                # Connect to branch switch in same branch
                branch_switch_in_branch = [s for s in branch_switches if s.get('branch') == branch]
                if branch_switch_in_branch:
                    target_switch = branch_switch_in_branch[hash(device['hostid']) % len(branch_switch_in_branch)]
                    edges.append({
                        'from': target_switch['hostid'],
                        'to': device['hostid'],
                        'color': color,
                        'width': 0.5,
                        'dashes': status != 'Up'
                    })
                elif branch_switches:
                    target_switch = branch_switches[hash(device['hostid']) % len(branch_switches)]
                    edges.append({
                        'from': target_switch['hostid'],
                        'to': device['hostid'],
                        'color': color,
                        'width': 0.5,
                        'dashes': True
                    })

    return {
        'nodes': nodes,
        'edges': edges,
        'stats': {
            'total_nodes': len(nodes),
            'total_edges': len(edges),
            'core_routers': len(core_routers),
            'branch_switches': len(branch_switches),
            'end_devices': len(end_devices),
            'total_devices': len(devices)
        }
    }

@app.get("/api/reports/downtime")
async def api_downtime_report_legacy(
    request: Request,
    period: str = 'weekly',
    region: Optional[str] = None,
    device_type: Optional[str] = None
):
    """Legacy route - no auth for backward compatibility"""
    zabbix = request.app.state.zabbix
    devices = await run_in_executor(zabbix.get_all_hosts)

    if region:
        devices = [d for d in devices if d['region'] == region]
    if device_type:
        devices = [d for d in devices if d['device_type'] == device_type]

    # Map period to hours
    period_hours = 168 if period == 'weekly' else 720  # 7 days or 30 days

    report = {
        'period': period,
        'generated_at': datetime.now().isoformat(),
        'total_devices': len(devices),
        'summary': {
            'total_downtime_hours': 0,
            'average_availability': 0,
            'devices_with_downtime': 0
        },
        'devices': []
    }

    for device in devices:
        # Calculate real availability from Zabbix history
        availability_data = await run_in_executor(
            zabbix.calculate_availability,
            device['hostid'],
            period_hours
        )

        report['devices'].append({
            'hostid': device['hostid'],
            'name': device['display_name'],
            'region': device['region'],
            'branch': device['branch'],
            'device_type': device['device_type'],
            'downtime_hours': availability_data['downtime_hours'],
            'availability_percent': availability_data['availability_percent'],
            'incidents': availability_data['incidents']
        })

        report['summary']['total_downtime_hours'] += availability_data['downtime_hours']
        if availability_data['downtime_hours'] > 0:
            report['summary']['devices_with_downtime'] += 1

    report['summary']['average_availability'] = round(
        sum(d['availability_percent'] for d in report['devices']) / len(devices) if devices else 0,
        2
    )

    return report

@app.get("/api/reports/mttr-extended")
async def api_mttr_extended_legacy(request: Request):
    """Legacy route - redirects to v1"""
    return await get_mttr_extended(request)

@app.post("/api/host/create")
async def api_create_host_legacy(request: Request, host_data: CreateHostRequest):
    """Legacy route - redirects to v1"""
    return await create_host(request, host_data)

@app.put("/api/host/update/{hostid}")
async def api_update_host_legacy(request: Request, hostid: str, host_data: UpdateHostRequest):
    """Legacy route - redirects to v1"""
    return await update_host(request, hostid, host_data)

@app.delete("/api/host/delete/{hostid}")
async def api_delete_host_legacy(request: Request, hostid: str):
    """Legacy route - redirects to v1"""
    return await delete_host(request, hostid)

# SSE endpoint for old frontend (dummy response)
@app.get("/stream/updates")
async def stream_updates_legacy():
    """Legacy SSE endpoint - dummy response (WebSocket is better)"""
    async def generate():
        # Keep connection alive with heartbeat
        while True:
            yield f"data: {json.dumps({'type': 'heartbeat', 'message': 'Connected', 'timestamp': datetime.now().isoformat()})}\n\n"
            await asyncio.sleep(30)

    from starlette.responses import StreamingResponse
    return StreamingResponse(generate(), media_type="text/event-stream")

# Serve old frontend pages with templates
# ============================================
# Page Routes - MOVED TO routers/pages.py
# ============================================
# These routes have been extracted to routers/pages.py for better organization
# Keeping here commented out for reference during migration

# ============================================
# Host Group Configuration Endpoints
# ============================================

# EXTRACTED TO: routers/config.py
# @app.get("/api/v1/config/zabbix-hostgroups")
# @app.get("/api/v1/config/monitored-hostgroups")
# @app.post("/api/v1/config/monitored-hostgroups")
# @app.get("/api/v1/config/georgian-cities")

# ============================================
# Authentication Endpoints
# ============================================

# ============================================
# Authentication Routes - MOVED TO routers/auth.py
# ============================================
# These routes have been extracted to routers/auth.py for better organization
# Includes: /api/v1/auth/login, /api/v1/auth/register, /api/v1/auth/me
# and all /api/v1/users/* endpoints

# ============================================
# Bulk Operations Endpoints
# ============================================

# EXTRACTED TO: routers/bulk.py
# @app.get("/api/v1/bulk/template")
# @app.post("/api/v1/bulk/import")
# @app.post("/api/v1/bulk/update")
# @app.post("/api/v1/bulk/delete")
# @app.get("/api/v1/bulk/export/csv")
# @app.get("/api/v1/bulk/export/excel")


# ============================================
# Frontend Routes (Serve React App)
# ============================================
# Note: In development, React runs on port 3000 (npm run dev)
# In production, build React first (npm run build), then uncomment below:

# @app.get("/", response_class=HTMLResponse)
# async def index(request: Request):
#     """Serve React app"""
#     return templates.TemplateResponse("index.html", {"request": request})
#
# @app.get("/{full_path:path}", response_class=HTMLResponse)
# async def catch_all(request: Request, full_path: str):
#     """Catch all routes for React Router"""
#     return templates.TemplateResponse("index.html", {"request": request})

# ============================================
# SSH Terminal API
# ============================================

@app.post("/api/v1/ssh/connect")
async def ssh_connect(
    ssh_request: SSHConnectRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Connect to device via SSH"""
    import paramiko
    import io

    try:
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect with timeout
        ssh.connect(
            hostname=ssh_request.host,
            port=ssh_request.port,
            username=ssh_request.username,
            password=ssh_request.password,
            timeout=10,
            look_for_keys=False,
            allow_agent=False
        )

        # Execute a simple command to verify connection
        stdin, stdout, stderr = ssh.exec_command('show version | include uptime' if '.5' in ssh_request.host else 'hostname')
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')

        ssh.close()

        return {
            'success': True,
            'output': output if output else 'Connected successfully',
            'message': f'SSH connection to {ssh_request.host} established'
        }

    except paramiko.AuthenticationException:
        return JSONResponse(
            status_code=401,
            content={'success': False, 'error': 'Authentication failed. Please check username and password.'}
        )
    except paramiko.SSHException as e:
        return JSONResponse(
            status_code=500,
            content={'success': False, 'error': f'SSH error: {str(e)}'}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'success': False, 'error': f'Connection failed: {str(e)}'}
        )

# ============================================
# WebSocket Endpoint for Real-time Notifications
# ============================================
# EXTRACTED TO: routers/websockets.py
# class ConnectionManager
# manager = ConnectionManager()
# @router.websocket("/ws/router-interfaces/{hostid}")
# @router.websocket("/ws/notifications")


# ============================================
# Settings Routes
# ============================================

# Settings page route - MOVED TO routers/pages.py


@app.get("/api/v1/settings/zabbix")
async def get_zabbix_settings(current_user: User = Depends(get_current_active_user)):
    """Get current Zabbix settings"""
    import os
    return {
        "zabbix_url": os.getenv("ZABBIX_URL", ""),
        "zabbix_user": os.getenv("ZABBIX_USER", "")
    }


@app.post("/api/v1/settings/test-zabbix")
async def test_zabbix_settings(
    config: dict,
    current_user: User = Depends(get_current_active_user)
):
    """Test Zabbix connection"""
    from pyzabbix import ZabbixAPI

    try:
        zapi = ZabbixAPI(config["url"].replace('/api_jsonrpc.php', ''), timeout=10)
        zapi.login(config["user"], config["password"])
        version = zapi.apiinfo.version()

        return {
            "success": True,
            "version": version
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/v1/settings/zabbix")
async def save_zabbix_settings(
    request: Request,
    config: dict,
    current_user: User = Depends(get_current_active_user)
):
    """Save Zabbix settings and reconfigure"""
    from dotenv import set_key
    import os

    try:
        # Save to .env file
        env_file = ".env"
        set_key(env_file, "ZABBIX_URL", config["zabbix_url"])
        set_key(env_file, "ZABBIX_USER", config["zabbix_user"])
        set_key(env_file, "ZABBIX_PASSWORD", config["zabbix_password"])

        # Update environment variables
        os.environ["ZABBIX_URL"] = config["zabbix_url"]
        os.environ["ZABBIX_USER"] = config["zabbix_user"]
        os.environ["ZABBIX_PASSWORD"] = config["zabbix_password"]

        # Reconfigure Zabbix client
        request.app.state.zabbix.reconfigure(
            url=config["zabbix_url"],
            user=config["zabbix_user"],
            password=config["zabbix_password"]
        )

        return {"success": True, "message": "Settings saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
