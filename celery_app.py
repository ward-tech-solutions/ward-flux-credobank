"""
WARD FLUX - Celery Application Configuration

Distributed task queue for background SNMP polling and monitoring.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
app = Celery(
    'ward_flux',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['monitoring.tasks']
)

# Celery configuration
app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={'master_name': 'mymaster'},

    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit

    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,

    # Broker settings
    broker_connection_retry_on_startup=True,
)

# Periodic task schedule
app.conf.beat_schedule = {
    # Poll all enabled monitoring items every minute
    'poll-all-devices-snmp': {
        'task': 'monitoring.tasks.poll_all_devices_snmp',
        'schedule': 60.0,  # Every 60 seconds
    },

    # Ping all devices every 30 seconds
    'ping-all-devices': {
        'task': 'monitoring.tasks.ping_all_devices',
        'schedule': 30.0,
    },

    # Cleanup old metrics every hour
    'cleanup-old-data': {
        'task': 'monitoring.tasks.cleanup_old_data',
        'schedule': crontab(minute=0),  # Every hour at :00
    },

    # Check device availability every 5 minutes
    'check-device-health': {
        'task': 'monitoring.tasks.check_device_health',
        'schedule': 300.0,  # Every 5 minutes
    },

    # Run scheduled discovery every hour
    'run-scheduled-discovery': {
        'task': 'monitoring.tasks.run_scheduled_discovery',
        'schedule': crontab(minute=0),  # Every hour at :00
    },

    # Cleanup ping telemetry daily
    'cleanup-ping-results': {
        'task': 'maintenance.cleanup_old_ping_results',
        'schedule': crontab(hour=3, minute=0),
        'kwargs': {'days': 90},
    },

    # Cleanup old discovery results daily
    'cleanup-discovery-results': {
        'task': 'monitoring.tasks.cleanup_old_discovery_results',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2:00 AM
        'kwargs': {'days': 30}
    },

    # 🚨 PRODUCTION ALERT ENGINE - Evaluate alert rules every minute
    'evaluate-alert-rules': {
        'task': 'monitoring.tasks.evaluate_alert_rules',
        'schedule': 60.0,  # Every 60 seconds
    },
}

if __name__ == '__main__':
    app.start()
