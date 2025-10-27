"""
WARD FLUX - Celery Tasks

Background tasks for distributed monitoring.
"""

import logging
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from sqlalchemy import text
from celery import shared_task

from database import SessionLocal
from monitoring.snmp.poller import SNMPPoller, SNMPCredentialData
from monitoring.snmp.credentials import decrypt_credential
from monitoring.snmp.oids import get_vendor_oids
from monitoring.victoria.client import get_victoria_client
from utils.victoriametrics_client import vm_client  # NEW: Robust VM client for ping data
from monitoring.models import (
    MonitoringItem,
    SNMPCredential,
    AlertRule,
    AlertHistory,
    MonitoringProfile,
    MonitoringMode,
    StandaloneDevice,
)
from monitoring.flapping_detector import FlappingDetector
from monitoring.alert_deduplicator import AlertDeduplicator

logger = logging.getLogger(__name__)


def utcnow():
    """Get current UTC time with timezone awareness"""
    return datetime.now(timezone.utc)


@shared_task(bind=True, name="monitoring.tasks.poll_device_snmp")
def poll_device_snmp(self, device_id: str):
    """
    Poll a single device via SNMP and store metrics

    Args:
        device_id: Device UUID
    """
    db = None
    try:
        db = SessionLocal()
        logger.info(f"Polling device: {device_id}")

        # Check if monitoring is enabled
        profile = db.query(MonitoringProfile).filter_by(is_active=True).first()
        if not profile:
            logger.debug(f"No active monitoring profile, skipping device {device_id}")
            return

        # Get device
        device = db.query(StandaloneDevice).filter_by(id=device_id).first()
        if not device:
            logger.error(f"Device {device_id} not found")
            return

        # Get device monitoring items
        items = db.query(MonitoringItem).filter_by(device_id=device_id, enabled=True).all()

        if not items:
            logger.warning(f"No monitoring items found for device {device_id}")
            return

        # Check for SNMP credentials (denormalized in standalone_devices table)
        if not device.snmp_community or not device.snmp_community.strip():
            logger.error(f"No SNMP credentials found for device {device.name} ({device.ip})")
            return

        # Build credential data from denormalized fields
        credentials = SNMPCredentialData(
            version=device.snmp_version or "v2c",
            community=device.snmp_community,
        )

        # Get device info
        device_ip = device.ip
        device_name = device.name
        snmp_port = device.snmp_port or 161

        # CRITICAL FIX: Extract all data from MonitoringItem objects BEFORE closing session
        # Otherwise we get DetachedInstanceError when accessing item.oid after session close
        items_data = []
        for item in items:
            items_data.append({
                "oid": item.oid,
                "oid_name": item.oid_name,
            })

        # CRITICAL FIX: Close database session BEFORE doing network operations
        # Keeping the session open during SNMP polling causes "idle in transaction"
        db.commit()  # Commit read-only transaction
        db.close()   # Close session immediately - we have all the data we need
        db = None    # Prevent double-close in finally block

        # Initialize clients (AFTER closing database)
        snmp_poller = SNMPPoller()
        vm_client = get_victoria_client()

        # Poll each monitoring item
        metrics_to_write = []

        for item_data in items_data:
            try:
                # Run async SNMP GET using asyncio.run() - properly manages event loop lifecycle
                # This is much more efficient than creating/destroying event loops manually
                result = asyncio.run(snmp_poller.get(device_ip, item_data["oid"], credentials, port=snmp_port))

                if result.success and result.value is not None:
                    # Prepare metric for VictoriaMetrics
                    metric = {
                        "metric_name": _sanitize_metric_name(item_data["oid_name"]),
                        "value": float(result.value) if result.value_type in ["integer", "gauge", "counter32", "counter64"] else 0,
                        "labels": {
                            "device": device_name or device_ip,
                            "device_id": str(device_id),
                            "ip": device_ip,
                            "item": item_data["oid_name"],
                            "oid": item_data["oid"],
                        },
                        "timestamp": utcnow(),
                    }

                    metrics_to_write.append(metric)
                    logger.debug(f"Polled {device_ip} - {item_data['oid_name']}: {result.value}")
                else:
                    logger.warning(f"Failed to poll {device_ip} - {item_data['oid_name']}: {result.error}")

            except Exception as e:
                logger.error(f"Error polling item {item_data['oid_name']} for device {device_id}: {e}")

        # Write metrics to VictoriaMetrics in bulk
        if metrics_to_write:
            vm_client.write_metrics_bulk(metrics_to_write)
            logger.info(f"Wrote {len(metrics_to_write)} metrics for device {device_id}")

        return {"device_id": device_id, "metrics_written": len(metrics_to_write)}

    except Exception as e:
        logger.error(f"Error in poll_device_snmp for {device_id}: {e}")
        raise
    finally:
        if db:
            db.close()


