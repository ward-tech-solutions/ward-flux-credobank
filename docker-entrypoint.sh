#!/bin/bash
set -e

# WARD OPS - Docker Entrypoint Script
# Handles database migrations and application startup

echo "🚀 WARD OPS Starting..."
echo "Environment: ${ENVIRONMENT:-development}"
echo "Python version: $(python3 --version)"

# Wait for database to be ready
if [ -n "$DATABASE_URL" ]; then
    echo "⏳ Waiting for database..."

    # Extract database host from DATABASE_URL
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')

    # Wait for PostgreSQL to be ready
    until pg_isready -h "$DB_HOST" -U ward_admin > /dev/null 2>&1; do
        echo "   Database is unavailable - sleeping"
        sleep 1
    done

    echo "✅ Database is ready!"
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
