#!/bin/bash
# Quick script to check if down_since column exists

echo "Checking down_since column..."
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'standalone_devices' AND column_name = 'down_since';"