@shared_task(name="monitoring.tasks.poll_all_devices_snmp")
def poll_all_devices_snmp():
    """
    Poll all devices with SNMP monitoring items
    """
    db = None
    try:
        db = SessionLocal()

        # Check if monitoring is enabled
        profile = db.query(MonitoringProfile).filter_by(is_active=True).first()
        if not profile:
            return

        # Get all devices with monitoring items
        devices = db.query(MonitoringItem.device_id).distinct().all()
        device_ids = [str(d.device_id) for d in devices]
        db.commit()  # Commit read-only transaction to prevent idle state

        logger.info(f"Polling {len(device_ids)} devices")

        # Schedule individual polling tasks
        for device_id in device_ids:
            poll_device_snmp.delay(device_id)

        return {"devices_scheduled": len(device_ids)}

    except Exception as e:
        logger.error(f"Error in poll_all_devices_snmp: {e}")
        raise
    finally:
        if db:
            db.close()


@shared_task(name="monitoring.tasks.ping_device")
def ping_device(device_id: str, device_ip: str):
    """
    Ping a single device via ICMP

    Args:
        device_id: Device UUID
        device_ip: Device IP address
    """
    db = None
    try:
        from icmplib import ping
        # NOTE: datetime, timezone already imported at module level (line 10)
        # NOTE: PingResult removed - ping data now stored in VictoriaMetrics (Phase 2)

        # Log execution for debugging (especially for target device)
        if device_ip == "10.195.83.252":
            logger.info(f"ping_device: EXECUTING ping for TARGET device {device_ip} (ID: {device_id})")

        # Perform ping (optimized: reduced from 5 to 2 pings, timeout from 2s to 1s)
        host = ping(device_ip, count=2, interval=0.2, timeout=1, privileged=False)

        # Save to database
        db = SessionLocal()
        from uuid import UUID
        device_uuid = UUID(device_id) if isinstance(device_id, str) else device_id
        device = db.query(StandaloneDevice).filter_by(id=device_uuid).first()

        # PHASE 2 CHANGE: Removed PostgreSQL ping_results writes
        # Previous state is now tracked via device.down_since (more efficient)
        # Historical ping data is stored in VictoriaMetrics instead

        current_state = host.is_alive  # True = UP, False = DOWN
        # Check previous state from device.down_since (None = was UP, has value = was DOWN)
        previous_state = device.down_since is None if device else True

        # Update down_since timestamp based on ACTUAL state transitions
        # CRITICAL: This must match Zabbix behavior - immediate state updates
        if device:
            # CASE 1: Device is UP (is_alive = True)
            if current_state:
                # If device was DOWN, log the recovery and resolve any active alerts
                if not previous_state:
                    if device.down_since:
                        # Handle timezone-naive down_since timestamps
                        down_since_aware = device.down_since.replace(tzinfo=timezone.utc) if device.down_since.tzinfo is None else device.down_since
                        downtime_duration = utcnow() - down_since_aware
                        logger.info(f"✅ Device {device.name} ({device_ip}) RECOVERED - was DOWN for {downtime_duration}")

                        # Resolve any active alerts for this device
                        active_alerts = db.query(AlertHistory).filter(
                            AlertHistory.device_id == device_uuid,
                            AlertHistory.resolved_at.is_(None)
                        ).all()

                        for alert in active_alerts:
                            alert.resolved_at = utcnow()
                            logger.info(f"Resolved alert {alert.id} for device {device.name}")
                    else:
                        logger.info(f"✅ Device {device.name} ({device_ip}) is now UP")

                # ALWAYS clear down_since when device is UP (Zabbix-like behavior)
                if device.down_since is not None:
                    logger.info(f"Clearing down_since for {device.name} ({device_ip}) - device is UP")
                    device.down_since = None

            # CASE 2: Device is DOWN (is_alive = False)
            else:
                # If device just went down, set down_since and create alert
                if previous_state:
                    device.down_since = utcnow()
                    logger.warning(f"❌ Device {device.name} ({device_ip}) went DOWN")

                    # Create alert in alert_history table
                    new_alert = AlertHistory(
                        id=uuid.uuid4(),
                        device_id=device_uuid,
                        rule_name="Device Unreachable",
                        severity="CRITICAL",
                        message=f"Device {device.name} is not responding to ICMP ping",
                        value=0,  # is_alive = 0
                        threshold=1,  # Expected is_alive = 1
                        triggered_at=utcnow(),
                        resolved_at=None,
                        acknowledged=False,
                        notifications_sent=0
                    )
                    db.add(new_alert)
                    logger.info(f"Created alert for device {device.name} going DOWN")

                # Ensure down_since is set for DOWN devices
                elif device.down_since is None:
                    logger.warning(f"❌ Device {device.name} ({device_ip}) is DOWN - setting down_since timestamp")
                    device.down_since = utcnow()

        db.commit()
        logger.debug(f"Ping complete for {device_ip}: is_alive={host.is_alive}, down_since={device.down_since if device else 'N/A'}")

        # PHASE 2: Write ping data to VictoriaMetrics (CRITICAL - replaces PostgreSQL)
        # Using new robust VM client with comprehensive labels for better querying
        try:
            import time

            # Prepare comprehensive labels for better filtering and dashboards
            base_labels = {
                "device_id": device_id,
                "device_ip": device_ip,
                "device_name": device.name if device else "Unknown",
            }

            # Add optional labels if device exists
            if device:
                if hasattr(device, 'branch') and device.branch:
                    base_labels["branch"] = device.branch
                if hasattr(device, 'region') and device.region:
                    base_labels["region"] = device.region
                if hasattr(device, 'device_type') and device.device_type:
                    base_labels["device_type"] = device.device_type

            # Write all ping metrics to VictoriaMetrics
            metrics = [
                {
                    "metric": "device_ping_status",
                    "value": 1 if host.is_alive else 0,
                    "labels": base_labels.copy(),
                    "timestamp": int(time.time())
                },
                {
                    "metric": "device_ping_rtt_ms",
                    "value": host.avg_rtt if host.avg_rtt else 0,
                    "labels": base_labels.copy(),
                    "timestamp": int(time.time())
                },
                {
                    "metric": "device_ping_rtt_min_ms",
                    "value": host.min_rtt if host.min_rtt else 0,
                    "labels": base_labels.copy(),
                    "timestamp": int(time.time())
                },
                {
                    "metric": "device_ping_rtt_max_ms",
                    "value": host.max_rtt if host.max_rtt else 0,
                    "labels": base_labels.copy(),
                    "timestamp": int(time.time())
                },
                {
                    "metric": "device_ping_packet_loss",
                    "value": host.packet_loss,
                    "labels": base_labels.copy(),
                    "timestamp": int(time.time())
                },
            ]

            # Use new robust VM client with retry logic
            success = vm_client.write_metrics(metrics)
            if success:
                logger.debug(f"✅ Wrote {len(metrics)} ping metrics to VictoriaMetrics for {device_ip}")
            else:
                logger.warning(f"⚠️ Failed to write ping metrics to VictoriaMetrics for {device_ip}")

        except Exception as vm_err:
            logger.error(f"❌ VictoriaMetrics write failed for {device_ip}: {vm_err}")

        logger.debug(f"Pinged {device_ip}: RTT={host.avg_rtt}ms, Loss={host.packet_loss}%")

        return {
            "device_id": device_id,
            "ip": device_ip,
            "is_alive": host.is_alive,
            "avg_rtt": host.avg_rtt,
            "packet_loss": host.packet_loss,
        }

    except Exception as e:
        logger.error(f"Error pinging {device_ip}: {e}")
        raise
    finally:
        if db:
            db.close()


