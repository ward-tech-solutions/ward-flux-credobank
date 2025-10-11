"""
WARD TECH SOLUTIONS - Network Monitoring Platform
Modern FastAPI-based Network Management System

Copyright © 2025 WARD Tech Solutions
Powered by FastAPI and modern async architecture
"""
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize logger
logger = logging.getLogger(__name__)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, UploadFile, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
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

import concurrent.futures

# Authentication imports
from database import get_db, User, UserRole, init_db
from auth import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    create_user,
    UserCreate,
    UserResponse,
    Token,
    require_admin,
    require_manager_or_admin,
    require_tech_or_admin,
)

# Bulk operations imports
from bulk_operations import (
    parse_csv_file,
    parse_excel_file,
    validate_bulk_import_data,
    process_bulk_import,
    bulk_update_devices,
    bulk_delete_devices,
    generate_csv_template,
    export_devices_to_csv,
    export_devices_to_excel,
    BulkOperationResult,
)

# Import router functions for legacy routes
from routers.devices import get_device_details
from routers.reports import get_mttr_extended
from routers.websockets import monitor_device_changes

# Thread pool for async operations
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

# ============================================
# Helper Functions
# ============================================


def get_monitored_groupids():
    """Get list of monitored group IDs from database"""
    from database import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        result = db.execute(text("SELECT groupid FROM monitored_hostgroups WHERE is_active = 1"))
        groupids = [row[0] for row in result.fetchall()]
        return groupids if groupids else None
    except Exception as e:
        logging.getLogger(__name__).error(f"Error getting monitored groups: {e}")
        return None
    finally:
        db.close()


def extract_city_from_hostname(hostname):
    """Extract city name from hostname"""
    # Remove IP if present: "Batumi-ATM 10.199.96.163" -> "Batumi-ATM"
    name = hostname.split()[0]

    # Handle special prefixes: "PING-Kabali-AP" -> skip "PING", use "Kabali"
    parts = name.split("-")

    # Skip common prefixes (PING, TEST, PROD, etc.)
    common_prefixes = ["PING", "TEST", "PROD", "DEV", "SW", "RTR"]
    if len(parts) > 1 and parts[0].upper() in common_prefixes:
        city = parts[1]  # Use second part as city
    else:
        city = parts[0]  # Use first part as city

    # Remove numbers: "Batumi1" -> "Batumi"
    city = "".join([c for c in city if not c.isdigit()])

    return city.strip()


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Skip initialization in test mode
    if os.getenv("TESTING") == "true":
        yield
        return

    # Initialize database
    init_db()

    # Create default admin user if it doesn't exist
    from database import SessionLocal, User, UserRole
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()
        default_admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD")

        if not admin_user:
            if not default_admin_password:
                logger.warning(
                    "DEFAULT_ADMIN_PASSWORD not set. Skipping creation of default admin user. "
                    "Create an admin manually or set DEFAULT_ADMIN_PASSWORD for automated provisioning."
                )
            else:
                admin_user = User(
                    username="admin",
                    email="admin@wardops.tech",
                    full_name="Administrator",
                    hashed_password=pwd_context.hash(default_admin_password),
                    role=UserRole.ADMIN,
                    is_active=True,
                    is_superuser=True,
                )
                db.add(admin_user)
                db.commit()
                logger.info("✓ Default admin user created (username: admin)")
        else:
            # Update existing admin user to ensure ADMIN role
            if admin_user.role != UserRole.ADMIN:
                admin_user.role = UserRole.ADMIN
                admin_user.is_superuser = True
                db.commit()
                logger.info("✓ Admin user role updated to ADMIN")
            else:
                logger.info("✓ Admin user already exists")
    except Exception as e:
        logger.info(f"Warning: Could not create default admin user: {e}")
    finally:
        db.close()

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
* 📊 **Real-time Monitoring** - Standalone SNMP and ping monitoring
* 🌐 **Network Diagnostics** - Ping, Traceroute, MTR tools
* 📈 **Performance Tracking** - Automated performance baselines
* 🗺️ **Network Topology** - Visual network mapping
* 👥 **Multi-user Support** - Role-based access control

