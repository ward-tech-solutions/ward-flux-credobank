#!/usr/bin/env python3
"""
Create alerts for all currently DOWN devices
Run this after fixing alert rules to create initial alerts
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Device, Branch, AlertRule, AlertHistory
from datetime import datetime
import uuid

def create_alerts_for_down_devices():
    """Create alerts for all devices that are currently down"""
    db = SessionLocal()

    try:
        # Get all DOWN devices (down_since is NOT NULL)
        down_devices = db.query(Device).filter(
            Device.down_since.isnot(None)
        ).all()

        print(f"Found {len(down_devices)} devices that are currently DOWN")

        if not down_devices:
            print("No DOWN devices found - nothing to do!")
            return

        # Get alert rules
        device_down_rule = db.query(AlertRule).filter(
            AlertRule.name == 'Device Down',
            AlertRule.enabled == True
        ).first()

        isp_down_rule = db.query(AlertRule).filter(
            AlertRule.name == 'ISP Link Down',
            AlertRule.enabled == True
        ).first()

        if not device_down_rule:
            print("ERROR: 'Device Down' alert rule not found!")
            return

        print(f"\nAlert rules loaded:")
        print(f"  - Device Down: {device_down_rule.severity}")
        if isp_down_rule:
            print(f"  - ISP Link Down: {isp_down_rule.severity}")

        created = 0
        skipped = 0

        for device in down_devices:
            # Determine which rule to use
            is_isp = device.ip and device.ip.endswith('.5')

            if is_isp and isp_down_rule:
                rule = isp_down_rule
                message = f"ISP Link {device.name} ({device.ip}) is DOWN"
            else:
                rule = device_down_rule
                message = f"{device.name} ({device.ip}) is DOWN - Not responding to ping"

            # Check if alert already exists
            existing_alert = db.query(AlertHistory).filter(
                AlertHistory.device_id == device.id,
                AlertHistory.rule_name == rule.name,
                AlertHistory.resolved_at.is_(None)
            ).first()

            if existing_alert:
                skipped += 1
                print(f"  ⏭️  {device.name} - alert already exists")
            else:
                # Create new alert
                alert = AlertHistory(
                    id=str(uuid.uuid4()),
                    rule_id=rule.id,
                    rule_name=rule.name,
                    device_id=device.id,
                    device_name=device.name,
                    branch_id=device.branch_id,
                    branch_name=device.branch.name if device.branch else None,
                    severity=rule.severity,
                    triggered_at=device.down_since,
                    message=message,
                    resolved_at=None
                )
                db.add(alert)
                created += 1
                print(f"  ✅ {rule.severity} - {message}")

        db.commit()

        # Show summary
        print(f"\n📊 SUMMARY:")
        print(f"  Created: {created} alerts")
        print(f"  Skipped: {skipped} existing alerts")

        # Count active alerts by severity
        from sqlalchemy import func
        alert_counts = db.query(
            AlertHistory.severity,
            func.count(AlertHistory.id)
        ).filter(
            AlertHistory.resolved_at.is_(None)
        ).group_by(AlertHistory.severity).all()

        print(f"\n  Active alerts by severity:")
        for severity, count in alert_counts:
            print(f"    {severity}: {count}")

        print("\n✅ Alert creation complete!")

    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_alerts_for_down_devices()
