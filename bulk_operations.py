"""
Bulk operations for device management
"""
import pandas as pd
import io
from typing import List, Dict, Any
from fastapi import UploadFile
from pydantic import BaseModel

class BulkDeviceImport(BaseModel):
    hostname: str
    visible_name: str
    ip_address: str
    group_ids: List[str]
    template_ids: List[str]

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
    df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
    return df

async def parse_excel_file(file: UploadFile) -> pd.DataFrame:
    """Parse uploaded Excel file"""
    contents = await file.read()
    df = pd.read_excel(io.BytesIO(contents))
    return df

def validate_bulk_import_data(df: pd.DataFrame) -> tuple[bool, List[str]]:
    """Validate bulk import data structure"""
    required_columns = ['hostname', 'visible_name', 'ip_address', 'groups', 'templates']
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
    if 'ip_address' in df.columns:
        import re
        ip_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
        invalid_ips = []
        for idx, ip in enumerate(df['ip_address']):
            if pd.notna(ip) and not ip_pattern.match(str(ip)):
                invalid_ips.append(f"Row {idx+2}: {ip}")
        if invalid_ips:
            errors.append(f"Invalid IP addresses: {', '.join(invalid_ips[:5])}")

    return len(errors) == 0, errors

async def process_bulk_import(df: pd.DataFrame, zabbix_client) -> BulkOperationResult:
    """Process bulk device import"""
    total = len(df)
    successful = 0
    failed = 0
    errors = []
    details = []

    for idx, row in df.iterrows():
        try:
            # Parse groups and templates (assuming comma-separated)
            groups = str(row['groups']).split(',') if pd.notna(row['groups']) else []
            templates = str(row['templates']).split(',') if pd.notna(row['templates']) else []

            # Create host
            result = zabbix_client.create_host(
                hostname=str(row['hostname']),
                visible_name=str(row['visible_name']),
                ip_address=str(row['ip_address']),
                group_ids=[g.strip() for g in groups],
                template_ids=[t.strip() for t in templates]
            )

            if result.get('success'):
                successful += 1
                details.append({
                    'row': idx + 2,
                    'hostname': str(row['hostname']),
                    'status': 'success',
                    'hostid': result.get('hostid')
                })
            else:
                failed += 1
                errors.append({
                    'row': idx + 2,
                    'hostname': str(row['hostname']),
                    'error': result.get('error', 'Unknown error')
                })
        except Exception as e:
            failed += 1
            errors.append({
                'row': idx + 2,
                'hostname': str(row.get('hostname', 'Unknown')),
                'error': str(e)
            })

    return BulkOperationResult(
        success=failed == 0,
        total=total,
        successful=successful,
        failed=failed,
        errors=errors,
        details=details
    )

async def bulk_update_devices(host_ids: List[str], update_data: Dict[str, Any], zabbix_client) -> BulkOperationResult:
    """Bulk update multiple devices"""
    total = len(host_ids)
    successful = 0
    failed = 0
    errors = []
    details = []

    for hostid in host_ids:
        try:
            result = zabbix_client.update_host(hostid, **update_data)
            if result.get('success'):
                successful += 1
                details.append({
                    'hostid': hostid,
                    'status': 'success'
                })
            else:
                failed += 1
                errors.append({
                    'hostid': hostid,
                    'error': result.get('error', 'Unknown error')
                })
        except Exception as e:
            failed += 1
            errors.append({
                'hostid': hostid,
                'error': str(e)
            })

    return BulkOperationResult(
        success=failed == 0,
        total=total,
        successful=successful,
        failed=failed,
        errors=errors,
        details=details
    )

async def bulk_delete_devices(host_ids: List[str], zabbix_client) -> BulkOperationResult:
    """Bulk delete multiple devices"""
    total = len(host_ids)
    successful = 0
    failed = 0
    errors = []
    details = []

    for hostid in host_ids:
        try:
            result = zabbix_client.delete_host(hostid)
            if result.get('success'):
                successful += 1
                details.append({
                    'hostid': hostid,
                    'status': 'deleted'
                })
            else:
                failed += 1
                errors.append({
                    'hostid': hostid,
                    'error': result.get('error', 'Unknown error')
                })
        except Exception as e:
            failed += 1
            errors.append({
                'hostid': hostid,
                'error': str(e)
            })

    return BulkOperationResult(
        success=failed == 0,
        total=total,
        successful=successful,
        failed=failed,
        errors=errors,
        details=details
    )

def generate_csv_template() -> str:
    """Generate CSV template for bulk import"""
    template = """hostname,visible_name,ip_address,groups,templates
Example-Switch-01,Example Switch 01,192.168.1.10,"2,4","10001,10047"
Example-Router-01,Example Router 01,192.168.1.1,"2","10050"
Example-ATM-01,Example ATM Device 01,192.168.2.100,"5","10001"
"""
    return template

def export_devices_to_csv(devices: List[Dict]) -> str:
    """Export devices to CSV format"""
    df = pd.DataFrame(devices)
    # Select relevant columns
    columns_to_export = ['hostname', 'display_name', 'ip', 'region', 'branch', 'device_type', 'ping_status']
    df = df[[col for col in columns_to_export if col in df.columns]]
    return df.to_csv(index=False)

def export_devices_to_excel(devices: List[Dict]) -> bytes:
    """Export devices to Excel format"""
    df = pd.DataFrame(devices)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Devices')
    return output.getvalue()
