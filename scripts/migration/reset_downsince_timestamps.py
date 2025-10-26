#!/usr/bin/env python3
"""
Reset down_since timestamps based on current ping status.

This script:
1. Clears down_since for all devices that are currently UP
2. Sets down_since to current time for devices that are DOWN (they just went down)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import SessionLocal
from monitoring.models import StandaloneDevice, PingResult
from datetime import datetime

def reset_timestamps():
    db = SessionLocal()

    try:
        devices = db.query(StandaloneDevice).all()

        cleared = 0
        reset = 0

        print("\nProcessing devices...\n")

        for device in devices:
            # Get latest ping result
            latest_ping = (
                db.query(PingResult)
                .filter(PingResult.device_ip == device.ip)
                .order_by(PingResult.timestamp.desc())
                .first()
            )

            if not latest_ping:
                print(f"⚠️  {device.name} ({device.ip}) - No ping results found")
                continue

            # Device is UP - clear down_since
            if latest_ping.is_reachable:
                if device.down_since is not None:
                    print(f"✓ {device.name} ({device.ip}) - Clearing down_since (device is UP)")
                    device.down_since = None
                    cleared += 1

            # Device is DOWN - set down_since to NOW (treat as fresh outage)
            else:
                old_value = device.down_since
                device.down_since = datetime.utcnow()
                if old_value:
                    print(f"✓ {device.name} ({device.ip}) - Resetting down_since from {old_value} to NOW")
                else:
                    print(f"✓ {device.name} ({device.ip}) - Setting down_since to NOW")
                reset += 1

        db.commit()

        print(f"\n✅ Complete!")
        print(f"   - Cleared {cleared} UP devices")
        print(f"   - Reset {reset} DOWN devices to current time")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("=================================================================")
    print("  Reset down_since Timestamps")
    print("=================================================================")
    reset_timestamps()
    print("\n=================================================================")
