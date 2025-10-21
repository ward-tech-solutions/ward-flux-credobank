#!/bin/bash

echo "==================================================================="
echo "  API Timestamp Diagnostic"
echo "==================================================================="
echo ""

# Get the first down device from the API
echo "Fetching devices from API..."
RESPONSE=$(docker exec wardops-api-prod python3 -c "
import psycopg2
from datetime import datetime
import json

conn = psycopg2.connect(
    host='postgres',
    database='ward_ops',
    user='ward_admin',
    password='ward_admin_password'
)
cur = conn.cursor()

# Get devices that are currently down
cur.execute('''
    SELECT
        sd.id,
        sd.name,
        sd.ip,
        sd.down_since,
        pr.is_reachable,
        pr.timestamp as last_ping
    FROM standalone_devices sd
    LEFT JOIN ping_results pr ON pr.device_ip = sd.ip
    WHERE pr.id = (
        SELECT id FROM ping_results
        WHERE device_ip = sd.ip
        ORDER BY timestamp DESC LIMIT 1
    )
    AND pr.is_reachable = false
    ORDER BY sd.down_since DESC
    LIMIT 5
''')

devices = cur.fetchall()
now_utc = datetime.utcnow()

print('Current UTC time:', now_utc.isoformat())
print('---')

for device in devices:
    dev_id, name, ip, down_since, is_reachable, last_ping = device
    if down_since:
        diff = now_utc - down_since
        hours = diff.total_seconds() / 3600
        print(f'Device: {name} ({ip})')
        print(f'  down_since (DB): {down_since.isoformat()}')
        print(f'  down_since (UTC): {down_since}')
        print(f'  Actual downtime: {hours:.2f} hours ({diff.total_seconds() / 60:.1f} minutes)')
        print(f'  last_ping: {last_ping}')
        print('---')

conn.close()
")

echo "$RESPONSE"

echo ""
echo "==================================================================="
echo "Now checking what the /api/v1/devices endpoint returns..."
echo "==================================================================="

# Get auth token
TOKEN=$(docker exec wardops-api-prod python3 -c "
from db import SessionLocal
from models import User
db = SessionLocal()
user = db.query(User).filter_by(username='admin').first()
if user:
    from routers.auth import create_access_token
    token = create_access_token({'sub': user.username})
    print(token)
" 2>/dev/null)

if [ -n "$TOKEN" ]; then
    echo "Token obtained, fetching devices..."
    docker exec wardops-api-prod curl -s -H "Authorization: Bearer $TOKEN" http://localhost:5001/api/v1/devices | python3 -m json.tool | grep -A 5 -B 5 "down_since" | head -30
else
    echo "Could not obtain auth token"
fi

echo ""
echo "==================================================================="