@shared_task(name="monitoring.tasks.ping_all_devices")
def ping_all_devices():
    """
    Ping all monitored devices
    """
    db = None
    try:
        db = SessionLocal()

        # Check if monitoring is enabled
        profile = db.query(MonitoringProfile).filter_by(is_active=True).first()
        if not profile:
            logger.warning("ping_all_devices: No active monitoring profile found")
            return

        devices = db.query(StandaloneDevice).filter_by(enabled=True).all()

        logger.info(f"ping_all_devices: Retrieved {len(devices)} enabled devices from database")

        # Log all device IPs for debugging
        device_ips = [d.ip for d in devices if d.ip]
        logger.info(f"ping_all_devices: Device IPs to ping: {device_ips}")

        # Check specifically for the problematic device
        target_ip = "10.195.83.252"
        target_device = next((d for d in devices if d.ip == target_ip), None)
        if target_device:
            logger.info(f"ping_all_devices: Found target device {target_ip} - ID: {target_device.id}, Name: {target_device.name}, Enabled: {target_device.enabled}")
        else:
            logger.warning(f"ping_all_devices: Target device {target_ip} NOT FOUND in enabled devices query!")
            # Check if it exists in database at all
            all_devices_count = db.query(StandaloneDevice).count()
            logger.info(f"ping_all_devices: Total devices in database: {all_devices_count}")
            specific_device = db.query(StandaloneDevice).filter_by(ip=target_ip).first()
            if specific_device:
                logger.warning(f"ping_all_devices: Device {target_ip} exists but enabled={specific_device.enabled}")
            else:
                logger.error(f"ping_all_devices: Device {target_ip} does NOT exist in database!")

        scheduled_count = 0
        for device in devices:
            if device.ip:
                ping_device.delay(str(device.id), device.ip)
                scheduled_count += 1
                if device.ip == target_ip:
                    logger.info(f"ping_all_devices: Successfully scheduled ping for target device {target_ip}")

        logger.info(f"ping_all_devices: Scheduled {scheduled_count} ping tasks")
        return {"devices_scheduled": scheduled_count}

    except Exception as e:
        logger.error(f"Error in ping_all_devices: {e}")
        raise
    finally:
        if db:
            db.close()


