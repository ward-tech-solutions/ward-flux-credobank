"""
Network Scanner Module
Provides ICMP ping sweep and network discovery capabilities
"""
import asyncio
import ipaddress
import logging
import platform
import subprocess
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PingResult:
    """Result of a ping scan"""
    ip: str
    responsive: bool
    latency_ms: Optional[float] = None
    hostname: Optional[str] = None
    error: Optional[str] = None


class NetworkScanner:
    """
    Network scanner for device discovery using ICMP ping
    """

    def __init__(self, timeout: int = 2, max_concurrent: int = 50):
        """
        Initialize network scanner

        Args:
            timeout: Ping timeout in seconds
            max_concurrent: Maximum concurrent ping operations
        """
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.is_windows = platform.system().lower() == 'windows'

    async def ping_host(self, ip: str) -> PingResult:
        """
        Ping a single host

        Args:
            ip: IP address to ping

        Returns:
            PingResult with ping status and latency
        """
        try:
            # Build ping command based on OS
            if self.is_windows:
                cmd = ['ping', '-n', '1', '-w', str(self.timeout * 1000), ip]
            else:
                cmd = ['ping', '-c', '1', '-W', str(self.timeout), ip]

            # Execute ping
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout + 1
            )

            if process.returncode == 0:
                # Parse latency from output
                output = stdout.decode()
                latency = self._parse_ping_latency(output)

                # Try to resolve hostname
                hostname = await self._resolve_hostname(ip)

                return PingResult(
                    ip=ip,
                    responsive=True,
                    latency_ms=latency,
                    hostname=hostname
                )
            else:
                return PingResult(
                    ip=ip,
                    responsive=False,
                    error="No response"
                )

        except asyncio.TimeoutError:
            return PingResult(
                ip=ip,
                responsive=False,
                error="Timeout"
            )
        except Exception as e:
            logger.error(f"Error pinging {ip}: {e}")
            return PingResult(
                ip=ip,
                responsive=False,
                error=str(e)
            )

    def _parse_ping_latency(self, output: str) -> Optional[float]:
        """Parse latency from ping output"""
        try:
            if self.is_windows:
                # Windows: "Reply from 192.168.1.1: bytes=32 time=1ms TTL=64"
                if 'time=' in output or 'Time=' in output:
                    time_str = output.split('time=')[1].split('ms')[0].strip()
                    if '<' in time_str:
                        return 0.5  # <1ms
                    return float(time_str)
            else:
                # Linux/Mac: "64 bytes from 192.168.1.1: icmp_seq=1 ttl=64 time=1.23 ms"
                if 'time=' in output:
                    time_str = output.split('time=')[1].split('ms')[0].strip()
                    return float(time_str)
        except (IndexError, ValueError) as e:
            logger.debug(f"Could not parse latency: {e}")

        return None

    async def _resolve_hostname(self, ip: str) -> Optional[str]:
        """Resolve IP to hostname"""
        try:
            # Use asyncio.to_thread for blocking socket.gethostbyaddr
            loop = asyncio.get_event_loop()
            hostname, _, _ = await asyncio.wait_for(
                loop.run_in_executor(None, __import__('socket').gethostbyaddr, ip),
                timeout=1
            )
            return hostname
        except (OSError, asyncio.TimeoutError):
            # OSError covers socket.herror, socket.gaierror, socket.timeout
            return None

    async def scan_network(
        self,
        network_range: str,
        excluded_ips: Optional[List[str]] = None
    ) -> List[PingResult]:
        """
        Scan a network range using ICMP ping

        Args:
            network_range: CIDR notation (e.g., "192.168.1.0/24")
            excluded_ips: List of IPs to skip

        Returns:
            List of PingResult objects
        """
        excluded_ips = excluded_ips or []
        results = []

        try:
            # Parse network range
            network = ipaddress.ip_network(network_range, strict=False)
            total_hosts = network.num_addresses

            logger.info(f"Starting ping scan of {network_range} ({total_hosts} hosts)")

            # Generate IP list
            ips_to_scan = [
                str(ip) for ip in network.hosts()
                if str(ip) not in excluded_ips
            ]

            # Add network and broadcast addresses for /31 and /32
            if network.prefixlen >= 31:
                ips_to_scan = [str(network.network_address)]

            # Scan in batches
            semaphore = asyncio.Semaphore(self.max_concurrent)

            async def limited_ping(ip: str) -> PingResult:
                async with semaphore:
                    return await self.ping_host(ip)

            # Execute ping scans
            results = await asyncio.gather(*[
                limited_ping(ip) for ip in ips_to_scan
            ])

            # Log summary
            responsive_count = sum(1 for r in results if r.responsive)
            logger.info(
                f"Scan complete: {responsive_count}/{len(results)} hosts responsive"
            )

            return results

        except ValueError as e:
            logger.error(f"Invalid network range {network_range}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error scanning network {network_range}: {e}")
            return []

    async def scan_multiple_networks(
        self,
        network_ranges: List[str],
        excluded_ips: Optional[List[str]] = None
    ) -> List[PingResult]:
        """
        Scan multiple network ranges

        Args:
            network_ranges: List of CIDR networks
            excluded_ips: List of IPs to skip

        Returns:
            Combined list of PingResult objects
        """
        all_results = []

        for network_range in network_ranges:
            results = await self.scan_network(network_range, excluded_ips)
            all_results.extend(results)

        return all_results

    def calculate_scan_stats(self, results: List[PingResult]) -> Dict:
        """
        Calculate statistics from scan results

        Args:
            results: List of PingResult objects

        Returns:
            Dictionary with scan statistics
        """
        total = len(results)
        responsive = sum(1 for r in results if r.responsive)
        unresponsive = total - responsive

        latencies = [r.latency_ms for r in results if r.latency_ms is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else None
        min_latency = min(latencies) if latencies else None
        max_latency = max(latencies) if latencies else None

        return {
            'total_scanned': total,
            'responsive': responsive,
            'unresponsive': unresponsive,
            'response_rate': (responsive / total * 100) if total > 0 else 0,
            'avg_latency_ms': round(avg_latency, 2) if avg_latency else None,
            'min_latency_ms': round(min_latency, 2) if min_latency else None,
            'max_latency_ms': round(max_latency, 2) if max_latency else None,
            'with_hostname': sum(1 for r in results if r.hostname is not None)
        }


# Utility functions

async def quick_ping(ip: str, timeout: int = 2) -> bool:
    """
    Quick ping check for a single IP

    Args:
        ip: IP address
        timeout: Timeout in seconds

    Returns:
        True if responsive, False otherwise
    """
    scanner = NetworkScanner(timeout=timeout)
    result = await scanner.ping_host(ip)
    return result.responsive


async def discover_local_network(timeout: int = 2, max_concurrent: int = 100) -> List[PingResult]:
    """
    Discover devices on local /24 network

    Returns:
        List of responsive hosts
    """
    import socket

    # Get local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()

        # Create /24 network from local IP
        network = ipaddress.ip_network(f"{local_ip}/24", strict=False)

        scanner = NetworkScanner(timeout=timeout, max_concurrent=max_concurrent)
        results = await scanner.scan_network(str(network))

        # Return only responsive hosts
        return [r for r in results if r.responsive]

    except Exception as e:
        logger.error(f"Error discovering local network: {e}")
        return []


# For testing
if __name__ == "__main__":
    async def test():
        scanner = NetworkScanner(timeout=1, max_concurrent=50)

        # Test single ping
        result = await scanner.ping_host("8.8.8.8")
        print(f"Ping 8.8.8.8: {result}")

        # Test network scan
        results = await scanner.scan_network("192.168.1.0/28")
        stats = scanner.calculate_scan_stats(results)
        print(f"\nScan results: {stats}")

        for r in results:
            if r.responsive:
                print(f"  {r.ip}: {r.latency_ms}ms - {r.hostname or 'no hostname'}")

    asyncio.run(test())
