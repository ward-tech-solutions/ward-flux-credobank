"""
WARD OPS - Independent Network Diagnostics
Real-time ping and traceroute functionality
"""
import logging
import subprocess
import re
import platform
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class NetworkDiagnostics:
    """Independent network diagnostics - ping and traceroute"""

    def __init__(self):
        self.system = platform.system()

    def ping(self, ip_address: str, count: int = 5, timeout: int = 5) -> Dict:
        """
        Perform ICMP ping check

        Returns:
            {
                'ip': str,
                'packets_sent': int,
                'packets_received': int,
                'packet_loss_percent': int,
                'min_rtt_ms': float,
                'avg_rtt_ms': float,
                'max_rtt_ms': float,
                'is_reachable': bool,
                'timestamp': datetime
            }
        """
        try:
            # Platform-specific ping command
            if self.system == "Windows":
                cmd = ["ping", "-n", str(count), "-w", str(timeout * 1000), ip_address]
            else:  # Linux/Mac
                cmd = ["ping", "-c", str(count), "-W", str(timeout), ip_address]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)

            output = result.stdout

            # Parse results
            if self.system == "Windows":
                return self._parse_ping_windows(output, ip_address, count)
            else:
                return self._parse_ping_unix(output, ip_address, count)

        except subprocess.TimeoutExpired:
            return self._ping_timeout_result(ip_address, count)
        except Exception as e:
            logger.info(f"Ping error for {ip_address}: {e}")
            return self._ping_error_result(ip_address, count)

    def _parse_ping_unix(self, output: str, ip: str, count: int) -> Dict:
        """Parse Unix/Linux/Mac ping output"""
        result = {
            "ip": ip,
            "packets_sent": count,
            "packets_received": 0,
            "packet_loss_percent": 100,
            "min_rtt_ms": None,
            "avg_rtt_ms": None,
            "max_rtt_ms": None,
            "is_reachable": False,
            "timestamp": datetime.utcnow(),
        }

        # Parse packet statistics
        # Example: "5 packets transmitted, 5 received, 0% packet loss"
        packet_match = re.search(
            r"(\d+)\s+packets transmitted,\s+(\d+)\s+(?:packets\s+)?received,\s+([\d.]+)%", output
        )
        if packet_match:
            result["packets_sent"] = int(packet_match.group(1))
            result["packets_received"] = int(packet_match.group(2))
            loss_percent = float(packet_match.group(3))
            result["packet_loss_percent"] = loss_percent
            result["is_reachable"] = result["packets_received"] > 0

        # Parse RTT statistics
        # Example: "round-trip min/avg/max/stddev = 10.5/12.3/15.2/1.8 ms"
        # or "rtt min/avg/max/mdev = 10.5/12.3/15.2/1.8 ms"
        rtt_match = re.search(r"(?:rtt|round-trip) min/avg/max(?:/(?:stddev|mdev))? = ([\d.]+)/([\d.]+)/([\d.]+)", output)
        if rtt_match:
            result["min_rtt_ms"] = float(rtt_match.group(1))
            result["avg_rtt_ms"] = float(rtt_match.group(2))
            result["max_rtt_ms"] = float(rtt_match.group(3))

        return result

    def _parse_ping_windows(self, output: str, ip: str, count: int) -> Dict:
        """Parse Windows ping output"""
        result = {
            "ip": ip,
            "packets_sent": count,
            "packets_received": 0,
            "packet_loss_percent": 100,
            "min_rtt_ms": None,
            "avg_rtt_ms": None,
            "max_rtt_ms": None,
            "is_reachable": False,
            "timestamp": datetime.utcnow(),
        }

        # Parse packet statistics
        packet_match = re.search(r"Sent = (\d+), Received = (\d+), Lost = \d+ \(([\d.]+)% loss\)", output)
        if packet_match:
            result["packets_sent"] = int(packet_match.group(1))
            result["packets_received"] = int(packet_match.group(2))
            result["packet_loss_percent"] = float(packet_match.group(3))
            result["is_reachable"] = result["packets_received"] > 0

        # Parse RTT statistics
        rtt_match = re.search(r"Minimum = (\d+)ms, Maximum = (\d+)ms, Average = (\d+)ms", output)
        if rtt_match:
            result["min_rtt_ms"] = float(rtt_match.group(1))
            result["max_rtt_ms"] = float(rtt_match.group(2))
            result["avg_rtt_ms"] = float(rtt_match.group(3))

        return result

    def _ping_timeout_result(self, ip: str, count: int) -> Dict:
        """Return timeout result"""
        return {
            "ip": ip,
            "packets_sent": count,
            "packets_received": 0,
            "packet_loss_percent": 100,
            "min_rtt_ms": None,
            "avg_rtt_ms": None,
            "max_rtt_ms": None,
            "is_reachable": False,
            "timestamp": datetime.utcnow(),
            "error": "Timeout",
        }

    def _ping_error_result(self, ip: str, count: int) -> Dict:
        """Return error result"""
        return {
            "ip": ip,
            "packets_sent": count,
            "packets_received": 0,
            "packet_loss_percent": 100,
            "min_rtt_ms": None,
            "avg_rtt_ms": None,
            "max_rtt_ms": None,
            "is_reachable": False,
            "timestamp": datetime.utcnow(),
            "error": "Ping failed",
        }

    def traceroute(self, ip_address: str, max_hops: int = 30, timeout: int = 30) -> Dict:
        """
        Perform traceroute to device

        Returns:
            {
                'target_ip': str,
                'hops': [
                    {
                        'hop_number': int,
                        'ip': str,
                        'hostname': str,
                        'latency_ms': float
                    }
                ],
                'total_hops': int,
                'timestamp': datetime
            }
        """
        try:
            # Platform-specific traceroute command
            if self.system == "Windows":
                cmd = ["tracert", "-h", str(max_hops), "-w", "2000", ip_address]
            else:  # Linux/Mac
                cmd = ["traceroute", "-m", str(max_hops), "-w", "2", ip_address]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

            output = result.stdout
            logger.info(f"Traceroute raw output for {ip_address}:\n{output}")

            # Parse results
            if self.system == "Windows":
                hops = self._parse_traceroute_windows(output)
            else:
                hops = self._parse_traceroute_unix(output)

            logger.info(f"Parsed {len(hops)} hops for {ip_address}: {hops}")

            return {
                "target_ip": ip_address,
                "hops": hops,
                "total_hops": len(hops),
                "reached_destination": any(h.get("ip") == ip_address for h in hops),
                "timestamp": datetime.utcnow(),
            }

        except subprocess.TimeoutExpired:
            return {
                "target_ip": ip_address,
                "hops": [],
                "total_hops": 0,
                "reached_destination": False,
                "timestamp": datetime.utcnow(),
                "error": "Traceroute timeout",
            }
        except Exception as e:
            logger.info(f"Traceroute error for {ip_address}: {e}")
            return {
                "target_ip": ip_address,
                "hops": [],
                "total_hops": 0,
                "reached_destination": False,
                "timestamp": datetime.utcnow(),
                "error": str(e),
            }

    def _parse_traceroute_unix(self, output: str) -> List[Dict]:
        """Parse Unix/Linux/Mac traceroute output"""
        hops = []

        # Example line: " 1  192.168.1.1 (192.168.1.1)  1.234 ms  1.345 ms  1.456 ms"
        # Example line: " 2  10.0.0.1 (10.0.0.1)  5.123 ms  5.234 ms  5.345 ms"
        # Example line: " 3  dns.google (8.8.8.8)  41.116 ms  40.759 ms  48.171 ms"
        # Example line: " 4  * * *"

        for line in output.split("\n"):
            # Skip header line
            if "traceroute to" in line.lower() or not line.strip():
                continue

            # Match hop number at start of line
            hop_match = re.match(r'^\s*(\d+)\s+(.+)', line)
            if not hop_match:
                continue

            hop_num = int(hop_match.group(1))
            rest = hop_match.group(2).strip()

            # Skip lines with all asterisks (no response)
            if re.match(r'^[\s\*]+$', rest):
                continue

            # Try to extract IP from parentheses: "hostname (IP)"
            ip_match = re.search(r'\(([\d\.]+)\)', rest)
            if not ip_match:
                continue

            ip = ip_match.group(1)

            # Extract hostname (everything before the IP in parentheses)
            hostname_match = re.match(r'^(.+?)\s+\(', rest)
            hostname = hostname_match.group(1).strip() if hostname_match else ip

            # Extract first latency value
            latency_match = re.search(r'([\d\.]+)\s+ms', rest)
            latency = float(latency_match.group(1)) if latency_match else None

            hops.append({
                "hop_number": hop_num,
                "ip": ip,
                "hostname": hostname,
                "latency_ms": latency
            })

        return hops

    def _parse_traceroute_windows(self, output: str) -> List[Dict]:
        """Parse Windows tracert output"""
        hops = []

        # Example line: "  1     1 ms     1 ms     1 ms  192.168.1.1"
        # Example line: "  2     5 ms     5 ms     5 ms  gateway.example.com [10.0.0.1]"
        pattern = r"^\s*(\d+)\s+(?:\*|<?\d+)\s+ms\s+(?:\*|<?\d+)\s+ms\s+(?:\*|<?\d+)\s+ms\s+(.+?)(?:\s+\[([\d\.]+)\])?$"

        for line in output.split("\n"):
            match = re.search(pattern, line)
            if match:
                hop_num = int(match.group(1))
                host_or_ip = match.group(2).strip()
                ip = match.group(3) if match.group(3) else host_or_ip

                # Extract latency (take first value)
                latency_match = re.search(r"(\d+)\s+ms", line)
                latency = float(latency_match.group(1)) if latency_match else None

                hops.append({"hop_number": hop_num, "ip": ip, "hostname": host_or_ip, "latency_ms": latency})

        return hops
