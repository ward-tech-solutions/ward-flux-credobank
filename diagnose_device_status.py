#!/usr/bin/env python3
"""
Diagnostic script to investigate device status mismatch issue
Specifically for Kharagauli device showing UP when it was DOWN

USAGE:
  # From inside Docker container:
  docker exec wardops-api-prod python3 /app/diagnose_device_status.py khargauli

  # Or use the wrapper script:
  ./diagnose_device_status.sh khargauli

  # For other devices:
  ./diagnose_device_status.sh "device-name-pattern"
"""

import sys
import os
from datetime import datetime, timezone

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, PingResult
from monitoring.models import StandaloneDevice
from sqlalchemy import func, desc


def diagnose_device(device_name_pattern: str):
    """
    Diagnose device status for a device matching the given name pattern

    Args:
        device_name_pattern: Part of device name to search for (e.g., "khargauli")
    """
    db = SessionLocal()

    try:
        print(f"\n{'='*80}")
        print(f"Device Status Diagnostic Report")
        print(f"{'='*80}\n")
        print(f"Searching for devices matching: '{device_name_pattern}'")
        print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n")

        # Find devices matching the pattern
        devices = db.query(StandaloneDevice).filter(
            func.lower(StandaloneDevice.name).like(f"%{device_name_pattern.lower()}%")
        ).all()

        if not devices:
            print(f"❌ No devices found matching '{device_name_pattern}'")
            return

        print(f"Found {len(devices)} device(s):\n")

        for device in devices:
            print(f"{'─'*80}")
            print(f"Device: {device.name}")
            print(f"IP: {device.ip}")
            print(f"Enabled: {device.enabled}")
            print(f"down_since: {device.down_since}")
            print(f"{'─'*80}\n")

            # Get latest 10 ping results for this device
            ping_results = db.query(PingResult).filter(
                PingResult.device_ip == device.ip
            ).order_by(desc(PingResult.timestamp)).limit(10).all()

            if not ping_results:
                print("❌ No ping results found for this device!\n")
                continue

            print(f"Latest {len(ping_results)} Ping Results:")
            print(f"{'─'*80}")
            print(f"{'Timestamp':<28} | {'Status':<8} | {'RTT (ms)':<10} | {'Loss %':<8}")
            print(f"{'─'*80}")

            for i, ping in enumerate(ping_results):
                status = "✅ UP" if ping.is_reachable else "❌ DOWN"
                rtt = f"{ping.avg_rtt_ms}" if ping.avg_rtt_ms else "N/A"
                loss = f"{ping.packet_loss_percent}%"
                timestamp = ping.timestamp.isoformat() if ping.timestamp else "N/A"

                marker = " ← LATEST" if i == 0 else ""
                print(f"{timestamp:<28} | {status:<8} | {rtt:<10} | {loss:<8}{marker}")

            print(f"{'─'*80}\n")

            # Check for status inconsistencies
            latest_ping = ping_results[0]
            print("Status Analysis:")
            print(f"  Latest ping status: {'UP ✅' if latest_ping.is_reachable else 'DOWN ❌'}")
            print(f"  Device.down_since: {device.down_since or 'None (device is UP)'}")

            # Check for inconsistency
            if latest_ping.is_reachable and device.down_since:
                print(f"\n⚠️  INCONSISTENCY DETECTED!")
                print(f"  Latest ping shows device is UP, but down_since is still set!")
                print(f"  This means device is showing as DOWN in UI despite being UP.")
                print(f"\n  Root cause: down_since was not cleared when device came back UP")
                print(f"  Solution: The ping task should clear down_since when is_reachable=True")

            elif not latest_ping.is_reachable and not device.down_since:
                print(f"\n⚠️  INCONSISTENCY DETECTED!")
                print(f"  Latest ping shows device is DOWN, but down_since is not set!")
                print(f"  This means device is showing as UP in UI despite being DOWN.")
                print(f"\n  Root cause: down_since was not set when device went DOWN")
                print(f"  Solution: The ping task should set down_since when is_reachable=False")

            elif not latest_ping.is_reachable and device.down_since:
                print(f"\n✅ Status is CONSISTENT - Device is correctly marked as DOWN")
                down_duration = datetime.now(timezone.utc) - device.down_since.replace(tzinfo=timezone.utc)
                hours = down_duration.total_seconds() / 3600
                print(f"   Down for: {hours:.2f} hours")

            else:
                print(f"\n✅ Status is CONSISTENT - Device is correctly marked as UP")

            print(f"\n{'='*80}\n")

            # Additional diagnostic: Check ping result timestamps
            if len(ping_results) >= 2:
                latest_time = ping_results[0].timestamp
                second_latest_time = ping_results[1].timestamp
                time_diff = (latest_time - second_latest_time).total_seconds()

                print("Ping Timing Analysis:")
                print(f"  Time between last 2 pings: {time_diff:.1f} seconds")
                print(f"  Expected interval: 30 seconds (ping_all_devices runs every 30s)")

                if time_diff > 90:
                    print(f"  ⚠️  WARNING: Large gap between pings ({time_diff:.1f}s)")
                    print(f"     This suggests ping task may not be running properly")
                elif time_diff < 10:
                    print(f"  ⚠️  WARNING: Very short interval ({time_diff:.1f}s)")
                    print(f"     This suggests duplicate pings or manual ping")
                else:
                    print(f"  ✅ Ping interval looks normal")

                print(f"\n{'='*80}\n")

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        device_pattern = sys.argv[1]
    else:
        device_pattern = "khargauli"  # Default to user's reported device

    diagnose_device(device_pattern)
