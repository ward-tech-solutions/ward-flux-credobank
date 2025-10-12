"""
WARD FLUX - Monitoring API Router
Standalone monitoring with Zabbix integration for device management
"""

import logging
import asyncio
import uuid
from typing import List, Dict, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database import get_db, User
from auth import get_current_active_user
from monitoring.models import (
    MonitoringProfile,
    SNMPCredential,
    MonitoringItem,
    MonitoringMode,
)
from monitoring.snmp.oids import UNIVERSAL_OIDS, get_vendor_oids
from monitoring.snmp.poller import get_snmp_poller, SNMPCredentialData
from monitoring.snmp.crypto import encrypt_credential, decrypt_credential

logger = logging.getLogger(__name__)

# Supported vendors
SUPPORTED_VENDORS = ["Cisco", "Fortinet", "Juniper", "HP", "Linux", "Windows", "MikroTik", "Ubiquiti", "PaloAlto"]

# Create router
router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


# ============================================
# Pydantic Models
# ============================================

class MonitoringProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    mode: str = Field(..., pattern="^(zabbix|standalone|hybrid)$")
    description: Optional[str] = None


class MonitoringProfileResponse(BaseModel):
    id: str
    name: str
    mode: str
    is_active: bool
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SNMPCredentialCreate(BaseModel):
    hostid: str = Field(..., description="Zabbix host ID")
    version: str = Field(..., pattern="^(v2c|v3)$")
    # v2c
    community: Optional[str] = None
    # v3
    username: Optional[str] = None
    auth_protocol: Optional[str] = None
    auth_key: Optional[str] = None
    priv_protocol: Optional[str] = None
    priv_key: Optional[str] = None
    security_level: Optional[str] = None


class SNMPCredentialResponse(BaseModel):
    id: str
    device_id: str
    version: str
    username: Optional[str]
    auth_protocol: Optional[str]
    priv_protocol: Optional[str]
    security_level: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeviceDetectionResponse(BaseModel):
    hostid: str
    hostname: str
    ip: str
    vendor: Optional[str]
    device_type: str
    sys_descr: Optional[str]
    recommended_template: Optional[str]
    available_oids: int


class MonitoringItemCreate(BaseModel):
    hostid: str
    oid_name: str
    oid: str
    interval: int = Field(default=60, ge=30, le=3600)
    enabled: bool = True


class MonitoringItemResponse(BaseModel):
    id: str
    device_id: str
    oid_name: str
    oid: str
    interval: int
    enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class OIDInfo(BaseModel):
    name: str
    oid: str
    description: str
    value_type: str
    category: str


# ============================================
# Helper Functions
# ============================================

def get_device_from_zabbix(request: Request, hostid: str) -> Dict:
    """Get device information from Zabbix"""
    zabbix = request.app.state.zabbix
    device = zabbix.get_host_details(hostid)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device not found in Zabbix: {hostid}")
    return device


# ============================================
# Monitoring Profile Endpoints
# ============================================

@router.get("/profiles", response_model=List[MonitoringProfileResponse])
def list_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all monitoring profiles"""
    profiles = db.query(MonitoringProfile).all()
    return profiles


@router.post("/profiles", response_model=MonitoringProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(
    profile: MonitoringProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new monitoring profile"""
    existing = db.query(MonitoringProfile).filter_by(name=profile.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Profile name already exists")

    new_profile = MonitoringProfile(
        id=uuid.uuid4(),
        name=profile.name,
        mode=MonitoringMode(profile.mode),
        description=profile.description,
    )

    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)

    logger.info(f"Created monitoring profile: {new_profile.name} (mode={new_profile.mode})")
    return new_profile