### API Documentation:
* Interactive Swagger UI: `/docs`
* Alternative ReDoc: `/redoc`
* OpenAPI Schema: `/openapi.json`
    """,
    version="2.0.0",
    contact={"name": "WARD Tech Solutions", "url": "https://wardops.tech", "email": "info@wardops.tech"},
    license_info={"name": "Proprietary", "url": "https://wardops.tech/license"},
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Allow all hosts (for Docker deployment with any IP/domain)
from starlette.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# ============================================
# Include Modular Routers
# ============================================
from routers import (
    alerts,
    auth,
    branches,
    bulk,
    config,
    dashboard,
    devices,
    devices_standalone,
    diagnostics,
    discovery,
    infrastructure,
    monitoring,
    reports,
    settings,
    snmp_credentials,
    templates,
    websockets,
)

app.include_router(auth.router)
app.include_router(config.router)
app.include_router(bulk.router)
app.include_router(devices.router)
app.include_router(devices_standalone.router)
app.include_router(snmp_credentials.router)
app.include_router(templates.router)
app.include_router(discovery.router)
app.include_router(reports.router)
app.include_router(alerts.router)
app.include_router(alerts.rules_router)
app.include_router(branches.router)
app.include_router(settings.router)
app.include_router(dashboard.router)
app.include_router(diagnostics.router)
app.include_router(websockets.router)
app.include_router(infrastructure.router)
app.include_router(monitoring.router)

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
    from slowapi import Limiter, _rate_limit_exceeded_handler  # type: ignore
    from slowapi.util import get_remote_address  # type: ignore
    from slowapi.errors import RateLimitExceeded  # type: ignore

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    RATE_LIMITING_ENABLED = True
except ImportError:
    logger.info("Warning: slowapi not installed. Rate limiting disabled. Install with: pip install slowapi")
    RATE_LIMITING_ENABLED = False
    limiter = None

# ============================================
# Setup Wizard Integration
# ============================================
# (Setup wizard removed)

from pathlib import Path


def _resolve_frontend_build_dir() -> Path | None:
    """Return the active frontend build directory, preferring Vite dist output."""
    dist_dir = Path("frontend/dist")
    if dist_dir.exists():
        return dist_dir
    legacy_dir = Path("static_new")
    if legacy_dir.exists():
        logger.warning("Using legacy static_new assets. Run npm run build to refresh frontend.")
        return legacy_dir
    return None


FRONTEND_BUILD_DIR = _resolve_frontend_build_dir()

if FRONTEND_BUILD_DIR:
    assets_dir = FRONTEND_BUILD_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    app.mount("/static", StaticFiles(directory=FRONTEND_BUILD_DIR), name="static")
else:
    logger.warning("React build not found. Run npm run build to generate static assets.")


def _frontend_file(relative_path: str) -> Path:
    """Resolve a file inside the compiled frontend bundle."""
    if not FRONTEND_BUILD_DIR:
        raise HTTPException(status_code=503, detail="Frontend build not available")
    file_path = FRONTEND_BUILD_DIR / relative_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Asset not found: {relative_path}")
    return file_path


@app.on_event("startup")
async def startup_event():
    # Startup event handler
    pass


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

# Authentication endpoint (for compatibility with frontend)
@app.post("/auth/token", response_model=Token)
async def login_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login endpoint - returns JWT token (compatibility route)"""
    from routers.auth import login
    return await login(request, form_data, db)

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
    online_devices = len([h for h in devices if h.get("ping_status") == "Up"])
    offline_devices = len([h for h in devices if h.get("ping_status") == "Down"])
    warning_devices = len([h for h in devices if h.get("ping_status") == "Unknown"])

    # Device types statistics
    device_types = {}
    for host in devices:
        dt = host["device_type"]
        if dt not in device_types:
            device_types[dt] = {"total": 0, "online": 0, "offline": 0}
        device_types[dt]["total"] += 1
        if host.get("ping_status") == "Up":
            device_types[dt]["online"] += 1
        elif host.get("ping_status") == "Down":
            device_types[dt]["offline"] += 1

    # Region statistics
    regions_stats = {}
    for host in devices:
        region_name = host["region"]
        if region_name not in regions_stats:
            regions_stats[region_name] = {"total": 0, "online": 0, "offline": 0}
        regions_stats[region_name]["total"] += 1
        if host.get("ping_status") == "Up":
            regions_stats[region_name]["online"] += 1
        elif host.get("ping_status") == "Down":
            regions_stats[region_name]["offline"] += 1

    return {
        "total_devices": total_devices,
        "online_devices": online_devices,
        "offline_devices": offline_devices,
        "warning_devices": warning_devices,
        "uptime_percentage": round((online_devices / total_devices * 100) if total_devices > 0 else 0, 2),
        "active_alerts": len(alerts),
        "critical_alerts": len([a for a in alerts if a["severity"] in ["High", "Disaster"]]),
        "device_types": device_types,
        "regions_stats": regions_stats,
    }


