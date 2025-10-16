"""
WARD Tech Solutions - Pages Router
Handles HTML page rendering
"""
import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)

# Flask-compatible url_for function for templates
def url_for(endpoint: str, **values):
    """Flask-compatible url_for function for Jinja2 templates"""
    if endpoint == "static":
        filename = values.get("filename", "")
        return f"/admin/static/{filename}"
    return f"/admin/{endpoint}"

# Templates with custom url_for (old UI in DisasterRecovery)
templates = Jinja2Templates(directory="DisasterRecovery/old_ui/templates")
templates.env.globals["url_for"] = url_for

# Create router with /admin prefix
router = APIRouter(prefix="/admin", tags=["pages"])


@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
async def index_page(request: Request):
    """Serve dashboard"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/devices", response_class=HTMLResponse)
async def devices_page(request: Request):
    """Serve devices page"""
    return templates.TemplateResponse("devices.html", {"request": request})


@router.get("/map", response_class=HTMLResponse)
async def map_page(request: Request):
    """Serve map page"""
    return templates.TemplateResponse("map.html", {"request": request})


@router.get("/topology", response_class=HTMLResponse)
async def topology_page(request: Request):
    """Serve network topology visualization"""
    return templates.TemplateResponse("topology.html", {"request": request})


@router.get("/diagnostics", response_class=HTMLResponse)
async def diagnostics_page(request: Request):
    """Serve network diagnostics page"""
    return templates.TemplateResponse("diagnostics.html", {"request": request})


@router.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request):
    """Serve reports page"""
    return templates.TemplateResponse("reports.html", {"request": request})


@router.get("/device/{hostid}", response_class=HTMLResponse)
async def device_details_page(request: Request, hostid: str):
    """Serve device details page"""
    return templates.TemplateResponse("device-details.html", {"request": request, "hostid": hostid})


@router.get("/add-host", response_class=HTMLResponse)
async def add_host_page(request: Request):
    """Serve add host page"""
    return templates.TemplateResponse("add-host.html", {"request": request})


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve login page"""
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    """Serve user management page (admin only)"""
    return templates.TemplateResponse("users.html", {"request": request})


@router.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    """Serve host group configuration page"""
    return templates.TemplateResponse("config.html", {"request": request})


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Serve settings page"""
    return templates.TemplateResponse("settings.html", {"request": request})
