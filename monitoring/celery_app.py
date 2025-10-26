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
    # Redis connection pooling - critical for 50 workers
    broker_pool_limit=100,                      # Increased from default 10
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    broker_connection_timeout=10,               # Connection timeout 10s
    redis_max_connections=200,                  # Max Redis connections
    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=500,  # Restart worker after 500 tasks (~4 hours, prevent memory leaks)
    # Task execution
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,
    # Retry settings - Only retry on specific transient errors
    # Don't retry programming errors (TypeError, KeyError, etc.)
    task_autoretry_for=(
        ConnectionError,
        TimeoutError,
    ),
    task_retry_kwargs={
        "max_retries": 3,
        "retry_backoff": True,      # Exponential backoff: 10s, 20s, 40s
        "retry_backoff_max": 300,   # Max wait 5 minutes
        "retry_jitter": True,       # Add randomness to prevent thundering herd
    },
    task_default_retry_delay=10,  # Start with 10 seconds (not 60)
    # Logging
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",
)

# Beat schedule (periodic tasks)
app.conf.beat_schedule = {
    # Poll devices every 60 seconds (BATCHED - 48x faster!)
    "poll-devices-snmp": {
        "task": "monitoring.tasks.poll_all_devices_snmp_batched",
        "schedule": 60.0,  # Every 60 seconds
    },
    # Ping devices every 10 seconds (BATCHED - Zabbix-like responsiveness!)
    # Batched processing: 874 devices in 9 batches = ~3 seconds total
    # Detection time: 0-10 seconds (competitive with Zabbix)
    "ping-devices-icmp": {
        "task": "monitoring.tasks.ping_all_devices_batched",
        "schedule": 10.0,  # Every 10 seconds (fast detection!)
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
    # Cleanup old ping results every day at 3 AM
    # Keeps 30 days of ping data (configurable)
    "cleanup-ping-results": {
        "task": "maintenance.cleanup_old_ping_results",
        "schedule": crontab(hour=3, minute=0),
        "kwargs": {"days": 30},  # Keep 30 days of data
    },
    # Monitor worker health every 5 minutes
    "check-worker-health": {
        "task": "monitoring.tasks.check_worker_health",
        "schedule": 300.0,  # Every 5 minutes
    },
    # Discover interfaces on all devices every hour
    "discover-all-interfaces": {
        "task": "monitoring.tasks.discover_all_interfaces",
        "schedule": crontab(minute=0),  # Every hour at :00
    },
    # Cleanup old interfaces every day at 4 AM
    "cleanup-old-interfaces": {
        "task": "monitoring.tasks.cleanup_old_interfaces",
        "schedule": crontab(hour=4, minute=0),
        "kwargs": {"days_threshold": 7},  # Remove interfaces not seen in 7 days
    },
    # Collect interface metrics every 5 minutes
    "collect-interface-metrics": {
        "task": "monitoring.tasks.collect_all_interface_metrics",
        "schedule": 300.0,  # Every 5 minutes
    },
    # Update interface metrics summaries every 15 minutes
    "update-interface-summaries": {
        "task": "monitoring.tasks.update_interface_metrics_summaries",
        "schedule": 900.0,  # Every 15 minutes
    },
    # Check interface thresholds every minute
    "check-interface-thresholds": {
        "task": "monitoring.tasks.check_interface_thresholds",
        "schedule": 60.0,  # Every minute
    },

    # REAL-TIME ALERT EVALUATION - Every 10 seconds
    "evaluate-alerts-realtime": {
        "task": "monitoring.alert_system.evaluate_alerts",
        "schedule": 10.0,  # Every 10 seconds for near real-time alerting
        "options": {"queue": "alerts"},  # High priority queue
    },

    # Cleanup duplicate alerts daily
    "cleanup-duplicate-alerts": {
        "task": "monitoring.alert_system.cleanup_duplicates",
        "schedule": crontab(hour=1, minute=0),  # Daily at 1 AM
    },
    # PHASE 3: Topology & Analytics
    # Discover network topology daily at 5 AM
    "discover-topology": {
        "task": "monitoring.tasks.discover_all_topology",
        "schedule": crontab(hour=5, minute=0),  # Daily at 5:00 AM
    },
    # Learn traffic baselines weekly on Sunday at 6 AM
    "learn-baselines": {
        "task": "monitoring.tasks.learn_all_baselines",
        "schedule": crontab(hour=6, minute=0, day_of_week=0),  # Sunday at 6:00 AM
        "kwargs": {"lookback_days": 14},
    },
    # Check for anomalies every 5 minutes
    "check-anomalies": {
        "task": "monitoring.tasks.check_anomalies",
        "schedule": 300.0,  # Every 5 minutes
    },
}

# Auto-discover tasks
app.autodiscover_tasks(["monitoring"])

logger.info(f"Celery app configured with broker: {REDIS_URL}")