@app.get("/api/devices")
async def api_devices_legacy(
    request: Request, region: Optional[str] = None, branch: Optional[str] = None, device_type: Optional[str] = None
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




@app.get("/api/search")
async def api_search_legacy(
    request: Request,
    q: Optional[str] = None,
    region: Optional[str] = None,
    branch: Optional[str] = None,
    device_type: Optional[str] = None,
    status: Optional[str] = None,
):
    """Legacy route - no auth for backward compatibility"""
    zabbix = request.app.state.zabbix
    devices = await run_in_executor(zabbix.get_all_hosts)

    # Apply text search
    if q:
        query = q.lower()
        devices = [
            d
            for d in devices
            if (
                query in d["display_name"].lower()
                or query in d["branch"].lower()
                or query in d["ip"].lower()
                or query in d["region"].lower()
            )
        ]

    # Apply filters
    if region:
        devices = [d for d in devices if d["region"] == region]
    if branch:
        devices = [d for d in devices if branch.lower() in d["branch"].lower()]
    if device_type:
        devices = [d for d in devices if d["device_type"] == device_type]
    if status:
        devices = [d for d in devices if d["ping_status"] == status]

    return devices


@app.get("/api/topology")
async def api_topology_legacy(
    request: Request, view: str = "hierarchical", limit: int = 200, region: Optional[str] = None
):
    """Legacy route - now using interface-based topology discovery"""
    zabbix = request.app.state.zabbix
    groupids = get_monitored_groupids()
    loop = asyncio.get_event_loop()
    devices = await loop.run_in_executor(executor, lambda: zabbix.get_all_hosts(group_ids=groupids))

    if region:
        devices = [d for d in devices if d["region"] == region]

    if len(devices) > limit:
        devices = devices[:limit]

    nodes = []
    edges = []
    edges_set = set()  # Track edges to avoid duplicates

    # Build device name mapping for connection discovery
    device_name_map = {}  # Maps normalized device names to hostids
    for device in devices:
        display_name = device.get("display_name", "").lower().strip()
        # Store multiple name variations for matching
        device_name_map[display_name] = device["hostid"]
        # Also store without suffixes like "-881", "-1111"
        base_name = display_name.split("-")[0].strip()
        if base_name and base_name != display_name:
            device_name_map[base_name] = device["hostid"]

    logger.info(f"[Topology] Built device name map with {len(device_name_map)} entries")

    # Create nodes for all devices
    for device in devices:
        status = device.get("ping_status", "Unknown")
        device_type = device.get("device_type", "Unknown")
        ip = device.get("ip", "")

        # Determine device type based on IP if not set
        if ip and device_type in ["Switch", "L3 Switch", "Branch Switch"]:
            last_octet = ip.split(".")[-1] if "." in ip else ""
            if last_octet == "5":
                device_type = "Router"
            elif last_octet in ["245", "246"]:
                device_type = "Switch"

        # Color and size based on device type
        if device_type == "Core Router":
            color = "#FF6B35" if status == "Up" else "#dc3545"
            size = 35
            shape = "diamond"
        elif device_type in ["Router", "Switch", "L3 Switch", "Branch Switch"]:
            color = "#14b8a6" if status == "Up" else "#dc3545"
            size = 25
            shape = "box"
        else:
            color = "#6B7280" if status == "Up" else "#dc3545"
            size = 15
            shape = "dot"

        nodes.append({
            "id": device["hostid"],
            "label": device["display_name"],
            "title": f"{device['display_name']}\n{ip}\nType: {device_type}\nStatus: {status}",
            "color": color,
            "size": size,
            "shape": shape,
            "deviceType": device_type,
            "branch": device.get("branch", "Unknown"),
        })

    logger.info(f"[Topology] Created {len(nodes)} nodes")

    # Discover connections from interface descriptions
    connection_count = 0
    for device in devices:
        try:
            # Fetch interfaces for this device
            interfaces = await loop.run_in_executor(
                executor, lambda d=device: zabbix.get_router_interfaces(d["hostid"])
            )

            # Parse interface descriptions to find connections
            for iface_name, iface_data in interfaces.items():
                description = iface_data.get("description", "").lower().strip()
                if not description or len(description) < 3:
                    continue

                # Skip management interfaces
                if any(skip in description for skip in ["mgmt", "loopback", "null", "vlan"]):
                    continue

                # Try to match description to device names
                matched_hostid = None
                for device_name, hostid in device_name_map.items():
                    if device_name in description or description in device_name:
                        # Don't connect device to itself
                        if hostid != device["hostid"]:
                            matched_hostid = hostid
                            break

                if matched_hostid:
                    # Create edge (avoid duplicates)
                    edge_key = tuple(sorted([device["hostid"], matched_hostid]))
                    if edge_key not in edges_set:
                        edges_set.add(edge_key)

                        # Get bandwidth info
                        bw_in_mbps = iface_data.get("bandwidth_in", 0) / 1000000
                        bw_out_mbps = iface_data.get("bandwidth_out", 0) / 1000000
                        iface_status = iface_data.get("status", "unknown")

                        edge_label = f"↓{bw_in_mbps:.1f}M ↑{bw_out_mbps:.1f}M" if bw_in_mbps > 0 else ""

                        edges.append({
                            "from": device["hostid"],
                            "to": matched_hostid,
                            "label": edge_label,
                            "title": f"Interface: {iface_name}\nDescription: {iface_data.get('description', '')}\n↓ {bw_in_mbps:.2f} Mbps\n↑ {bw_out_mbps:.2f} Mbps\nStatus: {iface_status}",
                            "color": "#14b8a6" if iface_status == "up" else "#dc3545",
                            "width": 3 if bw_in_mbps > 100 else 2,
                            "font": {"size": 10, "color": "#00d9ff"},
                        })
                        connection_count += 1

        except Exception as e:
            logger.debug(f"[Topology] Could not fetch interfaces for {device.get('display_name', 'unknown')}: {e}")
            continue

    logger.info(f"[Topology] Discovered {connection_count} connections from interface descriptions")

    # Count device types for stats
    from collections import defaultdict
    core_routers = [d for d in devices if d.get("device_type") == "Core Router"]
    branch_switches = [d for d in devices if d.get("device_type") in ["Switch", "L3 Switch", "Branch Switch", "Router"]]
    end_devices = [d for d in devices if d not in core_routers and d not in branch_switches]

    # Return discovered topology - old simulation code removed
    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "core_routers": len(core_routers),
            "branch_switches": len(branch_switches),
            "end_devices": len(end_devices),
            "total_devices": len(devices),
        },
    }


