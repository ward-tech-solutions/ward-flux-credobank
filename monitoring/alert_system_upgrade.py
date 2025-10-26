"""
COMPREHENSIVE ALERT SYSTEM UPGRADE
Real-time alerting with 10-second detection
ISP Link monitoring for .5 octet IPs
Duplicate removal and optimization
"""

from celery import shared_task
from database import SessionLocal
from monitoring.models import StandaloneDevice, AlertHistory, AlertRule, AlertSeverity
from datetime import datetime, timedelta, timezone
import logging
import uuid
from sqlalchemy import text

logger = logging.getLogger(__name__)

# ISP LINK IPS - All ending with .5 octet
ISP_LINK_PATTERNS = [
    '%.%.%.5',  # Any IP ending with .5
]

# ALERT RULES CONFIGURATION
ALERT_RULES_CONFIG = {
    # DEVICE CONNECTIVITY ALERTS (10-second detection)
    'device_down': {
        'name': 'Device Down',
        'description': 'Device not responding to ping',
        'severity': AlertSeverity.CRITICAL,
        'threshold_seconds': 10,  # Alert after 10 seconds
        'auto_resolve': True,
        'applies_to': 'all_devices'
    },

    'device_flapping': {
        'name': 'Device Flapping',
        'description': 'Device experiencing intermittent connectivity',
        'severity': AlertSeverity.HIGH,
        'threshold_changes': 3,  # 3+ changes in 5 minutes
        'window_minutes': 5,
        'applies_to': 'all_devices'
    },

    # ISP LINK ALERTS (CRITICAL - 10-second detection)
    'isp_link_down': {
        'name': 'ISP Link Down',
        'description': 'Internet service provider link is down',
        'severity': AlertSeverity.CRITICAL,
        'threshold_seconds': 10,  # Alert immediately
        'auto_resolve': True,
        'applies_to': 'isp_links',  # Only .5 IPs
        'priority': 1  # Highest priority
    },

    'isp_link_flapping': {
        'name': 'ISP Link Flapping',
        'description': 'ISP link experiencing intermittent connectivity',
        'severity': AlertSeverity.CRITICAL,  # More severe for ISP links
        'threshold_changes': 2,  # More sensitive - 2 changes trigger alert
        'window_minutes': 5,
        'applies_to': 'isp_links',
        'priority': 1
    },

    # RESPONSE TIME ALERTS
    'high_latency': {
        'name': 'High Latency',
        'description': 'Response time exceeds threshold',
        'severity': AlertSeverity.MEDIUM,
        'threshold_ms': 200,  # Alert if >200ms
        'applies_to': 'all_devices'
    },

    'isp_high_latency': {
        'name': 'ISP Link High Latency',
        'description': 'ISP link latency exceeds threshold',
        'severity': AlertSeverity.HIGH,  # More severe for ISP
        'threshold_ms': 100,  # Stricter threshold for ISP
        'applies_to': 'isp_links',
        'priority': 1
    },

    # PACKET LOSS ALERTS
    'packet_loss': {
        'name': 'Packet Loss Detected',
        'description': 'Device experiencing packet loss',
        'severity': AlertSeverity.MEDIUM,
        'threshold_percent': 10,  # Alert if >10% loss
        'applies_to': 'all_devices'
    },

    'isp_packet_loss': {
        'name': 'ISP Link Packet Loss',
        'description': 'ISP link experiencing packet loss',
        'severity': AlertSeverity.CRITICAL,
        'threshold_percent': 5,  # Stricter for ISP
        'applies_to': 'isp_links',
        'priority': 1
    }
}


def is_isp_link(device_ip):
    """Check if device is an ISP link (IP ends with .5)"""
    return device_ip and device_ip.endswith('.5')


