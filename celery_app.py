"""
WARD FLUX - Celery Application Configuration
ROBUST PRIORITY QUEUE ARCHITECTURE WITH AUTO-SCALING

ARCHITECTURE:
- Alerts Queue: High priority, dedicated workers, 10s interval
- Monitoring Queue: Medium priority, batch ping processing (auto-scaling)
- SNMP Queue: Low priority, batch SNMP polling
- Maintenance Queue: Background tasks, cleanup, etc.

PERFORMANCE:
- Near real-time: 10-second ping intervals
- Real-time alerts: 10-second evaluation
- Auto-scaling batches: Handles 100-10,000+ devices
- Task reduction: 2,627 → 72 tasks/min (36x improvement)
"""

import os
from celery import Celery
from celery.schedules import crontab
from kombu import Queue, Exchange

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
app = Celery(
    'ward_flux',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        'monitoring.tasks',
        'monitoring.tasks_batch',
        'monitoring.tasks_interface_discovery',
        'monitoring.tasks_interface_metrics'
    ]
)

# Define exchanges and queues with priorities
default_exchange = Exchange('default', type='direct')

app.conf.task_queues = (
    # HIGH PRIORITY: Alert evaluation (never delayed)
    Queue('alerts', exchange=default_exchange, routing_key='alerts', priority=10),

    # MEDIUM PRIORITY: Ping monitoring (real-time device status)
    Queue('monitoring', exchange=default_exchange, routing_key='monitoring', priority=5),

    # LOW PRIORITY: SNMP polling (metrics, can be delayed)
    Queue('snmp', exchange=default_exchange, routing_key='snmp', priority=2),

    # BACKGROUND: Maintenance tasks
    Queue('maintenance', exchange=default_exchange, routing_key='maintenance', priority=0),
)

# Task routing - route tasks to appropriate queues
app.conf.task_routes = {
    # CRITICAL: Alert evaluation and health checks (HIGH PRIORITY)
    'monitoring.tasks.evaluate_alert_rules': {
        'queue': 'alerts',
        'routing_key': 'alerts',
        'priority': 10
    },
    'monitoring.tasks.check_device_health': {
        'queue': 'alerts',
        'routing_key': 'alerts',
        'priority': 10
    },

    # IMPORTANT: Ping monitoring (MEDIUM PRIORITY) - BATCH TASKS
    'monitoring.tasks.ping_all_devices_batched': {
        'queue': 'monitoring',
        'routing_key': 'monitoring',
        'priority': 5
    },
    'monitoring.tasks.ping_devices_batch': {
        'queue': 'monitoring',
        'routing_key': 'monitoring',
        'priority': 5
    },
    'monitoring.tasks.ping_device': {
        'queue': 'monitoring',
        'routing_key': 'monitoring',
        'priority': 5
    },

    # NORMAL: SNMP polling (LOW PRIORITY) - BATCH TASKS
    'monitoring.tasks.poll_all_devices_snmp_batched': {
        'queue': 'snmp',
        'routing_key': 'snmp',
        'priority': 2
    },
    'monitoring.tasks.poll_devices_snmp_batch': {
        'queue': 'snmp',
        'routing_key': 'snmp',
        'priority': 2
    },
    'monitoring.tasks.poll_device_snmp': {
        'queue': 'snmp',
        'routing_key': 'snmp',
        'priority': 2
    },

    # BACKGROUND: Maintenance tasks
    'maintenance.cleanup_old_ping_results': {
        'queue': 'maintenance',
        'routing_key': 'maintenance',
        'priority': 0
    },
    'maintenance.cleanup_old_alerts': {
        'queue': 'maintenance',
        'routing_key': 'maintenance',
        'priority': 0
    },
    'maintenance.cleanup_old_discovery_results': {
        'queue': 'maintenance',
        'routing_key': 'maintenance',
        'priority': 0
    },
}

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

    # Worker settings - optimized for priority queues
    worker_prefetch_multiplier=1,  # CRITICAL: Process one task at a time to respect priorities
    worker_max_tasks_per_child=1000,

    # Broker settings
    broker_connection_retry_on_startup=True,

    # Priority settings
    task_default_priority=5,
    broker_transport_options={
        'priority_steps': list(range(11)),  # 0-10 priority levels
        'queue_order_strategy': 'priority',  # Process by priority
    },
)

# Periodic task schedule - AUTO-SCALING BATCH PROCESSING
app.conf.beat_schedule = {
    # SNMP polling every minute with BATCH PROCESSING
    # AUTO-SCALING: 875 devices → ~18 batch tasks (instead of 875 individual tasks)
    'poll-all-devices-snmp': {
        'task': 'monitoring.tasks.poll_all_devices_snmp_batched',
        'schedule': 60.0,  # Every 60 seconds
    },

    # Ping all devices every 10 seconds (NEAR REAL-TIME!) with AUTO-SCALING BATCHES
    # AUTO-SCALING: 875 devices → batch size 100 → ~9 batches every 10s (54 tasks/min)
    'ping-all-devices': {
        'task': 'monitoring.tasks.ping_all_devices_batched',
        'schedule': 10.0,  # Every 10 seconds (NEAR REAL-TIME downtime detection!)
    },

    # 🚨 PRODUCTION ALERT ENGINE - Evaluate alert rules every 10 seconds (REAL-TIME!)
    'evaluate-alert-rules': {
        'task': 'monitoring.tasks.evaluate_alert_rules',
        'schedule': 10.0,  # Every 10 seconds (REAL-TIME alerting!)
        'options': {'priority': 10}  # Highest priority
    },

    # Device health check every 5 minutes
    'check-device-health': {
        'task': 'monitoring.tasks.check_device_health',
        'schedule': 300.0,  # Every 5 minutes
    },

    # ISP Interface Status Polling - Every 60 seconds (REAL-TIME ISP monitoring!)
    # Polls operational status for ISP interfaces (Magti/Silknet) on .5 routers
    'collect-interface-metrics': {
        'task': 'monitoring.tasks.collect_all_interface_metrics',
        'schedule': 60.0,  # Every 60 seconds (keeps ISP status current)
    },

    # Cleanup old ping results daily at 3:00 AM
    'cleanup-old-pings': {
        'task': 'maintenance.cleanup_old_ping_results',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3:00 AM
        'kwargs': {'days': 30}
    },

    # Cleanup old resolved alerts weekly on Sunday at 3:30 AM
    'cleanup-old-alerts': {
        'task': 'maintenance.cleanup_old_alerts',
        'schedule': crontab(hour=3, minute=30, day_of_week=0),  # Sunday 3:30 AM
        'kwargs': {'days': 7}
    },

    # Cleanup old discovery results daily at 2:00 AM
    'cleanup-old-discovery': {
        'task': 'maintenance.cleanup_old_discovery_results',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2:00 AM
        'kwargs': {'days': 30}
    },
}

if __name__ == '__main__':
    app.start()
