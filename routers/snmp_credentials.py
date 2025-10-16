"""
WARD FLUX - SNMP Credential Management API

Provides CRUD operations for SNMP credentials with:
- SNMPv2c and SNMPv3 support
- Encrypted credential storage
- Connectivity testing
- Vendor auto-detection
- Template auto-assignment
"""

import logging
import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db, User
from monitoring.models import SNMPCredential, StandaloneDevice, MonitoringTemplate, MonitoringItem
from monitoring.snmp.crypto import encrypt_credential, decrypt_credential
from monitoring.snmp.poller import test_snmp_connection, detect_vendor
from routers.auth import get_current_active_user

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/snmp/credentials", tags=["snmp-credentials"])


# ============================================
# Pydantic Models
# ============================================

class SNMPv2cCreate(BaseModel):
    device_id: str
    community: str


class SNMPv3Create(BaseModel):
    device_id: str
    username: str
    security_level: str  # noAuthNoPriv, authNoPriv, authPriv
    auth_protocol: Optional[str] = None  # MD5, SHA
    auth_key: Optional[str] = None
    priv_protocol: Optional[str] = None  # DES, AES
    priv_key: Optional[str] = None


class SNMPCredentialResponse(BaseModel):
    id: str
    device_id: str
    version: str
    # v2c
    community_set: bool
    # v3
    username: Optional[str]
    security_level: Optional[str]
    auth_protocol: Optional[str]
    priv_protocol: Optional[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=str(obj.id),
            device_id=str(obj.device_id),
            version=obj.version,
            community_set=bool(obj.community_encrypted),
            username=obj.username,
            security_level=obj.security_level,
            auth_protocol=obj.auth_protocol,
            priv_protocol=obj.priv_protocol,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )

    class Config:
        from_attributes = True


class SNMPTestRequest(BaseModel):
    device_id: str
    test_oid: Optional[str] = "1.3.6.1.2.1.1.1.0"  # sysDescr


class SNMPTestResponse(BaseModel):
    success: bool
    device_ip: str
    oid: str
    value: Optional[str]
    error: Optional[str]
    vendor_detected: Optional[str]


# ============================================
# CRUD Endpoints
# ============================================

@router.post("/v2c", response_model=SNMPCredentialResponse, status_code=status.HTTP_201_CREATED)
def create_snmpv2c_credential(
    credential: SNMPv2cCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create SNMPv2c credential for a device"""

    # Verify device exists
    device = db.query(StandaloneDevice).filter_by(id=uuid.UUID(credential.device_id)).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Check if credential already exists
    existing = db.query(SNMPCredential).filter_by(device_id=device.id).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"SNMP credential already exists for device {device.name}. Use PUT to update."
        )

    # Encrypt community string
    community_encrypted = encrypt_credential(credential.community)

    # Create credential
    new_credential = SNMPCredential(
        id=uuid.uuid4(),
        device_id=device.id,
        version="v2c",
        community_encrypted=community_encrypted,
    )

    db.add(new_credential)
    db.commit()
    db.refresh(new_credential)

    logger.info(f"Created SNMPv2c credential for device: {device.name}")
    return SNMPCredentialResponse.from_orm(new_credential)


@router.post("/v3", response_model=SNMPCredentialResponse, status_code=status.HTTP_201_CREATED)
def create_snmpv3_credential(
    credential: SNMPv3Create,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create SNMPv3 credential for a device"""

    # Verify device exists
    device = db.query(StandaloneDevice).filter_by(id=uuid.UUID(credential.device_id)).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Check if credential already exists
    existing = db.query(SNMPCredential).filter_by(device_id=device.id).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"SNMP credential already exists for device {device.name}. Use PUT to update."
        )

    # Encrypt keys if provided
    auth_key_encrypted = encrypt_credential(credential.auth_key) if credential.auth_key else None
    priv_key_encrypted = encrypt_credential(credential.priv_key) if credential.priv_key else None

    # Create credential
    new_credential = SNMPCredential(
        id=uuid.uuid4(),
        device_id=device.id,
        version="v3",
        username=credential.username,
        security_level=credential.security_level,
        auth_protocol=credential.auth_protocol,
        auth_key_encrypted=auth_key_encrypted,
        priv_protocol=credential.priv_protocol,
        priv_key_encrypted=priv_key_encrypted,
    )

    db.add(new_credential)
    db.commit()
    db.refresh(new_credential)

    logger.info(f"Created SNMPv3 credential for device: {device.name}")
    return SNMPCredentialResponse.from_orm(new_credential)


