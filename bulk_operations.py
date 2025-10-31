"""
Bulk operations for device management
"""
import logging
import uuid
import pandas as pd
import io
from typing import List, Dict, Any
from fastapi import UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from monitoring.models import StandaloneDevice

logger = logging.getLogger(__name__)


class BulkOperationResult(BaseModel):
    success: bool
    total: int
    successful: int
    failed: int
    errors: List[Dict[str, Any]]
    details: List[Dict[str, Any]]


async def parse_csv_file(file: UploadFile) -> pd.DataFrame:
    """Parse uploaded CSV file"""
    contents = await file.read()
    df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    return df


async def parse_excel_file(file: UploadFile) -> pd.DataFrame:
    """Parse uploaded Excel file"""
    contents = await file.read()
    df = pd.read_excel(io.BytesIO(contents))
    return df


def validate_bulk_import_data(df: pd.DataFrame) -> tuple[bool, List[str]]:
    """Validate bulk import data structure"""
    required_columns = ["name", "ip"]
    errors = []

    # Check required columns
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors.append(f"Missing required columns: {', '.join(missing_columns)}")

    # Check for empty values
    if not errors:
        for col in required_columns:
            empty_count = df[col].isna().sum()
            if empty_count > 0:
                errors.append(f"Column '{col}' has {empty_count} empty values")

    # Validate IP addresses
    if "ip" in df.columns:
        import re

        ip_pattern = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")
        invalid_ips = []
        for idx, ip in enumerate(df["ip"]):
            if pd.notna(ip) and not ip_pattern.match(str(ip)):
                invalid_ips.append(f"Row {idx+2}: {ip}")
        if invalid_ips:
            errors.append(f"Invalid IP addresses: {', '.join(invalid_ips[:5])}")

    return len(errors) == 0, errors


def _get_value(row: pd.Series, column: str) -> Any:
    value = row.get(column)
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
    return value


async def process_bulk_import(df: pd.DataFrame, db: Session) -> BulkOperationResult:
    """Process bulk device import into standalone inventory"""
    total = len(df)
    successful = 0
    failed = 0
    errors = []
    details = []

    for idx, row in df.iterrows():
        try:
            name = _get_value(row, "name")
            ip = _get_value(row, "ip")

            if not name or not ip:
                raise ValueError("Missing required 'name' or 'ip'")

            vendor = _get_value(row, "vendor")
            device_type = _get_value(row, "device_type")
            location = _get_value(row, "location")
            enabled_raw = _get_value(row, "enabled")
            region = _get_value(row, "region")
            branch = _get_value(row, "branch")
            latitude = _get_value(row, "latitude")
            longitude = _get_value(row, "longitude")

            enabled = True
            if isinstance(enabled_raw, str):
                enabled = enabled_raw.lower() in ("1", "true", "yes", "on")
            elif isinstance(enabled_raw, (int, float)):
                enabled = bool(enabled_raw)
            elif isinstance(enabled_raw, bool):
                enabled = enabled_raw

            existing = db.query(StandaloneDevice).filter(StandaloneDevice.ip == ip).first()
            # Work on a fresh copy to ensure SQLAlchemy change detection
            custom_fields = dict((existing.custom_fields or {}) if existing else {})
            if region:
                custom_fields["region"] = region
            if branch:
                custom_fields["branch"] = branch
            if latitude is not None:
                try:
                    custom_fields["latitude"] = float(latitude)
                except ValueError:
                    pass
            if longitude is not None:
                try:
                    custom_fields["longitude"] = float(longitude)
                except ValueError:
                    pass

            if existing:
                existing.name = name
                existing.vendor = vendor
                existing.device_type = device_type
                existing.location = location
                existing.enabled = enabled
                existing.custom_fields = dict(custom_fields)
                db.add(existing)
                action = "updated"
            else:
                device = StandaloneDevice(
                    id=uuid.uuid4(),
                    name=name,
                    ip=ip,
                    vendor=vendor,
                    device_type=device_type,
                    location=location,
                    enabled=enabled,
                    custom_fields=dict(custom_fields),
                )
                db.add(device)
                action = "created"

            successful += 1
            details.append(
                {
                    "row": idx + 2,
                    "ip": ip,
                    "status": action,
                }
            )
        except Exception as e:
            failed += 1
            errors.append({"row": idx + 2, "device": str(row.get("name", row.get("ip", "Unknown"))), "error": str(e)})

    db.commit()

    return BulkOperationResult(
        success=failed == 0, total=total, successful=successful, failed=failed, errors=errors, details=details
    )


