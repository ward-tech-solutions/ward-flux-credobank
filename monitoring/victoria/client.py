"""
WARD FLUX - VictoriaMetrics Client

HTTP client for VictoriaMetrics API with Prometheus-compatible metrics.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class VictoriaMetricsClient:
    """
    VictoriaMetrics HTTP API client

    Provides methods for writing metrics and querying data.
    Compatible with Prometheus remote write protocol.
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize VictoriaMetrics client with retry logic

        Args:
            base_url: VictoriaMetrics base URL (defaults to env VICTORIA_URL)
        """
        self.base_url = base_url or os.getenv("VICTORIA_URL", "http://localhost:8428")
        self.session = requests.Session()

        # Configure automatic retries for transient failures
        # Prevents data loss during temporary network issues
        retry_strategy = Retry(
            total=3,                                        # Retry up to 3 times
            backoff_factor=0.5,                             # Wait 0.5s, 1s, 2s between retries
            status_forcelist=[429, 500, 502, 503, 504],    # Retry on these HTTP codes
            allowed_methods=["GET", "POST"],                # Retry safe methods
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,        # Connection pooling
            pool_maxsize=20             # Max connections in pool
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.session.headers.update({"Content-Type": "application/x-www-form-urlencoded"})

        logger.info(f"VictoriaMetrics client initialized: {self.base_url} (with retry logic)")

    def write_metric(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        Write a single metric to VictoriaMetrics

        Args:
            metric_name: Metric name (e.g., "cpu_usage", "interface_bytes_in")
            value: Metric value
            labels: Optional metric labels (e.g., {"device": "router1", "ip": "1.2.3.4"})
            timestamp: Optional timestamp (defaults to now)

        Returns:
            True if successful, False otherwise

        Example:
            client.write_metric(
                metric_name="cpu_usage",
                value=45.2,
                labels={"device": "router1", "vendor": "cisco"}
            )
        """
        try:
            if timestamp is None:
                timestamp = datetime.utcnow()

            # Convert to Unix timestamp in milliseconds
            ts_ms = int(timestamp.timestamp() * 1000)

            # Build metric line in Prometheus format
            labels_str = self._build_labels_string(labels or {})
            metric_line = f"{metric_name}{labels_str} {value} {ts_ms}"

            # Write using /api/v1/import/prometheus endpoint
            url = urljoin(self.base_url, "/api/v1/import/prometheus")
            response = self.session.post(url, data=metric_line)

            if response.status_code == 204:
                logger.debug(f"Metric written: {metric_name} = {value}")
                return True
            else:
                logger.error(f"Failed to write metric: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error writing metric {metric_name}: {e}")
            return False

    def write_metrics_bulk(self, metrics: List[Dict[str, Any]]) -> bool:
        """
        Write multiple metrics in a single request

        Args:
            metrics: List of metric dictionaries with keys:
                     - metric_name: str
                     - value: float
                     - labels: dict (optional)
                     - timestamp: datetime (optional)

        Returns:
            True if successful, False otherwise

        Example:
            metrics = [
                {"metric_name": "cpu_usage", "value": 45, "labels": {"device": "r1"}},
                {"metric_name": "memory_usage", "value": 60, "labels": {"device": "r1"}},
            ]
            client.write_metrics_bulk(metrics)
        """
        try:
            metric_lines = []

            for metric in metrics:
                metric_name = metric["metric_name"]
                value = metric["value"]
                labels = metric.get("labels", {})
                timestamp = metric.get("timestamp", datetime.utcnow())

                ts_ms = int(timestamp.timestamp() * 1000)
                labels_str = self._build_labels_string(labels)
                metric_lines.append(f"{metric_name}{labels_str} {value} {ts_ms}")

            # Join all metrics with newlines
            data = "\n".join(metric_lines)

            # Write using /api/v1/import/prometheus endpoint
            url = urljoin(self.base_url, "/api/v1/import/prometheus")
            response = self.session.post(url, data=data)

            if response.status_code == 204:
                logger.info(f"Bulk write successful: {len(metrics)} metrics")
                return True
            else:
                logger.error(f"Bulk write failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error writing bulk metrics: {e}")
            return False

    def query(self, query: str, time: Optional[datetime] = None) -> Optional[Dict]:
        """
        Execute instant query (PromQL)

        Args:
            query: PromQL query string
            time: Optional query time (defaults to now)

        Returns:
            Query result as dictionary or None on error

        Example:
            result = client.query('cpu_usage{device="router1"}')
        """
        try:
            url = urljoin(self.base_url, "/api/v1/query")
            params = {"query": query}

            if time:
                params["time"] = int(time.timestamp())

            response = self.session.get(url, params=params)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Query failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error executing query '{query}': {e}")
            return None

    def query_range(
        self, query: str, start: datetime, end: datetime, step: str = "60s"
    ) -> Optional[Dict]:
        """
        Execute range query (PromQL)

        Args:
            query: PromQL query string
            start: Start time
            end: End time
            step: Query resolution (e.g., "60s", "5m", "1h")

        Returns:
            Query result as dictionary or None on error

        Example:
            result = client.query_range(
                query='cpu_usage{device="router1"}',
                start=datetime.utcnow() - timedelta(hours=1),
                end=datetime.utcnow(),
                step="60s"
            )
        """
        try:
            url = urljoin(self.base_url, "/api/v1/query_range")
            params = {
                "query": query,
                "start": int(start.timestamp()),
                "end": int(end.timestamp()),
                "step": step,
            }

            response = self.session.get(url, params=params)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Range query failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error executing range query '{query}': {e}")
            return None

    def get_latest_value(self, metric_name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """
        Get latest value for a metric

        Args:
            metric_name: Metric name
            labels: Optional label filters

        Returns:
            Latest metric value or None

        Example:
            value = client.get_latest_value("cpu_usage", {"device": "router1"})
        """
        try:
            labels_str = self._build_labels_string(labels or {})
            query = f"{metric_name}{labels_str}"

            result = self.query(query)

            if result and result.get("status") == "success":
                data = result.get("data", {})
                result_data = data.get("result", [])

                if result_data:
                    value = result_data[0].get("value", [None, None])[1]
                    return float(value) if value is not None else None

            return None

        except Exception as e:
            logger.error(f"Error getting latest value for {metric_name}: {e}")
            return None

    def health_check(self) -> bool:
        """
        Check if VictoriaMetrics is healthy

        Returns:
            True if healthy, False otherwise
        """
        try:
            url = urljoin(self.base_url, "/health")
            response = self.session.get(url, timeout=5)
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def _build_labels_string(self, labels: Dict[str, str]) -> str:
        """
        Build Prometheus label string

        Args:
            labels: Label dictionary

        Returns:
            Formatted label string (e.g., '{device="router1",vendor="cisco"}')
        """
        if not labels:
            return ""

        label_pairs = [f'{key}="{value}"' for key, value in labels.items()]
        return "{" + ",".join(label_pairs) + "}"

    def delete_metrics(self, match: str) -> bool:
        """
        Delete metrics matching selector

        Args:
            match: Metric selector (e.g., '{device="router1"}')

        Returns:
            True if successful, False otherwise

        Warning: Use with caution! This permanently deletes data.
        """
        try:
            url = urljoin(self.base_url, "/api/v1/admin/tsdb/delete_series")
            params = {"match[]": match}

            response = self.session.post(url, params=params)

            if response.status_code == 204:
                logger.warning(f"Metrics deleted: {match}")
                return True
            else:
                logger.error(f"Delete failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error deleting metrics '{match}': {e}")
            return False

    def close(self):
        """Close HTTP session"""
        self.session.close()
        logger.info("VictoriaMetrics client closed")


# Singleton instance
_vm_client: Optional[VictoriaMetricsClient] = None


def get_victoria_client() -> VictoriaMetricsClient:
    """
    Get or create VictoriaMetrics client singleton

    Returns:
        VictoriaMetricsClient instance
    """
    global _vm_client

    if _vm_client is None:
        _vm_client = VictoriaMetricsClient()

    return _vm_client
