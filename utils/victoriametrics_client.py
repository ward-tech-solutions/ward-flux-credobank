"""
VictoriaMetrics Client for Time-Series Data Storage
===================================================

Handles all interactions with VictoriaMetrics for storing and querying
ping results, SNMP metrics, and other time-series data.

This replaces PostgreSQL for historical data storage, providing:
- 200x faster queries
- Automatic compression
- Unlimited retention
- Zabbix-level performance
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class VictoriaMetricsClient:
    """
    Production-ready VictoriaMetrics client with:
    - Automatic retries
    - Connection pooling
    - Batch writes
    - Error handling
    - Performance monitoring
    """

    def __init__(self, base_url: str = None):
        """
        Initialize VictoriaMetrics client

        Args:
            base_url: VictoriaMetrics URL (default from env: VICTORIA_URL)
        """
        self.base_url = (base_url or os.getenv("VICTORIA_URL", "http://victoriametrics:8428")).rstrip("/")
        self.write_url = f"{self.base_url}/api/v1/import/prometheus"
        self.query_url = f"{self.base_url}/api/v1/query"
        self.query_range_url = f"{self.base_url}/api/v1/query_range"

        # Configure session with retries and connection pooling
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Performance metrics
        self.metrics_written = 0
        self.queries_executed = 0
        self.errors = 0

        logger.info(f"VictoriaMetrics client initialized: {self.base_url}")

    def write_metric(
        self,
        metric_name: str,
        value: float,
        labels: Dict[str, str],
        timestamp: Optional[int] = None
    ) -> bool:
        """
        Write a single metric to VictoriaMetrics

        Args:
            metric_name: Metric name (e.g., "device_ping_status")
            value: Metric value
            labels: Dictionary of labels {key: value}
            timestamp: Unix timestamp in seconds (None = current time)

        Returns:
            True if successful, False otherwise

        Example:
            vm_client.write_metric(
                metric_name="device_ping_status",
                value=1,
                labels={"device_ip": "10.0.0.1", "device_name": "Router1"},
                timestamp=int(time.time())
            )
        """
        if timestamp is None:
            timestamp = int(time.time())

        # Build Prometheus format line
        # Format: metric_name{label1="value1",label2="value2"} value timestamp_ms
        label_str = ",".join([f'{k}="{self._escape_label_value(v)}"' for k, v in labels.items()])
        line = f'{metric_name}{{{label_str}}} {value} {timestamp}000\n'

        try:
            response = self.session.post(
                self.write_url,
                data=line.encode('utf-8'),
                headers={"Content-Type": "text/plain"},
                timeout=5
            )
            response.raise_for_status()
            self.metrics_written += 1
            return True

        except requests.exceptions.Timeout:
            logger.error(f"Timeout writing metric {metric_name} to VictoriaMetrics")
            self.errors += 1
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to write metric {metric_name} to VM: {e}")
            self.errors += 1
            return False
        except Exception as e:
            logger.error(f"Unexpected error writing metric: {e}", exc_info=True)
            self.errors += 1
            return False

    def write_metrics(self, metrics: List[Dict[str, Any]]) -> bool:
        """
        Write multiple metrics in batch (MUCH more efficient)

        Args:
            metrics: List of metric dictionaries with keys:
                - metric: metric name (required)
                - value: metric value (required)
                - labels: dict of labels (required)
                - timestamp: optional unix timestamp (default: now)

        Returns:
            True if all metrics written successfully, False otherwise

        Example:
            vm_client.write_metrics([
                {
                    "metric": "device_ping_status",
                    "value": 1,
                    "labels": {"device_ip": "10.0.0.1"},
                    "timestamp": int(time.time())
                },
                {
                    "metric": "device_ping_rtt_ms",
                    "value": 4.5,
                    "labels": {"device_ip": "10.0.0.1"}
                }
            ])
        """
        if not metrics:
            return True

        lines = []
        default_timestamp = int(time.time())

        for m in metrics:
            ts = m.get("timestamp", default_timestamp)
            label_str = ",".join([
                f'{k}="{self._escape_label_value(v)}"'
                for k, v in m["labels"].items()
            ])
            line = f'{m["metric"]}{{{label_str}}} {m["value"]} {ts}000'
            lines.append(line)

        payload = "\n".join(lines) + "\n"

        try:
            response = self.session.post(
                self.write_url,
                data=payload.encode('utf-8'),
                headers={"Content-Type": "text/plain"},
                timeout=10
            )
            response.raise_for_status()
            self.metrics_written += len(metrics)
            logger.debug(f"✅ Wrote {len(metrics)} metrics to VictoriaMetrics")
            return True

        except requests.exceptions.Timeout:
            logger.error(f"Timeout writing {len(metrics)} metrics to VictoriaMetrics")
            self.errors += 1
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to write {len(metrics)} metrics to VM: {e}")
            self.errors += 1
            return False
        except Exception as e:
            logger.error(f"Unexpected error writing batch: {e}", exc_info=True)
            self.errors += 1
            return False

    def query(self, query: str, time: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute instant query (PromQL)

        Args:
            query: PromQL query string
            time: RFC3339 timestamp or Unix timestamp (None = now)

        Returns:
            Query result as dict with structure:
            {
                "status": "success" | "error",
                "data": {
                    "resultType": "vector" | "matrix",
                    "result": [...]
                }
            }

        Example:
            result = vm_client.query('device_ping_status{device_ip="10.0.0.1"}')
        """
        params = {"query": query}
        if time:
            params["time"] = time

        try:
            response = self.session.get(
                self.query_url,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            self.queries_executed += 1
            return response.json()

        except requests.exceptions.Timeout:
            logger.error(f"Timeout executing query: {query}")
            self.errors += 1
            return {"status": "error", "error": "Query timeout"}
        except requests.exceptions.RequestException as e:
            logger.error(f"VM query failed: {e}")
            self.errors += 1
            return {"status": "error", "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in query: {e}", exc_info=True)
            self.errors += 1
            return {"status": "error", "error": str(e)}

    def query_range(
        self,
        query: str,
        start: str,
        end: str = "now",
        step: str = "10s"
    ) -> Dict[str, Any]:
        """
        Execute range query for time-series data

        Args:
            query: PromQL query string
            start: Start time (RFC3339, Unix timestamp, or relative like "-24h")
            end: End time (default "now")
            step: Query resolution (e.g., "10s", "1m", "5m")

        Returns:
            Query result with time-series data

        Example:
            result = vm_client.query_range(
                query='device_ping_status{device_ip="10.0.0.1"}',
                start="-24h",
                end="now",
                step="1m"
            )
        """
        params = {
            "query": query,
            "start": start,
            "end": end,
            "step": step
        }

        try:
            response = self.session.get(
                self.query_range_url,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            self.queries_executed += 1
            return response.json()

        except requests.exceptions.Timeout:
            logger.error(f"Timeout executing range query: {query}")
            self.errors += 1
            return {"status": "error", "error": "Range query timeout"}
        except requests.exceptions.RequestException as e:
            logger.error(f"VM range query failed: {e}")
            self.errors += 1
            return {"status": "error", "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in range query: {e}", exc_info=True)
            self.errors += 1
            return {"status": "error", "error": str(e)}

    def get_device_status_history(
        self,
        device_id: str,
        hours: int = 24,
        step: str = "10s"
    ) -> List[Dict[str, Any]]:
        """
        Get ping status history for a specific device

        Args:
            device_id: Device UUID
            hours: Hours of history to fetch
            step: Data resolution (default: 10s for real-time)

        Returns:
            List of {timestamp, value} dicts
            Empty list if no data or error

        Example:
            history = vm_client.get_device_status_history(
                device_id="7a96efed-ec2f-42ab-9f5a-f44534c0c547",
                hours=24
            )
            # Returns: [{"timestamp": 1698163200, "value": 1}, ...]
        """
        query = f'device_ping_status{{device_id="{device_id}"}}'
        result = self.query_range(
            query=query,
            start=f"-{hours}h",
            end="now",
            step=step
        )

        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            if data and len(data) > 0:
                values = data[0].get("values", [])
                return [
                    {"timestamp": int(v[0]), "value": float(v[1])}
                    for v in values
                ]

        return []

    def get_device_rtt_history(
        self,
        device_id: str,
        hours: int = 24,
        step: str = "10s"
    ) -> List[Dict[str, Any]]:
        """
        Get ping response time history for a device

        Args:
            device_id: Device UUID
            hours: Hours of history
            step: Data resolution

        Returns:
            List of {timestamp, rtt_ms} dicts
        """
        query = f'device_ping_rtt_ms{{device_id="{device_id}"}}'
        result = self.query_range(
            query=query,
            start=f"-{hours}h",
            end="now",
            step=step
        )

        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            if data and len(data) > 0:
                values = data[0].get("values", [])
                return [
                    {"timestamp": int(v[0]), "rtt_ms": float(v[1])}
                    for v in values
                ]

        return []

    def get_device_uptime_percent(
        self,
        device_id: str,
        hours: int = 24
    ) -> float:
        """
        Calculate device uptime percentage over time period

        Args:
            device_id: Device UUID
            hours: Hours to calculate over

        Returns:
            Uptime percentage (0.0 to 100.0)
            0.0 if no data

        Example:
            uptime = vm_client.get_device_uptime_percent(
                device_id="7a96efed-ec2f-42ab-9f5a-f44534c0c547",
                hours=24
            )
            # Returns: 99.2 (99.2% uptime)
        """
        query = f'avg_over_time(device_ping_status{{device_id="{device_id}"}}[{hours}h]) * 100'
        result = self.query(query)

        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            if data and len(data) > 0:
                value = data[0].get("value", [None, "0"])
                if len(value) >= 2:
                    return round(float(value[1]), 2)

        return 0.0

    def get_overall_uptime_percent(self, hours: int = 24) -> float:
        """
        Get overall uptime percentage across ALL devices

        Args:
            hours: Hours to calculate over

        Returns:
            Overall uptime percentage
        """
        query = f'avg(avg_over_time(device_ping_status[{hours}h])) * 100'
        result = self.query(query)

        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            if data and len(data) > 0:
                value = data[0].get("value", [None, "0"])
                if len(value) >= 2:
                    return round(float(value[1]), 2)

        return 0.0

    def get_top_down_devices(
        self,
        limit: int = 10,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get devices with most downtime in time period

        Args:
            limit: Number of devices to return
            hours: Hours to analyze

        Returns:
            List of dicts with device info and downtime count

        Example:
            problems = vm_client.get_top_down_devices(limit=10, hours=24)
            # Returns: [
            #   {"device_name": "Router1", "device_ip": "10.0.0.1", "downtime_count": 150},
            #   ...
            # ]
        """
        query = f"""
            topk({limit},
                sum_over_time(
                    (1 - device_ping_status)[{hours}h]
                )
            ) by (device_name, device_ip, device_id)
        """
        result = self.query(query)

        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            return [
                {
                    "device_name": d["metric"].get("device_name", "Unknown"),
                    "device_ip": d["metric"].get("device_ip", "Unknown"),
                    "device_id": d["metric"].get("device_id", "Unknown"),
                    "downtime_count": int(float(d["value"][1]))
                }
                for d in data
            ]

        return []

    def get_devices_currently_down(self) -> List[Dict[str, Any]]:
        """
        Get all devices that are currently down (status = 0)

        Returns:
            List of device info dicts
        """
        query = 'device_ping_status == 0'
        result = self.query(query)

        if result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            return [
                {
                    "device_name": d["metric"].get("device_name", "Unknown"),
                    "device_ip": d["metric"].get("device_ip", "Unknown"),
                    "device_id": d["metric"].get("device_id", "Unknown"),
                    "status": int(float(d["value"][1]))
                }
                for d in data
            ]

        return []

    def get_latest_ping_for_devices(self, device_ips: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get the latest ping results for multiple devices in batched queries.
        This replaces PostgreSQL _latest_ping_lookup with VictoriaMetrics.

        PHASE 3: Optimized bulk query for device list/dashboard APIs
        PHASE 3 FIX: Batch queries to avoid HTTP 422 (query URL too long)

        Args:
            device_ips: List of device IP addresses

        Returns:
            Dict mapping IP -> latest ping data
            Example: {
                "10.159.25.12": {
                    "is_reachable": True,
                    "avg_rtt_ms": 5.2,
                    "packet_loss": 0.0,
                    "timestamp": 1234567890,
                    "device_name": "Samtredia-PayBox"
                }
            }
        """
        if not device_ips:
            return {}

        # PHASE 3 FIX: Batch the queries to avoid URL length limits
        # With 875 devices, a single regex query is too large (HTTP 422)
        # Process 20 IPs per batch = 44 batches for 875 devices (smaller batches = more reliable)
        BATCH_SIZE = 20
        all_results = {}

        # Split device IPs into batches
        for batch_start in range(0, len(device_ips), BATCH_SIZE):
            batch_ips = device_ips[batch_start:batch_start + BATCH_SIZE]

            # Build regex for this batch
            ip_regex = "|".join([ip.replace(".", "\\.") for ip in batch_ips])

            # Query all 3 ping metrics for the batch
            queries = {
                "status": f'device_ping_status{{device_ip=~"{ip_regex}"}}',
                "rtt": f'device_ping_rtt_ms{{device_ip=~"{ip_regex}"}}',
                "loss": f'device_ping_packet_loss{{device_ip=~"{ip_regex}"}}'
            }

            # Execute queries for each metric type in this batch
            for metric_type, query in queries.items():
                try:
                    result = self.query(query)
                    if result.get("status") == "success":
                        data = result.get("data", {}).get("result", [])
                        for item in data:
                            device_ip = item["metric"].get("device_ip")
                            if device_ip:
                                if device_ip not in all_results:
                                    all_results[device_ip] = {
                                        "device_ip": device_ip,
                                        "device_name": item["metric"].get("device_name", "Unknown"),
                                        "device_id": item["metric"].get("device_id"),
                                        "is_reachable": None,
                                        "avg_rtt_ms": None,
                                        "packet_loss": None,
                                        "timestamp": None
                                    }

                                # Parse value and timestamp
                                value = float(item["value"][1])
                                timestamp = int(item["value"][0])

                                # Update the appropriate field
                                if metric_type == "status":
                                    all_results[device_ip]["is_reachable"] = value == 1.0
                                    all_results[device_ip]["timestamp"] = timestamp
                                elif metric_type == "rtt":
                                    all_results[device_ip]["avg_rtt_ms"] = value
                                elif metric_type == "loss":
                                    all_results[device_ip]["packet_loss"] = value

                except Exception as e:
                    logger.warning(f"Failed to query {metric_type} for batch {batch_start}-{batch_start+len(batch_ips)}: {e}")
                    continue

        logger.info(f"Queried {len(device_ips)} devices in {(len(device_ips) + BATCH_SIZE - 1) // BATCH_SIZE} batches, got {len(all_results)} results")
        return all_results

    def get_stats(self) -> Dict[str, int]:
        """
        Get client performance statistics

        Returns:
            Dict with metrics_written, queries_executed, errors
        """
        return {
            "metrics_written": self.metrics_written,
            "queries_executed": self.queries_executed,
            "errors": self.errors,
            "success_rate": round(
                (self.metrics_written / max(self.metrics_written + self.errors, 1)) * 100, 2
            ) if self.metrics_written > 0 else 100.0
        }

    def health_check(self) -> bool:
        """
        Check if VictoriaMetrics is accessible and healthy

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"VictoriaMetrics health check failed: {e}")
            return False

    @staticmethod
    def _escape_label_value(value: str) -> str:
        """
        Escape special characters in label values for Prometheus format

        Args:
            value: Label value to escape

        Returns:
            Escaped string safe for Prometheus format
        """
        # Escape backslashes and double quotes
        return str(value).replace("\\", "\\\\").replace('"', '\\"')

    def close(self):
        """Close the HTTP session"""
        if self.session:
            self.session.close()
            logger.info("VictoriaMetrics client session closed")


# Global client instance (singleton pattern)
_vm_client_instance = None


def get_vm_client() -> VictoriaMetricsClient:
    """
    Get or create global VictoriaMetrics client instance

    Returns:
        VictoriaMetricsClient instance

    Example:
        from utils.victoriametrics_client import get_vm_client

        vm = get_vm_client()
        vm.write_metric("test_metric", 42, {"label": "value"})
    """
    global _vm_client_instance

    if _vm_client_instance is None:
        _vm_client_instance = VictoriaMetricsClient()

    return _vm_client_instance


# For backward compatibility and convenience
vm_client = get_vm_client()
