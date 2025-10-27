"""
FIXED Alert Evaluation System
Removes SQL-like expressions that cause parsing errors
Direct Python logic for ISP link detection
"""

from celery import shared_task
from database import SessionLocal
from monitoring.models import StandaloneDevice, AlertHistory
from datetime import datetime, timedelta, timezone
import logging
import uuid

logger = logging.getLogger(__name__)

# Alert severity levels (matching database enum)
class AlertSeverity:
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


def is_isp_link(device):
    """Check if device is an ISP link (IP ends with .5)"""
    return device.ip and device.ip.endswith('.5')


def evaluate_device_alerts(device, db):
    """
    Evaluate all alert conditions for a single device
    Returns list of alerts to create
    """
    alerts_to_create = []
    is_isp = is_isp_link(device)

    # 1. DOWN ALERTS (10-second detection)
    if device.down_since:
        down_duration = (datetime.now(timezone.utc) - device.down_since).total_seconds()

        if down_duration >= 10:  # Alert after 10 seconds
            alert_name = 'ISP Link Down' if is_isp else 'Device Down'

            # Check if alert already exists
            existing = db.query(AlertHistory).filter(
                AlertHistory.device_id == device.id,
                AlertHistory.rule_name == alert_name,
                AlertHistory.resolved_at.is_(None)
            ).first()

            if not existing:
                alerts_to_create.append({
                    'rule_name': alert_name,
                    'severity': AlertSeverity.CRITICAL,
                    'message': f"{'ISP Link' if is_isp else 'Device'} {device.name} ({device.ip}) is DOWN for {int(down_duration)} seconds",
                    'value': "DOWN",
                    'threshold': "10 seconds"
                })

    # 2. FLAPPING ALERTS
    if device.is_flapping and device.flap_count:
        # ISP links are more sensitive - alert on 2+ changes
        # Regular devices alert on 3+ changes
        threshold = 2 if is_isp else 3

        if device.flap_count >= threshold:
            alert_name = 'ISP Link Flapping' if is_isp else 'Device Flapping'

            existing = db.query(AlertHistory).filter(
                AlertHistory.device_id == device.id,
                AlertHistory.rule_name == alert_name,
                AlertHistory.resolved_at.is_(None)
            ).first()

            if not existing:
                alerts_to_create.append({
                    'rule_name': alert_name,
                    'severity': AlertSeverity.CRITICAL if is_isp else AlertSeverity.HIGH,
                    'message': f"{'ISP Link' if is_isp else 'Device'} {device.name} ({device.ip}) is flapping - {device.flap_count} changes in 5 minutes",
                    'value': str(device.flap_count),
                    'threshold': f"{threshold} changes"
                })

    # 3. LATENCY ALERTS (only for UP devices)
    if not device.down_since and device.response_time_ms:
        # ISP links have stricter threshold (100ms) vs regular (200ms)
        threshold_ms = 100 if is_isp else 200

        if device.response_time_ms > threshold_ms:
            alert_name = 'ISP Link High Latency' if is_isp else 'High Latency'

            existing = db.query(AlertHistory).filter(
                AlertHistory.device_id == device.id,
                AlertHistory.rule_name == alert_name,
                AlertHistory.resolved_at.is_(None)
            ).first()

            if not existing:
                alerts_to_create.append({
                    'rule_name': alert_name,
                    'severity': AlertSeverity.HIGH if is_isp else AlertSeverity.MEDIUM,
                    'message': f"{'ISP Link' if is_isp else 'Device'} {device.name} ({device.ip}) latency is {device.response_time_ms:.1f}ms (threshold: {threshold_ms}ms)",
                    'value': f"{device.response_time_ms:.1f}ms",
                    'threshold': f"{threshold_ms}ms"
                })

    # 4. PACKET LOSS ALERTS (if we track packet loss)
    if hasattr(device, 'packet_loss_percent') and device.packet_loss_percent is not None:
        # ISP links have stricter threshold (5%) vs regular (10%)
        threshold_percent = 5 if is_isp else 10

        if device.packet_loss_percent > threshold_percent:
            alert_name = 'ISP Link Packet Loss' if is_isp else 'Packet Loss Detected'

            existing = db.query(AlertHistory).filter(
                AlertHistory.device_id == device.id,
                AlertHistory.rule_name == alert_name,
                AlertHistory.resolved_at.is_(None)
            ).first()

            if not existing:
                alerts_to_create.append({
                    'rule_name': alert_name,
                    'severity': AlertSeverity.CRITICAL if is_isp else AlertSeverity.MEDIUM,
                    'message': f"{'ISP Link' if is_isp else 'Device'} {device.name} ({device.ip}) packet loss is {device.packet_loss_percent}% (threshold: {threshold_percent}%)",
                    'value': f"{device.packet_loss_percent}%",
                    'threshold': f"{threshold_percent}%"
                })

    return alerts_to_create


