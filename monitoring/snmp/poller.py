"""
WARD FLUX - SNMP Poller using CLI commands (like Zabbix)

Uses snmpwalk/snmpget commands directly - battle-tested and reliable
"""

import logging
import asyncio
import subprocess
import re
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
