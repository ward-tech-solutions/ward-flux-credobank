"""
WARD FLUX - Interface Metrics Collection
Collects interface traffic, errors, and utilization metrics via SNMP
Stores time-series data in VictoriaMetrics
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import requests
from sqlalchemy import select

from database import SessionLocal
from monitoring.models import DeviceInterface, StandaloneDevice, InterfaceMetricsSummary
from monitoring.snmp.poller import SNMPPoller, SNMPCredentialData

logger = logging.getLogger(__name__)


# IF-MIB Counter OIDs (64-bit high-capacity counters)
INTERFACE_COUNTER_OIDS = {
    # STATUS METRICS (CRITICAL for ISP monitoring!)
    'oper_status': '1.3.6.1.2.1.2.2.1.8',             # ⭐ Operational status (1=UP, 2=DOWN)
    'admin_status': '1.3.6.1.2.1.2.2.1.7',            # Administrative status
    'speed': '1.3.6.1.2.1.31.1.1.1.15',               # Interface speed (high capacity)

    # TRAFFIC COUNTERS
    'if_hc_in_octets': '1.3.6.1.2.1.31.1.1.1.6',      # 64-bit inbound octets
    'if_hc_out_octets': '1.3.6.1.2.1.31.1.1.1.10',    # 64-bit outbound octets
    'if_hc_in_ucast_pkts': '1.3.6.1.2.1.31.1.1.1.7',  # Inbound unicast packets
    'if_hc_out_ucast_pkts': '1.3.6.1.2.1.31.1.1.1.11',# Outbound unicast packets

    # ERROR COUNTERS
    'if_in_errors': '1.3.6.1.2.1.2.2.1.14',           # Inbound errors
    'if_out_errors': '1.3.6.1.2.1.2.2.1.20',          # Outbound errors
    'if_in_discards': '1.3.6.1.2.1.2.2.1.13',         # Inbound discards
    'if_out_discards': '1.3.6.1.2.1.2.2.1.19',        # Outbound discards
}


class InterfaceMetricsCollector:
    """
    Collects interface metrics via SNMP and stores in VictoriaMetrics

    Metrics collected:
    - Traffic: Inbound/outbound octets (bytes)
    - Packets: Unicast packets
    - Errors: Input/output errors
    - Discards: Input/output discards
    """

    def __init__(self, victoriametrics_url: str = "http://localhost:8428"):
        """
        Initialize metrics collector

        Args:
            victoriametrics_url: VictoriaMetrics API endpoint
        """
        self.poller = SNMPPoller()
        self.poller.timeout = 3
        self.poller.retries = 1
        self.vm_url = victoriametrics_url

    async def collect_interface_metrics(
        self,
        device_ip: str,
        device_id: str,
        device_name: str,
        interfaces: List[Dict],
        snmp_community: str,
        snmp_version: str = 'v2c',
        snmp_port: int = 161
    ) -> Dict:
        """
        Collect metrics for all interfaces on a device

        Args:
            device_ip: Device IP address
            device_id: Device UUID
            device_name: Device name
            interfaces: List of interface dicts (from database)
            snmp_community: SNMP community string
            snmp_version: SNMP version
            snmp_port: SNMP port

        Returns:
            Dict with collection results
        """
        result = {
            'device_id': str(device_id),
            'device_ip': device_ip,
            'success': False,
            'interfaces_polled': 0,
            'metrics_collected': 0,
            'metrics_stored': 0,
            'error': None
        }

        try:
            # Build SNMP credentials
            credentials = SNMPCredentialData(
                version=snmp_version,
                community=snmp_community
            )

            # Collect metrics for each interface
            metrics_batch = []

            for interface in interfaces:
                # Skip disabled interfaces
                if not interface.get('monitoring_enabled', True):
                    continue

                if_index = interface['if_index']
                if_name = interface.get('if_name', f"if{if_index}")
                interface_type = interface.get('interface_type', 'other')
                isp_provider = interface.get('isp_provider')
                is_critical = interface.get('is_critical', False)

                # Poll all counter OIDs for this interface
                interface_metrics = await self._poll_interface_counters(
                    device_ip, if_index, credentials, snmp_port
                )

                if interface_metrics:
                    result['interfaces_polled'] += 1

                    # Add labels to metrics
                    labels = {
                        'device_id': str(device_id),
                        'device_name': device_name,
                        'device_ip': device_ip,
                        'interface_id': str(interface.get('id', '')),
                        'if_index': str(if_index),
                        'if_name': if_name,
                        'interface_type': interface_type,
                        'is_critical': str(is_critical).lower(),
                    }

                    # Add ISP provider label if available
                    if isp_provider:
                        labels['isp_provider'] = isp_provider

                    # Create metrics for VictoriaMetrics
                    for metric_name, value in interface_metrics.items():
                        if value is not None:
                            metrics_batch.append({
                                'metric': f'interface_{metric_name}',
                                'labels': labels,
                                'value': value,
                                'timestamp': int(datetime.utcnow().timestamp() * 1000)
                            })
                            result['metrics_collected'] += 1

            # Store metrics in VictoriaMetrics
            if metrics_batch:
                stored_count = await self._store_metrics_victoriametrics(metrics_batch)
                result['metrics_stored'] = stored_count

            result['success'] = True

        except Exception as e:
            logger.error(f"Failed to collect interface metrics for {device_ip}: {str(e)}", exc_info=True)
            result['error'] = str(e)

        return result

    async def _poll_interface_counters(
        self,
        device_ip: str,
        if_index: int,
        credentials: SNMPCredentialData,
        port: int = 161
    ) -> Optional[Dict]:
        """
        Poll all counter OIDs for a specific interface

        Args:
            device_ip: Device IP
            if_index: Interface index
            credentials: SNMP credentials
            port: SNMP port

        Returns:
            Dict of metric_name -> value or None on error
        """
        metrics = {}

        try:
            # Poll each counter OID
            for metric_name, base_oid in INTERFACE_COUNTER_OIDS.items():
                oid = f"{base_oid}.{if_index}"

                try:
                    result = await self.poller.get(device_ip, oid, credentials, port)

                    if result.success and result.value is not None:
                        metrics[metric_name] = int(result.value)
                    else:
                        metrics[metric_name] = None

                except Exception as e:
                    logger.debug(f"Failed to poll {metric_name} for {device_ip} if{if_index}: {str(e)}")
                    metrics[metric_name] = None

            # Return metrics if at least some were collected
            if any(v is not None for v in metrics.values()):
                return metrics
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to poll interface counters for {device_ip} if{if_index}: {str(e)}")
            return None

    async def _store_metrics_victoriametrics(self, metrics: List[Dict]) -> int:
        """
        Store metrics in VictoriaMetrics using import API

        Args:
            metrics: List of metric dicts with 'metric', 'labels', 'value', 'timestamp'

        Returns:
            Number of metrics stored
        """
        if not metrics:
            return 0

        try:
            # Convert to VictoriaMetrics import format (Prometheus-compatible)
            lines = []

            for m in metrics:
                # Build label string: {label1="value1",label2="value2"}
                label_parts = [f'{k}="{v}"' for k, v in m['labels'].items()]
                label_string = '{' + ','.join(label_parts) + '}'

                # Format: metric_name{labels} value timestamp
                line = f"{m['metric']}{label_string} {m['value']} {m['timestamp']}"
                lines.append(line)

            # Send to VictoriaMetrics
            payload = '\n'.join(lines)

            response = requests.post(
                f"{self.vm_url}/api/v1/import/prometheus",
                data=payload,
                headers={'Content-Type': 'text/plain'},
                timeout=10
            )

            if response.status_code == 204:
                logger.debug(f"Stored {len(metrics)} metrics in VictoriaMetrics")
                return len(metrics)
            else:
                logger.error(f"Failed to store metrics in VictoriaMetrics: HTTP {response.status_code}")
                return 0

        except Exception as e:
            logger.error(f"Failed to store metrics in VictoriaMetrics: {str(e)}", exc_info=True)
            return 0

    async def calculate_interface_rates(
        self,
        device_ip: str,
        interface_id: str,
        if_index: int,
        lookback_seconds: int = 300
    ) -> Optional[Dict]:
        """
        Calculate traffic rates from VictoriaMetrics counters

        Uses rate() function to calculate bytes/sec and packets/sec

        Args:
            device_ip: Device IP
            interface_id: Interface UUID
            if_index: Interface index
            lookback_seconds: Lookback period for rate calculation

        Returns:
            Dict with calculated rates or None
        """
        try:
            # Query VictoriaMetrics for rates
            queries = {
                'in_bps': f'rate(interface_if_hc_in_octets{{interface_id="{interface_id}"}}[{lookback_seconds}s]) * 8',
                'out_bps': f'rate(interface_if_hc_out_octets{{interface_id="{interface_id}"}}[{lookback_seconds}s]) * 8',
                'in_pps': f'rate(interface_if_hc_in_ucast_pkts{{interface_id="{interface_id}"}}[{lookback_seconds}s])',
                'out_pps': f'rate(interface_if_hc_out_ucast_pkts{{interface_id="{interface_id}"}}[{lookback_seconds}s])',
                'in_errors_rate': f'rate(interface_if_in_errors{{interface_id="{interface_id}"}}[{lookback_seconds}s])',
                'out_errors_rate': f'rate(interface_if_out_errors{{interface_id="{interface_id}"}}[{lookback_seconds}s])',
            }

            rates = {}

            for rate_name, query in queries.items():
                response = requests.get(
                    f"{self.vm_url}/api/v1/query",
                    params={'query': query},
                    timeout=5
                )

                if response.status_code == 200:
                    data = response.json()

                    if data.get('status') == 'success' and data.get('data', {}).get('result'):
                        value = float(data['data']['result'][0]['value'][1])
                        rates[rate_name] = value
                    else:
                        rates[rate_name] = 0.0
                else:
                    rates[rate_name] = 0.0

            return rates

        except Exception as e:
            logger.error(f"Failed to calculate rates for interface {interface_id}: {str(e)}")
            return None

    async def update_interface_metrics_summary(self, interface_id: str) -> bool:
        """
        Update cached metrics summary in PostgreSQL

        Queries VictoriaMetrics for last 24 hours and caches in database

        Args:
            interface_id: Interface UUID

        Returns:
            True if successful
        """
        try:
            # Query VictoriaMetrics for 24h metrics
            queries = {
                'avg_in_mbps': f'avg_over_time(rate(interface_if_hc_in_octets{{interface_id="{interface_id}"}}[5m]) * 8 / 1000000[24h])',
                'avg_out_mbps': f'avg_over_time(rate(interface_if_hc_out_octets{{interface_id="{interface_id}"}}[5m]) * 8 / 1000000[24h])',
                'max_in_mbps': f'max_over_time(rate(interface_if_hc_in_octets{{interface_id="{interface_id}"}}[5m]) * 8 / 1000000[24h])',
                'max_out_mbps': f'max_over_time(rate(interface_if_hc_out_octets{{interface_id="{interface_id}"}}[5m]) * 8 / 1000000[24h])',
                'total_in_gb': f'increase(interface_if_hc_in_octets{{interface_id="{interface_id}"}}[24h]) / 1000000000',
                'total_out_gb': f'increase(interface_if_hc_out_octets{{interface_id="{interface_id}"}}[24h]) / 1000000000',
                'in_errors': f'increase(interface_if_in_errors{{interface_id="{interface_id}"}}[24h])',
                'out_errors': f'increase(interface_if_out_errors{{interface_id="{interface_id}"}}[24h])',
                'in_discards': f'increase(interface_if_in_discards{{interface_id="{interface_id}"}}[24h])',
                'out_discards': f'increase(interface_if_out_discards{{interface_id="{interface_id}"}}[24h])',
            }

            summary = {}

            for metric_name, query in queries.items():
                response = requests.get(
                    f"{self.vm_url}/api/v1/query",
                    params={'query': query},
                    timeout=5
                )

                if response.status_code == 200:
                    data = response.json()

                    if data.get('status') == 'success' and data.get('data', {}).get('result'):
                        value = float(data['data']['result'][0]['value'][1])
                        summary[metric_name] = value
                    else:
                        summary[metric_name] = None

            # Calculate utilization (if speed is known)
            # TODO: Get interface speed from database and calculate utilization

            # Update database
            db = SessionLocal()
            try:
                from sqlalchemy.dialects.postgresql import insert

                stmt = insert(InterfaceMetricsSummary).values(
                    interface_id=interface_id,
                    **summary,
                    calculated_at=datetime.utcnow()
                )

                stmt = stmt.on_conflict_do_update(
                    index_elements=['interface_id'],
                    set_={
                        **summary,
                        'calculated_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    }
                )

                db.execute(stmt)
                db.commit()

                return True

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to update metrics summary for {interface_id}: {str(e)}", exc_info=True)
            return False


# Singleton instance
interface_metrics_collector = InterfaceMetricsCollector()
