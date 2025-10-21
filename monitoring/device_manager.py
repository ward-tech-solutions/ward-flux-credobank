"""
WARD FLUX - Device Manager Abstraction Layer
Manages standalone devices and monitoring operations
"""

import logging
import uuid
from typing import Dict, List, Optional
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session

from monitoring.models import MonitoringProfile, StandaloneDevice, MonitoringMode

logger = logging.getLogger(__name__)


# ============================================
# Device Abstraction Layer
# ============================================

class DeviceManager:
    """Unified device management for standalone monitoring"""

    def __init__(self, db: Session, request: Optional[Request] = None):
        self.db = db
        self.request = request
        self._active_mode = None

    def get_active_mode(self) -> MonitoringMode:
        """Get the currently active monitoring mode"""
        if self._active_mode:
            return self._active_mode

        # Get active profile from database
        active_profile = self.db.query(MonitoringProfile).filter_by(is_active=True).first()

        if not active_profile:
            # Default to standalone if no profile is active
            logger.warning("No active monitoring profile found, defaulting to STANDALONE mode")
            return MonitoringMode.standalone

        self._active_mode = active_profile.mode
        return self._active_mode

    def get_device(self, device_id: str) -> Dict:
        """
        Get device information from standalone database

        Args:
            device_id: Device UUID

        Returns:
            Device dict with unified schema
        """
        return self._get_standalone_device(device_id)

    def list_devices(
        self,
        enabled: Optional[bool] = None,
        vendor: Optional[str] = None,
        device_type: Optional[str] = None,
    ) -> List[Dict]:
        """
        List all devices from standalone database

        Returns:
            List of device dicts with unified schema
        """
        return self._list_standalone_devices(enabled, vendor, device_type)

    def _get_standalone_device(self, device_id: str) -> Dict:
        """Get device from standalone database"""
        try:
            device = self.db.query(StandaloneDevice).filter_by(
                id=uuid.UUID(device_id)
            ).first()

            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            return {
                "id": str(device.id),
                "source": "standalone",
                "name": device.name,
                "hostname": device.hostname or device.name,
                "ip": device.ip,
                "vendor": device.vendor,
                "device_type": device.device_type,
                "model": device.model,
                "location": device.location,
                "description": device.description,
                "enabled": device.enabled,
                "tags": device.tags or [],
                "custom_fields": device.custom_fields or {},
                "created_at": device.created_at.isoformat() if device.created_at else None,
                "updated_at": device.updated_at.isoformat() if device.updated_at else None,
            }

        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid device ID format")

    def _list_standalone_devices(
        self,
        enabled: Optional[bool] = None,
        vendor: Optional[str] = None,
        device_type: Optional[str] = None,
    ) -> List[Dict]:
        """List devices from standalone database"""
        query = self.db.query(StandaloneDevice)

        if enabled is not None:
            query = query.filter(StandaloneDevice.enabled == enabled)
        if vendor:
            query = query.filter(StandaloneDevice.vendor == vendor)
        if device_type:
            query = query.filter(StandaloneDevice.device_type == device_type)

        devices = query.all()

        return [
            {
                "id": str(device.id),
                "source": "standalone",
                "name": device.name,
                "hostname": device.hostname or device.name,
                "ip": device.ip,
                "vendor": device.vendor,
                "device_type": device.device_type,
                "model": device.model,
                "location": device.location,
                "enabled": device.enabled,
            }
            for device in devices
        ]

    def get_device_uuid(self, device_id: str) -> uuid.UUID:
        """
        Convert device ID to UUID for database storage

        Returns the UUID directly for standalone devices
        """
        try:
            return uuid.UUID(device_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid device UUID")


# ============================================
# Helper Functions
# ============================================

def get_device_manager(db: Session, request: Optional[Request] = None) -> DeviceManager:
    """Factory function to create DeviceManager instance"""
    return DeviceManager(db, request)