@shared_task(name="monitoring.tasks.check_alert_rules")
def check_alert_rules():
    """
    Check all alert rules and trigger alerts if conditions met
    """
    try:
        db = SessionLocal()

        # Get all enabled alert rules
        rules = db.query(AlertRule).filter_by(enabled=True).all()

        logger.info(f"Checking {len(rules)} alert rules")

        vm_client = get_victoria_client()
        triggered_alerts = 0

        for rule in rules:
            try:
                # Query VictoriaMetrics with rule expression
                # This is a simplified version - full implementation would parse expression
                result = vm_client.query(rule.expression)

                if result and result.get("status") == "success":
                    data = result.get("data", {}).get("result", [])

                    # If query returns data, condition is met
                    if data:
                        # Check if alert already exists
                        existing = (
                            db.query(AlertHistory)
                            .filter_by(rule_id=rule.id, resolved_at=None)
                            .first()
                        )

                        if not existing:
                            # Create new alert
                            alert = AlertHistory(
                                rule_id=rule.id,
                                device_id=rule.device_id,
                                severity=rule.severity,
                                message=f"Alert: {rule.name}",
                                details={"query_result": data},
                            )
                            db.add(alert)
                            db.commit()

                            triggered_alerts += 1
                            logger.warning(f"Alert triggered: {rule.name}")

                            # TODO: Send notifications via configured channels

            except Exception as e:
                logger.error(f"Error checking alert rule {rule.name}: {e}")

        db.close()
        return {"rules_checked": len(rules), "alerts_triggered": triggered_alerts}

    except Exception as e:
        logger.error(f"Error in check_alert_rules: {e}")
        raise


