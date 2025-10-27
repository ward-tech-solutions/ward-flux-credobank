"""
WARD FLUX - Async SNMP Poller

High-performance asynchronous SNMP polling engine with multi-vendor support.
"""

import logging
import asyncio
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# pysnmp 6.x (2025) - Use asyncio API with CamelCase functions
# Note: Despite deprecation warnings, pysnmp-lextudio 6.x uses asyncio module
from pysnmp.hlapi.asyncio import (
    getCmd,
    nextCmd,
    bulkCmd,
    SnmpEngine,
    CommunityData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
    UsmUserData,
    usmHMACMD5AuthProtocol,
    usmHMACSHAAuthProtocol,
    usmDESPrivProtocol,
    usmAesCfb128Protocol,
    usmAesCfb192Protocol,
    usmAesCfb256Protocol,
)
from pysnmp.proto.rfc1902 import Integer, OctetString, Counter32, Counter64, Gauge32, TimeTicks
from pyasn1.type.univ import ObjectIdentifier

from monitoring.snmp.oids import detect_vendor_from_oid, get_vendor_oids, classify_device_type, OIDDefinition
from monitoring.snmp.credentials import decrypt_credential

logger = logging.getLogger(__name__)


@dataclass
class SNMPCredentialData:
    """SNMP credential data structure"""

    version: str  # "v2c" or "v3"
    community: Optional[str] = None  # v2c
    username: Optional[str] = None  # v3
    auth_protocol: Optional[str] = None
    auth_key: Optional[str] = None
    priv_protocol: Optional[str] = None
    priv_key: Optional[str] = None
    security_level: Optional[str] = None


@dataclass
class SNMPResult:
    """SNMP polling result"""

    oid: str
    value: Any
    value_type: str
    success: bool
    error: Optional[str] = None


