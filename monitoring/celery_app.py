"""
WARD FLUX - Celery Application Configuration

Distributed task queue for SNMP polling, ICMP monitoring, and discovery.
"""

import os
import logging
from celery import Celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)

# Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
app = Celery("ward_monitoring", broker=REDIS_URL, backend=REDIS_URL)

# Celery configuration
app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={"master_name": "mymaster"},
    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (prevent memory leaks)
    # Task execution
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,
    # Retry settings
    task_autoretry_for=(Exception,),
    task_retry_kwargs={"max_retries": 3},
    task_default_retry_delay=60,  # 1 minute
    # Logging
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",
)

# Beat schedule (periodic tasks)
app.conf.beat_schedule = {
    # Poll devices every 60 seconds (will be dynamically configured)
    "poll-devices-snmp": {
        "task": "monitoring.tasks.poll_all_devices_snmp",
        "schedule": 60.0,  # Every 60 seconds
    },
    # Ping devices every 30 seconds
    "ping-devices-icmp": {
        "task": "monitoring.tasks.ping_all_devices",
        "schedule": 30.0,  # Every 30 seconds
    },
    # Check alert rules every 60 seconds
    "check-alert-rules": {
        "task": "monitoring.tasks.check_alert_rules",
        "schedule": 60.0,  # Every minute
    },
    # Cleanup old data every day at 2 AM
    "cleanup-old-data": {
        "task": "monitoring.tasks.cleanup_old_data",
        "schedule": crontab(hour=2, minute=0),
    },
}

# Auto-discover tasks
app.autodiscover_tasks(["monitoring"])

logger.info(f"Celery app configured with broker: {REDIS_URL}")