@shared_task(name="monitoring.tasks.cleanup_old_data")
def cleanup_old_data():
    """
    Clean up old alert history and discovery results
    """
    db = None
    try:
        db = SessionLocal()

        # Delete alerts older than 90 days
        cutoff_date = utcnow() - timedelta(days=90)
        deleted_alerts = (
            db.query(AlertHistory)
            .filter(AlertHistory.created_at < cutoff_date)
            .delete()
        )

        # Delete discovery results older than 30 days
        from monitoring.models import DiscoveryResult

        cutoff_date = utcnow() - timedelta(days=30)
        deleted_discoveries = (
            db.query(DiscoveryResult)
            .filter(DiscoveryResult.discovered_at < cutoff_date, DiscoveryResult.added_to_monitoring == True)
            .delete()
        )

        db.commit()

        logger.info(f"Cleanup complete: {deleted_alerts} alerts, {deleted_discoveries} discoveries deleted")
        return {"alerts_deleted": deleted_alerts, "discoveries_deleted": deleted_discoveries}

    except Exception as e:
        logger.error(f"Error in cleanup_old_data: {e}")
        if db:
            db.rollback()
        raise
    finally:
        if db:
            db.close()


def _build_credential_data(snmp_cred: SNMPCredential) -> SNMPCredentialData:
    """
    Build SNMPCredentialData from database model

    Args:
        snmp_cred: SNMPCredential database object

    Returns:
        SNMPCredentialData object
    """
    if snmp_cred.version == "v2c":
        return SNMPCredentialData(
            version="v2c", community=decrypt_credential(snmp_cred.community_encrypted) if snmp_cred.community_encrypted else "public"
        )
    else:  # v3
        return SNMPCredentialData(
            version="v3",
            username=snmp_cred.username,
            auth_protocol=snmp_cred.auth_protocol,
            auth_key=decrypt_credential(snmp_cred.auth_key_encrypted) if snmp_cred.auth_key_encrypted else None,
            priv_protocol=snmp_cred.priv_protocol,
            priv_key=decrypt_credential(snmp_cred.priv_key_encrypted) if snmp_cred.priv_key_encrypted else None,
            security_level=snmp_cred.security_level,
        )


def _sanitize_metric_name(name: str) -> str:
    """
    Sanitize metric name for Prometheus/VictoriaMetrics

    Args:
        name: Metric name

    Returns:
        Sanitized metric name
    """
    # Replace spaces and special characters with underscores
    sanitized = name.lower().replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "")

    # Remove consecutive underscores
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")

    return sanitized.strip("_")


# ============================================
# Discovery Tasks
# ============================================

