"""
WARD FLUX - Interface Metrics Collection Tasks
Celery tasks for collecting interface traffic and error metrics
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Dict
from sqlalchemy import select
from celery import shared_task

from database import SessionLocal
from monitoring.models import StandaloneDevice, DeviceInterface
from monitoring.interface_metrics import interface_metrics_collector

logger = logging.getLogger(__name__)


@shared_task(name="monitoring.tasks.collect_device_interface_metrics", bind=True)
def collect_device_interface_metrics_task(self, device_id: str):
    """
    Celery task: Collect interface metrics for a single device

    Args:
        device_id: Device UUID (as string)

    Returns:
        Collection result dict
    """
    logger.info(f"[Task {self.request.id}] Collecting interface metrics for device {device_id}")

    db = SessionLocal()
    try:
        # Fetch device
        stmt = select(StandaloneDevice).where(StandaloneDevice.id == device_id)
        device = db.execute(stmt).scalar_one_or_none()

        if not device:
            logger.error(f"Device {device_id} not found")
            return {
                'success': False,
                'error': 'Device not found',
                'device_id': device_id
            }

        if not device.enabled:
            logger.info(f"Device {device_id} is disabled, skipping metrics collection")
            return {
                'success': False,
                'error': 'Device disabled',
                'device_id': device_id
            }

        # Fetch interfaces for this device
        stmt = select(DeviceInterface).where(
            DeviceInterface.device_id == device_id,
            DeviceInterface.enabled == True,
            DeviceInterface.monitoring_enabled == True
        )
        interfaces = db.execute(stmt).scalars().all()

        if not interfaces:
            logger.info(f"No interfaces found for device {device_id}")
            return {
                'success': True,
                'interfaces_polled': 0,
                'device_id': device_id
            }

        # Convert to dict for collector
        interfaces_data = []
        for interface in interfaces:
            interfaces_data.append({
                'id': str(interface.id),
                'if_index': interface.if_index,
                'if_name': interface.if_name,
                'interface_type': interface.interface_type,
                'isp_provider': interface.isp_provider,
                'is_critical': interface.is_critical,
                'monitoring_enabled': interface.monitoring_enabled
            })

        # Get SNMP credentials
        snmp_community = device.snmp_community or 'XoNaz-<h'
        snmp_version = device.snmp_version or 'v2c'
        snmp_port = device.snmp_port or 161

        # Collect metrics (async)
        result = asyncio.run(
            interface_metrics_collector.collect_interface_metrics(
                device_ip=device.ip,
                device_id=str(device.id),
                device_name=device.name,
                interfaces=interfaces_data,
                snmp_community=snmp_community,
                snmp_version=snmp_version,
                snmp_port=snmp_port
            )
        )

        return result

    except Exception as e:
        logger.error(f"Metrics collection task failed for device {device_id}: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'device_id': device_id
        }
    finally:
        db.close()


@shared_task(name="monitoring.tasks.collect_all_interface_metrics", bind=True)
def collect_all_interface_metrics_task(self):
    """
    Celery task: Collect interface metrics for all enabled devices

    Runs every 5 minutes via Celery Beat

    Returns:
        Summary of collection results
    """
    logger.info(f"[Task {self.request.id}] Collecting interface metrics for all devices")

    db = SessionLocal()
    summary = {
        'total_devices': 0,
        'successful': 0,
        'failed': 0,
        'total_interfaces_polled': 0,
        'total_metrics_collected': 0,
        'total_metrics_stored': 0,
        'errors': [],
        'started_at': datetime.utcnow().isoformat(),
    }

    try:
        # Fetch all enabled devices with interfaces
        stmt = select(StandaloneDevice).where(
            StandaloneDevice.enabled == True,
            StandaloneDevice.snmp_community.isnot(None)
        )
        devices = db.execute(stmt).scalars().all()

        summary['total_devices'] = len(devices)
        logger.info(f"Found {len(devices)} devices for metrics collection")

        # Collect metrics for each device
        for device in devices:
            try:
                # Fetch interfaces
                stmt = select(DeviceInterface).where(
                    DeviceInterface.device_id == device.id,
                    DeviceInterface.enabled == True,
                    DeviceInterface.monitoring_enabled == True
                )
                interfaces = db.execute(stmt).scalars().all()

                if not interfaces:
                    continue

                # Convert to dict
                interfaces_data = []
                for interface in interfaces:
                    interfaces_data.append({
                        'id': str(interface.id),
                        'if_index': interface.if_index,
                        'if_name': interface.if_name,
                        'interface_type': interface.interface_type,
                        'isp_provider': interface.isp_provider,
                        'is_critical': interface.is_critical,
                        'monitoring_enabled': interface.monitoring_enabled
                    })

                # Collect metrics
                snmp_community = device.snmp_community or 'XoNaz-<h'
                snmp_version = device.snmp_version or 'v2c'
                snmp_port = device.snmp_port or 161

                result = asyncio.run(
                    interface_metrics_collector.collect_interface_metrics(
                        device_ip=device.ip,
                        device_id=str(device.id),
                        device_name=device.name,
                        interfaces=interfaces_data,
                        snmp_community=snmp_community,
                        snmp_version=snmp_version,
                        snmp_port=snmp_port
                    )
                )

                if result['success']:
                    summary['successful'] += 1
                    summary['total_interfaces_polled'] += result['interfaces_polled']
                    summary['total_metrics_collected'] += result['metrics_collected']
                    summary['total_metrics_stored'] += result['metrics_stored']
                else:
                    summary['failed'] += 1
                    summary['errors'].append({
                        'device_ip': device.ip,
                        'device_id': str(device.id),
                        'error': result.get('error', 'Unknown error')
                    })

            except Exception as e:
                logger.error(f"Failed to collect metrics for device {device.ip}: {str(e)}")
                summary['failed'] += 1
                summary['errors'].append({
                    'device_ip': device.ip,
                    'device_id': str(device.id),
                    'error': str(e)
                })

        summary['completed_at'] = datetime.utcnow().isoformat()

        logger.info(
            f"Metrics collection completed: "
            f"{summary['successful']}/{summary['total_devices']} devices successful, "
            f"{summary['total_metrics_stored']} metrics stored"
        )

        return summary

    except Exception as e:
        logger.error(f"Metrics collection task failed: {str(e)}", exc_info=True)
        summary['errors'].append({'error': str(e)})
        return summary
    finally:
        db.close()


@shared_task(name="monitoring.tasks.update_interface_metrics_summaries", bind=True)
def update_interface_metrics_summaries_task(self):
    """
    Celery task: Update cached metrics summaries for all interfaces

    Queries VictoriaMetrics for 24h statistics and caches in PostgreSQL

    Runs every 15 minutes via Celery Beat

    Returns:
        Number of summaries updated
    """
    logger.info(f"[Task {self.request.id}] Updating interface metrics summaries")

    db = SessionLocal()
    updated_count = 0

    try:
        # Get all interfaces with monitoring enabled
        stmt = select(DeviceInterface).where(
            DeviceInterface.enabled == True,
            DeviceInterface.monitoring_enabled == True
        )
        interfaces = db.execute(stmt).scalars().all()

        logger.info(f"Updating metrics summaries for {len(interfaces)} interfaces")

        # Update summary for each interface
        for interface in interfaces:
            try:
                success = asyncio.run(
                    interface_metrics_collector.update_interface_metrics_summary(
                        str(interface.id)
                    )
                )

                if success:
                    updated_count += 1

            except Exception as e:
                logger.error(f"Failed to update summary for interface {interface.id}: {str(e)}")
                continue

        logger.info(f"Updated {updated_count}/{len(interfaces)} interface metrics summaries")

        return {
            'success': True,
            'total_interfaces': len(interfaces),
            'updated_count': updated_count,
            'completed_at': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Metrics summary update task failed: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'updated_count': updated_count
        }
    finally:
        db.close()


@shared_task(name="monitoring.tasks.check_interface_thresholds", bind=True)
def check_interface_thresholds_task(self):
    """
    Celery task: Check interface metrics against thresholds

    Triggers alerts for:
    - High utilization (>80%)
    - High error rate (>0.1%)
    - Interface down (oper_status != 1)

    Runs every 1 minute via Celery Beat

    Returns:
        Number of alerts triggered
    """
    logger.info(f"[Task {self.request.id}] Checking interface thresholds")

    db = SessionLocal()
    alerts_triggered = 0

    try:
        from monitoring.models import AlertHistory, AlertSeverity

        # Get all critical interfaces
        stmt = select(DeviceInterface, StandaloneDevice).join(
            StandaloneDevice,
            DeviceInterface.device_id == StandaloneDevice.id
        ).where(
            DeviceInterface.is_critical == True,
            DeviceInterface.enabled == True
        )

        results = db.execute(stmt).all()

        for interface, device in results:
            try:
                # Check interface status
                if interface.oper_status == 2:  # Down
                    # Trigger critical alert
                    alert = AlertHistory(
                        device_id=device.id,
                        severity=AlertSeverity.CRITICAL,
                        message=f"Critical interface {interface.if_name} is DOWN on {device.name}",
                        value=f"oper_status={interface.oper_status}",
                        triggered_at=datetime.utcnow()
                    )

                    # Check if alert already exists (don't spam)
                    existing = db.execute(
                        select(AlertHistory).where(
                            AlertHistory.device_id == device.id,
                            AlertHistory.message.like(f"%{interface.if_name}%DOWN%"),
                            AlertHistory.resolved_at.is_(None)
                        )
                    ).scalar_one_or_none()

                    if not existing:
                        db.add(alert)
                        alerts_triggered += 1
                        logger.warning(f"ALERT: {alert.message}")

                # TODO: Check utilization and error rates from VictoriaMetrics

            except Exception as e:
                logger.error(f"Failed to check thresholds for interface {interface.id}: {str(e)}")
                continue

        db.commit()

        logger.info(f"Triggered {alerts_triggered} interface alerts")

        return {
            'success': True,
            'alerts_triggered': alerts_triggered,
            'completed_at': datetime.utcnow().isoformat()
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Interface threshold check task failed: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'alerts_triggered': alerts_triggered
        }
    finally:
        db.close()
