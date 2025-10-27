#!/bin/bash
set -e

echo "1. Check SNMP credentials table schema..."
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "\d snmp_credentials"

echo ""
echo "2. Show SNMP credentials..."
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "SELECT * FROM snmp_credentials LIMIT 5;"

echo ""
echo "3. Test SNMP manually from container to 10.195.57.5..."
docker exec wardops-worker-snmp-prod bash -c "
apt-get update -qq && apt-get install -y -qq snmp > /dev/null 2>&1
snmpwalk -v2c -c credo@bank 10.195.57.5 1.3.6.1.2.1.1.1.0 -t 2 -r 1
"

echo ""
echo "4. Check if SNMP port 161 is accessible..."
docker exec wardops-worker-snmp-prod bash -c "
timeout 3 nc -zv 10.195.57.5 161 2>&1 || echo 'Port 161 not accessible'
"
