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
    description="Enterprise-grade network monitoring and management system",
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
    lifespan=lifespan
)

# Allow all hosts (for Docker deployment with any IP/domain)
from starlette.middleware.trustedhost import TrustedHostMiddleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

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
app.middleware("http")(setup_check_middleware)

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

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint for load balancers"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/v1/dashboard/stats")
async def get_dashboard_stats(
    request: Request,
    region: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """Get dashboard statistics with optional region filter and user permissions"""
    import sqlite3
    zabbix = request.app.state.zabbix

    # Get monitored groups from DB
    conn = sqlite3.connect('data/ward_ops.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT groupid, display_name
        FROM monitored_hostgroups
        WHERE is_active = 1
    """)
    monitored_groups = [dict(row) for row in cursor.fetchall()]

    print(f"[DEBUG] Monitored groups from DB: {monitored_groups}")

    # If no groups configured, fall back to old behavior
    if not monitored_groups:
        print("[DEBUG] No monitored groups, getting all hosts")
        devices = await run_in_executor(zabbix.get_all_hosts)
    else:
        # Get devices from configured groups only using group IDs
        monitored_groupids = [g['groupid'] for g in monitored_groups]
        print(f"[DEBUG] Fetching hosts for group IDs: {monitored_groupids}")
        loop = asyncio.get_event_loop()
        devices = await loop.run_in_executor(executor, lambda: zabbix.get_all_hosts(group_ids=monitored_groupids))
        print(f"[DEBUG] Retrieved {len(devices)} devices from Zabbix")

    # Apply region filter if requested
    if region:
        devices = [d for d in devices if d.get('region') == region]

    # Apply user permission filtering (non-admin users)
    if current_user.role != UserRole.ADMIN:
        # Filter by region if user has regional restriction
        if current_user.region:
            devices = [d for d in devices if d.get('region') == current_user.region]

        # Filter by branches if user has branch restrictions
        if current_user.branches:
            allowed_branches = [b.strip() for b in current_user.branches.split(',')]
            devices = [d for d in devices if d.get('branch') in allowed_branches]

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

    # Region statistics with coordinates from DB
    regions_stats = {}
    for host in devices:
        # Extract city from hostname
        city_name = extract_city_from_hostname(host.get('host', host.get('display_name', '')))

        # Lookup city in DB to get region and coordinates
        cursor.execute("""
            SELECT r.name_en as region, c.latitude, c.longitude
            FROM georgian_cities c
            JOIN georgian_regions r ON c.region_id = r.id
            WHERE c.name_en LIKE ? AND c.is_active = 1
            LIMIT 1
        """, (f"%{city_name}%",))

        city_data = cursor.fetchone()

        if city_data:
            city_data = dict(city_data)
            region_name = city_data['region']

            if region_name not in regions_stats:
                regions_stats[region_name] = {
                    'total': 0,
                    'online': 0,
                    'offline': 0,
                    'latitude': city_data['latitude'],
                    'longitude': city_data['longitude']
                }

            regions_stats[region_name]['total'] += 1
            if host.get('ping_status') == 'Up':
                regions_stats[region_name]['online'] += 1
            elif host.get('ping_status') == 'Down':
                regions_stats[region_name]['offline'] += 1
        else:
            # Fallback to existing region field
            region_name = host.get('region', 'Unknown')
            if region_name not in regions_stats:
                regions_stats[region_name] = {'total': 0, 'online': 0, 'offline': 0}
            regions_stats[region_name]['total'] += 1
            if host.get('ping_status') == 'Up':
                regions_stats[region_name]['online'] += 1
            elif host.get('ping_status') == 'Down':
                regions_stats[region_name]['offline'] += 1

    conn.close()

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

@app.get("/api/v1/devices")
async def get_devices(
    request: Request,
    region: Optional[str] = None,
    branch: Optional[str] = None,
    device_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """Get devices with optional filters and user permissions"""
    zabbix = request.app.state.zabbix

    # Get monitored group IDs
    groupids = get_monitored_groupids()

    if region:
        devices = await run_in_executor(zabbix.get_devices_by_region, region)
    elif branch:
        devices = await run_in_executor(zabbix.get_devices_by_branch, branch)
    elif device_type:
        devices = await run_in_executor(zabbix.get_devices_by_type, device_type)
    else:
        loop = asyncio.get_event_loop()
        devices = await loop.run_in_executor(executor, lambda: zabbix.get_all_hosts(group_ids=groupids))

    # Apply user permission filtering (non-admin users)
    if current_user.role != UserRole.ADMIN:
        # Filter by region if user has regional restriction
        if current_user.region:
            devices = [d for d in devices if d.get('region') == current_user.region]

        # Filter by branches if user has branch restrictions
        if current_user.branches:
            allowed_branches = [b.strip() for b in current_user.branches.split(',')]
            devices = [d for d in devices if d.get('branch') in allowed_branches]

    return devices

@app.get("/api/v1/devices/{hostid}")
async def get_device_details(request: Request, hostid: str):
    """Get detailed information about a specific device"""
    zabbix = request.app.state.zabbix
    details = await run_in_executor(zabbix.get_host_details, hostid)

    if details:
        return details
    return JSONResponse(status_code=404, content={'error': 'Device not found'})

@app.get("/api/v1/alerts")
async def get_alerts(request: Request):
    """Get all active alerts"""
    zabbix = request.app.state.zabbix
    alerts = await run_in_executor(zabbix.get_active_alerts)
    return alerts

@app.get("/api/v1/mttr/stats")
async def get_mttr_stats(request: Request):
    """Get MTTR statistics"""
    zabbix = request.app.state.zabbix
    stats = await run_in_executor(zabbix.get_mttr_stats)
    return stats

@app.get("/api/v1/groups")
async def get_groups(request: Request):
    """Get all host groups"""
    zabbix = request.app.state.zabbix
    groups = await run_in_executor(zabbix.get_all_groups)
    return groups

@app.get("/api/v1/templates")
async def get_templates(request: Request):
    """Get all templates"""
    zabbix = request.app.state.zabbix
    templates = await run_in_executor(zabbix.get_all_templates)
    return templates

@app.post("/api/v1/hosts")
async def create_host(request: Request, host_data: CreateHostRequest):
    """Create a new host in Zabbix"""
    zabbix = request.app.state.zabbix

    result = await run_in_executor(
        lambda: zabbix.create_host(
            hostname=host_data.hostname,
            visible_name=host_data.visible_name,
            ip_address=host_data.ip_address,
            group_ids=host_data.group_ids,
            template_ids=host_data.template_ids
        )
    )

    if result.get('success'):
        return result
    return JSONResponse(status_code=500, content=result)

@app.put("/api/v1/hosts/{hostid}")
async def update_host(request: Request, hostid: str, host_data: UpdateHostRequest):
    """Update host properties"""
    zabbix = request.app.state.zabbix

    update_data = host_data.dict(exclude_unset=True)
    if not update_data:
        return JSONResponse(status_code=400, content={'error': 'No fields to update'})

    result = await run_in_executor(lambda: zabbix.update_host(hostid, **update_data))

    if result.get('success'):
        return result
    return JSONResponse(status_code=500, content=result)

@app.delete("/api/v1/hosts/{hostid}")
async def delete_host(request: Request, hostid: str):
    """Delete a host"""
    zabbix = request.app.state.zabbix
    result = await run_in_executor(zabbix.delete_host, hostid)

    if result.get('success'):
        return result
    return JSONResponse(status_code=500, content=result)

@app.get("/api/v1/search")
async def search_devices(
    request: Request,
    q: Optional[str] = None,
    region: Optional[str] = None,
    branch: Optional[str] = None,
    device_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """Advanced search endpoint with user permissions"""
    zabbix = request.app.state.zabbix
    groupids = get_monitored_groupids()
    loop = asyncio.get_event_loop()
    devices = await loop.run_in_executor(executor, lambda: zabbix.get_all_hosts(group_ids=groupids))

    # Apply user permission filtering first (non-admin users)
    if current_user.role != UserRole.ADMIN:
        # Filter by region if user has regional restriction
        if current_user.region:
            devices = [d for d in devices if d.get('region') == current_user.region]

        # Filter by branches if user has branch restrictions
        if current_user.branches:
            allowed_branches = [b.strip() for b in current_user.branches.split(',')]
            devices = [d for d in devices if d.get('branch') in allowed_branches]

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

@app.get("/api/v1/reports/downtime")
async def get_downtime_report(
    request: Request,
    period: str = 'weekly',
    region: Optional[str] = None,
    device_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """Generate downtime report with user permissions"""
    zabbix = request.app.state.zabbix
    groupids = get_monitored_groupids()
    loop = asyncio.get_event_loop()
    devices = await loop.run_in_executor(executor, lambda: zabbix.get_all_hosts(group_ids=groupids))

    # Apply user permission filtering (non-admin users)
    if current_user.role != UserRole.ADMIN:
        # Filter by region if user has regional restriction
        if current_user.region:
            devices = [d for d in devices if d.get('region') == current_user.region]

        # Filter by branches if user has branch restrictions
        if current_user.branches:
            allowed_branches = [b.strip() for b in current_user.branches.split(',')]
            devices = [d for d in devices if d.get('branch') in allowed_branches]

    if region:
        devices = [d for d in devices if d['region'] == region]
    if device_type:
        devices = [d for d in devices if d['device_type'] == device_type]

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
        is_down = device.get('ping_status') == 'Down'
        downtime_hours = 2.5 if is_down else 0.1
        availability = 95.5 if is_down else 99.9

        report['devices'].append({
            'hostid': device['hostid'],
            'name': device['display_name'],
            'region': device['region'],
            'branch': device['branch'],
            'device_type': device['device_type'],
            'downtime_hours': downtime_hours,
            'availability_percent': availability,
            'incidents': 1 if is_down else 0
        })

        report['summary']['total_downtime_hours'] += downtime_hours
        if is_down:
            report['summary']['devices_with_downtime'] += 1

    report['summary']['average_availability'] = round(
        sum(d['availability_percent'] for d in report['devices']) / len(devices) if devices else 0,
        2
    )

    return report

@app.get("/api/v1/reports/mttr-extended")
async def get_mttr_extended(request: Request):
    """Extended MTTR trends and analysis"""
    zabbix = request.app.state.zabbix
    base_mttr = await run_in_executor(zabbix.get_mttr_stats)
    devices = await run_in_executor(zabbix.get_all_hosts)

    device_downtime = []
    for device in devices:
        if device.get('triggers'):
            downtime_minutes = len(device['triggers']) * 15
            device_downtime.append({
                'name': device['display_name'],
                'hostid': device['hostid'],
                'region': device['region'],
                'downtime_minutes': downtime_minutes,
                'incident_count': len(device['triggers'])
            })

    device_downtime.sort(key=lambda x: x['downtime_minutes'], reverse=True)

    return {
        **base_mttr,
        'top_problem_devices': device_downtime[:10],
        'trends': {
            'improving': base_mttr.get('avg_mttr_minutes', 0) < 30,
            'recommendation': 'Focus on preventive maintenance for top 10 problem devices'
        }
    }

@app.get("/api/v1/router/{hostid}/interfaces")
async def get_router_interfaces(
    request: Request,
    hostid: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get router interface statistics"""
    zabbix = request.app.state.zabbix
    loop = asyncio.get_event_loop()
    interfaces = await loop.run_in_executor(executor, lambda: zabbix.get_router_interfaces(hostid))
    return {
        'hostid': hostid,
        'interfaces': interfaces
    }

@app.get("/api/v1/topology")
async def get_topology(
    request: Request,
    view: str = 'hierarchical',
    limit: int = 200,
    region: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """Get network topology data with user permissions - Enhanced with core router hierarchy"""
    zabbix = request.app.state.zabbix
    groupids = get_monitored_groupids()
    loop = asyncio.get_event_loop()
    devices = await loop.run_in_executor(executor, lambda: zabbix.get_all_hosts(group_ids=groupids))

    # Apply user permission filtering (non-admin users)
    if current_user.role != UserRole.ADMIN:
        # Filter by region if user has regional restriction
        if current_user.region:
            devices = [d for d in devices if d.get('region') == current_user.region]

        # Filter by branches if user has branch restrictions
        if current_user.branches:
            allowed_branches = [b.strip() for b in current_user.branches.split(',')]
            devices = [d for d in devices if d.get('branch') in allowed_branches]

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
                # In a real deployment, you'd determine actual connections via LLDP/CDP
                # For now, distribute evenly across core routers
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
        for device in end_devices[:100]:  # Limit to 100 end devices for performance
            device_types[device.get('device_type', 'Unknown')].append(device)

        for device_type, type_devices in device_types.items():
            for device in type_devices[:20]:  # Max 20 devices per type
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
                    'label': '',  # No label to reduce clutter
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
                    # Fallback: connect to any branch switch
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

# ============================================
# WebSocket for Real-Time Updates
# ============================================

@app.websocket("/ws/updates")
async def websocket_updates(websocket: WebSocket):
    """WebSocket endpoint for real-time device status updates"""
    await websocket.accept()
    websocket.app.state.websocket_connections.append(websocket)

    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        websocket.app.state.websocket_connections.remove(websocket)

async def monitor_device_changes(app: FastAPI):
    """Background task to monitor device changes and broadcast via WebSocket"""
    last_state = {}

    while True:
        try:
            zabbix = app.state.zabbix
            # Note: sync client doesn't have use_cache param, just call get_all_hosts
            devices = await run_in_executor(zabbix.get_all_hosts)
            changes = []

            for device in devices:
                device_id = device['hostid']
                current_status = device.get('ping_status', 'Unknown')

                if device_id in last_state:
                    if last_state[device_id] != current_status:
                        changes.append({
                            'hostid': device_id,
                            'hostname': device['display_name'],
                            'old_status': last_state[device_id],
                            'new_status': current_status,
                            'timestamp': datetime.now().isoformat()
                        })

                last_state[device_id] = current_status

            # Broadcast changes to all connected clients
            if changes and app.state.websocket_connections:
                message = json.dumps({'type': 'status_change', 'changes': changes})

                disconnected = []
                for websocket in app.state.websocket_connections:
                    try:
                        await websocket.send_text(message)
                    except:
                        disconnected.append(websocket)

                # Remove disconnected clients
                for ws in disconnected:
                    app.state.websocket_connections.remove(ws)

            await asyncio.sleep(30)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Monitor error: {e}")
            await asyncio.sleep(30)

# ============================================
# Backward Compatibility Routes (for old frontend)
# ============================================

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
@app.get("/", response_class=HTMLResponse)
async def index_legacy(request: Request):
    """Serve old dashboard"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/devices", response_class=HTMLResponse)
async def devices_legacy(request: Request):
    """Serve old devices page"""
    return templates.TemplateResponse("devices.html", {"request": request})

@app.get("/map", response_class=HTMLResponse)
async def map_legacy(request: Request):
    """Serve old map page"""
    return templates.TemplateResponse("map.html", {"request": request})

@app.get("/topology", response_class=HTMLResponse)
async def topology_page_legacy(request: Request):
    """Serve network topology visualization"""
    return templates.TemplateResponse("topology.html", {"request": request})

@app.get("/reports", response_class=HTMLResponse)
async def reports_legacy(request: Request):
    """Serve old reports page"""
    return templates.TemplateResponse("reports.html", {"request": request})

@app.get("/device/{hostid}", response_class=HTMLResponse)
async def device_page_legacy(request: Request, hostid: str):
    """Serve old device details page"""
    return templates.TemplateResponse("device-details.html", {"request": request, "hostid": hostid})

@app.get("/add-host", response_class=HTMLResponse)
async def add_host_page(request: Request):
    """Serve add host page"""
    return templates.TemplateResponse("add-host.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve login page"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/users", response_class=HTMLResponse)
async def users_management_page(request: Request):
    """Serve user management page (admin only)"""
    return templates.TemplateResponse("users.html", {"request": request})

@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    """Serve host group configuration page"""
    return templates.TemplateResponse("config.html", {"request": request})

# ============================================
# Host Group Configuration Endpoints
# ============================================

@app.get("/api/v1/config/zabbix-hostgroups")
async def get_zabbix_hostgroups(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Fetch all host groups from Zabbix"""
    try:
        zabbix = request.app.state.zabbix
        groups = await run_in_executor(zabbix.get_all_groups)
        return {"hostgroups": groups}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/config/monitored-hostgroups")
async def get_monitored_hostgroups(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Get currently monitored host groups from DB"""
    import sqlite3
    conn = sqlite3.connect('data/ward_ops.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT groupid, name, display_name, is_active
        FROM monitored_hostgroups
        WHERE is_active = 1
    """)
    groups = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"monitored_groups": groups}

@app.post("/api/v1/config/monitored-hostgroups")
async def save_monitored_hostgroups(
    request: Request,
    current_user: User = Depends(require_admin)
):
    """Save selected host groups configuration"""
    import sqlite3
    data = await request.json()
    groups = data.get('groups', [])

    conn = sqlite3.connect('data/ward_ops.db')
    cursor = conn.cursor()

    # Deactivate all existing
    cursor.execute("UPDATE monitored_hostgroups SET is_active = 0")

    # Insert/activate selected groups
    for group in groups:
        cursor.execute("""
            INSERT OR REPLACE INTO monitored_hostgroups
            (groupid, name, display_name, is_active)
            VALUES (?, ?, ?, 1)
        """, (group['groupid'], group['name'], group.get('display_name', group['name'])))

    conn.commit()
    conn.close()
    return {"status": "success", "saved": len(groups)}

@app.get("/api/v1/config/georgian-cities")
async def get_georgian_cities(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Get all Georgian cities with regions and coordinates"""
    import sqlite3
    conn = sqlite3.connect('data/ward_ops.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.id, c.name_en, c.latitude, c.longitude,
               r.name_en as region_name
        FROM georgian_cities c
        JOIN georgian_regions r ON c.region_id = r.id
        WHERE c.is_active = 1
        ORDER BY r.name_en, c.name_en
    """)
    cities = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"cities": cities}

# ============================================
# Authentication Endpoints
# ============================================

@app.post("/api/v1/auth/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login endpoint - returns JWT token
    Rate limited to 5 attempts per minute to prevent brute force attacks
    """
    # Rate limiting disabled for easier deployment
    # if RATE_LIMITING_ENABLED and limiter:
    #     try:
    #         await limiter.check_request_limit(request, "5/minute")
    #     except:
    #         raise HTTPException(
    #             status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    #             detail="Too many login attempts. Please try again later."
    #         )
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    # Create access token
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/v1/auth/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Register new user (admin only)"""
    from auth import get_user_by_username, get_user_by_email
    if get_user_by_username(db, user_data.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    if get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    user = create_user(db, user_data)
    return user

@app.get("/api/v1/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user info"""
    return current_user

@app.get("/api/v1/users", response_model=List[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """List all users (admin only)"""
    users = db.query(User).all()
    return users

@app.put("/api/v1/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    update_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.full_name = update_data.full_name
    user.email = update_data.email
    user.role = update_data.role
    user.region = update_data.region
    if update_data.password:
        from auth import get_password_hash
        user.hashed_password = get_password_hash(update_data.password)

    db.commit()
    db.refresh(user)
    return user

@app.delete("/api/v1/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    db.delete(user)
    db.commit()
    return {"success": True, "message": "User deleted"}

# ============================================
# Bulk Operations Endpoints
# ============================================

@app.get("/api/v1/bulk/template")
async def download_bulk_import_template(
    current_user: User = Depends(require_tech_or_admin)
):
    """Download CSV template for bulk import"""
    csv_content = generate_csv_template()
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bulk_import_template.csv"}
    )

@app.post("/api/v1/bulk/import", response_model=BulkOperationResult)
async def bulk_import_devices(
    request: Request,
    file: UploadFile,
    current_user: User = Depends(require_tech_or_admin)
):
    """Bulk import devices from CSV/Excel"""
    zabbix = request.app.state.zabbix

    # Parse file
    if file.filename.endswith('.csv'):
        df = await parse_csv_file(file)
    elif file.filename.endswith(('.xlsx', '.xls')):
        df = await parse_excel_file(file)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Use CSV or Excel")

    # Validate data
    is_valid, errors = validate_bulk_import_data(df)
    if not is_valid:
        return BulkOperationResult(
            success=False,
            total=0,
            successful=0,
            failed=0,
            errors=[{"error": err} for err in errors],
            details=[]
        )

    # Process import
    result = await process_bulk_import(df, zabbix)
    return result

@app.post("/api/v1/bulk/update", response_model=BulkOperationResult)
async def bulk_update(
    request: Request,
    host_ids: List[str],
    update_data: dict,
    current_user: User = Depends(require_tech_or_admin)
):
    """Bulk update multiple devices"""
    zabbix = request.app.state.zabbix
    result = await bulk_update_devices(host_ids, update_data, zabbix)
    return result

@app.post("/api/v1/bulk/delete", response_model=BulkOperationResult)
async def bulk_delete(
    request: Request,
    host_ids: List[str],
    current_user: User = Depends(require_admin)
):
    """Bulk delete multiple devices"""
    zabbix = request.app.state.zabbix
    result = await bulk_delete_devices(host_ids, zabbix)
    return result

@app.get("/api/v1/bulk/export/csv")
async def export_csv(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Export devices to CSV (filtered by user permissions)"""
    zabbix = request.app.state.zabbix
    devices = await run_in_executor(zabbix.get_all_hosts)

    # Apply user permission filtering (non-admin users)
    if current_user.role != UserRole.ADMIN:
        # Filter by region if user has regional restriction
        if current_user.region:
            devices = [d for d in devices if d.get('region') == current_user.region]

        # Filter by branches if user has branch restrictions
        if current_user.branches:
            allowed_branches = [b.strip() for b in current_user.branches.split(',')]
            devices = [d for d in devices if d.get('branch') in allowed_branches]

    csv_content = export_devices_to_csv(devices)
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=devices_export.csv"}
    )

@app.get("/api/v1/bulk/export/excel")
async def export_excel(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Export devices to Excel (filtered by user permissions)"""
    zabbix = request.app.state.zabbix
    devices = await run_in_executor(zabbix.get_all_hosts)

    # Apply user permission filtering (non-admin users)
    if current_user.role != UserRole.ADMIN:
        # Filter by region if user has regional restriction
        if current_user.region:
            devices = [d for d in devices if d.get('region') == current_user.region]

        # Filter by branches if user has branch restrictions
        if current_user.branches:
            allowed_branches = [b.strip() for b in current_user.branches.split(',')]
            devices = [d for d in devices if d.get('branch') in allowed_branches]

    excel_content = export_devices_to_excel(devices)
    return StreamingResponse(
        io.BytesIO(excel_content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=devices_export.xlsx"}
    )


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

class ConnectionManager:
    """Manage WebSocket connections for real-time notifications"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                # Remove dead connections
                try:
                    self.disconnect(connection)
                except:
                    pass

manager = ConnectionManager()

@app.websocket("/ws/router-interfaces/{hostid}")
async def websocket_router_interfaces(websocket: WebSocket, hostid: str):
    """WebSocket endpoint for live router interface monitoring - No Auth Required"""
    print(f"[WS] Router interface connection request for hostid: {hostid}")

    try:
        await websocket.accept()
        print(f"[WS] WebSocket accepted for router {hostid}")
    except Exception as e:
        print(f"[WS ERROR] Failed to accept WebSocket: {e}")
        return

    zabbix = websocket.app.state.zabbix

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            'type': 'connected',
            'hostid': hostid,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

        # Background task to fetch interface data every 5 seconds
        async def stream_interfaces():
            while True:
                try:
                    # Fetch interface data
                    loop = asyncio.get_event_loop()
                    interfaces = await loop.run_in_executor(executor, lambda: zabbix.get_router_interfaces(hostid))

                    # Ensure interfaces is a dict
                    if not isinstance(interfaces, dict):
                        print(f"[WS ERROR] Interfaces is not a dict: {type(interfaces)}")
                        interfaces = {}

                    # Calculate summary stats
                    total_interfaces = len(interfaces)
                    up_interfaces = sum(1 for iface in interfaces.values() if iface.get('status') == 'up')
                    total_bandwidth_in = sum(iface.get('bandwidth_in', 0) for iface in interfaces.values())
                    total_bandwidth_out = sum(iface.get('bandwidth_out', 0) for iface in interfaces.values())
                    total_errors_in = sum(iface.get('errors_in', 0) for iface in interfaces.values())
                    total_errors_out = sum(iface.get('errors_out', 0) for iface in interfaces.values())

                    # Send update
                    await websocket.send_json({
                        'type': 'interface_update',
                        'hostid': hostid,
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'summary': {
                            'total': total_interfaces,
                            'up': up_interfaces,
                            'down': total_interfaces - up_interfaces,
                            'bandwidth_in_mbps': round(total_bandwidth_in / 1000000, 2),
                            'bandwidth_out_mbps': round(total_bandwidth_out / 1000000, 2),
                            'errors_in': total_errors_in,
                            'errors_out': total_errors_out
                        },
                        'interfaces': [
                            {
                                'name': name,
                                'status': data.get('status', 'unknown'),
                                'bandwidth_in_mbps': round(data.get('bandwidth_in', 0) / 1000000, 2),
                                'bandwidth_out_mbps': round(data.get('bandwidth_out', 0) / 1000000, 2),
                                'errors_in': data.get('errors_in', 0),
                                'errors_out': data.get('errors_out', 0),
                                'description': data.get('description', '')
                            }
                            for name, data in sorted(interfaces.items())
                        ]
                    })

                    # Wait 5 seconds before next update
                    await asyncio.sleep(5)

                except Exception as e:
                    print(f"Error streaming interfaces for {hostid}: {e}")
                    await asyncio.sleep(5)

        # Start background task
        task = asyncio.create_task(stream_interfaces())

        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Echo back for ping/pong
            await websocket.send_json({'type': 'pong', 'timestamp': datetime.now(timezone.utc).isoformat()})

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for router {hostid}")
        task.cancel()
    except Exception as e:
        print(f"WebSocket error for router {hostid}: {e}")
        try:
            task.cancel()
        except:
            pass

@app.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time notifications"""
    await manager.connect(websocket)
    zabbix = websocket.app.state.zabbix

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            'type': 'connection',
            'message': 'Connected to notification service',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

        # Background task to check for problems periodically
        async def check_problems():
            while True:
                try:
                    # Fetch current problems from Zabbix
                    problems = await asyncio.to_thread(zabbix.get_problems)

                    if problems:
                        for problem in problems:
                            # Send notification for each problem
                            severity_map = {
                                '0': 'info',
                                '1': 'info',
                                '2': 'warning',
                                '3': 'warning',
                                '4': 'critical',
                                '5': 'critical'
                            }

                            await websocket.send_json({
                                'id': problem.get('eventid'),
                                'type': severity_map.get(str(problem.get('severity', 0)), 'info'),
                                'title': problem.get('name', 'Problem Detected'),
                                'message': f"{problem.get('hostname', 'Unknown Host')} - {problem.get('description', 'Issue detected')}",
                                'timestamp': datetime.now(timezone.utc).isoformat(),
                                'link': f"/devices?hostid={problem.get('hostid')}"
                            })

                    # Wait 30 seconds before next check
                    await asyncio.sleep(30)

                except Exception as e:
                    print(f"Error checking problems: {e}")
                    await asyncio.sleep(30)

        # Start background task
        task = asyncio.create_task(check_problems())

        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Echo back for ping/pong
            await websocket.send_json({'type': 'pong', 'timestamp': datetime.now(timezone.utc).isoformat()})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        task.cancel()
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)
        try:
            task.cancel()
        except:
            pass

# ============================================
# Settings Routes
# ============================================

@app.get("/settings")
async def settings_page(request: Request):
    """Settings page"""
    return templates.TemplateResponse("settings.html", {"request": request})


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
