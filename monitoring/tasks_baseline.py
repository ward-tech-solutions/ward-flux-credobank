"""
WARD FLUX - Baseline Learning Tasks
Celery tasks for learning traffic patterns and detecting anomalies
"""

import logging
import asyncio
from datetime import datetime
from celery import shared_task

from monitoring.baseline_learning import baseline_learning

logger = logging.getLogger(__name__)


@shared_task(name="monitoring.tasks.learn_all_baselines", bind=True)
def learn_all_baselines_task(self, lookback_days: int = 14):
    """
    Celery task: Learn baselines for all critical interfaces

    Runs weekly via Celery Beat

    Args:
        lookback_days: Days to look back for learning (default 14)

    Returns:
        Summary of learning results
    """
    logger.info(f"[Task {self.request.id}] Learning baselines (lookback: {lookback_days} days)")

    try:
        summary = asyncio.run(
            baseline_learning.update_all_baselines(lookback_days)
        )

        logger.info(
            f"Baseline learning completed: {summary['baselines_updated']} baselines updated "
            f"for {summary['total_interfaces']} interfaces"
        )

        return summary

    except Exception as e:
        logger.error(f"Baseline learning task failed: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


@shared_task(name="monitoring.tasks.check_anomalies", bind=True)
def check_anomalies_task(self):
    """
    Celery task: Check current metrics against baselines for anomaly detection

    Runs every 5 minutes via Celery Beat

    Returns:
        Number of anomalies detected
    """
    logger.info(f"[Task {self.request.id}] Checking for anomalies")

    from database import SessionLocal
    from monitoring.models import DeviceInterface, AlertHistory, AlertSeverity
    from sqlalchemy import select

    db = SessionLocal()
    anomalies_detected = 0

    try:
        # Get current time context
        now = datetime.utcnow()
        hour_of_day = now.hour
        day_of_week = now.weekday()  # 0=Monday

        # Get all critical interfaces
        stmt = select(DeviceInterface).where(
            DeviceInterface.is_critical == True,
            DeviceInterface.enabled == True,
            DeviceInterface.monitoring_enabled == True
        )

        interfaces = db.execute(stmt).scalars().all()

        logger.info(f"Checking {len(interfaces)} critical interfaces for anomalies")

        for interface in interfaces:
            try:
                # Get current traffic rate from VictoriaMetrics
                # TODO: Query VictoriaMetrics for current rate
                current_value = 0.0  # Placeholder

                # Detect anomaly
                anomaly = asyncio.run(
                    baseline_learning.detect_anomaly(
                        str(interface.id),
                        current_value,
                        hour_of_day,
                        day_of_week
                    )
                )

                if anomaly and anomaly.is_anomaly:
                    # Check if alert already exists
                    existing_alert = db.execute(
                        select(AlertHistory).where(
                            AlertHistory.device_id == interface.device_id,
                            AlertHistory.message.like(f"%{interface.if_name}%anomaly%"),
                            AlertHistory.resolved_at.is_(None)
                        )
                    ).scalar_one_or_none()

                    if not existing_alert:
                        # Create anomaly alert
                        severity_map = {
                            'critical': AlertSeverity.CRITICAL,
                            'high': AlertSeverity.HIGH,
                            'medium': AlertSeverity.MEDIUM,
                            'low': AlertSeverity.LOW
                        }

                        alert = AlertHistory(
                            device_id=interface.device_id,
                            severity=severity_map.get(anomaly.severity, AlertSeverity.MEDIUM),
                            message=f"Interface {interface.if_name}: {anomaly.message}",
                            value=str(anomaly.current_value),
                            triggered_at=datetime.utcnow()
                        )

                        db.add(alert)
                        anomalies_detected += 1

                        logger.warning(f"ANOMALY DETECTED: {alert.message}")

            except Exception as e:
                logger.error(f"Failed to check anomaly for interface {interface.id}: {str(e)}")
                continue

        db.commit()

        logger.info(f"Anomaly check completed: {anomalies_detected} anomalies detected")

        return {
            'success': True,
            'anomalies_detected': anomalies_detected,
            'interfaces_checked': len(interfaces),
            'completed_at': datetime.utcnow().isoformat()
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Anomaly check task failed: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'anomalies_detected': anomalies_detected
        }
    finally:
        db.close()
