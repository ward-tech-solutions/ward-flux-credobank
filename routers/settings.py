"""
WARD FLUX - Settings Router
System settings management
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from auth import get_current_active_user, require_admin
from routers.utils import get_zabbix_client
from database import User

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


# Pydantic Models
class ZabbixSettings(BaseModel):
    url: str
    username: str
    password: Optional[str] = None


class EmailSettings(BaseModel):
    smtp_server: str
    smtp_port: int
    smtp_username: str
    smtp_password: Optional[str] = None
    from_email: str


class NotificationSettings(BaseModel):
    email_enabled: bool = True
    slack_enabled: bool = False
    slack_webhook: Optional[str] = None


class FeatureToggles(BaseModel):
    discovery: bool = True
    topology: bool = True
    diagnostics: bool = True
    reports: bool = True
    map: bool = True
    regions: bool = True


# In-memory storage for now (replace with database later)
_settings_storage = {
    "zabbix": {
        "url": "",
        "username": "",
    },
    "email": {
        "smtp_server": "",
        "smtp_port": 587,
        "smtp_username": "",
        "from_email": "noreply@ward.com",
    },
    "notifications": {
        "email_enabled": True,
        "slack_enabled": False,
        "slack_webhook": "",
    },
    "features": {
        "discovery": True,
        "topology": True,
        "diagnostics": True,
        "reports": True,
        "map": True,
        "regions": True,
    }
}


@router.get("/zabbix")
def get_zabbix_settings(current_user: User = Depends(get_current_active_user)):
    """Get Zabbix settings"""
    return _settings_storage["zabbix"]


@router.post("/zabbix")
def save_zabbix_settings(
    settings: ZabbixSettings,
    request: Request,
    current_user: User = Depends(require_admin)
):
    """Save Zabbix settings (admin only)"""
    stored = _settings_storage.get("zabbix", {})
    password = settings.password or stored.get("password")

    if not password:
        raise HTTPException(status_code=400, detail="Password is required when configuring Zabbix")

    try:
        client = get_zabbix_client(request)
        client.reconfigure(settings.url, settings.username, password)

        if not client.is_configured():
            raise HTTPException(status_code=400, detail="Unable to connect to Zabbix with provided credentials")

        _settings_storage["zabbix"] = {
            "url": settings.url,
            "username": settings.username,
            "password": password,
        }

        return {"success": True, "message": "Zabbix settings saved"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving Zabbix settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-zabbix")
def test_zabbix_connection(
    settings: ZabbixSettings,
    current_user: User = Depends(require_admin)
):
    """Test Zabbix connection"""
    password = settings.password
    if not password:
        raise HTTPException(status_code=400, detail="Password is required to test Zabbix connectivity")

    try:
        from zabbix_client import ZabbixClient

        client = ZabbixClient(settings.url, settings.username, password)
        if not client.is_configured():
            raise HTTPException(status_code=400, detail="Unable to authenticate with Zabbix")

        # Basic request to confirm API works
        client.get_all_groups()
        return {"success": True, "message": "Zabbix connection successful"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing Zabbix connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/email")
def get_email_settings(current_user: User = Depends(get_current_active_user)):
    """Get email settings"""
    return _settings_storage["email"]


@router.post("/email")
def save_email_settings(
    settings: EmailSettings,
    current_user: User = Depends(require_admin)
):
    """Save email settings (admin only)"""
    try:
        _settings_storage["email"] = settings.dict(exclude_none=True)
        return {"success": True, "message": "Email settings saved"}
    except Exception as e:
        logger.error(f"Error saving email settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications")
def get_notification_settings(current_user: User = Depends(get_current_active_user)):
    """Get notification settings"""
    return _settings_storage["notifications"]


@router.post("/notifications")
def save_notification_settings(
    settings: NotificationSettings,
    current_user: User = Depends(require_admin)
):
    """Save notification settings (admin only)"""
    try:
        _settings_storage["notifications"] = settings.dict()
        return {"success": True, "message": "Notification settings saved"}
    except Exception as e:
        logger.error(f"Error saving notification settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/features")
def get_feature_toggles(current_user: User = Depends(get_current_active_user)):
    """Get system-wide feature toggles (applies to all users) - READ access for all authenticated users"""
    return _settings_storage["features"]


@router.post("/features")
def save_feature_toggles(
    features: FeatureToggles,
    current_user: User = Depends(require_admin)
):
    """Save system-wide feature toggles (admin only - affects all users)"""
    try:
        _settings_storage["features"] = features.dict()
        logger.info(f"Admin {current_user.username} updated feature toggles: {features.dict()}")
        return {"success": True, "message": "Feature toggles saved successfully"}
    except Exception as e:
        logger.error(f"Error saving feature toggles: {e}")
        raise HTTPException(status_code=500, detail=str(e))
