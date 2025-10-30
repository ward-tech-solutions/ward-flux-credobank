#!/bin/bash

# Alert History Diagnostic Script
# Run this on the production server to diagnose alert issues

echo "================================================"
echo "WARD FLUX - Alert History Diagnostics"
echo "================================================"
echo ""

# Check if PostgreSQL container is running
if ! docker ps | grep -q wardops-postgres-prod; then
    echo "ERROR: PostgreSQL container is not running!"
    exit 1
fi

echo "Running diagnostic queries..."
echo ""

# Execute the SQL file
docker exec -i wardops-postgres-prod psql -U ward_admin -d ward_ops < diagnose-alerts.sql

echo ""
echo "================================================"
echo "Diagnostics Complete!"
echo "================================================"