class SNMPPoller:
    """
    Asynchronous SNMP polling engine

    Supports SNMPv2c and SNMPv3 with automatic vendor detection.
    """

    def __init__(self):
        """Initialize SNMP poller"""
        self.timeout = 5  # seconds
        self.retries = 2
        logger.info("SNMP Poller initialized")

    async def get(
        self, ip: str, oid: str, credentials: SNMPCredentialData, port: int = 161
    ) -> SNMPResult:
        """
        Perform SNMP GET operation

        Args:
            ip: Target IP address
            oid: OID to query
            credentials: SNMP credentials
            port: SNMP port (default 161)

        Returns:
            SNMPResult object
        """
        try:
            # Build SNMP auth data
            auth_data = self._build_auth_data(credentials)
            target = UdpTransportTarget((ip, port), timeout=self.timeout, retries=self.retries)

            # Perform GET
            error_indication, error_status, error_index, var_binds = await getCmd(
                SnmpEngine(),
                auth_data,
                target,
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )

            if error_indication:
                logger.warning(f"SNMP GET error for {ip} OID {oid}: {error_indication}")
                return SNMPResult(oid=oid, value=None, value_type="error", success=False, error=str(error_indication))

            if error_status:
                logger.warning(f"SNMP GET error status for {ip} OID {oid}: {error_status.prettyPrint()}")
                return SNMPResult(oid=oid, value=None, value_type="error", success=False, error=error_status.prettyPrint())

            # Extract value
            for var_bind in var_binds:
                oid_result, value = var_bind
                value_str, value_type = self._parse_value(value)

                logger.debug(f"SNMP GET {ip} {oid}: {value_str} ({value_type})")
                return SNMPResult(oid=oid, value=value_str, value_type=value_type, success=True)

            return SNMPResult(oid=oid, value=None, value_type="none", success=False, error="No data returned")

        except Exception as e:
            logger.error(f"SNMP GET exception for {ip} OID {oid}: {e}")
            return SNMPResult(oid=oid, value=None, value_type="error", success=False, error=str(e))

    async def walk(
        self, ip: str, oid: str, credentials: SNMPCredentialData, port: int = 161, max_results: int = 1000
    ) -> List[SNMPResult]:
        """
        Perform SNMP WALK operation

        Args:
            ip: Target IP address
            oid: Starting OID to walk
            credentials: SNMP credentials
            port: SNMP port (default 161)
            max_results: Maximum results to return

        Returns:
            List of SNMPResult objects
        """
        try:
            results = []
            auth_data = self._build_auth_data(credentials)
            target = UdpTransportTarget((ip, port), timeout=self.timeout, retries=self.retries)

            # Use async bulkCmd - pysnmp asyncio API
            async for (error_indication, error_status, error_index, var_binds) in bulkCmd(
                SnmpEngine(),
                auth_data,
                target,
                ContextData(),
                0, 25,  # Non-repeaters=0, Max-repetitions=25
                ObjectType(ObjectIdentity(oid)),
                lexicographicMode=False
            ):
                if error_indication:
                    logger.warning(f"SNMP WALK error for {ip} OID {oid}: {error_indication}")
                    break

                if error_status:
                    logger.warning(f"SNMP WALK error status for {ip} OID {oid}: {error_status.prettyPrint()}")
                    break

                # Extract values
                for var_bind in var_binds:
                    oid_result, value = var_bind
                    value_str, value_type = self._parse_value(value)

                    results.append(
                        SNMPResult(oid=str(oid_result), value=value_str, value_type=value_type, success=True)
                    )

                    if len(results) >= max_results:
                        logger.warning(f"SNMP WALK limit reached for {ip} OID {oid}: {max_results} results")
                        break

                if len(results) >= max_results:
                    break

            logger.info(f"SNMP WALK {ip} {oid}: {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"SNMP WALK exception for {ip} OID {oid}: {e}")
            return [SNMPResult(oid=oid, value=None, value_type="error", success=False, error=str(e))]

    async def bulk_get(
        self, ip: str, oids: List[str], credentials: SNMPCredentialData, port: int = 161
    ) -> List[SNMPResult]:
        """
        Perform bulk SNMP GET for multiple OIDs using GETBULK (SNMPv2c+)

        For SNMPv1, falls back to multiple GET operations.
        GETBULK is significantly faster when polling multiple OIDs from the same device.

        Args:
            ip: Target IP address
            oids: List of OIDs to query
            credentials: SNMP credentials
            port: SNMP port

        Returns:
            List of SNMPResult objects
        """
        try:
            auth_data = self._build_auth_data(credentials)
            target = UdpTransportTarget((ip, port), timeout=self.timeout, retries=self.retries)

            # Build OID objects
            oid_objects = [ObjectType(ObjectIdentity(oid)) for oid in oids]

            # Use GETBULK for SNMPv2c/v3, fall back to getCmd for SNMPv1
            if credentials.version == "v1":
                # SNMPv1 doesn't support GETBULK, use multiple GET
                error_indication, error_status, error_index, var_binds = await getCmd(
                    SnmpEngine(),
                    auth_data,
                    target,
                    ContextData(),
                    *oid_objects
                )
            else:
                # SNMPv2c/v3 - use GETBULK for better performance
                # max-repetitions: how many rows to return per OID (we want just 1 for GET-like behavior)
                error_indication, error_status, error_index, var_binds = await bulkCmd(
                    SnmpEngine(),
                    auth_data,
                    target,
                    ContextData(),
                    0,  # non-repeaters (number of scalar OIDs)
                    len(oids),  # max-repetitions (how many results per repeating OID)
                    *oid_objects
                )

            if error_indication:
                logger.warning(f"SNMP BULK GET error for {ip}: {error_indication}")
                return [SNMPResult(oid=oid, value=None, value_type="error", success=False, error=str(error_indication)) for oid in oids]

            if error_status:
                logger.warning(f"SNMP BULK GET error status for {ip}: {error_status.prettyPrint()}")
                return [SNMPResult(oid=oid, value=None, value_type="error", success=False, error=error_status.prettyPrint()) for oid in oids]

            # Parse results
            results = []
            for var_bind in var_binds:
                oid_result, value = var_bind
                value_str, value_type = self._parse_value(value)

                results.append(
                    SNMPResult(oid=str(oid_result), value=value_str, value_type=value_type, success=True)
                )

            logger.info(f"SNMP BULK GET {ip}: {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"SNMP BULK GET exception for {ip}: {e}")
            return [SNMPResult(oid=oid, value=None, value_type="error", success=False, error=str(e)) for oid in oids]

    async def detect_device(
        self, ip: str, credentials: SNMPCredentialData, port: int = 161
    ) -> Dict[str, Optional[str]]:
        """
        Detect device vendor and type

        Args:
            ip: Target IP address
            credentials: SNMP credentials
            port: SNMP port

        Returns:
            Dictionary with detection results:
            {
                'vendor': str,
                'device_type': str,
                'sys_descr': str,
                'sys_object_id': str,
                'sys_name': str,
                'sys_uptime': str
            }
        """
        try:
            # Get system information
            oids = {
                "sysDescr": "1.3.6.1.2.1.1.1.0",
                "sysObjectID": "1.3.6.1.2.1.1.2.0",
                "sysName": "1.3.6.1.2.1.1.5.0",
                "sysUpTime": "1.3.6.1.2.1.1.3.0",
            }

            results = await self.bulk_get(ip, list(oids.values()), credentials, port)

            # Parse results
            sys_info = {}
            for key, oid in oids.items():
                result = next((r for r in results if r.oid == oid), None)
                if result and result.success:
                    sys_info[key] = result.value
                else:
                    sys_info[key] = None

            # Detect vendor from sysObjectID
            vendor = None
            if sys_info.get("sysObjectID"):
                vendor = detect_vendor_from_oid(sys_info["sysObjectID"])

            # Classify device type
            device_type = "generic"
            if sys_info.get("sysDescr"):
                device_type = classify_device_type(sys_info["sysDescr"])

            detection_result = {
                "vendor": vendor,
                "device_type": device_type,
                "sys_descr": sys_info.get("sysDescr"),
                "sys_object_id": sys_info.get("sysObjectID"),
                "sys_name": sys_info.get("sysName"),
                "sys_uptime": sys_info.get("sysUpTime"),
            }

            logger.info(f"Device detection for {ip}: vendor={vendor}, type={device_type}")
            return detection_result

        except Exception as e:
            logger.error(f"Device detection error for {ip}: {e}")
            return {
                "vendor": None,
                "device_type": "unknown",
                "sys_descr": None,
                "sys_object_id": None,
                "sys_name": None,
                "sys_uptime": None,
                "error": str(e),
            }

    def _build_auth_data(self, credentials: SNMPCredentialData):
        """
        Build pysnmp authentication data from credentials

        Args:
            credentials: SNMPCredentialData object

        Returns:
            pysnmp auth data object
        """
        if credentials.version == "v2c":
            # SNMPv2c
            community = credentials.community or "public"
            return CommunityData(community, mpModel=1)  # mpModel=1 for v2c

        elif credentials.version == "v3":
            # SNMPv3
            auth_protocol_map = {
                "MD5": usmHMACMD5AuthProtocol,
                "SHA": usmHMACSHAAuthProtocol,
                "SHA224": usmHMAC128SHA224AuthProtocol,
                "SHA256": usmHMAC192SHA256AuthProtocol,
                "SHA384": usmHMAC256SHA384AuthProtocol,
                "SHA512": usmHMAC384SHA512AuthProtocol,
            }

            priv_protocol_map = {
                "DES": usmDESPrivProtocol,
                "3DES": usm3DESEDEPrivProtocol,
                "AES": usmAesCfb128Protocol,
                "AES192": usmAesCfb192Protocol,
                "AES256": usmAesCfb256Protocol,
            }

            auth_protocol = auth_protocol_map.get(credentials.auth_protocol, usmNoAuthProtocol)
            priv_protocol = priv_protocol_map.get(credentials.priv_protocol, usmNoPrivProtocol)

            return UsmUserData(
                userName=credentials.username or "",
                authKey=credentials.auth_key,
                privKey=credentials.priv_key,
                authProtocol=auth_protocol,
                privProtocol=priv_protocol,
            )

        else:
            # Default to v2c with public
            logger.warning(f"Unknown SNMP version: {credentials.version}, defaulting to v2c")
            return CommunityData("public", mpModel=1)

    def _parse_value(self, value) -> Tuple[Any, str]:
        """
        Parse SNMP value and determine type

        Args:
            value: pysnmp value object

        Returns:
            Tuple of (parsed_value, value_type)
        """
        if isinstance(value, Integer):
            return int(value), "integer"
        elif isinstance(value, Counter32):
            return int(value), "counter32"
        elif isinstance(value, Counter64):
            return int(value), "counter64"
        elif isinstance(value, Gauge32):
            return int(value), "gauge"
        elif isinstance(value, TimeTicks):
            return int(value), "timeticks"
        elif isinstance(value, OctetString):
            try:
                # Try to decode as string
                return str(value), "string"
            except (UnicodeDecodeError, AttributeError):
                # Return hex if decode fails
                return value.hexValue, "hex"
        elif isinstance(value, ObjectIdentifier):
            return str(value), "oid"
        else:
            return str(value), "unknown"


# Singleton instance with thread-safe initialization
_snmp_poller: Optional[SNMPPoller] = None
_snmp_poller_lock = threading.Lock()


def get_snmp_poller() -> SNMPPoller:
    """
    Get or create SNMPPoller singleton (thread-safe)

    Returns:
        SNMPPoller instance
    """
    global _snmp_poller

    # Double-checked locking pattern for thread safety
    if _snmp_poller is None:
        with _snmp_poller_lock:
            if _snmp_poller is None:  # Double check inside lock
                _snmp_poller = SNMPPoller()

    return _snmp_poller


# ============================================
# Helper Functions for API
# ============================================

async def test_snmp_connection(ip: str, oid: str, snmp_params: dict) -> dict:
    """
    Test SNMP connectivity to a device
    
    Args:
        ip: Device IP address
        oid: OID to query (default: sysDescr)
        snmp_params: SNMP parameters dict
        
    Returns:
        dict with success, value, error
    """
    try:
        # Create credential object
        credentials = SNMPCredentialData(
            version=snmp_params.get("version", "v2c"),
            community=snmp_params.get("community"),
            username=snmp_params.get("username"),
            auth_protocol=snmp_params.get("auth_protocol"),
            auth_key=snmp_params.get("auth_key"),
            priv_protocol=snmp_params.get("priv_protocol"),
            priv_key=snmp_params.get("priv_key"),
            security_level=snmp_params.get("security_level"),
        )
        
        poller = get_snmp_poller()
        result = await poller.get(ip, oid, credentials)
        
        if result.success:
            return {
                "success": True,
                "value": result.value,
                "value_type": result.value_type,
                "error": None
            }
        else:
            return {
                "success": False,
                "value": None,
                "error": result.error or "Unknown error"
            }
            
    except Exception as e:
        logger.error(f"SNMP test failed for {ip}: {e}")
        return {
            "success": False,
            "value": None,
            "error": str(e)
        }


def detect_vendor(sys_descr: str) -> Optional[str]:
    """
    Detect vendor from sysDescr string
    
    Args:
        sys_descr: sysDescr value from device
        
    Returns:
        Vendor name or None
    """
    if not sys_descr:
        return None
        
    sys_descr_lower = sys_descr.lower()
    
    # Vendor detection patterns
    vendors = {
        "Cisco": ["cisco", "ios", "nx-os", "asa", "catalyst"],
        "Fortinet": ["fortinet", "fortigate", "fortios"],
        "Juniper": ["juniper", "junos", "netscreen"],
        "HP": ["hp", "aruba", "procurve", "comware"],
        "Linux": ["linux", "ubuntu", "debian", "centos", "red hat", "fedora"],
        "Windows": ["windows", "microsoft"],
        "Dell": ["dell", "powerconnect", "force10"],
        "Huawei": ["huawei", "vrp"],
        "MikroTik": ["mikrotik", "routeros"],
        "Ubiquiti": ["ubiquiti", "unifi", "edgeos"],
        "Palo Alto": ["palo alto", "pan-os"],
        "Check Point": ["check point", "gaia"],
    }
    
    for vendor, patterns in vendors.items():
        for pattern in patterns:
            if pattern in sys_descr_lower:
                return vendor
                
    return None