@app.get("/api/reports/downtime")
async def api_downtime_report_legacy(
    request: Request, period: str = "weekly", region: Optional[str] = None, device_type: Optional[str] = None
):
    """Legacy route - no auth for backward compatibility"""
    zabbix = request.app.state.zabbix
    devices = await run_in_executor(zabbix.get_all_hosts)

    if region:
        devices = [d for d in devices if d["region"] == region]
    if device_type:
        devices = [d for d in devices if d["device_type"] == device_type]

    # Map period to hours
    period_hours = 168 if period == "weekly" else 720  # 7 days or 30 days

    report = {
        "period": period,
        "generated_at": datetime.now().isoformat(),
        "total_devices": len(devices),
        "summary": {"total_downtime_hours": 0, "average_availability": 0, "devices_with_downtime": 0},
        "devices": [],
    }

    for device in devices:
        # Calculate real availability from Zabbix history
        availability_data = await run_in_executor(zabbix.calculate_availability, device["hostid"], period_hours)

        report["devices"].append(
            {
                "hostid": device["hostid"],
                "name": device["display_name"],
                "region": device["region"],
                "branch": device["branch"],
                "device_type": device["device_type"],
                "downtime_hours": availability_data["downtime_hours"],
                "availability_percent": availability_data["availability_percent"],
                "incidents": availability_data["incidents"],
            }
        )

        report["summary"]["total_downtime_hours"] += availability_data["downtime_hours"]
        if availability_data["downtime_hours"] > 0:
            report["summary"]["devices_with_downtime"] += 1

    report["summary"]["average_availability"] = round(
        sum(d["availability_percent"] for d in report["devices"]) / len(devices) if devices else 0, 2
    )

    return report


