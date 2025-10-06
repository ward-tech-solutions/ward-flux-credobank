"""
SNMP Discovery Scanner Module
SNMP-based device discovery and identification
"""
import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from monitoring.snmp.poller import SNMPPoller, SNMPCredentialData, SNMPResult


logger = logging.getLogger(__name__)


# Standard SNMP OIDs for discovery
SNMP_OIDS = {
    'sysDescr': '1.3.6.1.2.1.1.1.0',       # System Description
    'sysObjectID': '1.3.6.1.2.1.1.2.0',    # System Object ID
    'sysUpTime': '1.3.6.1.2.1.1.3.0',      # System Uptime
    'sysContact': '1.3.6.1.2.1.1.4.0',     # System Contact
    'sysName': '1.3.6.1.2.1.1.5.0',        # System Name
    'sysLocation': '1.3.6.1.2.1.1.6.0',    # System Location
    'ifNumber': '1.3.6.1.2.1.2.1.0',       # Number of interfaces
    'ipAdEntAddr': '1.3.6.1.2.1.4.20.1.1', # IP addresses (table)
}


@dataclass
class SNMPDiscoveryResult:
    """Result of SNMP discovery scan"""
    ip: str
    responsive: bool
    version: Optional[str] = None  # 'v1', 'v2c', 'v3'
    community: Optional[str] = None  # Working community (v2c only)

    # SNMP system info
    sys_descr: Optional[str] = None
    sys_name: Optional[str] = None
    sys_oid: Optional[str] = None
    sys_uptime: Optional[int] = None
    sys_contact: Optional[str] = None
    sys_location: Optional[str] = None

    # Detected vendor
    vendor: Optional[str] = None
    device_type: Optional[str] = None
    model: Optional[str] = None
    os_version: Optional[str] = None

    # Discovery metadata
    error: Optional[str] = None
    scan_duration_ms: Optional[float] = None


