"""
WARD Tech Solutions - Bulk Operations Router
Handles bulk import, update, delete, and export operations
"""
import logging
import io
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from auth import get_current_active_user, require_admin, require_tech_or_admin
from bulk_operations import (
    BulkOperationResult,
    bulk_delete_devices,
    bulk_update_devices,
    export_devices_to_csv,
    export_devices_to_excel,
    generate_csv_template,
    parse_csv_file,
    parse_excel_file,
    process_bulk_import,
    validate_bulk_import_data,
)
from database import User, UserRole, get_db
from monitoring.models import StandaloneDevice

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/bulk", tags=["bulk-operations"])


@router.get("/template")
async def download_bulk_import_template(current_user: User = Depends(require_tech_or_admin)):
    """Download CSV template for bulk import"""
    csv_content = generate_csv_template()
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bulk_import_template.csv"},
    )


@router.post("/import", response_model=BulkOperationResult)
async def bulk_import_devices(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tech_or_admin),
):
    """Bulk import devices from CSV/Excel"""

    # Parse file
    if file.filename.endswith(".csv"):
        df = await parse_csv_file(file)
    elif file.filename.endswith((".xlsx", ".xls")):
        df = await parse_excel_file(file)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Use CSV or Excel")

    # Validate data
    is_valid, errors = validate_bulk_import_data(df)
    if not is_valid:
        return BulkOperationResult(
            success=False, total=0, successful=0, failed=0, errors=[{"error": err} for err in errors], details=[]
        )

    # Process import
    result = await process_bulk_import(df, db)
    return result


@router.post("/update", response_model=BulkOperationResult)
async def bulk_update(
    host_ids: List[str],
    update_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tech_or_admin),
):
    """Bulk update multiple devices"""
    result = await bulk_update_devices(host_ids, update_data, db)
    return result


@router.post("/delete", response_model=BulkOperationResult)
async def bulk_delete(
    host_ids: List[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Bulk delete multiple devices"""
    result = await bulk_delete_devices(host_ids, db)
    return result


@router.get("/export/csv")
async def export_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Export devices to CSV (filtered by user permissions)"""
    devices = _filter_devices_for_user(db, current_user)
    csv_content = export_devices_to_csv(devices)
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=devices_export.csv"},
    )


@router.get("/export/excel")
async def export_excel(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Export devices to Excel (filtered by user permissions)"""
    devices = _filter_devices_for_user(db, current_user)
    excel_content = export_devices_to_excel(devices)
    return StreamingResponse(
        io.BytesIO(excel_content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=devices_export.xlsx"},
    )


def _filter_devices_for_user(db: Session, user: User) -> List[StandaloneDevice]:
    devices = db.query(StandaloneDevice).all()
    if user.role == UserRole.ADMIN:
        return devices

    allowed = [b.strip() for b in (user.branches or "").split(",") if b.strip()] if user.branches else []

    filtered: List[StandaloneDevice] = []
    for device in devices:
        fields = device.custom_fields or {}
        if user.region and fields.get("region") != user.region:
            continue
        if allowed and fields.get("branch") not in allowed:
            continue
        filtered.append(device)
    return filtered