@router.post("/profiles/{profile_id}/activate")
def activate_profile(
    profile_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Activate a monitoring profile"""
    profile = db.query(MonitoringProfile).filter_by(id=uuid.UUID(profile_id)).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Deactivate all profiles
    db.query(MonitoringProfile).update({"is_active": False})
    profile.is_active = True
    db.commit()

    logger.info(f"Activated monitoring profile: {profile.name} (mode={profile.mode})")
    return {"success": True, "active_profile": profile.name, "mode": profile.mode.value}


# ============================================
# SNMP Credential Endpoints
# ============================================

@router.post("/credentials", response_model=SNMPCredentialResponse, status_code=status.HTTP_201_CREATED)
def create_snmp_credential(
    request: Request,
    credential: SNMPCredentialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create SNMP credentials for a Zabbix device"""
    # Verify device exists in Zabbix
    device = get_device_from_zabbix(request, credential.hostid)

    # Use hostid as device_id (store as UUID)
    device_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"zabbix-host-{credential.hostid}")

    # Check if credentials already exist
    existing = db.query(SNMPCredential).filter_by(device_id=device_uuid).first()
    if existing:
        raise HTTPException(status_code=400, detail="Credentials already exist for this device")

    # Create new credentials
    new_cred = SNMPCredential(
        id=uuid.uuid4(),
        device_id=device_uuid,
        version=credential.version,
    )

    if credential.version == "v2c":
        if not credential.community:
            raise HTTPException(status_code=400, detail="Community string required for SNMPv2c")
        new_cred.community_encrypted = encrypt_credential(credential.community)
    else:  # v3
        if not credential.username:
            raise HTTPException(status_code=400, detail="Username required for SNMPv3")
        new_cred.username = credential.username
        new_cred.auth_protocol = credential.auth_protocol
        new_cred.priv_protocol = credential.priv_protocol
        new_cred.security_level = credential.security_level
        if credential.auth_key:
            new_cred.auth_key_encrypted = encrypt_credential(credential.auth_key)
        if credential.priv_key:
            new_cred.priv_key_encrypted = encrypt_credential(credential.priv_key)

    db.add(new_cred)
    db.commit()
    db.refresh(new_cred)

    logger.info(f"Created SNMP credentials for {device['hostname']} ({credential.version})")
    return new_cred


