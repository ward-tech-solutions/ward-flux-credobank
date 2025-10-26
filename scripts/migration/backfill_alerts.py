#!/usr/bin/env python3
"""
Backfill Alert History from Existing Down Devices

This script creates alert records for devices that are currently down
based on their down_since timestamps. This populates the alert history
with existing outages.

Usage:
    python scripts/backfill_alerts.py
"""

import sys
import os
from datetime import datetime, timezone
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, PingResult
from monitoring.models import StandaloneDevice, AlertHistory


def utcnow():
    """Get current UTC time with timezone awareness"""
    return datetime.now(timezone.utc)


def backfill_alerts():
    """Create alerts for currently down devices"""
    db = SessionLocal()

    try:
        print("🔍 Scanning for devices with down_since timestamps...")

        # Find all devices that have down_since set (currently down)
        down_devices = db.query(StandaloneDevice).filter(
            StandaloneDevice.down_since.isnot(None)
        ).all()

        print(f"📋 Found {len(down_devices)} devices currently marked as down\n")

        if len(down_devices) == 0:
            print("✅ No down devices found - nothing to backfill")
            return

        alerts_created = 0
        alerts_skipped = 0

        for device in down_devices:
            # Check if there's already an active alert for this device
            existing_alert = db.query(AlertHistory).filter(
                AlertHistory.device_id == device.id,
                AlertHistory.resolved_at.is_(None)
            ).first()

            if existing_alert:
                print(f"⏭️  Skipped {device.name} - already has active alert")
                alerts_skipped += 1
                continue

            # Ensure down_since is timezone-aware
            down_since = device.down_since
            if down_since.tzinfo is None:
                down_since = down_since.replace(tzinfo=timezone.utc)

            # Calculate how long device has been down
            duration = utcnow() - down_since
            hours = int(duration.total_seconds() / 3600)
            minutes = int((duration.total_seconds() % 3600) / 60)

            # Create alert
            new_alert = AlertHistory(
                id=uuid.uuid4(),
                device_id=device.id,
                rule_name="Device Unreachable",
                severity="CRITICAL",
                message=f"Device {device.name} is not responding to ICMP ping",
                value=0,  # is_alive = 0
                threshold=1,  # Expected is_alive = 1
                triggered_at=down_since,
                resolved_at=None,
                acknowledged=False,
                notifications_sent=0
            )

            db.add(new_alert)
            alerts_created += 1

            print(f"✅ Created alert for {device.name} ({device.ip})")
            print(f"   Down since: {down_since.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"   Duration: {hours}h {minutes}m")
            print()

        # Commit all changes
        db.commit()

        print("=" * 60)
        print(f"✅ Backfill complete!")
        print(f"   Alerts created: {alerts_created}")
        print(f"   Alerts skipped: {alerts_skipped}")
        print(f"   Total processed: {len(down_devices)}")
        print("=" * 60)
        print()
        print("📝 Next steps:")
        print("   1. Open Device Details for any down device")
        print("   2. Alert History panel should now show the alert")
        print("   3. When device comes back up, alert will auto-resolve")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(backfill_alerts())
