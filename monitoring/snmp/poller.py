"""
WARD FLUX - SNMP Poller using CLI commands (like Zabbix)

Uses snmpwalk/snmpget commands directly - battle-tested and reliable
"""

import logging
import asyncio
import subprocess
import re
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SNMPCredentialData:
    """SNMP credential data structure"""
    version: str  # "v2c", "2c", or "v3"
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
    SNMP poller using CLI commands (snmpwalk/snmpget)

    This is what Zabbix uses - rock solid and reliable
    """

    def __init__(self, timeout: int = 5, retries: int = 2):
        """Initialize SNMP poller

        Args:
            timeout: SNMP timeout in seconds (default: 5)
            retries: Number of retries (default: 2)
        """
        self.timeout = timeout
        self.retries = retries
        logger.info(f"SNMP CLI Poller initialized (timeout={timeout}s, retries={retries})")

    def _normalize_version(self, version: str) -> str:
        """Normalize version string (2c -> v2c)"""
        version = version.lower()
        if version == "2c":
            return "2c"  # snmpwalk uses -v2c format
        elif version == "v2c":
            return "2c"
        elif version == "3" or version == "v3":
            return "3"
        return version

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
        version = self._normalize_version(credentials.version)
        community = credentials.community or "public"

        cmd = [
            'snmpget',
            f'-v{version}',
            f'-c{community}',
            f'-t{self.timeout}',
            f'-r{self.retries}',
            '-Oqv',  # Quick output, value only
            ip,
            oid
        ]

        try:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                result.communicate(),
                timeout=self.timeout * (self.retries + 2)
            )

            if result.returncode != 0:
                error_msg = stderr.decode().strip() or "SNMP GET failed"
                logger.warning(f"SNMP GET error for {ip} OID {oid}: {error_msg}")
                return SNMPResult(
                    oid=oid,
                    value=None,
                    value_type="error",
                    success=False,
                    error=error_msg
                )

            value = stdout.decode().strip().strip('"')
            return SNMPResult(
                oid=oid,
                value=value,
                value_type="string",
                success=True
            )

        except asyncio.TimeoutError:
            logger.warning(f"SNMP GET timeout for {ip} OID {oid}")
            return SNMPResult(
                oid=oid,
                value=None,
                value_type="error",
                success=False,
                error="Timeout"
            )
        except Exception as e:
            logger.error(f"SNMP GET exception for {ip} OID {oid}: {e}")
            return SNMPResult(
                oid=oid,
                value=None,
                value_type="error",
                success=False,
                error=str(e)
            )

    async def walk(
        self,
        ip: str,
        oid: str,
        credentials: SNMPCredentialData,
        port: int = 161,
        max_results: int = 10000
    ) -> List[SNMPResult]:
        """
        Perform SNMP WALK operation

        Args:
            ip: Target IP address
            oid: OID to walk
            credentials: SNMP credentials
            port: SNMP port (default 161)
            max_results: Maximum results to return

        Returns:
            List of SNMPResult objects
        """
        version = self._normalize_version(credentials.version)
        community = credentials.community or "public"

        cmd = [
            'snmpwalk',
            f'-v{version}',
            f'-c{community}',
            f'-t{self.timeout}',
            f'-r{self.retries}',
            '-OQn',  # Quick output, numeric OIDs
            ip,
            oid
        ]

        try:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                result.communicate(),
                timeout=self.timeout * (self.retries + 2) * 2  # Walk takes longer
            )

            if result.returncode != 0:
                error_msg = stderr.decode().strip() or "SNMP WALK failed"
                logger.warning(f"SNMP WALK error for {ip} OID {oid}: {error_msg}")
                return [SNMPResult(
                    oid=oid,
                    value=None,
                    value_type="error",
                    success=False,
                    error=error_msg
                )]

            # Parse output
            results = []
            for line in stdout.decode().strip().split('\n'):
                if not line:
                    continue

                # Format: .1.3.6.1.2.1.2.2.1.2.1 = "FastEthernet0"
                # or: .1.3.6.1.2.1.2.2.1.2.1 = STRING: "FastEthernet0"
                match = re.match(r'^(\.[\d\.]+)\s*=\s*(?:\w+:\s*)?(.+)$', line)
                if match:
                    oid_result = match.group(1)
                    value = match.group(2).strip().strip('"')
                    results.append(SNMPResult(
                        oid=oid_result,
                        value=value,
                        value_type="string",
                        success=True
                    ))

                    if len(results) >= max_results:
                        logger.warning(f"SNMP WALK limit reached for {ip} OID {oid}: {max_results}")
                        break

            logger.info(f"SNMP WALK {ip} {oid}: {len(results)} results")
            return results

        except asyncio.TimeoutError:
            logger.warning(f"SNMP WALK timeout for {ip} OID {oid}")
            return [SNMPResult(
                oid=oid,
                value=None,
                value_type="error",
                success=False,
                error="Timeout"
            )]
        except Exception as e:
            logger.error(f"SNMP WALK exception for {ip} OID {oid}: {e}")
            return [SNMPResult(
                oid=oid,
                value=None,
                value_type="error",
                success=False,
                error=str(e)
            )]

    async def bulk_get(
        self, ip: str, oids: List[str], credentials: SNMPCredentialData, port: int = 161
    ) -> List[SNMPResult]:
        """
        Perform SNMP BULK GET (multiple GET operations)

        Args:
            ip: Target IP address
            oids: List of OIDs to query
            credentials: SNMP credentials
            port: SNMP port (default 161)

        Returns:
            List of SNMPResult objects
        """
        # Just run multiple GET operations in parallel
        tasks = [self.get(ip, oid, credentials, port) for oid in oids]
        return await asyncio.gather(*tasks)


# ============================================
# Singleton Instance (Thread-Safe)
# ============================================

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
