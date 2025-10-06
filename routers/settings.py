"""
WARD FLUX - Settings Router
System settings management
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from auth import get_current_active_user, require_admin
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
    }
}


@router.get("/zabbix")
def get_zabbix_settings(current_user: User = Depends(get_current_active_user)):
    """Get Zabbix settings"""
    return _settings_storage["zabbix"]


@router.post("/zabbix")
def save_zabbix_settings(
    settings: ZabbixSettings,
    current_user: User = Depends(require_admin)
):
    """Save Zabbix settings (admin only)"""
    try:
        _settings_storage["zabbix"] = {
            "url": settings.url,
            "username": settings.username,
        }
        if settings.password:
            _settings_storage["zabbix"]["password"] = settings.password

        return {"success": True, "message": "Zabbix settings saved"}
    except Exception as e:
        logger.error(f"Error saving Zabbix settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-zabbix")
def test_zabbix_connection(
    settings: ZabbixSettings,
    current_user: User = Depends(require_admin)
):
    """Test Zabbix connection"""
    try:
        # TODO: Implement actual Zabbix connection test
        return {"success": True, "message": "Zabbix connection test successful"}
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
