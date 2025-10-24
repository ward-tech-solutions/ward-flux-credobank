"""
Flapping Detection Engine
Prevents alert storms when devices rapidly change state (UP→DOWN→UP)

A device is considered "flapping" when it changes state 3+ times in 5 minutes.
This prevents creating 10+ alerts for a single unstable device.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from database import SessionLocal, PingResult
from monitoring.models import StandaloneDevice

logger = logging.getLogger(__name__)


def utcnow():
    """Get current UTC time with timezone awareness"""
    return datetime.now(timezone.utc)


class FlappingDetector:
    """
    Detects devices that are rapidly changing state (flapping)

    A flapping device is one that changes state (UP↔DOWN) multiple times
    in a short period, indicating network instability rather than a real outage.

    Configuration:
    - Detection window: 5 minutes
    - Threshold: 3+ state transitions
    - Suppression period: 10 minutes after last flap
    """

    # Configuration
    DETECTION_WINDOW_MINUTES = 5
    TRANSITION_THRESHOLD = 3
    SUPPRESSION_PERIOD_MINUTES = 10

    @classmethod
    def is_flapping(cls, device_id: UUID, db=None) -> bool:
        """
        Check if a device is currently flapping

        Args:
            device_id: Device UUID to check
            db: Database session (optional, will create if not provided)

        Returns:
            True if device is flapping, False otherwise
        """
        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True

        try:
            # Get device
            device = db.query(StandaloneDevice).filter_by(id=device_id).first()
            if not device or not device.ip:
                return False

            # Get recent ping results
            detection_window_start = utcnow() - timedelta(minutes=cls.DETECTION_WINDOW_MINUTES)

            recent_pings = db.query(PingResult).filter(
                PingResult.device_ip == device.ip,
                PingResult.timestamp >= detection_window_start
            ).order_by(PingResult.timestamp).all()

            if len(recent_pings) < 3:
                # Not enough data to detect flapping
                return False

            # Count state transitions (UP→DOWN or DOWN→UP)
            transitions = 0
            for i in range(1, len(recent_pings)):
                previous_state = recent_pings[i-1].is_reachable
                current_state = recent_pings[i].is_reachable

                if previous_state != current_state:
                    transitions += 1

            is_flapping = transitions >= cls.TRANSITION_THRESHOLD

            if is_flapping:
                logger.warning(
                    f"Device {device.name} ({device.ip}) is FLAPPING: "
                    f"{transitions} state transitions in {cls.DETECTION_WINDOW_MINUTES} minutes"
                )

            return is_flapping

        except Exception as e:
            logger.error(f"Error detecting flapping for device {device_id}: {e}")
            return False

        finally:
            if should_close_db and db:
                db.close()

    @classmethod
    def get_flapping_details(cls, device_id: UUID, db=None) -> Optional[dict]:
        """
        Get detailed flapping information for a device

        Returns:
            Dictionary with flapping details or None if not flapping
            {
                'is_flapping': bool,
                'transition_count': int,
                'detection_window_minutes': int,
                'state_changes': list[dict],  # List of state changes
                'suppression_recommended': bool
            }
        """
        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True

        try:
            device = db.query(StandaloneDevice).filter_by(id=device_id).first()
            if not device or not device.ip:
                return None

            detection_window_start = utcnow() - timedelta(minutes=cls.DETECTION_WINDOW_MINUTES)

            recent_pings = db.query(PingResult).filter(
                PingResult.device_ip == device.ip,
                PingResult.timestamp >= detection_window_start
            ).order_by(PingResult.timestamp).all()

            if len(recent_pings) < 3:
                return None

            # Track state changes
            state_changes = []
            transitions = 0

            for i in range(1, len(recent_pings)):
                previous_state = recent_pings[i-1].is_reachable
                current_state = recent_pings[i].is_reachable

                if previous_state != current_state:
                    transitions += 1
                    state_changes.append({
                        'timestamp': recent_pings[i].timestamp,
                        'previous_state': 'UP' if previous_state else 'DOWN',
                        'current_state': 'UP' if current_state else 'DOWN',
                        'transition_number': transitions
                    })

            is_flapping = transitions >= cls.TRANSITION_THRESHOLD

            return {
                'is_flapping': is_flapping,
                'transition_count': transitions,
                'detection_window_minutes': cls.DETECTION_WINDOW_MINUTES,
                'state_changes': state_changes,
                'suppression_recommended': is_flapping,
                'device_name': device.name,
                'device_ip': device.ip
            }

        except Exception as e:
            logger.error(f"Error getting flapping details for device {device_id}: {e}")
            return None

        finally:
            if should_close_db and db:
                db.close()

    @classmethod
    def should_suppress_alert(cls, device_id: UUID, db=None) -> bool:
        """
        Check if alerts should be suppressed for this device

        This is the main method to use in alert evaluation.
        Returns True if the device is flapping and alerts should be suppressed.

        Args:
            device_id: Device UUID
            db: Database session (optional)

        Returns:
            True if alerts should be suppressed, False otherwise
        """
        return cls.is_flapping(device_id, db)