class SNMPScanner:
    """
    SNMP-based network device scanner
    """

    def __init__(self, timeout: int = 5, retries: int = 2):
        """
        Initialize SNMP scanner

        Args:
            timeout: SNMP timeout in seconds
            retries: Number of retries per request
        """
        self.timeout = timeout
        self.retries = retries
        self.poller = SNMPPoller()

    async def scan_host_v2c(
        self,
        ip: str,
        communities: List[str],
        port: int = 161
    ) -> SNMPDiscoveryResult:
        """
        Scan a host using SNMPv2c with multiple communities

        Args:
            ip: Target IP address
            communities: List of community strings to try
            port: SNMP port (default 161)

        Returns:
            SNMPDiscoveryResult with scan results
        """
        start_time = datetime.now()

        for community in communities:
            try:
                # Create v2c credentials
                creds = SNMPCredentialData(
                    version='v2c',
                    community=community,
                    port=port,
                    timeout=self.timeout,
                    retries=self.retries
                )

                # Try to get sysDescr
                result = await self.poller.get(ip, SNMP_OIDS['sysDescr'], creds)

                if result.success and result.value:
                    # Community works! Get full system info
                    sys_info = await self._get_system_info(ip, creds)

                    # Detect vendor and device type
                    vendor, device_type, model, os_version = self._parse_sys_descr(
                        sys_info.get('sysDescr', '')
                    )

                    duration = (datetime.now() - start_time).total_seconds() * 1000

                    return SNMPDiscoveryResult(
                        ip=ip,
                        responsive=True,
                        version='v2c',
                        community=community,
                        sys_descr=sys_info.get('sysDescr'),
                        sys_name=sys_info.get('sysName'),
                        sys_oid=sys_info.get('sysObjectID'),
                        sys_uptime=sys_info.get('sysUpTime'),
                        sys_contact=sys_info.get('sysContact'),
                        sys_location=sys_info.get('sysLocation'),
                        vendor=vendor,
                        device_type=device_type,
                        model=model,
                        os_version=os_version,
                        scan_duration_ms=duration
                    )

            except Exception as e:
                logger.debug(f"Community '{community}' failed for {ip}: {e}")
                continue

        # No community worked
        duration = (datetime.now() - start_time).total_seconds() * 1000
        return SNMPDiscoveryResult(
            ip=ip,
            responsive=False,
            error="No working community found",
            scan_duration_ms=duration
        )

    async def scan_host_v3(
        self,
        ip: str,
        v3_credentials: List[Dict],
        port: int = 161
    ) -> SNMPDiscoveryResult:
        """
        Scan a host using SNMPv3 with multiple credential sets

        Args:
            ip: Target IP address
            v3_credentials: List of SNMPv3 credential dictionaries
            port: SNMP port (default 161)

        Returns:
            SNMPDiscoveryResult with scan results
        """
        start_time = datetime.now()

        for cred_dict in v3_credentials:
            try:
                # Create v3 credentials
                creds = SNMPCredentialData(
                    version='v3',
                    username=cred_dict.get('username'),
                    auth_protocol=cred_dict.get('auth_protocol'),
                    auth_key=cred_dict.get('auth_key'),
                    priv_protocol=cred_dict.get('priv_protocol'),
                    priv_key=cred_dict.get('priv_key'),
                    port=port,
                    timeout=self.timeout,
                    retries=self.retries
                )

                # Try to get sysDescr
                result = await self.poller.get(ip, SNMP_OIDS['sysDescr'], creds)

                if result.success and result.value:
                    # Credentials work! Get full system info
                    sys_info = await self._get_system_info(ip, creds)

                    # Detect vendor and device type
                    vendor, device_type, model, os_version = self._parse_sys_descr(
                        sys_info.get('sysDescr', '')
                    )

                    duration = (datetime.now() - start_time).total_seconds() * 1000

                    return SNMPDiscoveryResult(
                        ip=ip,
                        responsive=True,
                        version='v3',
                        sys_descr=sys_info.get('sysDescr'),
                        sys_name=sys_info.get('sysName'),
                        sys_oid=sys_info.get('sysObjectID'),
                        sys_uptime=sys_info.get('sysUpTime'),
                        sys_contact=sys_info.get('sysContact'),
                        sys_location=sys_info.get('sysLocation'),
                        vendor=vendor,
                        device_type=device_type,
                        model=model,
                        os_version=os_version,
                        scan_duration_ms=duration
                    )

            except Exception as e:
                logger.debug(f"SNMPv3 credentials failed for {ip}: {e}")
                continue

        # No credentials worked
        duration = (datetime.now() - start_time).total_seconds() * 1000
        return SNMPDiscoveryResult(
            ip=ip,
            responsive=False,
            error="No working SNMPv3 credentials found",
            scan_duration_ms=duration
        )

    async def _get_system_info(
        self,
        ip: str,
        creds: SNMPCredentialData
    ) -> Dict[str, str]:
        """
        Get complete system information via SNMP

        Args:
            ip: Target IP
            creds: Working SNMP credentials

        Returns:
            Dictionary of system information
        """
        sys_info = {}

        # Get all system OIDs
        tasks = [
            self.poller.get(ip, oid, creds)
            for oid in SNMP_OIDS.values()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for key, result in zip(SNMP_OIDS.keys(), results):
            if isinstance(result, SNMPResult) and result.success:
                sys_info[key] = result.value

        return sys_info

    def _parse_sys_descr(self, sys_descr: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """
        Parse sysDescr to extract vendor, device type, model, and OS version

        Args:
            sys_descr: System description string

        Returns:
            Tuple of (vendor, device_type, model, os_version)
        """
        if not sys_descr:
            return None, None, None, None

        sys_descr_lower = sys_descr.lower()
        vendor = None
        device_type = None
        model = None
        os_version = None

        # Vendor detection
        vendor_patterns = {
            'Cisco': ['cisco', 'ios', 'nx-os', 'catalyst'],
            'Fortinet': ['fortinet', 'fortigate', 'fortios'],
            'Juniper': ['juniper', 'junos'],
            'HP': ['hp', 'hewlett', 'procurve', 'aruba'],
            'Aruba': ['aruba'],
            'Dell': ['dell', 'powerconnect'],
            'Huawei': ['huawei', 'vrp'],
            'MikroTik': ['mikrotik', 'routeros'],
            'Ubiquiti': ['ubiquiti', 'edgeos', 'unifi'],
            'Palo Alto': ['palo alto', 'pan-os'],
            'F5': ['f5', 'big-ip'],
            'Linux': ['linux', 'debian', 'ubuntu', 'centos', 'red hat'],
            'Windows': ['windows', 'microsoft'],
        }

        for v, patterns in vendor_patterns.items():
            for pattern in patterns:
                if pattern in sys_descr_lower:
                    vendor = v
                    break
            if vendor:
                break

        # Device type detection
        device_type_patterns = {
            'switch': ['switch', 'catalyst'],
            'router': ['router', 'asr', 'isr'],
            'firewall': ['firewall', 'fortigate', 'asa', 'palo alto', 'checkpoint'],
            'access_point': ['access point', 'ap', 'wireless'],
            'server': ['server', 'linux', 'windows'],
            'load_balancer': ['load balancer', 'f5', 'big-ip'],
        }

        for dtype, patterns in device_type_patterns.items():
            for pattern in patterns:
                if pattern in sys_descr_lower:
                    device_type = dtype
                    break
            if device_type:
                break

        # Extract model (basic extraction, vendor-specific)
        if vendor == 'Cisco':
            # Example: "Cisco IOS Software, C3560 Software..."
            if 'catalyst' in sys_descr_lower or 'c3' in sys_descr_lower:
                parts = sys_descr.split(',')
                for part in parts:
                    if 'c2' in part.lower() or 'c3' in part.lower() or 'c4' in part.lower():
                        model = part.strip()
                        break

        elif vendor == 'Fortinet':
            # Example: "FortiGate-60E v6.4.4..."
            if 'fortigate' in sys_descr_lower:
                parts = sys_descr.split()
                for i, part in enumerate(parts):
                    if 'fortigate' in part.lower() and i + 1 < len(parts):
                        model = f"FortiGate {parts[i+1]}"
                        break

        # Extract OS version (basic extraction)
        version_keywords = ['version', 'v', 'release', 'software']
        for keyword in version_keywords:
            if keyword in sys_descr_lower:
                # Try to find version number after keyword
                idx = sys_descr_lower.find(keyword)
                after_keyword = sys_descr[idx:idx+50]

                # Look for version pattern (e.g., "15.2(4)M")
                import re
                version_match = re.search(r'(\d+\.[\d\.]+[\w\(\)]*)', after_keyword)
                if version_match:
                    os_version = version_match.group(1)
                    break

        return vendor, device_type, model, os_version

    async def scan_network(
        self,
        ips: List[str],
        communities: Optional[List[str]] = None,
        v3_credentials: Optional[List[Dict]] = None,
        port: int = 161,
        max_concurrent: int = 20
    ) -> List[SNMPDiscoveryResult]:
        """
        Scan multiple hosts for SNMP

        Args:
            ips: List of IP addresses to scan
            communities: SNMPv2c communities to try
            v3_credentials: SNMPv3 credentials to try
            port: SNMP port
            max_concurrent: Max concurrent scans

        Returns:
            List of SNMPDiscoveryResult objects
        """
        communities = communities or ['public', 'private']
        v3_credentials = v3_credentials or []

        semaphore = asyncio.Semaphore(max_concurrent)

        async def limited_scan(ip: str) -> SNMPDiscoveryResult:
            async with semaphore:
                # Try v2c first
                result = await self.scan_host_v2c(ip, communities, port)
                if result.responsive:
                    return result

                # Try v3 if configured
                if v3_credentials:
                    result = await self.scan_host_v3(ip, v3_credentials, port)

                return result

        results = await asyncio.gather(*[
            limited_scan(ip) for ip in ips
        ])

        # Log summary
        responsive_count = sum(1 for r in results if r.responsive)
        logger.info(
            f"SNMP scan complete: {responsive_count}/{len(results)} hosts responsive"
        )

        return results

    def calculate_scan_stats(self, results: List[SNMPDiscoveryResult]) -> Dict:
        """Calculate statistics from SNMP scan results"""
        total = len(results)
        responsive = sum(1 for r in results if r.responsive)

        # Group by vendor
        vendors = {}
        for r in results:
            if r.vendor:
                vendors[r.vendor] = vendors.get(r.vendor, 0) + 1

        # Group by device type
        device_types = {}
        for r in results:
            if r.device_type:
                device_types[r.device_type] = device_types.get(r.device_type, 0) + 1

        # Calculate avg scan duration
        durations = [r.scan_duration_ms for r in results if r.scan_duration_ms]
        avg_duration = sum(durations) / len(durations) if durations else None

        return {
            'total_scanned': total,
            'responsive': responsive,
            'unresponsive': total - responsive,
            'response_rate': (responsive / total * 100) if total > 0 else 0,
            'vendors': vendors,
            'device_types': device_types,
            'avg_scan_duration_ms': round(avg_duration, 2) if avg_duration else None
        }


# Utility functions

async def quick_snmp_check(
    ip: str,
    community: str = 'public',
    timeout: int = 3
) -> bool:
    """
    Quick SNMP availability check

    Args:
        ip: IP address
        community: SNMP community
        timeout: Timeout in seconds

    Returns:
        True if SNMP is responsive
    """
    scanner = SNMPScanner(timeout=timeout)
    result = await scanner.scan_host_v2c(ip, [community])
    return result.responsive


# For testing
if __name__ == "__main__":
    async def test():
        scanner = SNMPScanner(timeout=3)

        # Test single host
        result = await scanner.scan_host_v2c(
            "192.168.1.1",
            communities=["public", "private"]
        )
        print(f"SNMP scan result: {result}")

        # Test network
        ips = [f"192.168.1.{i}" for i in range(1, 11)]
        results = await scanner.scan_network(ips)

        stats = scanner.calculate_scan_stats(results)
        print(f"\nScan stats: {stats}")

        for r in results:
            if r.responsive:
                print(f"{r.ip}: {r.vendor} {r.device_type} - {r.sys_descr[:60]}")

    asyncio.run(test())
