"""
WARD Tech Solutions - Configuration Router
Handles host group configuration and settings
"""
import logging
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request

from auth import get_current_active_user, require_admin
from database import User
from routers.utils import get_zabbix_client, run_in_executor

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/config", tags=["configuration"])


@router.get("/zabbix-hostgroups")
async def get_zabbix_hostgroups(request: Request, current_user: User = Depends(get_current_active_user)):
    """Fetch all host groups from Zabbix"""
    try:
        zabbix = get_zabbix_client(request)
        groups = await run_in_executor(zabbix.get_all_groups)
        return {"hostgroups": groups}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitored-hostgroups")
async def get_monitored_hostgroups(request: Request, current_user: User = Depends(get_current_active_user)):
    """Get currently monitored host groups from DB"""
    import os
    db_path = os.getenv("SQLITE_DB_PATH", "data/ward_ops.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT groupid, name, display_name, is_active
        FROM monitored_hostgroups
        WHERE is_active = 1
    """
    )
    groups = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"monitored_groups": groups}


@router.post("/monitored-hostgroups")
async def save_monitored_hostgroups(request: Request, current_user: User = Depends(require_admin)):
    """Save selected host groups configuration"""
    data = await request.json()
    groups = data.get("groups", [])

    import os
    db_path = os.getenv("SQLITE_DB_PATH", "data/ward_ops.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Deactivate all existing
    cursor.execute("UPDATE monitored_hostgroups SET is_active = 0")

    # Insert/activate selected groups
    for group in groups:
        cursor.execute(
            """
            INSERT OR REPLACE INTO monitored_hostgroups
            (groupid, name, display_name, is_active)
            VALUES (?, ?, ?, 1)
        """,
            (group["groupid"], group["name"], group.get("display_name", group["name"])),
        )

    conn.commit()
    conn.close()
    return {"status": "success", "saved": len(groups)}


@router.get("/georgian-cities")
async def get_georgian_cities(request: Request, current_user: User = Depends(get_current_active_user)):
    """Get all Georgian cities with regions and coordinates"""
    import os
    db_path = os.getenv("SQLITE_DB_PATH", "data/ward_ops.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT c.id, c.name_en, c.latitude, c.longitude,
               r.name_en as region_name
        FROM georgian_cities c
        JOIN georgian_regions r ON c.region_id = r.id
        WHERE c.is_active = 1
        ORDER BY r.name_en, c.name_en
    """
    )
    cities = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"cities": cities}