@shared_task(bind=True, name="monitoring.tasks.run_scheduled_discovery")
def run_scheduled_discovery(self):
    """
    Run all scheduled discovery rules

    Checks for discovery rules that are due to run and executes them
    """
    from models import DiscoveryRule, DiscoveryJob
    from routers.discovery import run_discovery_scan
    import uuid
    from datetime import datetime

    db = SessionLocal()
    try:
        # Find rules that are due to run
        now = utcnow()
        rules = db.query(DiscoveryRule).filter(
            DiscoveryRule.enabled == True,
            DiscoveryRule.schedule_enabled == True,
            DiscoveryRule.next_run <= now
        ).all()

        logger.info(f"Found {len(rules)} discovery rules to run")

        for rule in rules:
            try:
                # Create job
                job = DiscoveryJob(
                    id=uuid.uuid4(),
                    rule_id=rule.id,
                    status='running',
                    triggered_by='scheduled'
                )
                db.add(job)
                db.commit()
                db.refresh(job)

                # Run discovery in background
                logger.info(f"Starting scheduled discovery for rule {rule.name}")

                # Calculate next run time from cron expression
                if rule.schedule_cron:
                    from croniter import croniter
                    cron = croniter(rule.schedule_cron, now)
                    rule.next_run = cron.get_next(datetime)

                # Run the scan
                asyncio.run(run_discovery_scan(str(job.id), str(rule.id)))

            except Exception as e:
                logger.error(f"Error running discovery rule {rule.name}: {e}", exc_info=True)
                db.rollback()  # Rollback on error

        db.commit()

    except Exception as e:
        logger.error(f"Error in scheduled discovery: {e}", exc_info=True)
        db.rollback()  # Rollback on error
    finally:
        db.close()


