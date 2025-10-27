#!/bin/bash
# WARD FLUX - Start Monitoring Stack
# Starts VictoriaMetrics, Redis, and Celery workers

echo "======================================================================"
echo "WARD FLUX - Monitoring Stack Startup"
echo "======================================================================"

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo "✓ Docker found"

    # Start monitoring stack
    echo ""
    echo "Starting VictoriaMetrics and Redis..."
    docker-compose -f docker-compose.monitoring.yml up -d

    # Wait for services
    echo "Waiting for services to start..."
    sleep 5

    # Check if services are running
    if docker ps | grep -q ward-victoriametrics; then
        echo "✓ VictoriaMetrics running on http://localhost:8428"
    else
        echo "❌ VictoriaMetrics failed to start"
    fi

    if docker ps | grep -q ward-redis; then
        echo "✓ Redis running on localhost:6379"
    else
        echo "❌ Redis failed to start"
    fi
else
    echo "⚠️  Docker not found - please install Docker to run VictoriaMetrics and Redis"
    echo ""
    echo "Alternative: Install locally"
    echo "  - VictoriaMetrics: https://docs.victoriametrics.com/Single-server-VictoriaMetrics.html"
    echo "  - Redis: brew install redis (macOS) or apt-get install redis (Linux)"
    echo ""
    exit 1
fi

echo ""
echo "======================================================================"
echo "Starting Celery Workers"
echo "======================================================================"

# Check if Redis is accessible
if nc -z localhost 6379 2>/dev/null; then
    echo "✓ Redis is accessible"

    # Start Celery worker
    echo "Starting Celery worker..."
    celery -A celery_app worker --loglevel=info --detach \
        --logfile=logs/celery_worker.log \
        --pidfile=logs/celery_worker.pid

    sleep 2

    # Start Celery beat (scheduler)
    echo "Starting Celery beat (scheduler)..."
    celery -A celery_app beat --loglevel=info --detach \
        --logfile=logs/celery_beat.log \
        --pidfile=logs/celery_beat.pid \
        --schedule=logs/celerybeat-schedule.db

    echo ""
    echo "✓ Celery worker started (logs: logs/celery_worker.log)"
    echo "✓ Celery beat started (logs/celery_beat.log)"
else
    echo "❌ Redis is not accessible on localhost:6379"
    echo "   Please start Redis first"
    exit 1
fi

echo ""
echo "======================================================================"
echo "Monitoring Stack Status"
echo "======================================================================"
echo "VictoriaMetrics: http://localhost:8428"
echo "Grafana:         http://localhost:3000 (admin/admin)"
echo "Redis:           localhost:6379"
echo "Celery Worker:   Running (check logs/celery_worker.log)"
echo "Celery Beat:     Running (check logs/celery_beat.log)"
echo ""
echo "✅ Monitoring stack is running!"
echo ""
echo "To stop the stack, run: ./stop_monitoring.sh"
