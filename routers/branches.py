"""
Branch Management API Router
Provides CRUD operations for branch/location management
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from auth import get_current_active_user
from database import User
from models import Branch

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/branches", tags=["branches"])


# ==================================================================
# Pydantic Models
# ==================================================================

class BranchCreate(BaseModel):
    name: str
    display_name: str
    region: Optional[str] = None
    branch_code: Optional[str] = None
    address: Optional[str] = None
    is_active: bool = True


class BranchUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    region: Optional[str] = None
    branch_code: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


# ==================================================================
# Endpoints
# ==================================================================

@router.get("")
async def get_branches(
    region: Optional[str] = Query(None, description="Filter by region"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name or display name"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all branches with optional filtering"""

    query = db.query(Branch)

    # Apply filters
    if region:
        query = query.filter(Branch.region == region)
    if is_active is not None:
        query = query.filter(Branch.is_active == is_active)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Branch.name.like(search_pattern)) |
            (Branch.display_name.like(search_pattern))
        )

    branches = query.order_by(Branch.device_count.desc()).all()

    return {
        "branches": [
            {
                "id": branch.id,
                "name": branch.name,
                "display_name": branch.display_name,
                "region": branch.region,
                "branch_code": branch.branch_code,
                "address": branch.address,
                "is_active": branch.is_active,
                "device_count": branch.device_count,
                "created_at": branch.created_at.isoformat() if branch.created_at else None,
                "updated_at": branch.updated_at.isoformat() if branch.updated_at else None,
            }
            for branch in branches
        ]
    }


@router.get("/stats")
async def get_branch_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get aggregated branch statistics"""

    total_branches = db.query(Branch).count()
    active_branches = db.query(Branch).filter(Branch.is_active == True).count()

    # Get region distribution
    regions = db.execute("""
        SELECT region, COUNT(*) as count
        FROM branches
        WHERE region IS NOT NULL
        GROUP BY region
        ORDER BY count DESC
    """).fetchall()

    return {
        "total_branches": total_branches,
        "active_branches": active_branches,
        "inactive_branches": total_branches - active_branches,
        "regions": [
            {"region": row[0], "count": row[1]}
            for row in regions
        ]
    }


@router.get("/{branch_id}")
async def get_branch(
    branch_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a single branch by ID"""

    branch = db.query(Branch).filter(Branch.id == branch_id).first()

    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    # Get device count from standalone_devices
    device_count = db.execute(
        "SELECT COUNT(*) FROM standalone_devices WHERE branch_id = ?",
        (branch_id,)
    ).fetchone()[0]

    return {
        "id": branch.id,
        "name": branch.name,
        "display_name": branch.display_name,
        "region": branch.region,
        "branch_code": branch.branch_code,
        "address": branch.address,
        "is_active": branch.is_active,
        "device_count": device_count,
        "created_at": branch.created_at.isoformat() if branch.created_at else None,
        "updated_at": branch.updated_at.isoformat() if branch.updated_at else None,
    }


@router.get("/{branch_id}/devices")
async def get_branch_devices(
    branch_id: str,
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all devices in a branch"""

    # Verify branch exists
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    # Build query
    query = "SELECT * FROM standalone_devices WHERE branch_id = ?"
    params = [branch_id]

    if device_type:
        query += " AND device_type = ?"
        params.append(device_type)

    query += " ORDER BY normalized_name"

    devices = db.execute(query, params).fetchall()

    return {
        "branch": {
            "id": branch.id,
            "name": branch.name,
            "display_name": branch.display_name,
        },
        "devices": [
            {
                "id": str(device[0]),  # id column
                "name": device[1],  # name column
                "normalized_name": device[7] if len(device) > 7 else None,
                "ip": device[2],
                "device_type": device[5],
                "device_subtype": device[8] if len(device) > 8 else None,
                "enabled": bool(device[9]) if len(device) > 9 else True,
            }
            for device in devices
        ]
    }


@router.post("")
async def create_branch(
    branch_data: BranchCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new branch"""

    # Check if branch with same name already exists
    existing = db.query(Branch).filter(Branch.name == branch_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Branch with name '{branch_data.name}' already exists")

    # Create new branch
    new_branch = Branch(
        id=str(uuid.uuid4()),
        name=branch_data.name,
        display_name=branch_data.display_name,
        region=branch_data.region,
        branch_code=branch_data.branch_code,
        address=branch_data.address,
        is_active=branch_data.is_active,
        device_count=0,
    )

    db.add(new_branch)
    db.commit()
    db.refresh(new_branch)

    logger.info(f"Created branch: {new_branch.display_name} by {current_user.username}")

    return {
        "success": True,
        "branch": {
            "id": new_branch.id,
            "name": new_branch.name,
            "display_name": new_branch.display_name,
            "region": new_branch.region,
            "branch_code": new_branch.branch_code,
        }
    }


@router.put("/{branch_id}")
async def update_branch(
    branch_id: str,
    branch_data: BranchUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update an existing branch"""

    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    # Update fields if provided
    if branch_data.name is not None:
        # Check for duplicate name
        existing = db.query(Branch).filter(
            Branch.name == branch_data.name,
            Branch.id != branch_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Branch with name '{branch_data.name}' already exists")
        branch.name = branch_data.name

    if branch_data.display_name is not None:
        branch.display_name = branch_data.display_name
    if branch_data.region is not None:
        branch.region = branch_data.region
    if branch_data.branch_code is not None:
        branch.branch_code = branch_data.branch_code
    if branch_data.address is not None:
        branch.address = branch_data.address
    if branch_data.is_active is not None:
        branch.is_active = branch_data.is_active

    db.commit()
    db.refresh(branch)

    logger.info(f"Updated branch: {branch.display_name} by {current_user.username}")

    return {
        "success": True,
        "branch": {
            "id": branch.id,
            "name": branch.name,
            "display_name": branch.display_name,
            "region": branch.region,
            "branch_code": branch.branch_code,
        }
    }


@router.delete("/{branch_id}")
async def delete_branch(
    branch_id: str,
    force: bool = Query(False, description="Force delete even if devices are assigned"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a branch"""

    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    # Check for assigned devices
    device_count = db.execute(
        "SELECT COUNT(*) FROM standalone_devices WHERE branch_id = ?",
        (branch_id,)
    ).fetchone()[0]

    if device_count > 0 and not force:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete branch with {device_count} assigned devices. Use force=true to delete anyway."
        )

    # If force delete, unassign devices
    if force and device_count > 0:
        db.execute(
            "UPDATE standalone_devices SET branch_id = NULL WHERE branch_id = ?",
            (branch_id,)
        )
        logger.warning(f"Force deleted branch {branch.display_name}, unassigned {device_count} devices")

    branch_name = branch.display_name
    db.delete(branch)
    db.commit()

    logger.info(f"Deleted branch: {branch_name} by {current_user.username}")

    return {"success": True, "message": f"Branch '{branch_name}' deleted"}