@shared_task(bind=True, name="monitoring.tasks.cleanup_old_discovery_results")
def cleanup_old_discovery_results(self, days: int = 30):
    """
    Cleanup old discovery results

    Args:
        days: Number of days to keep results
    """
    from models import DiscoveryResult
    from datetime import datetime, timedelta

    db = SessionLocal()
    try:
        cutoff_date = utcnow() - timedelta(days=days)

        # Delete old results that were not imported
        deleted = db.query(DiscoveryResult).filter(
            DiscoveryResult.discovered_at < cutoff_date,
            DiscoveryResult.status != 'imported'
        ).delete()

        db.commit()
        logger.info(f"Cleaned up {deleted} old discovery results")

        return {"deleted": deleted}

    except Exception as e:
        logger.error(f"Error cleaning up discovery results: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


def evaluate_alert_rules(self):
    """
    FIXED ALERT ENGINE - No SQL expression parsing
    Evaluates alerts based on device.down_since field
    Runs every 10 seconds for real-time detection
    """
    db = SessionLocal()
    try:
        from datetime import timezone
        import uuid

        logger.info("📊 Starting FIXED alert evaluation (no SQL parsing)...")

        stats = {
            'devices_evaluated': 0,
            'alerts_created': 0,
            'alerts_resolved': 0,
            'isp_links_evaluated': 0
        }

        # Get all enabled devices only
        devices = db.query(StandaloneDevice).filter(
            StandaloneDevice.enabled == True
        ).all()

        for device in devices:
            stats['devices_evaluated'] += 1

            # Check if ISP link (IP ends with .5)
            is_isp = device.ip and device.ip.endswith('.5')
            if is_isp:
                stats['isp_links_evaluated'] += 1

            # CHECK DOWN STATUS - using device.down_since as source of truth
            if device.down_since:
                # Ensure timezone awareness
                down_since = device.down_since
                if down_since.tzinfo is None:
                    down_since = down_since.replace(tzinfo=timezone.utc)

                down_duration = (utcnow() - down_since).total_seconds()

                if down_duration >= 10:  # Alert after 10 seconds
                    alert_name = 'ISP Link Down' if is_isp else 'Device Down'
                    severity = 'CRITICAL'

                    # Check if alert already exists
                    existing = db.query(AlertHistory).filter(
                        AlertHistory.device_id == device.id,
                        AlertHistory.rule_name == alert_name,
                        AlertHistory.resolved_at.is_(None)
                    ).first()

                    if not existing:
                        # Create new alert
                        new_alert = AlertHistory(
                            id=uuid.uuid4(),
                            device_id=device.id,
                            rule_name=alert_name,
                            severity=severity,
                            message=f"{'ISP Link' if is_isp else 'Device'} {device.name} ({device.ip}) is DOWN for {int(down_duration)} seconds",
                            value="DOWN",
                            threshold="10 seconds",
                            triggered_at=utcnow(),
                            acknowledged=False,
                            notifications_sent=[]
                        )
                        db.add(new_alert)
                        stats['alerts_created'] += 1
                        logger.critical(f"🚨 ALERT: {new_alert.message}")

            # AUTO-RESOLVE if device is UP
            else:
                # Find any unresolved DOWN alerts for this device
                unresolved = db.query(AlertHistory).filter(
                    AlertHistory.device_id == device.id,
                    AlertHistory.rule_name.in_(['Device Down', 'ISP Link Down']),
                    AlertHistory.resolved_at.is_(None)
                ).all()

                for alert in unresolved:
                    alert.resolved_at = utcnow()
                    stats['alerts_resolved'] += 1
                    logger.info(f"✅ Auto-resolved: {alert.rule_name} for {device.name}")

            # CHECK FLAPPING
            if hasattr(device, 'is_flapping') and device.is_flapping:
                flap_threshold = 2 if is_isp else 3

                if device.flap_count and device.flap_count >= flap_threshold:
                    alert_name = 'ISP Link Flapping' if is_isp else 'Device Flapping'
                    severity = 'CRITICAL' if is_isp else 'HIGH'

                    # Check if flapping alert exists
                    existing = db.query(AlertHistory).filter(
                        AlertHistory.device_id == device.id,
                        AlertHistory.rule_name == alert_name,
                        AlertHistory.resolved_at.is_(None)
                    ).first()

                    if not existing:
                        new_alert = AlertHistory(
                            id=uuid.uuid4(),
                            device_id=device.id,
                            rule_name=alert_name,
                            severity=severity,
                            message=f"{'ISP Link' if is_isp else 'Device'} {device.name} ({device.ip}) is flapping - {device.flap_count} changes in 5 minutes",
                            value=str(device.flap_count),
                            threshold=f"{flap_threshold} changes",
                            triggered_at=utcnow(),
                            acknowledged=False,
                            notifications_sent=[]
                        )
                        db.add(new_alert)
                        stats['alerts_created'] += 1
                        logger.warning(f"⚠️ FLAPPING ALERT: {new_alert.message}")

            # Auto-resolve flapping alerts if device stabilizes
            elif hasattr(device, 'is_flapping'):
                unresolved = db.query(AlertHistory).filter(
                    AlertHistory.device_id == device.id,
                    AlertHistory.rule_name.in_(['Device Flapping', 'ISP Link Flapping']),
                    AlertHistory.resolved_at.is_(None)
                ).all()

                for alert in unresolved:
                    alert.resolved_at = utcnow()
                    stats['alerts_resolved'] += 1
                    logger.info(f"✅ Auto-resolved flapping: {alert.rule_name} for {device.name}")

        # Commit all changes
        db.commit()

        # Get summary
        active_alerts = db.query(AlertHistory).filter(
            AlertHistory.resolved_at.is_(None)
        ).count()

        logger.info(
            f"📊 Alert Evaluation Complete: "
            f"Evaluated={stats['devices_evaluated']} devices "
            f"(ISP={stats['isp_links_evaluated']}), "
            f"Created={stats['alerts_created']}, "
            f"Resolved={stats['alerts_resolved']}, "
            f"Active={active_alerts}"
        )

        return stats

    except Exception as exc:
        db.rollback()
        logger.error(f"Error evaluating alert rules: {exc}", exc_info=True)
        raise
    finally:
        db.close()

    """Delete ping_results entries older than the provided number of days."""
    cutoff = utcnow() - timedelta(days=days)
    try:
        db = SessionLocal()
        deleted = db.execute(
            text("DELETE FROM ping_results WHERE timestamp < :cutoff"),
            {"cutoff": cutoff},
        )
        db.commit()
        count = deleted.rowcount if deleted.rowcount is not None else 0
        logger.info(f"🧹 Removed {count} ping_results rows older than {days} days")
        return {"deleted": count, "cutoff": cutoff.isoformat()}

    except Exception as exc:
        logger.error(f"Error cleaning old ping results: {exc}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(name="maintenance.cleanup_old_alerts")
def cleanup_old_alerts(days: int = 7):
    """
    Delete resolved alerts older than the provided number of days.

    RETENTION POLICY:
    - Keep ALL unresolved alerts (regardless of age)
    - Delete RESOLVED alerts older than {days} days
    - Default: 7 days retention for resolved alerts

    This keeps the database lean while preserving active alerts.
    """
    cutoff = utcnow() - timedelta(days=days)
    try:
        db = SessionLocal()

        # Count before deletion
        before_count = db.execute(text("SELECT COUNT(*) FROM alert_history")).scalar()

        # Delete only RESOLVED alerts older than cutoff
        deleted = db.execute(
            text("DELETE FROM alert_history WHERE resolved_at IS NOT NULL AND resolved_at < :cutoff"),
            {"cutoff": cutoff},
        )
        db.commit()

        count = deleted.rowcount if deleted.rowcount is not None else 0
        after_count = db.execute(text("SELECT COUNT(*) FROM alert_history")).scalar()

        logger.info(
            f"🧹 Alert cleanup complete: "
            f"Deleted {count} resolved alerts older than {days} days "
            f"(Before: {before_count}, After: {after_count})"
        )

        # Vacuum to reclaim disk space
        db.execute(text("VACUUM ANALYZE alert_history"))
        db.commit()

        return {
            "deleted": count,
            "before_count": before_count,
            "after_count": after_count,
            "cutoff": cutoff.isoformat()
        }

    except Exception as exc:
        logger.error(f"Error cleaning old alerts: {exc}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(name="monitoring.tasks.check_worker_health")
def check_worker_health():
    """
    Monitor Celery worker health and detect issues

    Checks:
    - Number of active workers
    - Queue length (tasks waiting)
    - Worker responsiveness
    - Memory usage (if available)

    Alerts if:
    - No workers detected (critical)
    - High queue length (> 1000 tasks)
    - Workers not responding

    Returns:
        Dict with health status and metrics
    """
    try:
        from celery import current_app

        inspect = current_app.control.inspect()

        # Check active workers
        stats = inspect.stats()
        active = inspect.active()
        reserved = inspect.reserved()

        if not stats:
            logger.error("🚨 NO CELERY WORKERS DETECTED! System is not monitoring devices!")
            return {
                "status": "critical",
                "workers": 0,
                "queue_length": "unknown",
                "message": "No workers detected - monitoring stopped!"
            }

        worker_count = len(stats)

        # Calculate queue length
        queue_length = 0
        if reserved:
            queue_length = sum(len(tasks) for tasks in reserved.values())

        # Check active tasks
        active_task_count = 0
        if active:
            active_task_count = sum(len(tasks) for tasks in active.values())

        # Determine status
        status = "healthy"
        warnings = []

        if worker_count == 0:
            status = "critical"
            warnings.append("No workers running")
        elif worker_count < 5:
            status = "degraded"
            warnings.append(f"Only {worker_count} workers (expected 50+)")

        if queue_length > 1000:
            status = "degraded"
            warnings.append(f"High queue length: {queue_length} tasks waiting")
        elif queue_length > 5000:
            status = "critical"
            warnings.append(f"Very high queue length: {queue_length} tasks waiting")

        # Log result
        if status == "healthy":
            logger.info(f"✅ Worker health: {worker_count} workers, {queue_length} queued, {active_task_count} active")
        elif status == "degraded":
            logger.warning(f"⚠️  Worker health degraded: {', '.join(warnings)}")
        else:
            logger.error(f"🚨 Worker health critical: {', '.join(warnings)}")

        return {
            "status": status,
            "workers": worker_count,
            "queue_length": queue_length,
            "active_tasks": active_task_count,
            "warnings": warnings,
            "timestamp": utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error checking worker health: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "timestamp": utcnow().isoformat()
        }
