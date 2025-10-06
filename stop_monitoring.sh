#!/bin/bash
# WARD FLUX - Stop Monitoring Stack

echo "======================================================================"
echo "WARD FLUX - Stopping Monitoring Stack"
echo "======================================================================"

# Stop Celery workers
if [ -f logs/celery_worker.pid ]; then
    echo "Stopping Celery worker..."
    kill $(cat logs/celery_worker.pid) 2>/dev/null
    rm logs/celery_worker.pid
    echo "✓ Celery worker stopped"
else
    echo "ℹ️  Celery worker not running"
fi

# Stop Celery beat
if [ -f logs/celery_beat.pid ]; then
    echo "Stopping Celery beat..."
    kill $(cat logs/celery_beat.pid) 2>/dev/null
    rm logs/celery_beat.pid
    echo "✓ Celery beat stopped"
else
    echo "ℹ️  Celery beat not running"
fi

# Stop Docker containers
if command -v docker &> /dev/null; then
    echo ""
    echo "Stopping Docker containers..."
    docker-compose -f docker-compose.monitoring.yml down
    echo "✓ Docker containers stopped"
fi

echo ""
echo "✅ Monitoring stack stopped"