async def bulk_update_devices(host_ids: List[str], update_data: Dict[str, Any], db: Session) -> BulkOperationResult:
    """Bulk update multiple standalone devices"""
    total = len(host_ids)
    successful = 0
    failed = 0
    errors = []
    details = []

    for hostid in host_ids:
        try:
            device_uuid = uuid.UUID(hostid)
            device = db.query(StandaloneDevice).filter(StandaloneDevice.id == device_uuid).first()
            if not device:
                raise ValueError("Device not found")

            fields = dict(device.custom_fields or {})
            for key, value in update_data.items():
                if key in {"name", "hostname"}:
                    device.name = value
                elif key == "vendor":
                    device.vendor = value
                elif key == "device_type":
                    device.device_type = value
                elif key == "ip":
                    device.ip = value
                elif key == "location":
                    device.location = value
                elif key in {"enabled", "is_active"}:
                    device.enabled = bool(value)
                elif key in {"region", "branch", "latitude", "longitude"}:
                    fields[key] = value
                else:
                    # store any other custom field
                    fields[key] = value

            device.custom_fields = dict(fields)
            db.add(device)
            successful += 1
            details.append({"hostid": hostid, "status": "success"})
        except Exception as e:
            failed += 1
            errors.append({"hostid": hostid, "error": str(e)})

    db.commit()

    return BulkOperationResult(
        success=failed == 0, total=total, successful=successful, failed=failed, errors=errors, details=details
    )


async def bulk_delete_devices(host_ids: List[str], db: Session) -> BulkOperationResult:
    """Bulk delete standalone devices"""
    total = len(host_ids)
    successful = 0
    failed = 0
    errors = []
    details = []

    for hostid in host_ids:
        try:
            device_uuid = uuid.UUID(hostid)
            device = db.query(StandaloneDevice).filter(StandaloneDevice.id == device_uuid).first()
            if not device:
                raise ValueError("Device not found")
            db.delete(device)
            successful += 1
            details.append({"hostid": hostid, "status": "deleted"})
        except Exception as e:
            failed += 1
            errors.append({"hostid": hostid, "error": str(e)})

    db.commit()

    return BulkOperationResult(
        success=failed == 0, total=total, successful=successful, failed=failed, errors=errors, details=details
    )


def generate_csv_template() -> str:
    """Generate CSV template for bulk import"""
    template = """name,ip,vendor,device_type,region,branch,latitude,longitude,enabled
Branch-Switch-01,192.168.1.10,Cisco,Switch,Tbilisi,Didube,41.779,44.8,true
Router-Edge-01,192.168.1.1,Cisco,Router,Imereti,Kutaisi,,,
"""
    return template


def _serialize_device(device: StandaloneDevice) -> Dict[str, Any]:
    fields = device.custom_fields or {}
    return {
        "id": str(device.id),
        "name": device.name,
        "ip": device.ip,
        "vendor": device.vendor,
        "device_type": device.device_type,
        "region": fields.get("region"),
        "branch": fields.get("branch"),
        "latitude": fields.get("latitude"),
        "longitude": fields.get("longitude"),
        "enabled": device.enabled,
        "location": device.location,
    }


def export_devices_to_csv(devices: List[StandaloneDevice]) -> str:
    """Export standalone devices to CSV format"""
    records = [_serialize_device(device) for device in devices]
    df = pd.DataFrame(records)
    columns_to_export = ["id", "name", "ip", "vendor", "device_type", "region", "branch", "latitude", "longitude", "enabled"]
    df = df[[col for col in columns_to_export if col in df.columns]]
    return df.to_csv(index=False)


def export_devices_to_excel(devices: List[StandaloneDevice]) -> bytes:
    """Export standalone devices to Excel format"""
    records = [_serialize_device(device) for device in devices]
    df = pd.DataFrame(records)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Devices")
    return output.getvalue()