@router.get("/device/{device_id}", response_model=SNMPCredentialResponse)
def get_device_credential(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get SNMP credential for a device"""

    credential = db.query(SNMPCredential).filter_by(device_id=uuid.UUID(device_id)).first()
    if not credential:
        raise HTTPException(status_code=404, detail="SNMP credential not found for this device")

    return SNMPCredentialResponse.from_orm(credential)


@router.delete("/device/{device_id}")
def delete_device_credential(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete SNMP credential for a device"""

    credential = db.query(SNMPCredential).filter_by(device_id=uuid.UUID(device_id)).first()
    if not credential:
        raise HTTPException(status_code=404, detail="SNMP credential not found")

    db.delete(credential)
    db.commit()

    logger.info(f"Deleted SNMP credential for device: {device_id}")
    return {"success": True, "message": "SNMP credential deleted"}


@router.get("/list", response_model=List[SNMPCredentialResponse])
def list_credentials(
    version: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all SNMP credentials with optional filters"""

    query = db.query(SNMPCredential)

    if version:
        query = query.filter(SNMPCredential.version == version)

    credentials = query.offset(skip).limit(limit).all()
    return [SNMPCredentialResponse.from_orm(c) for c in credentials]


# ============================================
# SNMP Testing & Detection
# ============================================

@router.post("/test", response_model=SNMPTestResponse)
async def test_snmp_credential(
    test_request: SNMPTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Test SNMP connectivity and optionally detect vendor"""

    # Get device
    device = db.query(StandaloneDevice).filter_by(id=uuid.UUID(test_request.device_id)).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Get credential
    credential = db.query(SNMPCredential).filter_by(device_id=device.id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="SNMP credential not found for this device")

    # Prepare SNMP parameters
    if credential.version == "v2c":
        community = decrypt_credential(credential.community_encrypted)
        snmp_params = {
            "version": "v2c",
            "community": community,
        }
    else:  # v3
        snmp_params = {
            "version": "v3",
            "username": credential.username,
            "security_level": credential.security_level,
        }
        if credential.auth_key_encrypted:
            snmp_params["auth_protocol"] = credential.auth_protocol
            snmp_params["auth_key"] = decrypt_credential(credential.auth_key_encrypted)
        if credential.priv_key_encrypted:
            snmp_params["priv_protocol"] = credential.priv_protocol
            snmp_params["priv_key"] = decrypt_credential(credential.priv_key_encrypted)

    # Test SNMP connection
    try:
        result = await test_snmp_connection(device.ip, test_request.test_oid, snmp_params)

        # If testing sysDescr, try to detect vendor
        vendor_detected = None
        if test_request.test_oid == "1.3.6.1.2.1.1.1.0" and result.get("success"):
            vendor_detected = detect_vendor(result.get("value", ""))

            # Update device vendor if detected and not already set
            if vendor_detected and not device.vendor:
                device.vendor = vendor_detected
                db.commit()
                logger.info(f"Auto-detected vendor for {device.name}: {vendor_detected}")

        return SNMPTestResponse(
            success=result.get("success", False),
            device_ip=device.ip,
            oid=test_request.test_oid,
            value=result.get("value"),
            error=result.get("error"),
            vendor_detected=vendor_detected,
        )

    except Exception as e:
        logger.error(f"SNMP test failed for {device.name}: {e}")
        return SNMPTestResponse(
            success=False,
            device_ip=device.ip,
            oid=test_request.test_oid,
            value=None,
            error=str(e),
            vendor_detected=None,
        )


@router.post("/detect-vendor/{device_id}")
async def detect_device_vendor(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Auto-detect device vendor via SNMP sysDescr"""

    # Get device
    device = db.query(StandaloneDevice).filter_by(id=uuid.UUID(device_id)).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Get credential
    credential = db.query(SNMPCredential).filter_by(device_id=device.id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="SNMP credential not found. Please add credentials first.")

    # Prepare SNMP parameters
    if credential.version == "v2c":
        community = decrypt_credential(credential.community_encrypted)
        snmp_params = {"version": "v2c", "community": community}
    else:
        snmp_params = {
            "version": "v3",
            "username": credential.username,
            "security_level": credential.security_level,
        }
        if credential.auth_key_encrypted:
            snmp_params["auth_protocol"] = credential.auth_protocol
            snmp_params["auth_key"] = decrypt_credential(credential.auth_key_encrypted)
        if credential.priv_key_encrypted:
            snmp_params["priv_protocol"] = credential.priv_protocol
            snmp_params["priv_key"] = decrypt_credential(credential.priv_key_encrypted)

    # Query sysDescr
    try:
        result = await test_snmp_connection(device.ip, "1.3.6.1.2.1.1.1.0", snmp_params)

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=f"SNMP query failed: {result.get('error')}")

        sys_descr = result.get("value", "")
        vendor_detected = detect_vendor(sys_descr)

        if vendor_detected:
            # Update device
            old_vendor = device.vendor
            device.vendor = vendor_detected
            device.updated_at = datetime.utcnow()
            db.commit()

            logger.info(f"Detected vendor for {device.name}: {vendor_detected} (was: {old_vendor})")

            return {
                "success": True,
                "device_name": device.name,
                "sys_descr": sys_descr[:200],  # Truncate for response
                "vendor_detected": vendor_detected,
                "vendor_updated": True,
            }
        else:
            return {
                "success": False,
                "device_name": device.name,
                "sys_descr": sys_descr[:200],
                "vendor_detected": None,
                "vendor_updated": False,
                "message": "Could not determine vendor from sysDescr",
            }

    except Exception as e:
        logger.error(f"Vendor detection failed for {device.name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-assign-template/{device_id}")
def auto_assign_template(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Auto-assign monitoring template based on detected vendor"""

    # Get device
    device = db.query(StandaloneDevice).filter_by(id=uuid.UUID(device_id)).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if not device.vendor:
        raise HTTPException(
            status_code=400,
            detail="Device vendor not set. Run vendor detection first."
        )

    # Find matching template
    template = db.query(MonitoringTemplate).filter_by(
        vendor=device.vendor,
        is_default=True
    ).first()

    if not template:
        raise HTTPException(
            status_code=404,
            detail=f"No default template found for vendor: {device.vendor}"
        )

    # Check if items already exist
    existing_items = db.query(MonitoringItem).filter_by(device_id=device.id).count()
    if existing_items > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Device already has {existing_items} monitoring items. Delete them first to re-assign template."
        )

    # Create monitoring items from template
    created_items = []
    for item_def in template.items:
        monitoring_item = MonitoringItem(
            id=uuid.uuid4(),
            device_id=device.id,
            template_id=template.id,
            oid_name=item_def["oid_name"],
            oid=item_def["oid"],
            interval=item_def.get("interval", 60),
            value_type=item_def.get("value_type", "integer"),
            units=item_def.get("units", ""),
            enabled=True,
        )
        db.add(monitoring_item)
        created_items.append(item_def["name"])

    db.commit()

    logger.info(f"Auto-assigned template '{template.name}' to device {device.name}: {len(created_items)} items created")

    return {
        "success": True,
        "device_name": device.name,
        "vendor": device.vendor,
        "template_name": template.name,
        "items_created": len(created_items),
        "item_names": created_items[:10],  # First 10 for preview
    }


# ============================================
# Manual OID Query
# ============================================

@router.post("/query-oid")
async def query_oid_manual(
    device_id: str,
    oid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Manually query a specific OID on a device (for testing/debugging)"""

    # Get device
    device = db.query(StandaloneDevice).filter_by(id=uuid.UUID(device_id)).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Get credential
    credential = db.query(SNMPCredential).filter_by(device_id=device.id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="SNMP credential not found")

    # Prepare SNMP parameters
    if credential.version == "v2c":
        community = decrypt_credential(credential.community_encrypted)
        snmp_params = {"version": "v2c", "community": community}
    else:
        snmp_params = {
            "version": "v3",
            "username": credential.username,
            "security_level": credential.security_level,
        }
        if credential.auth_key_encrypted:
            snmp_params["auth_protocol"] = credential.auth_protocol
            snmp_params["auth_key"] = decrypt_credential(credential.auth_key_encrypted)
        if credential.priv_key_encrypted:
            snmp_params["priv_protocol"] = credential.priv_protocol
            snmp_params["priv_key"] = decrypt_credential(credential.priv_key_encrypted)

    # Query OID
    try:
        result = await test_snmp_connection(device.ip, oid, snmp_params)
        return {
            "success": result.get("success", False),
            "device_name": device.name,
            "device_ip": device.ip,
            "oid": oid,
            "value": result.get("value"),
            "error": result.get("error"),
        }
    except Exception as e:
        logger.error(f"Manual OID query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
