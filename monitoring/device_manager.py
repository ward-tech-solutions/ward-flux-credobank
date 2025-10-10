"""
WARD FLUX - Device Manager Abstraction Layer
Routes between Zabbix and Standalone devices based on active monitoring mode
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
    """Unified device management - routes to Zabbix or Standalone based on mode"""

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
        Get device information - routes to correct source based on mode

        Args:
            device_id: Device ID (UUID for standalone, hostid for Zabbix)

        Returns:
            Device dict with unified schema
        """
        mode = self.get_active_mode()

        if mode == MonitoringMode.standalone:
            return self._get_standalone_device(device_id)

        elif mode == MonitoringMode.zabbix:
            return self._get_zabbix_device(device_id)

        elif mode == MonitoringMode.hybrid:
            # Try standalone first, fallback to Zabbix
            try:
                return self._get_standalone_device(device_id)
            except HTTPException:
                return self._get_zabbix_device(device_id)

    def list_devices(
        self,
        enabled: Optional[bool] = None,
        vendor: Optional[str] = None,
        device_type: Optional[str] = None,
    ) -> List[Dict]:
        """
        List all devices - routes to correct source based on mode

        Returns:
            List of device dicts with unified schema
        """
        mode = self.get_active_mode()

        if mode == MonitoringMode.standalone:
            return self._list_standalone_devices(enabled, vendor, device_type)

        elif mode == MonitoringMode.zabbix:
            return self._list_zabbix_devices()

        elif mode == MonitoringMode.hybrid:
            # Merge both sources
            standalone = self._list_standalone_devices(enabled, vendor, device_type)
            zabbix = self._list_zabbix_devices()
            return standalone + zabbix

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

    def _get_zabbix_device(self, hostid: str) -> Dict:
        """Get device from Zabbix API"""
        if not self.request:
            raise HTTPException(status_code=500, detail="Request context required for Zabbix access")

        zabbix = self.request.app.state.zabbix
        device = zabbix.get_host_details(hostid)

        if not device:
            raise HTTPException(status_code=404, detail=f"Device not found in Zabbix: {hostid}")

        return {
            "id": hostid,
            "source": "zabbix",
            "name": device.get("display_name", device.get("hostname")),
            "hostname": device.get("hostname"),
            "ip": device.get("ip"),
            "vendor": None,  # Zabbix doesn't store vendor
            "device_type": device.get("device_type"),
            "model": None,
            "location": device.get("region"),
            "description": None,
            "enabled": device.get("status") == "Enabled",
            "tags": [],
            "custom_fields": {},
            "created_at": None,
            "updated_at": None,
        }

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

    def _list_zabbix_devices(self) -> List[Dict]:
        """List devices from Zabbix"""
        if not self.request:
            return []

        zabbix = self.request.app.state.zabbix
        try:
            devices = zabbix.get_all_hosts()
            return [
                {
                    "id": device.get("hostid"),
                    "source": "zabbix",
                    "name": device.get("display_name"),
                    "hostname": device.get("hostname"),
                    "ip": device.get("ip"),
                    "vendor": None,
                    "device_type": device.get("device_type"),
                    "location": device.get("region"),
                    "enabled": device.get("status") == "Enabled",
                }
                for device in devices
            ]
        except Exception as e:
            logger.error(f"Error fetching Zabbix devices: {e}")
            return []

    def get_device_uuid(self, device_id: str) -> uuid.UUID:
        """
        Convert device ID to UUID for database storage

        For standalone: Returns the UUID directly
        For Zabbix: Creates deterministic UUID from hostid
        """
        mode = self.get_active_mode()

        if mode == MonitoringMode.standalone:
            try:
                return uuid.UUID(device_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid device UUID")

        elif mode == MonitoringMode.zabbix:
            # Create deterministic UUID from Zabbix hostid
            return uuid.uuid5(uuid.NAMESPACE_DNS, f"zabbix-host-{device_id}")

        elif mode == MonitoringMode.hybrid:
            # Try UUID first (standalone), then hostid (Zabbix)
            try:
                return uuid.UUID(device_id)
            except ValueError:
                return uuid.uuid5(uuid.NAMESPACE_DNS, f"zabbix-host-{device_id}")


# ============================================
# Helper Functions
# ============================================

def get_device_manager(db: Session, request: Optional[Request] = None) -> DeviceManager:
    """Factory function to create DeviceManager instance"""
    return DeviceManager(db, request)
