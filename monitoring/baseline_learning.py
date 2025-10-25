"""
WARD FLUX - Baseline Learning & Anomaly Detection
Learns normal traffic patterns and detects deviations
Uses statistical analysis for intelligent alerting
"""

import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import statistics

from database import SessionLocal
from monitoring.models import DeviceInterface
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert

logger = logging.getLogger(__name__)


@dataclass
class BaselineStats:
    """Statistical baseline for a metric"""
    mean: float
    std_dev: float
    min_value: float
    max_value: float
    sample_count: int
    confidence: float  # 0.0-1.0


@dataclass
class AnomalyDetection:
    """Anomaly detection result"""
    is_anomaly: bool
    current_value: float
    expected_value: float
    z_score: float  # Number of standard deviations from mean
    severity: str  # 'low', 'medium', 'high', 'critical'
    message: str


class BaselineLearning:
    """
    Baseline Learning & Anomaly Detection Engine

    Learns normal behavior patterns from historical data:
    - Hourly patterns (24 baselines per day)
    - Day-of-week patterns (7 baselines per week)
    - Calculates mean and standard deviation
    - Detects anomalies using z-score (3-sigma rule)
    """

    def __init__(self, victoriametrics_url: str = "http://localhost:8428"):
        """
        Initialize baseline learning

        Args:
            victoriametrics_url: VictoriaMetrics API endpoint
        """
        self.vm_url = victoriametrics_url
        self.min_samples = 7  # Minimum samples for baseline (1 week)
        self.z_score_threshold = 3.0  # 3 standard deviations = anomaly

    async def learn_interface_baseline(
        self,
        interface_id: str,
        hour_of_day: int,
        day_of_week: int,
        lookback_days: int = 14
    ) -> Optional[BaselineStats]:
        """
        Learn baseline for an interface at specific time

        Args:
            interface_id: Interface UUID
            hour_of_day: Hour (0-23)
            day_of_week: Day (0=Monday, 6=Sunday)
            lookback_days: Days to look back (default 14)

        Returns:
            BaselineStats or None if insufficient data
        """
        try:
            # Query VictoriaMetrics for historical data
            # Get traffic rate for this hour/day over last N weeks
            query = f"""
            avg_over_time(
                rate(interface_if_hc_in_octets{{interface_id="{interface_id}"}}[5m]) * 8 / 1000000
                [{lookback_days}d:1h]
            )
            """

            response = requests.get(
                f"{self.vm_url}/api/v1/query",
                params={'query': query},
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"VictoriaMetrics query failed: HTTP {response.status_code}")
                return None

            data = response.json()

            if data.get('status') != 'success' or not data.get('data', {}).get('result'):
                logger.debug(f"No data for interface {interface_id}")
                return None

            # Extract values
            values = []
            for result in data['data']['result']:
                if result.get('value') and len(result['value']) == 2:
                    value = float(result['value'][1])
                    values.append(value)

            if len(values) < self.min_samples:
                logger.debug(f"Insufficient samples for baseline: {len(values)} < {self.min_samples}")
                return None

            # Calculate statistics
            mean = statistics.mean(values)
            std_dev = statistics.stdev(values) if len(values) > 1 else 0.0
            min_val = min(values)
            max_val = max(values)
            sample_count = len(values)

            # Calculate confidence (more samples = higher confidence)
            confidence = min(sample_count / 28.0, 1.0)  # Max at 4 weeks

            return BaselineStats(
                mean=mean,
                std_dev=std_dev,
                min_value=min_val,
                max_value=max_val,
                sample_count=sample_count,
                confidence=confidence
            )

        except Exception as e:
            logger.error(f"Failed to learn baseline for {interface_id}: {str(e)}", exc_info=True)
            return None

    async def detect_anomaly(
        self,
        interface_id: str,
        current_value: float,
        hour_of_day: int,
        day_of_week: int
    ) -> Optional[AnomalyDetection]:
        """
        Detect if current value is anomalous compared to baseline

        Args:
            interface_id: Interface UUID
            current_value: Current metric value
            hour_of_day: Current hour (0-23)
            day_of_week: Current day (0=Monday, 6=Sunday)

        Returns:
            AnomalyDetection result or None
        """
        try:
            # Get baseline from database
            db = SessionLocal()

            try:
                from monitoring.models import InterfaceBaseline

                stmt = select(InterfaceBaseline).where(
                    and_(
                        InterfaceBaseline.interface_id == interface_id,
                        InterfaceBaseline.hour_of_day == hour_of_day,
                        InterfaceBaseline.day_of_week == day_of_week
                    )
                )

                baseline = db.execute(stmt).scalar_one_or_none()

                if not baseline:
                    logger.debug(f"No baseline found for interface {interface_id}")
                    return None

                # Check confidence threshold
                if baseline.confidence < 0.5:
                    logger.debug(f"Baseline confidence too low: {baseline.confidence}")
                    return None

                # Calculate z-score (number of standard deviations from mean)
                if baseline.std_dev_in_mbps and baseline.std_dev_in_mbps > 0:
                    z_score = (current_value - baseline.avg_in_mbps) / baseline.std_dev_in_mbps
                else:
                    # If std_dev is 0 (constant traffic), check if current value differs
                    z_score = 0.0 if current_value == baseline.avg_in_mbps else float('inf')

                # Determine if anomaly
                is_anomaly = abs(z_score) > self.z_score_threshold

                # Determine severity
                severity = self._calculate_severity(abs(z_score))

                # Build message
                direction = "higher" if z_score > 0 else "lower"
                message = (
                    f"Traffic {direction} than expected: {current_value:.2f} Mbps "
                    f"(expected {baseline.avg_in_mbps:.2f} ± {baseline.std_dev_in_mbps:.2f} Mbps, "
                    f"z-score: {z_score:.2f})"
                )

                return AnomalyDetection(
                    is_anomaly=is_anomaly,
                    current_value=current_value,
                    expected_value=baseline.avg_in_mbps,
                    z_score=z_score,
                    severity=severity,
                    message=message
                )

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Anomaly detection failed for {interface_id}: {str(e)}", exc_info=True)
            return None

    def _calculate_severity(self, z_score: float) -> str:
        """
        Calculate severity based on z-score

        Args:
            z_score: Absolute z-score

        Returns:
            Severity string
        """
        if z_score >= 5.0:
            return 'critical'  # >5 sigma (extremely rare)
        elif z_score >= 4.0:
            return 'high'  # 4-5 sigma
        elif z_score >= 3.0:
            return 'medium'  # 3-4 sigma
        else:
            return 'low'  # <3 sigma

    async def update_all_baselines(self, lookback_days: int = 14) -> Dict:
        """
        Update baselines for all critical interfaces

        Args:
            lookback_days: Days to look back for learning

        Returns:
            Summary dict
        """
        db = SessionLocal()
        summary = {
            'total_interfaces': 0,
            'baselines_updated': 0,
            'baselines_created': 0,
            'errors': 0,
            'started_at': datetime.utcnow().isoformat()
        }

        try:
            from monitoring.models import InterfaceBaseline

            # Get all critical interfaces
            stmt = select(DeviceInterface).where(
                DeviceInterface.is_critical == True,
                DeviceInterface.enabled == True,
                DeviceInterface.monitoring_enabled == True
            )

            interfaces = db.execute(stmt).scalars().all()
            summary['total_interfaces'] = len(interfaces)

            logger.info(f"Updating baselines for {len(interfaces)} critical interfaces")

            # For each interface, learn baselines for all hour/day combinations
            for interface in interfaces:
                try:
                    for hour in range(24):  # 0-23
                        for day in range(7):  # 0-6 (Monday-Sunday)
                            baseline_stats = await self.learn_interface_baseline(
                                str(interface.id), hour, day, lookback_days
                            )

                            if baseline_stats:
                                # Upsert baseline
                                stmt = insert(InterfaceBaseline).values(
                                    interface_id=str(interface.id),
                                    hour_of_day=hour,
                                    day_of_week=day,
                                    avg_in_mbps=baseline_stats.mean,
                                    std_dev_in_mbps=baseline_stats.std_dev,
                                    min_in_mbps=baseline_stats.min_value,
                                    max_in_mbps=baseline_stats.max_value,
                                    sample_count=baseline_stats.sample_count,
                                    confidence=baseline_stats.confidence,
                                    last_updated=datetime.utcnow()
                                )

                                stmt = stmt.on_conflict_do_update(
                                    index_elements=['interface_id', 'hour_of_day', 'day_of_week'],
                                    set_={
                                        'avg_in_mbps': stmt.excluded.avg_in_mbps,
                                        'std_dev_in_mbps': stmt.excluded.std_dev_in_mbps,
                                        'min_in_mbps': stmt.excluded.min_in_mbps,
                                        'max_in_mbps': stmt.excluded.max_in_mbps,
                                        'sample_count': stmt.excluded.sample_count,
                                        'confidence': stmt.excluded.confidence,
                                        'last_updated': stmt.excluded.last_updated,
                                    }
                                )

                                db.execute(stmt)
                                summary['baselines_updated'] += 1

                    db.commit()

                except Exception as e:
                    logger.error(f"Failed to update baselines for interface {interface.id}: {str(e)}")
                    summary['errors'] += 1
                    continue

            summary['completed_at'] = datetime.utcnow().isoformat()

            logger.info(
                f"Baseline update completed: {summary['baselines_updated']} baselines updated "
                f"for {summary['total_interfaces']} interfaces"
            )

            return summary

        except Exception as e:
            logger.error(f"Baseline update failed: {str(e)}", exc_info=True)
            summary['errors'] += 1
            return summary
        finally:
            db.close()


# Singleton instance
baseline_learning = BaselineLearning()
