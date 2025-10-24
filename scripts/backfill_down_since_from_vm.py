#!/usr/bin/env python3
"""
Backfill down_since timestamps from VictoriaMetrics historical data

Problem: When worker restarts, devices that are DOWN get down_since reset to NOW
         instead of preserving the original downtime start from VictoriaMetrics

Solution: Query VictoriaMetrics for each DOWN device to find when it actually went down
          and set down_since to that historical timestamp

Usage: python3 scripts/backfill_down_since_from_vm.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from monitoring.models import StandaloneDevice
from utils.victoriametrics_client import vm_client
from datetime import datetime, timezone, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def find_downtime_start(device_id: str, device_ip: str, lookback_days: int = 30) -> datetime | None:
    """
    Query VictoriaMetrics to find when device actually went DOWN

    Returns: datetime when device went DOWN, or None if device is UP or no data
    """
    try:
        # Query last 30 days of ping status (1 = UP, 0 = DOWN)
        query = f'device_ping_status{{device_id="{device_id}"}}'
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=lookback_days)

        # Get status history with 5-minute resolution
        response = vm_client.session.get(
            f"{vm_client.base_url}/api/v1/query_range",
            params={
                "query": query,
                "start": int(start_time.timestamp()),
                "end": int(end_time.timestamp()),
                "step": "5m"
            },
            timeout=30
        )

        if response.status_code != 200:
            logger.warning(f"VictoriaMetrics query failed for {device_ip}: {response.status_code}")
            return None

        data = response.json()
        if data.get("status") != "success":
            logger.warning(f"VictoriaMetrics query unsuccessful for {device_ip}")
            return None

        results = data.get("data", {}).get("result", [])
        if not results:
            logger.warning(f"No VictoriaMetrics data for {device_ip}")
            return None

        values = results[0].get("values", [])
        if not values:
            logger.warning(f"No values in VictoriaMetrics response for {device_ip}")
            return None

        # Walk backwards from most recent to find when device went DOWN
        # values format: [[timestamp, "0" or "1"], ...]
        last_status = None
        downtime_start_ts = None

        for timestamp, status in reversed(values):
            current_status = int(float(status))  # 1=UP, 0=DOWN

            if current_status == 0:  # Device is DOWN at this point
                downtime_start_ts = timestamp
                if last_status == 1:  # Previous point was UP - found the transition!
                    break
            elif current_status == 1:  # Device was UP
                last_status = 1
                downtime_start_ts = None  # Reset if we find device was UP

        if downtime_start_ts:
            return datetime.fromtimestamp(int(downtime_start_ts), tz=timezone.utc)

        return None

    except Exception as e:
        logger.error(f"Error querying VictoriaMetrics for {device_ip}: {e}")
        return None


def backfill_down_since():
    """Backfill down_since timestamps for all DOWN devices from VictoriaMetrics history"""

    db = SessionLocal()
    try:
        logger.info("Starting down_since backfill from VictoriaMetrics...")

        # Get all devices that are currently DOWN (down_since is set)
        down_devices = db.query(StandaloneDevice).filter(
            StandaloneDevice.down_since.isnot(None),
            StandaloneDevice.enabled == True
        ).all()

        logger.info(f"Found {len(down_devices)} devices with down_since set")

        backfilled_count = 0
        skipped_count = 0

        for device in down_devices:
            current_down_since = device.down_since

            # Make timezone-aware if needed
            if current_down_since.tzinfo is None:
                current_down_since = current_down_since.replace(tzinfo=timezone.utc)

            # Find actual downtime start from VictoriaMetrics
            logger.info(f"Checking {device.name} ({device.ip})...")
            vm_downtime_start = find_downtime_start(str(device.id), device.ip)

            if vm_downtime_start:
                # Compare with current down_since
                time_diff = abs((current_down_since - vm_downtime_start).total_seconds())

                if time_diff > 3600:  # More than 1 hour difference
                    logger.info(
                        f"  📝 Backfilling {device.name}:\n"
                        f"     Current: {current_down_since} (down for {datetime.now(timezone.utc) - current_down_since})\n"
                        f"     Actual:  {vm_downtime_start} (down for {datetime.now(timezone.utc) - vm_downtime_start})"
                    )
                    device.down_since = vm_downtime_start
                    backfilled_count += 1
                else:
                    logger.info(f"  ✓ {device.name}: down_since already correct ({current_down_since})")
                    skipped_count += 1
            else:
                logger.warning(f"  ⚠️  Could not find downtime start for {device.name} in VictoriaMetrics")
                skipped_count += 1

        if backfilled_count > 0:
            logger.info(f"\n💾 Committing {backfilled_count} backfilled timestamps...")
            db.commit()

        logger.info(
            f"\n✅ Backfill complete:\n"
            f"   - Backfilled: {backfilled_count} devices\n"
            f"   - Skipped: {skipped_count} devices\n"
            f"   - Total: {len(down_devices)} devices"
        )

    except Exception as e:
        logger.error(f"Error during backfill: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    backfill_down_since()
