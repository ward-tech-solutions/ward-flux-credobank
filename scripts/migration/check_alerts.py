#!/usr/bin/env python3
"""
Check Alert History for a Specific Device

Usage:
    python scripts/check_alerts.py <device_name_or_ip>
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from monitoring.models import StandaloneDevice, AlertHistory


def check_alerts(search_term=None):
    """Check alerts for a device"""
    db = SessionLocal()

    try:
        # If search term provided, find specific device
        if search_term:
            device = db.query(StandaloneDevice).filter(
                (StandaloneDevice.name.ilike(f"%{search_term}%")) |
                (StandaloneDevice.ip == search_term)
            ).first()

            if not device:
                print(f"❌ Device not found: {search_term}")
                return 1

            print(f"📱 Device: {device.name} ({device.ip})")
            print(f"   ID: {device.id}")
            print(f"   Down Since: {device.down_since}")
            print()

            # Get alerts for this device
            alerts = db.query(AlertHistory).filter(
                AlertHistory.device_id == device.id
            ).order_by(AlertHistory.triggered_at.desc()).limit(10).all()

            print(f"📋 Alerts for this device: {len(alerts)}")
            print()

            if alerts:
                for alert in alerts:
                    status = "🔴 ACTIVE" if alert.resolved_at is None else "✅ RESOLVED"
                    print(f"{status} - {alert.severity}")
                    print(f"   Rule: {alert.rule_name}")
                    print(f"   Message: {alert.message}")
                    print(f"   Triggered: {alert.triggered_at}")
                    print(f"   Resolved: {alert.resolved_at}")
                    if alert.resolved_at and alert.triggered_at:
                        duration = alert.resolved_at - alert.triggered_at
                        print(f"   Duration: {duration}")
                    print()
            else:
                print("   No alerts found for this device")

        else:
            # Show summary of all alerts
            total_alerts = db.query(AlertHistory).count()
            active_alerts = db.query(AlertHistory).filter(
                AlertHistory.resolved_at.is_(None)
            ).count()
            resolved_alerts = total_alerts - active_alerts

            print(f"📊 Alert Summary:")
            print(f"   Total Alerts: {total_alerts}")
            print(f"   Active: {active_alerts}")
            print(f"   Resolved: {resolved_alerts}")
            print()

            # Show sample of recent alerts
            print("Recent Alerts (last 10):")
            recent = db.query(AlertHistory, StandaloneDevice).join(
                StandaloneDevice, AlertHistory.device_id == StandaloneDevice.id
            ).order_by(AlertHistory.triggered_at.desc()).limit(10).all()

            for alert, device in recent:
                status = "🔴 ACTIVE" if alert.resolved_at is None else "✅ RESOLVED"
                print(f"\n{status} - {device.name} ({device.ip})")
                print(f"   Severity: {alert.severity}")
                print(f"   Triggered: {alert.triggered_at}")
                if alert.resolved_at:
                    print(f"   Resolved: {alert.resolved_at}")

    finally:
        db.close()

    return 0


if __name__ == "__main__":
    search_term = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(check_alerts(search_term))
