"""
WARD FLUX - Monitoring Template Management API

Provides CRUD operations for monitoring templates, including:
- Template creation and management
- Import/export functionality
- Apply templates to devices
- Clone templates
"""

import logging
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db, User
from monitoring.models import MonitoringTemplate, MonitoringItem, StandaloneDevice
from routers.auth import get_current_active_user

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/templates", tags=["monitoring-templates"])


# ============================================
# Pydantic Models
# ============================================

class TemplateItemCreate(BaseModel):
    name: str
    oid_name: str
    oid: str
    interval: int = 60
    value_type: str = "integer"
    units: Optional[str] = ""
    description: Optional[str] = ""
    is_table: bool = False


class TemplateTriggerCreate(BaseModel):
    name: str
    expression: str
    severity: str
    for_duration: int = 300
    description: Optional[str] = ""


class TemplateCreate(BaseModel):
    name: str
    description: Optional[str]
    vendor: Optional[str]
    device_types: List[str] = []
    items: List[TemplateItemCreate] = []
    triggers: List[TemplateTriggerCreate] = []
    is_default: bool = False


class TemplateUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    vendor: Optional[str]
    device_types: Optional[List[str]]
    items: Optional[List[dict]]
    triggers: Optional[List[dict]]
    is_default: Optional[bool]


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    vendor: Optional[str]
    device_types: List[str]
    items: List[dict]
    triggers: List[dict]
    is_default: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=str(obj.id),
            name=obj.name,
            description=obj.description,
            vendor=obj.vendor,
            device_types=obj.device_types or [],
            items=obj.items or [],
            triggers=obj.triggers or [],
            is_default=obj.is_default,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )

    class Config:
        from_attributes = True


class ApplyTemplateRequest(BaseModel):
    device_ids: List[str]
    template_id: str


# ============================================
# Template CRUD Endpoints
# ============================================

@router.get("/list", response_model=List[TemplateResponse])
def list_templates(
    vendor: Optional[str] = None,
    is_default: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all monitoring templates with optional filters"""
    query = db.query(MonitoringTemplate)

    if vendor:
        query = query.filter(MonitoringTemplate.vendor == vendor)
    if is_default is not None:
        query = query.filter(MonitoringTemplate.is_default == is_default)

    templates = query.offset(skip).limit(limit).all()
    return [TemplateResponse.from_orm(t) for t in templates]


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a specific monitoring template by ID"""
    template = db.query(MonitoringTemplate).filter_by(id=uuid.UUID(template_id)).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return TemplateResponse.from_orm(template)


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    template: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new monitoring template"""

    # Check for duplicate name
    existing = db.query(MonitoringTemplate).filter_by(name=template.name).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Template with name '{template.name}' already exists"
        )

    # Convert Pydantic models to dicts
    items_data = [item.model_dump() for item in template.items]
    triggers_data = [trigger.model_dump() for trigger in template.triggers]

    new_template = MonitoringTemplate(
        id=uuid.uuid4(),
        name=template.name,
        description=template.description,
        vendor=template.vendor,
        device_types=template.device_types,
        items=items_data,
        triggers=triggers_data,
        is_default=template.is_default,
        created_by=current_user.id,
    )

    db.add(new_template)
    db.commit()
    db.refresh(new_template)

    logger.info(f"Created template: {new_template.name} ({new_template.vendor})")
    return TemplateResponse.from_orm(new_template)


@router.put("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: str,
    template_update: TemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a monitoring template"""
    template = db.query(MonitoringTemplate).filter_by(id=uuid.UUID(template_id)).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check for name conflict if name is being changed
    if template_update.name and template_update.name != template.name:
        existing = db.query(MonitoringTemplate).filter_by(name=template_update.name).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Template with name '{template_update.name}' already exists"
            )

    # Update fields
    update_data = template_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    template.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(template)

    logger.info(f"Updated template: {template.name}")
    return TemplateResponse.from_orm(template)


@router.delete("/{template_id}")
def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a monitoring template"""
    template = db.query(MonitoringTemplate).filter_by(id=uuid.UUID(template_id)).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check if template is in use
    items_count = db.query(MonitoringItem).filter_by(template_id=template.id).count()
    if items_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete template: {items_count} monitoring items are using it"
        )

    template_name = template.name
    db.delete(template)
    db.commit()

    logger.info(f"Deleted template: {template_name}")
    return {"success": True, "message": f"Template '{template_name}' deleted"}


# ============================================
# Template Operations
# ============================================

@router.post("/{template_id}/clone", response_model=TemplateResponse)
def clone_template(
    template_id: str,
    new_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Clone an existing template with a new name"""
    source_template = db.query(MonitoringTemplate).filter_by(id=uuid.UUID(template_id)).first()
    if not source_template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check if new name already exists
    existing = db.query(MonitoringTemplate).filter_by(name=new_name).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Template with name '{new_name}' already exists"
        )

    # Clone the template
    cloned_template = MonitoringTemplate(
        id=uuid.uuid4(),
        name=new_name,
        description=f"Cloned from {source_template.name}",
        vendor=source_template.vendor,
        device_types=source_template.device_types,
        items=source_template.items,  # JSON is copied by value
        triggers=source_template.triggers,
        is_default=False,  # Clones are never default
        created_by=current_user.id,
    )

    db.add(cloned_template)
    db.commit()
    db.refresh(cloned_template)

    logger.info(f"Cloned template: {source_template.name} → {new_name}")
    return TemplateResponse.from_orm(cloned_template)


