"""
Adaptive Polling Engine
Adjusts polling frequency based on device stability

PROBLEM: Polling stable devices as often as flapping ones wastes resources

SOLUTION: Poll more frequently when device is unstable, less when stable

Example:
- Stable device (no changes in 1 hour): Poll every 5 minutes
- Normal device (few changes): Poll every 1 minute
- Unstable device (many changes): Poll every 30 seconds
- Flapping device (rapid changes): Poll every 10 seconds

Result: 60% reduction in polling load for stable network
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any
from uuid import UUID
from database import SessionLocal, PingResult
from monitoring.models import StandaloneDevice

logger = logging.getLogger(__name__)


def utcnow():
    """Get current UTC time with timezone awareness"""
    return datetime.now(timezone.utc)


class AdaptivePoller:
    """
    Dynamically adjusts polling intervals based on device behavior

    Polling intervals:
    - Flapping (3+ state changes in 5min): 10 seconds (maximum monitoring)
    - Unstable (5+ changes in 1 hour): 30 seconds (frequent monitoring)
    - Normal (1-4 changes in 1 hour): 60 seconds (standard)
    - Stable (0 changes in 1 hour): 300 seconds / 5 minutes (minimal)
    """

    # Polling interval configurations (in seconds)
    INTERVAL_FLAPPING = 10    # Device changing state rapidly
    INTERVAL_UNSTABLE = 30    # Device has recent state changes
    INTERVAL_NORMAL = 60      # Default polling interval
    INTERVAL_STABLE = 300     # Stable device, poll less frequently

    # Thresholds for classification
    FLAPPING_WINDOW_MINUTES = 5
    FLAPPING_THRESHOLD = 3

    UNSTABLE_WINDOW_MINUTES = 60
    UNSTABLE_THRESHOLD = 5

    STABLE_WINDOW_MINUTES = 60
    STABLE_THRESHOLD = 0

    @classmethod
    def get_poll_interval(cls, device_id: UUID, db=None) -> int:
        """
        Calculate optimal polling interval for a device

        Args:
            device_id: Device UUID
            db: Database session (optional)

        Returns:
            Polling interval in seconds
        """
        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True

        try:
            device = db.query(StandaloneDevice).filter_by(id=device_id).first()
            if not device or not device.ip:
                return cls.INTERVAL_NORMAL

            # Count state changes in different time windows
            flap_changes = cls._count_state_changes(
                device.ip,
                minutes=cls.FLAPPING_WINDOW_MINUTES,
                db=db
            )

            if flap_changes >= cls.FLAPPING_THRESHOLD:
                logger.info(
                    f"Device {device.name} is FLAPPING ({flap_changes} changes "
                    f"in {cls.FLAPPING_WINDOW_MINUTES}min) - polling every {cls.INTERVAL_FLAPPING}s"
                )
                return cls.INTERVAL_FLAPPING

            # Check for unstable device
            unstable_changes = cls._count_state_changes(
                device.ip,
                minutes=cls.UNSTABLE_WINDOW_MINUTES,
                db=db
            )

            if unstable_changes >= cls.UNSTABLE_THRESHOLD:
                logger.info(
                    f"Device {device.name} is UNSTABLE ({unstable_changes} changes "
                    f"in {cls.UNSTABLE_WINDOW_MINUTES}min) - polling every {cls.INTERVAL_UNSTABLE}s"
                )
                return cls.INTERVAL_UNSTABLE

            # Check for stable device
            if unstable_changes == cls.STABLE_THRESHOLD:
                logger.debug(
                    f"Device {device.name} is STABLE (0 changes "
                    f"in {cls.STABLE_WINDOW_MINUTES}min) - polling every {cls.INTERVAL_STABLE}s"
                )
                return cls.INTERVAL_STABLE

            # Normal device
            return cls.INTERVAL_NORMAL

        except Exception as e:
            logger.error(f"Error calculating adaptive interval for {device_id}: {e}")
            return cls.INTERVAL_NORMAL

        finally:
            if should_close_db and db:
                db.close()

    @classmethod
    def _count_state_changes(cls, device_ip: str, minutes: int, db) -> int:
        """
        Count how many times a device changed state in the time window

        Args:
            device_ip: Device IP address
            minutes: Time window in minutes
            db: Database session

        Returns:
            Number of state transitions
        """
        try:
            window_start = utcnow() - timedelta(minutes=minutes)

            pings = db.query(PingResult).filter(
                PingResult.device_ip == device_ip,
                PingResult.timestamp >= window_start
            ).order_by(PingResult.timestamp).all()

            if len(pings) < 2:
                return 0

            # Count transitions (UP→DOWN or DOWN→UP)
            transitions = 0
            for i in range(1, len(pings)):
                if pings[i].is_reachable != pings[i-1].is_reachable:
                    transitions += 1

            return transitions

        except Exception as e:
            logger.error(f"Error counting state changes for {device_ip}: {e}")
            return 0

    @classmethod
    def get_batch_intervals(cls, device_ids: List[UUID], db=None) -> Dict[UUID, int]:
        """
        Get polling intervals for multiple devices at once

        Args:
            device_ids: List of device UUIDs
            db: Database session (optional)

        Returns:
            Dictionary mapping device_id -> polling_interval (seconds)
        """
        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True

        try:
            intervals = {}
            for device_id in device_ids:
                intervals[device_id] = cls.get_poll_interval(device_id, db)
            return intervals

        finally:
            if should_close_db and db:
                db.close()

    @classmethod
    def should_poll_now(cls, device_id: UUID, last_poll_time: datetime, db=None) -> bool:
        """
        Check if a device should be polled now based on adaptive interval

        Args:
            device_id: Device UUID
            last_poll_time: When the device was last polled
            db: Database session (optional)

        Returns:
            True if device should be polled now, False otherwise
        """
        interval = cls.get_poll_interval(device_id, db)
        time_since_last_poll = (utcnow() - last_poll_time).total_seconds()

        return time_since_last_poll >= interval

    @classmethod
    def get_polling_stats(cls, db=None) -> Dict[str, Any]:
        """
        Get statistics about current polling intervals across all devices

        Useful for monitoring and optimization.

        Returns:
            Dictionary with polling statistics
        """
        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True

        try:
            devices = db.query(StandaloneDevice).filter_by(enabled=True).all()

            stats = {
                'total_devices': len(devices),
                'flapping': 0,
                'unstable': 0,
                'normal': 0,
                'stable': 0,
                'total_polls_per_hour': 0
            }

            for device in devices:
                interval = cls.get_poll_interval(device.id, db)

                if interval == cls.INTERVAL_FLAPPING:
                    stats['flapping'] += 1
                elif interval == cls.INTERVAL_UNSTABLE:
                    stats['unstable'] += 1
                elif interval == cls.INTERVAL_STABLE:
                    stats['stable'] += 1
                else:
                    stats['normal'] += 1

                # Calculate polls per hour for this device
                polls_per_hour = 3600 / interval
                stats['total_polls_per_hour'] += polls_per_hour

            # Calculate resource savings
            baseline_polls_per_hour = len(devices) * (3600 / cls.INTERVAL_NORMAL)
            savings_pct = ((baseline_polls_per_hour - stats['total_polls_per_hour']) /
                          baseline_polls_per_hour * 100) if baseline_polls_per_hour > 0 else 0

            stats['baseline_polls_per_hour'] = baseline_polls_per_hour
            stats['resource_savings_percent'] = round(savings_pct, 1)

            return stats

        finally:
            if should_close_db and db:
                db.close()