def auto_resolve_alerts(device, db):
    """
    Auto-resolve alerts when conditions no longer apply
    """
    resolved_count = 0

    # 1. Resolve DOWN alerts when device is UP
    if not device.down_since:
        down_alerts = db.query(AlertHistory).filter(
            AlertHistory.device_id == device.id,
            AlertHistory.rule_name.in_(['Device Down', 'ISP Link Down']),
            AlertHistory.resolved_at.is_(None)
        ).all()

        for alert in down_alerts:
            alert.resolved_at = datetime.now(timezone.utc)
            resolved_count += 1
            logger.info(f"✅ Auto-resolved: {alert.rule_name} for {device.name}")

    # 2. Resolve FLAPPING alerts when device stabilizes
    if not device.is_flapping:
        flapping_alerts = db.query(AlertHistory).filter(
            AlertHistory.device_id == device.id,
            AlertHistory.rule_name.in_(['Device Flapping', 'ISP Link Flapping']),
            AlertHistory.resolved_at.is_(None)
        ).all()

        for alert in flapping_alerts:
            alert.resolved_at = datetime.now(timezone.utc)
            resolved_count += 1
            logger.info(f"✅ Auto-resolved: {alert.rule_name} for {device.name}")

    # 3. Resolve LATENCY alerts when response time normalizes
    if device.response_time_ms:
        is_isp = is_isp_link(device)
        threshold_ms = 100 if is_isp else 200

        if device.response_time_ms <= threshold_ms:
            latency_alerts = db.query(AlertHistory).filter(
                AlertHistory.device_id == device.id,
                AlertHistory.rule_name.in_(['High Latency', 'ISP Link High Latency']),
                AlertHistory.resolved_at.is_(None)
            ).all()

            for alert in latency_alerts:
                alert.resolved_at = datetime.now(timezone.utc)
                resolved_count += 1
                logger.info(f"✅ Auto-resolved: {alert.rule_name} for {device.name}")

    return resolved_count


