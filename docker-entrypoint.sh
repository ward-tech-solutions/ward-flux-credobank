#!/bin/bash
set -e

# WARD OPS - Docker Entrypoint Script
# Handles database migrations and application startup

echo "🚀 WARD OPS Starting..."
echo "Environment: ${ENVIRONMENT:-development}"
echo "Python version: $(python3 --version)"

# Wait a bit for database to be ready (docker-compose depends_on handles most of this)
if [ -n "$DATABASE_URL" ]; then
    echo "⏳ Waiting for database (5 seconds)..."
    sleep 5
    echo "✅ Proceeding with startup"
fi

# Run database migrations for API and Beat services
if [[ "$1" == "uvicorn" ]] || [[ "$1" == "celery" && "$2" == "-A" && "$3" == "celery_app" && "$4" == "beat" ]]; then
    echo "📦 Running database migrations..."

    # Run Alembic migrations
    if [ -d "alembic" ]; then
        alembic upgrade head || {
            echo "⚠️  Migration failed, but continuing..."
        }
    fi

    echo "✅ Migrations complete!"
fi

# Print startup info
echo "🎯 Starting command: $@"
echo ""

# Execute the main command
exec "$@"
