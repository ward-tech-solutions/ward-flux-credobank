"""
WARD Tech Solutions - Bulk Operations Router
Handles bulk import, update, delete, and export operations
"""
import io
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

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
from database import User, UserRole
from routers.utils import run_in_executor

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
    request: Request, file: UploadFile, current_user: User = Depends(require_tech_or_admin)
):
    """Bulk import devices from CSV/Excel"""
    zabbix = request.app.state.zabbix

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
    result = await process_bulk_import(df, zabbix)
    return result


@router.post("/update", response_model=BulkOperationResult)
async def bulk_update(
    request: Request, host_ids: List[str], update_data: dict, current_user: User = Depends(require_tech_or_admin)
):
    """Bulk update multiple devices"""
    zabbix = request.app.state.zabbix
    result = await bulk_update_devices(host_ids, update_data, zabbix)
    return result


@router.post("/delete", response_model=BulkOperationResult)
async def bulk_delete(request: Request, host_ids: List[str], current_user: User = Depends(require_admin)):
    """Bulk delete multiple devices"""
    zabbix = request.app.state.zabbix
    result = await bulk_delete_devices(host_ids, zabbix)
    return result


@router.get("/export/csv")
async def export_csv(request: Request, current_user: User = Depends(get_current_active_user)):
    """Export devices to CSV (filtered by user permissions)"""
    zabbix = request.app.state.zabbix
    devices = await run_in_executor(zabbix.get_all_hosts)

    # Apply user permission filtering (non-admin users)
    if current_user.role != UserRole.ADMIN:
        # Filter by region if user has regional restriction
        if current_user.region:
            devices = [d for d in devices if d.get("region") == current_user.region]

        # Filter by branches if user has branch restrictions
        if current_user.branches:
            allowed_branches = [b.strip() for b in current_user.branches.split(",")]
            devices = [d for d in devices if d.get("branch") in allowed_branches]

    csv_content = export_devices_to_csv(devices)
    return StreamingResponse(
        iter([csv_content]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=devices_export.csv"}
    )


@router.get("/export/excel")
async def export_excel(request: Request, current_user: User = Depends(get_current_active_user)):
    """Export devices to Excel (filtered by user permissions)"""
    zabbix = request.app.state.zabbix
    devices = await run_in_executor(zabbix.get_all_hosts)

    # Apply user permission filtering (non-admin users)
    if current_user.role != UserRole.ADMIN:
        # Filter by region if user has regional restriction
        if current_user.region:
            devices = [d for d in devices if d.get("region") == current_user.region]

        # Filter by branches if user has branch restrictions
        if current_user.branches:
            allowed_branches = [b.strip() for b in current_user.branches.split(",")]
            devices = [d for d in devices if d.get("branch") in allowed_branches]

    excel_content = export_devices_to_excel(devices)
    return StreamingResponse(
        io.BytesIO(excel_content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=devices_export.xlsx"},
    )