@router.get("/credentials/host/{hostid}", response_model=SNMPCredentialResponse)
def get_credentials_by_host(
    hostid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get SNMP credentials for a Zabbix host"""
    device_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"zabbix-host-{hostid}")
    cred = db.query(SNMPCredential).filter_by(device_id=device_uuid).first()
    if not cred:
        raise HTTPException(status_code=404, detail="No credentials found for this host")
    return cred


@router.delete("/credentials/{credential_id}")
def delete_credential(
    credential_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete SNMP credentials"""
    cred = db.query(SNMPCredential).filter_by(id=uuid.UUID(credential_id)).first()
    if not cred:
        raise HTTPException(status_code=404, detail="Credentials not found")

    db.delete(cred)
    db.commit()
    logger.info(f"Deleted SNMP credentials {credential_id}")
    return {"success": True, "message": "Credentials deleted"}


@router.post("/credentials/test")
async def test_snmp_credentials(
    request: Request,
    credential: SNMPCredentialCreate,
    current_user: User = Depends(get_current_active_user),
):
    """Test SNMP credentials against a Zabbix device"""
    # Get device IP from Zabbix
    device = get_device_from_zabbix(request, credential.hostid)
    device_ip = device.get("ip")
    if not device_ip or device_ip == "N/A":
        raise HTTPException(status_code=400, detail="Device has no IP address in Zabbix")

    # Build credential data
    cred_data = SNMPCredentialData(version=credential.version)
    if credential.version == "v2c":
        cred_data.community = credential.community or "public"
    else:
        cred_data.username = credential.username
        cred_data.auth_protocol = credential.auth_protocol
        cred_data.auth_key = credential.auth_key
        cred_data.priv_protocol = credential.priv_protocol
        cred_data.priv_key = credential.priv_key
        cred_data.security_level = credential.security_level

    # Test connection
    poller = get_snmp_poller()
    try:
        result = await poller.get(device_ip, UNIVERSAL_OIDS["sysDescr"].oid, cred_data)
        if result.success:
            logger.info(f"SNMP test successful for {device['hostname']} ({device_ip})")
            return {
                "success": True,
                "message": "SNMP connection successful",
                "sys_descr": result.value,
                "device": device['hostname'],
                "ip": device_ip
            }
        else:
            return {
                "success": False,
                "message": f"SNMP connection failed: {result.error}",
                "device": device['hostname'],
                "ip": device_ip
            }
    except Exception as e:
        logger.error(f"SNMP test error for {device_ip}: {e}")
        raise HTTPException(status_code=500, detail=f"SNMP test failed: {str(e)}")


# ============================================
# Device Detection Endpoint
# ============================================

@router.post("/detect/{hostid}", response_model=DeviceDetectionResponse)
async def detect_device(
    request: Request,
    hostid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Auto-detect device vendor and type via SNMP"""
    # Get device from Zabbix
    device = get_device_from_zabbix(request, hostid)
    device_ip = device.get("ip")
    if not device_ip or device_ip == "N/A":
        raise HTTPException(status_code=400, detail="Device has no IP address")

    # Get SNMP credentials
    device_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"zabbix-host-{hostid}")
    cred = db.query(SNMPCredential).filter_by(device_id=device_uuid).first()
    if not cred:
        raise HTTPException(status_code=400, detail="No SNMP credentials configured. Please add credentials first.")

    # Build credential data
    cred_data = SNMPCredentialData(version=cred.version)
    if cred.version == "v2c":
        cred_data.community = decrypt_credential(cred.community_encrypted)
    else:
        cred_data.username = cred.username
        cred_data.auth_protocol = cred.auth_protocol
        cred_data.auth_key = decrypt_credential(cred.auth_key_encrypted) if cred.auth_key_encrypted else None
        cred_data.priv_protocol = cred.priv_protocol
        cred_data.priv_key = decrypt_credential(cred.priv_key_encrypted) if cred.priv_key_encrypted else None
        cred_data.security_level = cred.security_level

    # Detect device
    poller = get_snmp_poller()
    try:
        detection_result = await poller.detect_device(device_ip, cred_data)

        vendor = detection_result.get("vendor")
        vendor_oids = get_vendor_oids(vendor) if vendor else UNIVERSAL_OIDS
        recommended_template = f"{vendor} {detection_result.get('device_type', 'Generic')}" if vendor else None

        logger.info(f"Device detection for {device['hostname']}: vendor={vendor}, type={detection_result.get('device_type')}")

        return DeviceDetectionResponse(
            hostid=hostid,
            hostname=device['hostname'],
            ip=device_ip,
            vendor=vendor,
            device_type=detection_result.get("device_type", "unknown"),
            sys_descr=detection_result.get("sys_descr"),
            recommended_template=recommended_template,
            available_oids=len(vendor_oids)
        )
    except Exception as e:
        logger.error(f"Device detection failed for {hostid}: {e}")
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")


# ============================================
# Monitoring Item Endpoints
# ============================================

@router.post("/items", response_model=MonitoringItemResponse, status_code=status.HTTP_201_CREATED)
def create_monitoring_item(
    request: Request,
    item: MonitoringItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a monitoring item for a Zabbix device"""
    # Verify device exists in Zabbix
    device = get_device_from_zabbix(request, item.hostid)

    # Convert hostid to UUID
    device_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"zabbix-host-{item.hostid}")

    # Create monitoring item
    new_item = MonitoringItem(
        id=uuid.uuid4(),
        device_id=device_uuid,
        oid_name=item.oid_name,
        oid=item.oid,
        interval=item.interval,
        enabled=item.enabled,
    )

    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    logger.info(f"Created monitoring item {item.oid_name} for {device['hostname']}")
    return new_item


@router.get("/items/host/{hostid}", response_model=List[MonitoringItemResponse])
def list_monitoring_items(
    hostid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all monitoring items for a Zabbix host"""
    device_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"zabbix-host-{hostid}")
    items = db.query(MonitoringItem).filter_by(device_id=device_uuid).all()
    return items


@router.delete("/items/{item_id}")
def delete_monitoring_item(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a monitoring item"""
    item = db.query(MonitoringItem).filter_by(id=uuid.UUID(item_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Monitoring item not found")

    db.delete(item)
    db.commit()
    logger.info(f"Deleted monitoring item {item_id}")
    return {"success": True, "message": "Monitoring item deleted"}


# ============================================
# Polling Endpoint
# ============================================

@router.post("/poll/{hostid}")
async def poll_device(
    request: Request,
    hostid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Manually trigger SNMP polling for a device"""
    # Get device
    device = get_device_from_zabbix(request, hostid)
    device_ip = device.get("ip")
    if not device_ip or device_ip == "N/A":
        raise HTTPException(status_code=400, detail="Device has no IP address")

    # Get credentials
    device_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"zabbix-host-{hostid}")
    cred = db.query(SNMPCredential).filter_by(device_id=device_uuid).first()
    if not cred:
        raise HTTPException(status_code=400, detail="No SNMP credentials configured")

    # Get monitoring items
    items = db.query(MonitoringItem).filter_by(device_id=device_uuid, enabled=True).all()
    if not items:
        raise HTTPException(status_code=400, detail="No monitoring items configured")

    # Build credential data
    cred_data = SNMPCredentialData(version=cred.version)
    if cred.version == "v2c":
        cred_data.community = decrypt_credential(cred.community_encrypted)
    else:
        cred_data.username = cred.username
        cred_data.auth_protocol = cred.auth_protocol
        cred_data.auth_key = decrypt_credential(cred.auth_key_encrypted) if cred.auth_key_encrypted else None
        cred_data.priv_protocol = cred.priv_protocol
        cred_data.priv_key = decrypt_credential(cred.priv_key_encrypted) if cred.priv_key_encrypted else None
        cred_data.security_level = cred.security_level

    # Poll all items
    poller = get_snmp_poller()
    oids = [item.oid for item in items]

    try:
        results = await poller.bulk_get(device_ip, oids, cred_data)

        # Format results
        poll_results = []
        for item, result in zip(items, results):
            poll_results.append({
                "oid_name": item.oid_name,
                "oid": item.oid,
                "success": result.success,
                "value": result.value if result.success else None,
                "error": result.error if not result.success else None,
            })

        logger.info(f"Manual poll completed for {device['hostname']}: {len(poll_results)} items")
        return {
            "success": True,
            "device": device['hostname'],
            "ip": device_ip,
            "timestamp": datetime.utcnow().isoformat(),
            "results": poll_results
        }

    except Exception as e:
        logger.error(f"Poll failed for {hostid}: {e}")
        raise HTTPException(status_code=500, detail=f"Polling failed: {str(e)}")


# ============================================
# OID Library Endpoints
# ============================================

@router.get("/oids", response_model=Dict[str, List[OIDInfo]])
def get_oid_library(
    vendor: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
):
    """Get OID library - universal or vendor-specific"""
    if vendor:
        oids = get_vendor_oids(vendor)
        if not oids:
            raise HTTPException(status_code=404, detail=f"No OIDs found for vendor: {vendor}")
    else:
        oids = UNIVERSAL_OIDS

    oid_list = []
    for name, oid_obj in oids.items():
        oid_list.append(OIDInfo(
            name=name,
            oid=oid_obj.oid,
            description=oid_obj.description,
            value_type=oid_obj.value_type,
            category=oid_obj.category,
        ))

    return {"oids": oid_list, "total": len(oid_list)}


@router.get("/vendors")
def list_vendors(current_user: User = Depends(get_current_active_user)):
    """List all supported vendors"""
    return {
        "vendors": SUPPORTED_VENDORS,
        "total": len(SUPPORTED_VENDORS),
        "description": "Vendors with specialized OID libraries"
    }


# ============================================
# Health Check
# ============================================

@router.get("/health")
def monitoring_health():
    """Health check for monitoring module"""
    return {
        "status": "operational",
        "module": "WARD FLUX Standalone Monitoring",
        "version": "2.0.0",
        "phase": "4 - Zabbix Integration Complete",
        "integration": "Zabbix API for device management",
        "endpoints": {
            "profiles": 3,
            "credentials": 4,
            "detection": 1,
            "items": 3,
            "polling": 1,
            "library": 2,
        },
        "total_endpoints": 14
    }
