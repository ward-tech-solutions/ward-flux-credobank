"""
Batch processing tasks - Zabbix-style architecture with AUTO-SCALING
Process multiple devices in parallel within a single task
Automatically adjusts batch size based on device count
"""

import asyncio
import math
import time
from celery import shared_task
from database import SessionLocal
from monitoring.models import StandaloneDevice
from datetime import datetime, timezone
import logging
from utils.victoriametrics_client import vm_client  # PHASE 2: VictoriaMetrics integration

logger = logging.getLogger(__name__)


def utcnow():
    """Get current UTC time with timezone info"""
    return datetime.now(timezone.utc)


def calculate_optimal_batch_size(device_count: int, target_batches: int = 10) -> int:
    """
    AUTO-SCALING: Calculate optimal batch size to keep task count manageable

    Strategy: Always aim for ~10 batches regardless of device count

    Examples:
    - 875 devices  → 875/10 = 88 → rounded to 100 (9 batches)
    - 1,500 devices → 1,500/10 = 150 (10 batches)
    - 3,000 devices → 3,000/10 = 300 (10 batches)
    - 10,000 devices → 10,000/10 = 1,000 (10 batches)

    This keeps queue size constant as you scale!

    Args:
        device_count: Number of devices to process
        target_batches: Target number of batches (default 10)

    Returns:
        Optimal batch size (between 50 and 500)
    """
    if device_count == 0:
        return 50

    # Calculate base batch size
    batch_size = math.ceil(device_count / target_batches)

    # Round to nearest 50 for cleaner batches
    batch_size = math.ceil(batch_size / 50) * 50

    # Enforce limits: 50-500 devices per batch
    # Min 50: Ensures we use batch processing even for small deployments
    # Max 500: Prevents individual batches from taking too long
    batch_size = max(50, min(batch_size, 500))

    logger.info(f"AUTO-SCALING: {device_count} devices → batch size {batch_size} → ~{math.ceil(device_count/batch_size)} batches")

    return batch_size


@shared_task(name="monitoring.tasks.ping_devices_batch")
def ping_devices_batch(device_ids: list[str], device_ips: list[str]):
    """
    Ping multiple devices in PARALLEL within a single task
    This is how Zabbix does it - batch processing!

    Args:
        device_ids: List of device UUIDs
        device_ips: List of device IPs

    Instead of 875 individual tasks, we have ~18 batch tasks (50 devices each)
    This reduces task queue from 1,750/min to 36/min (48x reduction!)
    """
    import asyncio
    from icmplib import async_ping
    from database import PingResult
    from monitoring.models import AlertHistory, AlertSeverity
    import uuid

    db = None
    try:
        db = SessionLocal()

        # Ping all devices in parallel using asyncio
        async def ping_all():
            tasks = [async_ping(ip, count=2, interval=0.2, timeout=1, privileged=False)
                     for ip in device_ips]
            return await asyncio.gather(*tasks, return_exceptions=True)

        # Execute parallel pings
        results = asyncio.run(ping_all())

        # Process results
        ping_count = 0
        for device_id, device_ip, result in zip(device_ids, device_ips, results):
            if isinstance(result, Exception):
                logger.error(f"Error pinging {device_ip}: {result}")
                continue

            # Get device from database
            device_uuid = uuid.UUID(device_id)
            device = db.query(StandaloneDevice).filter_by(id=device_uuid).first()

            if not device:
                continue

            # PHASE 4 FIX: Use device.down_since to determine previous state
            # (can't use ping_results anymore since we stopped writing to PostgreSQL)
            current_state = result.is_alive
            previous_state = device.down_since is None  # If down_since is None, device was UP

            # Save ping result
            ping_result = PingResult(
                device_ip=device_ip,
                device_name=device.name if device else None,
                packets_sent=result.packets_sent,
                packets_received=result.packets_received,
                packet_loss_percent=int(result.packet_loss),
                min_rtt_ms=int(result.min_rtt) if result.min_rtt else 0,
                avg_rtt_ms=int(result.avg_rtt) if result.avg_rtt else 0,
                max_rtt_ms=int(result.max_rtt) if result.max_rtt else 0,
                is_reachable=result.is_alive,
                timestamp=utcnow()
            )
            # db.add(ping_result)  # PHASE 4: Disabled - using VictoriaMetrics only
            ping_count += 1

            # PHASE 2: Write ping data to VictoriaMetrics
            try:
                base_labels = {
                    "device_id": str(device_id),
                    "device_ip": device_ip,
                    "device_name": device.name if device else "Unknown",
                }

                # Add optional labels
                if device:
                    if hasattr(device, 'branch') and device.branch:
                        base_labels["branch"] = device.branch
                    if hasattr(device, 'region') and device.region:
                        base_labels["region"] = device.region
                    if hasattr(device, 'device_type') and device.device_type:
                        base_labels["device_type"] = device.device_type

                # Write metrics to VictoriaMetrics
                metrics = [
                    {
                        "metric": "device_ping_status",
                        "value": 1 if result.is_alive else 0,
                        "labels": base_labels.copy(),
                        "timestamp": int(time.time())
                    },
                    {
                        "metric": "device_ping_rtt_ms",
                        "value": result.avg_rtt if result.avg_rtt else 0,
                        "labels": base_labels.copy(),
                        "timestamp": int(time.time())
                    },
                    {
                        "metric": "device_ping_packet_loss",
                        "value": result.packet_loss,
                        "labels": base_labels.copy(),
                        "timestamp": int(time.time())
                    },
                ]

                success = vm_client.write_metrics(metrics)
                if not success:
                    logger.warning(f"Failed to write ping metrics to VictoriaMetrics for {device_ip}")
            except Exception as vm_err:
                logger.error(f"VictoriaMetrics write failed for {device_ip}: {vm_err}")

            # Handle state transitions
            if current_state and not previous_state:
                # Device came UP
                if device.down_since:
                    logger.info(f"✅ Device {device.name} ({device_ip}) RECOVERED")
                    # Resolve alerts
                    active_alerts = db.query(AlertHistory).filter(
                        AlertHistory.device_id == device_uuid,
                        AlertHistory.resolved_at.is_(None)
                    ).all()
                    for alert in active_alerts:
                        alert.resolved_at = utcnow()
                device.down_since = None

            elif not current_state and previous_state:
                # Device went DOWN
                device.down_since = utcnow()
                logger.warning(f"❌ Device {device.name} ({device_ip}) went DOWN")

                # Create alert
                new_alert = AlertHistory(
                    id=uuid.uuid4(),
                    device_id=device_uuid,
                    rule_name="Device Unreachable",
                    severity=AlertSeverity.CRITICAL,
                    message=f"Device {device.name} is not responding to ICMP ping",
                    value="0",
                    threshold="1",
                    triggered_at=utcnow(),
                    acknowledged=False,
                    notifications_sent=[]
                )
                db.add(new_alert)

            elif not current_state and device.down_since is None:
                # Device is DOWN but down_since not set
                device.down_since = utcnow()

        db.commit()
        logger.info(f"Batch processed {ping_count} devices")

        return {"devices_pinged": ping_count, "batch_size": len(device_ids)}

    except Exception as e:
        logger.error(f"Error in ping_devices_batch: {e}")
        if db:
            db.rollback()
        raise
    finally:
        if db:
            db.close()