def get_or_create_alert_rule(db, rule_config, device=None):
    """Get or create an alert rule based on configuration"""
    rule_name = rule_config['name']

    # Build expression based on rule type
    if 'threshold_seconds' in rule_config:
        expression = f"down_time > {rule_config['threshold_seconds']}"
    elif 'threshold_changes' in rule_config:
        expression = f"status_changes >= {rule_config['threshold_changes']} in {rule_config['window_minutes']} minutes"
    elif 'threshold_ms' in rule_config:
        expression = f"response_time > {rule_config['threshold_ms']}ms"
    elif 'threshold_percent' in rule_config:
        expression = f"packet_loss > {rule_config['threshold_percent']}%"
    else:
        expression = "custom"

    # Check if rule exists
    query = db.query(AlertRule).filter(AlertRule.name == rule_name)
    if device:
        query = query.filter(AlertRule.device_id == device.id)
    else:
        query = query.filter(AlertRule.device_id.is_(None))

    rule = query.first()

    if not rule:
        # Create new rule
        rule = AlertRule(
            id=uuid.uuid4(),
            name=rule_name,
            description=rule_config['description'],
            expression=expression,
            severity=rule_config['severity'].value,
            device_id=device.id if device else None,
            enabled=True
        )
        db.add(rule)
        logger.info(f"Created alert rule: {rule_name}")

    return rule


@shared_task(name="monitoring.alert_system.evaluate_alerts")
def evaluate_alerts():
    """
    Evaluate all alert rules every 10 seconds
    This provides near real-time alerting
    """
    db = None
    try:
        db = SessionLocal()

        # Get all enabled devices
        devices = db.query(StandaloneDevice).filter(StandaloneDevice.enabled == True).all()

        for device in devices:
            # Determine if this is an ISP link
            is_isp = is_isp_link(device.ip)

            # DEVICE DOWN ALERTS (10-second detection)
            if device.down_since:
                down_duration = (datetime.now(timezone.utc) - device.down_since).total_seconds()

                if down_duration >= 10:  # Alert after 10 seconds
                    # Check if alert already exists
                    existing_alert = db.query(AlertHistory).filter(
                        AlertHistory.device_id == device.id,
                        AlertHistory.rule_name == ('ISP Link Down' if is_isp else 'Device Down'),
                        AlertHistory.resolved_at.is_(None)
                    ).first()

                    if not existing_alert:
                        # Create alert
                        severity = AlertSeverity.CRITICAL if is_isp else AlertSeverity.HIGH
                        alert = AlertHistory(
                            id=uuid.uuid4(),
                            device_id=device.id,
                            rule_name='ISP Link Down' if is_isp else 'Device Down',
                            severity=severity,
                            message=f"{'ISP Link' if is_isp else 'Device'} {device.name} ({device.ip}) is DOWN for {int(down_duration)} seconds",
                            value="DOWN",
                            threshold="10 seconds",
                            triggered_at=datetime.now(timezone.utc),
                            acknowledged=False,
                            notifications_sent=[]
                        )
                        db.add(alert)
                        logger.critical(f"🚨 {'ISP LINK' if is_isp else 'DEVICE'} DOWN: {device.name} ({device.ip})")

            # FLAPPING ALERTS (with different sensitivity for ISP links)
            if device.is_flapping:
                # Check if flapping alert exists
                existing_alert = db.query(AlertHistory).filter(
                    AlertHistory.device_id == device.id,
                    AlertHistory.rule_name == ('ISP Link Flapping' if is_isp else 'Device Flapping'),
                    AlertHistory.resolved_at.is_(None)
                ).first()

                if not existing_alert:
                    severity = AlertSeverity.CRITICAL if is_isp else AlertSeverity.HIGH
                    alert = AlertHistory(
                        id=uuid.uuid4(),
                        device_id=device.id,
                        rule_name='ISP Link Flapping' if is_isp else 'Device Flapping',
                        severity=severity,
                        message=f"{'ISP Link' if is_isp else 'Device'} {device.name} ({device.ip}) is flapping - {device.flap_count} changes",
                        value=str(device.flap_count),
                        threshold="3" if not is_isp else "2",
                        triggered_at=datetime.now(timezone.utc),
                        acknowledged=False,
                        notifications_sent=[]
                    )
                    db.add(alert)
                    logger.warning(f"⚠️ {'ISP LINK' if is_isp else 'Device'} FLAPPING: {device.name} ({device.ip})")

            # AUTO-RESOLVE ALERTS when device recovers
            if not device.down_since:  # Device is UP
                # Resolve any DOWN alerts
                down_alerts = db.query(AlertHistory).filter(
                    AlertHistory.device_id == device.id,
                    AlertHistory.rule_name.in_(['Device Down', 'ISP Link Down']),
                    AlertHistory.resolved_at.is_(None)
                ).all()

                for alert in down_alerts:
                    alert.resolved_at = datetime.now(timezone.utc)
                    logger.info(f"✅ Resolved: {alert.rule_name} for {device.name}")

            # Resolve flapping alerts when device stabilizes
            if not device.is_flapping:
                flapping_alerts = db.query(AlertHistory).filter(
                    AlertHistory.device_id == device.id,
                    AlertHistory.rule_name.in_(['Device Flapping', 'ISP Link Flapping']),
                    AlertHistory.resolved_at.is_(None)
                ).all()

                for alert in flapping_alerts:
                    alert.resolved_at = datetime.now(timezone.utc)
                    logger.info(f"✅ Resolved: {alert.rule_name} for {device.name}")

        db.commit()

        # Return summary
        active_alerts = db.query(AlertHistory).filter(
            AlertHistory.resolved_at.is_(None)
        ).count()

        isp_alerts = db.query(AlertHistory).filter(
            AlertHistory.resolved_at.is_(None),
            AlertHistory.rule_name.like('ISP%')
        ).count()

        return {
            'evaluated_devices': len(devices),
            'active_alerts': active_alerts,
            'isp_alerts': isp_alerts
        }

    except Exception as e:
        logger.error(f"Error evaluating alerts: {e}", exc_info=True)
        if db:
            db.rollback()
        raise
    finally:
        if db:
            db.close()