@app.get("/api/reports/mttr-extended")
async def api_mttr_extended_legacy(request: Request):
    """Legacy route - redirects to v1"""
    return await get_mttr_extended(request)




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

from fastapi.responses import FileResponse

# Serve new React UI as default
@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve React app"""
    return FileResponse(_frontend_file("index.html"))

# Serve static files from root (logo, favicon, etc.)
@app.get("/logo-ward.svg")
async def serve_logo():
    """Serve WARD logo"""
    return FileResponse(_frontend_file("logo-ward.svg"))

@app.get("/favicon.svg")
async def serve_favicon():
    """Serve favicon"""
    return FileResponse(_frontend_file("favicon.svg"))

# Catch all routes for React Router (except API and admin routes)
@app.get("/{full_path:path}", response_class=HTMLResponse)
async def catch_all(request: Request, full_path: str):
    """Catch all routes for React Router"""
    # Don't catch API routes or admin routes
    if full_path.startswith("api/") or full_path.startswith("admin/"):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(_frontend_file("index.html"))

# ============================================
# SSH Terminal API
# ============================================


@app.post("/api/v1/ssh/connect")
async def ssh_connect(ssh_request: SSHConnectRequest, current_user: User = Depends(get_current_active_user)):
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
            allow_agent=False,
        )

        # Execute a simple command to verify connection
        stdin, stdout, stderr = ssh.exec_command(
            "show version | include uptime" if ".5" in ssh_request.host else "hostname"
        )
        output = stdout.read().decode("utf-8", errors="ignore")
        error = stderr.read().decode("utf-8", errors="ignore")

        ssh.close()

        return {
            "success": True,
            "output": output if output else "Connected successfully",
            "message": f"SSH connection to {ssh_request.host} established",
        }

    except paramiko.AuthenticationException:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Authentication failed. Please check username and password."},
        )
    except paramiko.SSHException as e:
        return JSONResponse(status_code=500, content={"success": False, "error": f"SSH error: {str(e)}"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": f"Connection failed: {str(e)}"})


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



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5001)