@shared_task(name="monitoring.tasks.ping_all_devices_batched")
def ping_all_devices_batched():
    """
    Schedule ping tasks in BATCHES (Zabbix-style)

    Instead of:
      - 875 individual ping_device tasks = 1,750 tasks/min

    We do:
      - 18 batch tasks (50 devices each) = 36 tasks/min

    This is 48x fewer tasks in the queue!
    """
    db = None
    try:
        db = SessionLocal()

        # Check if monitoring is enabled
        from monitoring.models import MonitoringProfile
        profile = db.query(MonitoringProfile).filter_by(is_active=True).first()
        if not profile:
            return

        # Get all enabled devices
        devices = db.query(StandaloneDevice).filter_by(enabled=True).all()

        if not devices:
            return

        # AUTO-SCALING: Calculate optimal batch size based on device count
        # This automatically adjusts as you add/remove devices!
        BATCH_SIZE = calculate_optimal_batch_size(len(devices))
        batches = []

        for i in range(0, len(devices), BATCH_SIZE):
            batch = devices[i:i+BATCH_SIZE]
            device_ids = [str(d.id) for d in batch if d.ip]
            device_ips = [d.ip for d in batch if d.ip]

            if device_ids:
                batches.append((device_ids, device_ips))

        logger.info(f"Scheduling {len(batches)} batch ping tasks for {len(devices)} devices")

        # Schedule batch tasks
        for device_ids, device_ips in batches:
            ping_devices_batch.delay(device_ids, device_ips)

        return {
            "total_devices": len(devices),
            "batches_scheduled": len(batches),
            "batch_size": BATCH_SIZE
        }

    except Exception as e:
        logger.error(f"Error in ping_all_devices_batched: {e}")
        raise
    finally:
        if db:
            db.close()


@shared_task(name="monitoring.tasks.poll_devices_snmp_batch")
def poll_devices_snmp_batch(device_ids: list[str]):
    """
    Poll multiple devices via SNMP in batch
    Reduces SNMP queue from 875 tasks/min to ~18 tasks/min
    """
    from monitoring.tasks import poll_device_snmp

    results = []
    for device_id in device_ids:
        try:
            result = poll_device_snmp(device_id)
            results.append(result)
        except Exception as e:
            logger.error(f"Error polling device {device_id}: {e}")

    return {
        "devices_polled": len(results),
        "batch_size": len(device_ids)
    }


@shared_task(name="monitoring.tasks.poll_all_devices_snmp_batched")
def poll_all_devices_snmp_batched():
    """
    Schedule SNMP polling in BATCHES
    Reduces queue size by 48x
    """
    db = None
    try:
        db = SessionLocal()

        # Get devices with SNMP enabled
        devices = db.query(StandaloneDevice).filter(
            StandaloneDevice.enabled == True,
            StandaloneDevice.snmp_community.isnot(None)
        ).all()

        if not devices:
            return

        # AUTO-SCALING: Calculate optimal batch size based on device count
        BATCH_SIZE = calculate_optimal_batch_size(len(devices))
        batches = []

        for i in range(0, len(devices), BATCH_SIZE):
            batch = devices[i:i+BATCH_SIZE]
            device_ids = [str(d.id) for d in batch]
            if device_ids:
                batches.append(device_ids)

        logger.info(f"Scheduling {len(batches)} SNMP batch tasks for {len(devices)} devices")

        # Schedule batch tasks
        for device_ids in batches:
            poll_devices_snmp_batch.delay(device_ids)

        return {
            "total_devices": len(devices),
            "batches_scheduled": len(batches),
            "batch_size": BATCH_SIZE
        }

    except Exception as e:
        logger.error(f"Error in poll_all_devices_snmp_batched: {e}")
        raise
    finally:
        if db:
            db.close()