@shared_task(name="monitoring.alert_evaluator.evaluate_all_alerts")
def evaluate_all_alerts():
    """
    Main alert evaluation task - runs every 10 seconds
    This provides near real-time alerting without SQL expression parsing
    """
    db = None
    try:
        db = SessionLocal()

        # Statistics
        stats = {
            'devices_evaluated': 0,
            'alerts_created': 0,
            'alerts_resolved': 0,
            'isp_links_evaluated': 0,
            'errors': 0
        }

        # Get all enabled devices
        devices = db.query(StandaloneDevice).filter(
            StandaloneDevice.enabled == True
        ).all()

        for device in devices:
            try:
                stats['devices_evaluated'] += 1

                if is_isp_link(device):
                    stats['isp_links_evaluated'] += 1

                # Evaluate alerts for this device
                alerts_to_create = evaluate_device_alerts(device, db)

                # Create new alerts
                for alert_data in alerts_to_create:
                    alert = AlertHistory(
                        id=uuid.uuid4(),
                        device_id=device.id,
                        rule_name=alert_data['rule_name'],
                        severity=alert_data['severity'],
                        message=alert_data['message'],
                        value=alert_data['value'],
                        threshold=alert_data['threshold'],
                        triggered_at=datetime.now(timezone.utc),
                        acknowledged=False,
                        notifications_sent=[]
                    )
                    db.add(alert)
                    stats['alerts_created'] += 1

                    # Log critical alerts
                    if alert_data['severity'] == AlertSeverity.CRITICAL:
                        logger.critical(f"🚨 CRITICAL ALERT: {alert_data['message']}")
                    else:
                        logger.warning(f"⚠️ ALERT: {alert_data['message']}")

                # Auto-resolve alerts that no longer apply
                resolved = auto_resolve_alerts(device, db)
                stats['alerts_resolved'] += resolved

            except Exception as e:
                stats['errors'] += 1
                logger.error(f"Error evaluating alerts for device {device.name}: {e}")
                continue

        # Commit all changes
        db.commit()

        # Get summary of active alerts
        active_alerts = db.query(AlertHistory).filter(
            AlertHistory.resolved_at.is_(None)
        ).count()

        critical_alerts = db.query(AlertHistory).filter(
            AlertHistory.resolved_at.is_(None),
            AlertHistory.severity == AlertSeverity.CRITICAL
        ).count()

        isp_alerts = db.query(AlertHistory).filter(
            AlertHistory.resolved_at.is_(None),
            AlertHistory.rule_name.like('ISP%')
        ).count()

        logger.info(
            f"📊 Alert Evaluation Complete: "
            f"Evaluated={stats['devices_evaluated']} devices "
            f"(ISP={stats['isp_links_evaluated']}), "
            f"Created={stats['alerts_created']}, "
            f"Resolved={stats['alerts_resolved']}, "
            f"Active={active_alerts} (Critical={critical_alerts}, ISP={isp_alerts}), "
            f"Errors={stats['errors']}"
        )

        return {
            **stats,
            'active_alerts': active_alerts,
            'critical_alerts': critical_alerts,
            'isp_alerts': isp_alerts
        }

    except Exception as e:
        logger.error(f"Fatal error in alert evaluation: {e}", exc_info=True)
        if db:
            db.rollback()
        raise
    finally:
        if db:
            db.close()


@shared_task(name="monitoring.alert_evaluator.cleanup_stale_alerts")
def cleanup_stale_alerts():
    """
    Clean up stale alerts that should have been auto-resolved
    Runs hourly to ensure consistency
    """
    db = None
    try:
        db = SessionLocal()
        cleaned = 0

        # Find alerts older than 24 hours that are still open
        stale_alerts = db.query(AlertHistory).filter(
            AlertHistory.resolved_at.is_(None),
            AlertHistory.triggered_at < datetime.now(timezone.utc) - timedelta(hours=24)
        ).all()

        for alert in stale_alerts:
            # Verify if device state matches alert
            device = db.query(StandaloneDevice).filter(
                StandaloneDevice.id == alert.device_id
            ).first()

            if device:
                should_resolve = False

                # Check DOWN alerts
                if alert.rule_name in ['Device Down', 'ISP Link Down']:
                    if not device.down_since:
                        should_resolve = True

                # Check FLAPPING alerts
                elif alert.rule_name in ['Device Flapping', 'ISP Link Flapping']:
                    if not device.is_flapping:
                        should_resolve = True

                if should_resolve:
                    alert.resolved_at = datetime.now(timezone.utc)
                    cleaned += 1
                    logger.info(f"🧹 Cleaned stale alert: {alert.rule_name} for {device.name}")

        db.commit()
        logger.info(f"Stale alert cleanup complete: {cleaned} alerts resolved")

        return {'stale_alerts_cleaned': cleaned}

    except Exception as e:
        logger.error(f"Error cleaning stale alerts: {e}")
        if db:
            db.rollback()
        raise
    finally:
        if db:
            db.close()