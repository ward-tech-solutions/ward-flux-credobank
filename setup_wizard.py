"""
WARD TECH SOLUTIONS - Setup Wizard API
Multi-tenant initial configuration
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, validator
from typing import List, Optional
import os
from dotenv import load_dotenv, set_key
from pyzabbix import ZabbixAPI
from passlib.context import CryptContext

from database import get_db
from database import User
from models import Organization, SystemConfig, SetupWizardState

load_dotenv()

router = APIRouter(prefix="/setup", tags=["setup"])
templates = Jinja2Templates(directory="templates")
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# ============================================
# Pydantic Models
# ============================================

class ZabbixConfig(BaseModel):
    url: str
    user: str
    password: str


class HostGroupSelection(BaseModel):
    id: str
    name: str


class AdminAccount(BaseModel):
    username: str
    email: EmailStr
    password: str

    @validator('password')
    def validate_password_length(cls, v):
        """Validate password length for bcrypt compatibility"""
        if len(v.encode('utf-8')) > 72:
            raise ValueError('Password cannot be longer than 72 bytes')
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class SetupData(BaseModel):
    organization: dict
    zabbix: ZabbixConfig
    groups: List[HostGroupSelection]
    admin: AdminAccount


# ============================================
# Helper Functions
# ============================================

def is_setup_complete(db: Session) -> bool:
    """Check if initial setup has been completed"""
    state = db.query(SetupWizardState).first()
    if not state:
        return False
    return state.is_complete


def test_zabbix_connection(url: str, user: str, password: str) -> dict:
    """Test connection to Zabbix server"""
    try:
        zapi = ZabbixAPI(url, timeout=10)
        zapi.login(user, password)

        # Get host count
        hosts = zapi.host.get(output=["hostid"])
        hosts_count = len(hosts)

        zapi.user.logout()

        return {
            "success": True,
            "hosts_count": hosts_count
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_zabbix_host_groups(url: str, user: str, password: str) -> dict:
    """Get all host groups from Zabbix"""
    try:
        zapi = ZabbixAPI(url, timeout=10)
        zapi.login(user, password)

        groups = zapi.hostgroup.get(
            output=["groupid", "name"],
            sortfield="name"
        )

        zapi.user.logout()

        return {
            "success": True,
            "groups": groups
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def save_config_to_env(config: dict):
    """Save configuration to .env file"""
    env_file = ".env"

    # Create .env if it doesn't exist
    if not os.path.exists(env_file):
        with open(env_file, 'w') as f:
            f.write("# WARD TECH SOLUTIONS - Environment Configuration\n")
            f.write(f"# Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d')}\n\n")

    # Update values
    for key, value in config.items():
        set_key(env_file, key, str(value))


# ============================================
# Routes
# ============================================

@router.get("/", response_class=HTMLResponse)
async def setup_wizard_page(request: Request, db: Session = Depends(get_db)):
    """Show setup wizard (only if setup not complete)"""
    if is_setup_complete(db):
        return HTMLResponse(
            content="""
            <html><body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>Setup Already Complete</h1>
                <p>This platform has already been configured.</p>
                <a href="/" style="color: #5EBBA8;">Go to Dashboard</a>
            </body></html>
            """,
            status_code=200
        )

    return templates.TemplateResponse("setup/wizard.html", {"request": request})


@router.post("/test-zabbix")
async def test_zabbix(config: ZabbixConfig):
    """Test Zabbix connection"""
    result = test_zabbix_connection(config.url, config.user, config.password)
    return result


@router.post("/get-groups")
async def get_groups(config: ZabbixConfig):
    """Get Zabbix host groups"""
    result = get_zabbix_host_groups(config.url, config.user, config.password)
    return result


@router.post("/complete")
async def complete_setup(setup_data: SetupData, db: Session = Depends(get_db)):
    """Complete the setup wizard and save configuration"""
    try:
        # Check if already setup
        if is_setup_complete(db):
            raise HTTPException(status_code=400, detail="Setup already complete")

        # 1. Create Organization
        org = Organization(
            name=setup_data.organization["name"],
            zabbix_url=setup_data.zabbix.url,
            zabbix_user=setup_data.zabbix.user,
            zabbix_password=setup_data.zabbix.password,
            monitored_groups=[g.id for g in setup_data.groups],
            is_active=True,
            is_setup_complete=True
        )
        db.add(org)
        db.flush()

        # 2. Create Admin User
        hashed_password = pwd_context.hash(setup_data.admin.password)
        admin_user = User(
            username=setup_data.admin.username,
            email=setup_data.admin.email,
            hashed_password=hashed_password,
            full_name="Administrator",
            organization_id=org.id,
            role="admin",
            is_active=True,
            is_superuser=True
        )
        db.add(admin_user)

        # 3. Save to environment variables
        env_config = {
            "ZABBIX_URL": setup_data.zabbix.url,
            "ZABBIX_USER": setup_data.zabbix.user,
            "ZABBIX_PASSWORD": setup_data.zabbix.password,
            "ORGANIZATION_NAME": setup_data.organization["name"],
            "MONITORED_GROUPS": ",".join([g.id for g in setup_data.groups])
        }
        save_config_to_env(env_config)

        # 4. Update wizard state
        wizard_state = db.query(SetupWizardState).first()
        if not wizard_state:
            wizard_state = SetupWizardState()
            db.add(wizard_state)

        wizard_state.step_1_welcome = True
        wizard_state.step_2_zabbix = True
        wizard_state.step_3_groups = True
        wizard_state.step_4_admin = True
        wizard_state.step_5_complete = True
        wizard_state.is_complete = True

        # 5. Save system config
        configs = [
            SystemConfig(key="setup_complete", value="true", description="Initial setup completed"),
            SystemConfig(key="organization_id", value=str(org.id), description="Primary organization ID"),
            SystemConfig(key="setup_date", value=str(__import__('datetime').datetime.now()), description="Setup completion date")
        ]
        for config in configs:
            db.add(config)

        db.commit()

        # 6. Reconfigure Zabbix client with new credentials
        request.app.state.zabbix.reconfigure(
            url=setup_data.zabbix.url,
            user=setup_data.zabbix.user,
            password=setup_data.zabbix.password
        )

        return {
            "success": True,
            "message": "Setup completed successfully",
            "organization_id": org.id
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Setup failed: {str(e)}")


@router.get("/status")
async def setup_status(db: Session = Depends(get_db)):
    """Check setup status"""
    is_complete = is_setup_complete(db)
    state = db.query(SetupWizardState).first()

    return {
        "is_complete": is_complete,
        "current_step": None if is_complete else (
            1 if not state or not state.step_1_welcome else
            2 if not state.step_2_zabbix else
            3 if not state.step_3_groups else
            4 if not state.step_4_admin else
            5
        )
    }