@shared_task(name="monitoring.alert_system.cleanup_duplicates")
def cleanup_duplicate_alerts():
    """Remove duplicate alert rules and consolidate alerts"""
    db = None
    try:
        db = SessionLocal()

        # Find and remove duplicate alert rules
        duplicates_removed = 0

        # Get all rules grouped by name
        result = db.execute(text("""
            SELECT name, COUNT(*) as count, array_agg(id) as ids
            FROM alert_rules
            GROUP BY name
            HAVING COUNT(*) > 1
        """))

        for row in result:
            rule_name, count, ids = row
            # Keep the first, delete the rest
            for rule_id in ids[1:]:
                db.execute(text("DELETE FROM alert_rules WHERE id = :id"), {'id': rule_id})
                duplicates_removed += 1
                logger.info(f"Removed duplicate rule: {rule_name} (ID: {rule_id})")

        # Remove old unresolved alerts for devices that are now UP
        old_alerts_removed = 0
        stale_alerts = db.query(AlertHistory).filter(
            AlertHistory.resolved_at.is_(None),
            AlertHistory.triggered_at < datetime.now(timezone.utc) - timedelta(hours=24)
        ).all()

        for alert in stale_alerts:
            # Check if device is actually UP
            device = db.query(StandaloneDevice).filter(
                StandaloneDevice.id == alert.device_id
            ).first()

            if device and not device.down_since:
                alert.resolved_at = datetime.now(timezone.utc)
                old_alerts_removed += 1
                logger.info(f"Auto-resolved stale alert: {alert.rule_name} for device {device.name}")

        db.commit()

        return {
            'duplicates_removed': duplicates_removed,
            'stale_alerts_resolved': old_alerts_removed
        }

    except Exception as e:
        logger.error(f"Error cleaning up alerts: {e}")
        if db:
            db.rollback()
        raise
    finally:
        if db:
            db.close()


def get_isp_links(db):
    """Get all ISP link devices (IPs ending with .5)"""
    return db.query(StandaloneDevice).filter(
        StandaloneDevice.enabled == True,
        StandaloneDevice.ip.like('%.5')
    ).all()


def get_alert_statistics(db):
    """Get comprehensive alert statistics"""
    stats = {
        'total_devices': db.query(StandaloneDevice).filter(StandaloneDevice.enabled == True).count(),
        'isp_links': db.query(StandaloneDevice).filter(
            StandaloneDevice.enabled == True,
            StandaloneDevice.ip.like('%.5')
        ).count(),
        'devices_down': db.query(StandaloneDevice).filter(
            StandaloneDevice.down_since.isnot(None)
        ).count(),
        'devices_flapping': db.query(StandaloneDevice).filter(
            StandaloneDevice.is_flapping == True
        ).count(),
        'active_alerts': db.query(AlertHistory).filter(
            AlertHistory.resolved_at.is_(None)
        ).count(),
        'critical_alerts': db.query(AlertHistory).filter(
            AlertHistory.resolved_at.is_(None),
            AlertHistory.severity == AlertSeverity.CRITICAL
        ).count(),
        'isp_alerts': db.query(AlertHistory).filter(
            AlertHistory.resolved_at.is_(None),
            AlertHistory.rule_name.like('ISP%')
        ).count()
    }
    return stats