"""
Alert Deduplication Engine
Prevents creating multiple alerts for the same problem

Problem: Device goes down triggers 3 rules:
- ping_unreachable >= 1 (immediate)
- ping_unreachable >= 2 (2 minutes)
- ping_unreachable >= 5 (5 minutes)

Result: 3 alerts for ONE problem!

Solution: Only create highest-severity alert, suppress duplicates
"""

import logging
from typing import Optional, List
from uuid import UUID
from database import SessionLocal
from monitoring.models import AlertHistory, AlertSeverity

logger = logging.getLogger(__name__)


class AlertDeduplicator:
    """
    Prevents duplicate alerts for the same problem

    When multiple alert rules match the same device issue, only the
    highest-severity alert is created, and lower-severity duplicates
    are suppressed.
    """

    # Alert rule priority (higher = more severe, keep this one)
    SEVERITY_PRIORITY = {
        AlertSeverity.CRITICAL: 4,
        AlertSeverity.HIGH: 3,
        AlertSeverity.MEDIUM: 2,
        AlertSeverity.LOW: 1,
        AlertSeverity.INFO: 0,
    }

    # Related alert rule groups (alerts in same group are duplicates)
    ALERT_GROUPS = {
        'device_unreachable': [
            'Ping Unavailable',
            'Device Down - High Priority',
            'Device Down - Critical',
            'Device Unreachable',
        ],
        'high_latency': [
            'High Latency',
            'Network Performance Degraded',
        ],
        'packet_loss': [
            'High Packet Loss',
            'Network Quality Issues',
        ]
    }

    @classmethod
    def should_create_alert(
        cls,
        device_id: UUID,
        rule_name: str,
        severity: AlertSeverity,
        db=None
    ) -> bool:
        """
        Check if we should create this alert or suppress it as duplicate

        Args:
            device_id: Device UUID
            rule_name: Name of the alert rule
            severity: Severity of the new alert
            db: Database session (optional)

        Returns:
            True if alert should be created, False if it's a duplicate
        """
        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True

        try:
            # Find which group this alert belongs to
            alert_group = cls._get_alert_group(rule_name)
            if not alert_group:
                # Not in any group, always create
                return True

            # Get related rule names in same group
            related_rules = cls.ALERT_GROUPS[alert_group]

            # Check for existing active alerts in same group
            existing_alerts = db.query(AlertHistory).filter(
                AlertHistory.device_id == device_id,
                AlertHistory.rule_name.in_(related_rules),
                AlertHistory.resolved_at.is_(None)  # Only active alerts
            ).all()

            if not existing_alerts:
                # No existing alerts in this group, create this one
                return True

            # Compare severity with existing alerts
            new_alert_priority = cls.SEVERITY_PRIORITY.get(severity, 0)

            for existing in existing_alerts:
                existing_priority = cls.SEVERITY_PRIORITY.get(existing.severity, 0)

                if existing_priority >= new_alert_priority:
                    # Higher or equal severity alert already exists
                    logger.info(
                        f"Suppressing duplicate alert '{rule_name}' ({severity}) - "
                        f"already have '{existing.rule_name}' ({existing.severity})"
                    )
                    return False

            # This alert is higher severity than existing ones
            # We should create it (and potentially resolve lower-severity ones)
            logger.info(
                f"Creating higher-severity alert '{rule_name}' ({severity}) - "
                f"will supersede {len(existing_alerts)} lower-severity alert(s)"
            )
            return True

        except Exception as e:
            logger.error(f"Error in alert deduplication: {e}")
            # On error, allow alert to be created (fail-safe)
            return True

        finally:
            if should_close_db and db:
                db.close()

    @classmethod
    def _get_alert_group(cls, rule_name: str) -> Optional[str]:
        """Find which group this alert rule belongs to"""
        for group_name, rules in cls.ALERT_GROUPS.items():
            if rule_name in rules:
                return group_name
        return None

    @classmethod
    def resolve_lower_severity_alerts(
        cls,
        device_id: UUID,
        new_rule_name: str,
        new_severity: AlertSeverity,
        db=None
    ) -> int:
        """
        Resolve any lower-severity alerts when a higher-severity alert is created

        Args:
            device_id: Device UUID
            new_rule_name: Name of the new alert rule
            new_severity: Severity of the new alert
            db: Database session (optional)

        Returns:
            Number of alerts resolved
        """
        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True

        try:
            # Find which group this alert belongs to
            alert_group = cls._get_alert_group(new_rule_name)
            if not alert_group:
                return 0

            # Get related rule names
            related_rules = cls.ALERT_GROUPS[alert_group]

            # Find lower-severity active alerts
            new_priority = cls.SEVERITY_PRIORITY.get(new_severity, 0)

            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)

            resolved_count = 0

            existing_alerts = db.query(AlertHistory).filter(
                AlertHistory.device_id == device_id,
                AlertHistory.rule_name.in_(related_rules),
                AlertHistory.resolved_at.is_(None)
            ).all()

            for alert in existing_alerts:
                alert_priority = cls.SEVERITY_PRIORITY.get(alert.severity, 0)

                if alert_priority < new_priority:
                    # This is a lower-severity alert, resolve it
                    alert.resolved_at = now
                    resolved_count += 1
                    logger.info(
                        f"Auto-resolved lower-severity alert '{alert.rule_name}' "
                        f"(superseded by '{new_rule_name}')"
                    )

            if resolved_count > 0:
                db.commit()

            return resolved_count

        except Exception as e:
            logger.error(f"Error resolving lower-severity alerts: {e}")
            if db:
                db.rollback()
            return 0

        finally:
            if should_close_db and db:
                db.close()

    @classmethod
    def get_duplicate_count(cls, device_id: UUID, rule_name: str, db=None) -> int:
        """
        Get count of active duplicate alerts for this device/rule

        Useful for debugging and metrics.
        """
        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True

        try:
            alert_group = cls._get_alert_group(rule_name)
            if not alert_group:
                return 0

            related_rules = cls.ALERT_GROUPS[alert_group]

            count = db.query(AlertHistory).filter(
                AlertHistory.device_id == device_id,
                AlertHistory.rule_name.in_(related_rules),
                AlertHistory.resolved_at.is_(None)
            ).count()

            return count

        finally:
            if should_close_db and db:
                db.close()
