"""
WARD FLUX - Celery Tasks

Background tasks for distributed monitoring.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from celery import shared_task

from database import SessionLocal
from monitoring.snmp.poller import get_snmp_poller, SNMPCredentialData
from monitoring.snmp.credentials import decrypt_credential
from monitoring.snmp.oids import get_vendor_oids
from monitoring.victoria.client import get_victoria_client
from monitoring.models import (
    MonitoringItem,
    SNMPCredential,
    AlertRule,
    AlertHistory,
    MonitoringProfile,
    MonitoringMode,
    StandaloneDevice,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="monitoring.tasks.poll_device_snmp")
def poll_device_snmp(self, device_id: str):
    """
    Poll a single device via SNMP and store metrics

    Args:
        device_id: Device UUID
    """
    try:
        db = SessionLocal()
        logger.info(f"Polling device: {device_id}")

        # Check if standalone monitoring is enabled
        profile = db.query(MonitoringProfile).filter_by(is_active=True).first()
        if not profile or profile.mode == MonitoringMode.zabbix:
            logger.debug(f"Standalone monitoring not active, skipping device {device_id}")
            db.close()
            return

        # Get device monitoring items
        items = db.query(MonitoringItem).filter_by(device_id=device_id, enabled=True).all()

        if not items:
            logger.warning(f"No monitoring items found for device {device_id}")
            db.close()
            return

        # Get SNMP credentials
        snmp_cred = db.query(SNMPCredential).filter_by(device_id=device_id).first()

        if not snmp_cred:
            logger.error(f"No SNMP credentials found for device {device_id}")
            db.close()
            return

        # Build credential data
        credentials = _build_credential_data(snmp_cred)

        # Get device info
        device = items[0].device
        device_ip = device.ip

        # Initialize clients
        snmp_poller = get_snmp_poller()
        vm_client = get_victoria_client()

        # Poll each monitoring item
        metrics_to_write = []

        for item in items:
            try:
                # Run async SNMP GET
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(snmp_poller.get(device_ip, item.oid, credentials))
                loop.close()

                if result.success and result.value is not None:
                    # Prepare metric for VictoriaMetrics
                    metric = {
                        "metric_name": _sanitize_metric_name(item.name),
                        "value": float(result.value) if result.value_type in ["integer", "gauge", "counter32", "counter64"] else 0,
                        "labels": {
                            "device": device.name or device_ip,
                            "device_id": str(device_id),
                            "ip": device_ip,
                            "item": item.name,
                            "oid": item.oid,
                        },
                        "timestamp": datetime.utcnow(),
                    }

                    metrics_to_write.append(metric)
                    logger.debug(f"Polled {device_ip} - {item.name}: {result.value}")
                else:
                    logger.warning(f"Failed to poll {device_ip} - {item.name}: {result.error}")

            except Exception as e:
                logger.error(f"Error polling item {item.name} for device {device_id}: {e}")

        # Write metrics to VictoriaMetrics in bulk
        if metrics_to_write:
            vm_client.write_metrics_bulk(metrics_to_write)
            logger.info(f"Wrote {len(metrics_to_write)} metrics for device {device_id}")

        db.close()
        return {"device_id": device_id, "metrics_written": len(metrics_to_write)}

    except Exception as e:
        logger.error(f"Error in poll_device_snmp for {device_id}: {e}")
        raise


@shared_task(name="monitoring.tasks.poll_all_devices_snmp")
def poll_all_devices_snmp():
    """
    Poll all devices with SNMP monitoring items
    """
    try:
        db = SessionLocal()

        # Check if standalone monitoring is enabled
        profile = db.query(MonitoringProfile).filter_by(is_active=True).first()
        if not profile or profile.mode == MonitoringMode.zabbix:
            db.close()
            return

        # Get all devices with monitoring items
        devices = db.query(MonitoringItem.device_id).distinct().all()
        device_ids = [str(d.device_id) for d in devices]

        logger.info(f"Polling {len(device_ids)} devices")

        # Schedule individual polling tasks
        for device_id in device_ids:
            poll_device_snmp.delay(device_id)

        db.close()
        return {"devices_scheduled": len(device_ids)}

    except Exception as e:
        logger.error(f"Error in poll_all_devices_snmp: {e}")
        raise


@shared_task(name="monitoring.tasks.ping_device")
def ping_device(device_id: str, device_ip: str):
    """
    Ping a single device via ICMP

    Args:
        device_id: Device UUID
        device_ip: Device IP address
    """
    try:
        from icmplib import ping

        # Perform ping
        host = ping(device_ip, count=5, interval=0.2, timeout=2, privileged=False)

        # Write metrics to VictoriaMetrics
        vm_client = get_victoria_client()

        metrics = [
            {
                "metric_name": "ping_rtt_ms",
                "value": host.avg_rtt,
                "labels": {"device_id": device_id, "ip": device_ip},
            },
            {
                "metric_name": "ping_packet_loss",
                "value": host.packet_loss,
                "labels": {"device_id": device_id, "ip": device_ip},
            },
            {
                "metric_name": "ping_is_alive",
                "value": 1 if host.is_alive else 0,
                "labels": {"device_id": device_id, "ip": device_ip},
            },
        ]

        vm_client.write_metrics_bulk(metrics)
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


@shared_task(name="monitoring.tasks.ping_all_devices")
def ping_all_devices():
    """
    Ping all monitored devices
    """
    try:
        db = SessionLocal()

        # Check if standalone monitoring is enabled
        profile = db.query(MonitoringProfile).filter_by(is_active=True).first()
        if not profile or profile.mode == MonitoringMode.zabbix:
            db.close()
            return

        devices = db.query(StandaloneDevice).filter_by(enabled=True).all()

        logger.info(f"Pinging {len(devices)} standalone devices")

        for device in devices:
            if device.ip:
                ping_device.delay(str(device.id), device.ip)

        db.close()
        return {"devices_scheduled": len(devices)}

    except Exception as e:
        logger.error(f"Error in ping_all_devices: {e}")
        raise


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
    try:
        db = SessionLocal()

        # Delete alerts older than 90 days
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        deleted_alerts = (
            db.query(AlertHistory)
            .filter(AlertHistory.created_at < cutoff_date)
            .delete()
        )

        # Delete discovery results older than 30 days
        from monitoring.models import DiscoveryResult

        cutoff_date = datetime.utcnow() - timedelta(days=30)
        deleted_discoveries = (
            db.query(DiscoveryResult)
            .filter(DiscoveryResult.discovered_at < cutoff_date, DiscoveryResult.added_to_monitoring == True)
            .delete()
        )

        db.commit()
        db.close()

        logger.info(f"Cleanup complete: {deleted_alerts} alerts, {deleted_discoveries} discoveries deleted")
        return {"alerts_deleted": deleted_alerts, "discoveries_deleted": deleted_discoveries}

    except Exception as e:
        logger.error(f"Error in cleanup_old_data: {e}")
        raise


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
        now = datetime.utcnow()
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

        db.commit()

    except Exception as e:
        logger.error(f"Error in scheduled discovery: {e}", exc_info=True)
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
        cutoff_date = datetime.utcnow() - timedelta(days=days)

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