@router.post("/apply", status_code=status.HTTP_200_OK)
def apply_template_to_devices(
    request: ApplyTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Apply a monitoring template to multiple devices"""

    # Validate template exists
    template = db.query(MonitoringTemplate).filter_by(id=uuid.UUID(request.template_id)).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    created_items = []
    failed_devices = []

    for device_id_str in request.device_ids:
        try:
            device_uuid = uuid.UUID(device_id_str)

            # Verify device exists
            device = db.query(StandaloneDevice).filter_by(id=device_uuid).first()
            if not device:
                failed_devices.append({"device_id": device_id_str, "error": "Device not found"})
                continue

            # Create monitoring items from template
            for item_def in template.items:
                monitoring_item = MonitoringItem(
                    id=uuid.uuid4(),
                    device_id=device_uuid,
                    template_id=template.id,
                    oid_name=item_def["oid_name"],
                    oid=item_def["oid"],
                    interval=item_def.get("interval", 60),
                    value_type=item_def.get("value_type", "integer"),
                    units=item_def.get("units", ""),
                    enabled=True,
                )
                db.add(monitoring_item)
                created_items.append(str(monitoring_item.id))

        except ValueError:
            failed_devices.append({"device_id": device_id_str, "error": "Invalid UUID format"})
        except Exception as e:
            failed_devices.append({"device_id": device_id_str, "error": str(e)})

    db.commit()

    logger.info(f"Applied template '{template.name}' to {len(request.device_ids)} devices, created {len(created_items)} monitoring items")

    return {
        "success": True,
        "template": template.name,
        "devices_processed": len(request.device_ids),
        "items_created": len(created_items),
        "failed_devices": failed_devices,
    }


# ============================================
# Template Import/Export
# ============================================

@router.post("/import", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def import_template(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Import a template from JSON file"""

    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON file")

    try:
        content = file.file.read()
        template_data = json.loads(content)

        # Check if template already exists
        existing = db.query(MonitoringTemplate).filter_by(name=template_data["name"]).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Template '{template_data['name']}' already exists. Delete it first or rename the import."
            )

        # Create template from imported data
        new_template = MonitoringTemplate(
            id=uuid.uuid4(),
            name=template_data["name"],
            description=template_data.get("description"),
            vendor=template_data.get("vendor"),
            device_types=template_data.get("device_types", []),
            items=template_data.get("items", []),
            triggers=template_data.get("triggers", []),
            is_default=template_data.get("is_default", False),
            created_by=current_user.id,
        )

        db.add(new_template)
        db.commit()
        db.refresh(new_template)

        logger.info(f"Imported template: {new_template.name} from {file.filename}")
        return TemplateResponse.from_orm(new_template)

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/{template_id}/export")
def export_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Export a template as JSON"""

    template = db.query(MonitoringTemplate).filter_by(id=uuid.UUID(template_id)).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    export_data = {
        "name": template.name,
        "description": template.description,
        "vendor": template.vendor,
        "device_types": template.device_types or [],
        "is_default": template.is_default,
        "items": template.items or [],
        "triggers": template.triggers or [],
    }

    return export_data


@router.post("/import-defaults", status_code=status.HTTP_200_OK)
def import_default_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Import all default vendor templates from the templates directory"""

    templates_dir = Path(__file__).parent.parent / "monitoring" / "templates"
    if not templates_dir.exists():
        raise HTTPException(status_code=404, detail="Templates directory not found")

    imported = []
    skipped = []
    failed = []

    for template_file in templates_dir.glob("*.json"):
        try:
            with open(template_file, 'r') as f:
                template_data = json.load(f)

            # Check if template already exists
            existing = db.query(MonitoringTemplate).filter_by(name=template_data["name"]).first()
            if existing:
                skipped.append(template_data["name"])
                continue

            # Create template
            new_template = MonitoringTemplate(
                id=uuid.uuid4(),
                name=template_data["name"],
                description=template_data.get("description"),
                vendor=template_data.get("vendor"),
                device_types=template_data.get("device_types", []),
                items=template_data.get("items", []),
                triggers=template_data.get("triggers", []),
                is_default=template_data.get("is_default", True),
                created_by=current_user.id,
            )

            db.add(new_template)
            imported.append(template_data["name"])

        except Exception as e:
            failed.append({"file": template_file.name, "error": str(e)})

    if imported:
        db.commit()

    logger.info(f"Imported {len(imported)} default templates, skipped {len(skipped)}, failed {len(failed)}")

    return {
        "success": True,
        "imported": imported,
        "skipped": skipped,
        "failed": failed,
    }


# ============================================
# Template Statistics
# ============================================

@router.get("/stats/summary")
def get_template_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get template statistics"""
    from sqlalchemy import func

    total = db.query(func.count(MonitoringTemplate.id)).scalar()
    default_count = db.query(func.count(MonitoringTemplate.id)).filter_by(is_default=True).scalar()

    by_vendor = db.query(
        MonitoringTemplate.vendor,
        func.count(MonitoringTemplate.id)
    ).group_by(MonitoringTemplate.vendor).all()

    return {
        "total_templates": total,
        "default_templates": default_count,
        "custom_templates": total - default_count,
        "by_vendor": {vendor: count for vendor, count in by_vendor if vendor},
    }
