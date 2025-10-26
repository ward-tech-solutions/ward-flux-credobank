#!/usr/bin/env python3
"""
Detect and report flapping devices in WARD OPS monitoring system
Run this on the production server to identify devices with unstable connectivity
"""

import psycopg2
from datetime import datetime, timedelta
import json
import requests

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'ward_ops',
    'user': 'ward_admin',
    'password': 'ward_admin_password'
}

# VictoriaMetrics configuration
VM_URL = "http://localhost:8428"

def get_db_connection():
    """Create database connection"""
    return psycopg2.connect(**DB_CONFIG)

def get_device_metrics(device_ip, minutes=30):
    """Get ping metrics from VictoriaMetrics for last N minutes"""
    end_time = int(datetime.now().timestamp())
    start_time = int((datetime.now() - timedelta(minutes=minutes)).timestamp())

    query = f'device_ping_status{{device_ip="{device_ip}"}}'
    url = f"{VM_URL}/api/v1/query_range"
    params = {
        'query': query,
        'start': start_time,
        'end': end_time,
        'step': '10s'
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if data['data']['result']:
            values = data['data']['result'][0]['values']
            return values
    except Exception as e:
        print(f"Error querying VictoriaMetrics: {e}")

    return []

def analyze_flapping(values, threshold_minutes=5, min_changes=3):
    """
    Analyze metrics to detect flapping
    Returns: (is_flapping, change_count, flapping_periods)
    """
    if not values:
        return False, 0, []

    # Convert to status changes
    changes = []
    last_status = None

    for timestamp, value in values:
        status = int(float(value))  # 1 = UP, 0 = DOWN
        if last_status is not None and status != last_status:
            changes.append((timestamp, 'UP' if status == 1 else 'DOWN'))
        last_status = status

    # Check for flapping in sliding window
    flapping_periods = []
    window_seconds = threshold_minutes * 60

    for i, (change_time, _) in enumerate(changes):
        # Count changes within window
        window_end = change_time + window_seconds
        window_changes = 1  # Include current change

        for j in range(i + 1, len(changes)):
            if changes[j][0] <= window_end:
                window_changes += 1

        if window_changes >= min_changes:
            flapping_periods.append({
                'start_time': datetime.fromtimestamp(change_time),
                'changes': window_changes,
                'duration_seconds': window_seconds
            })

    is_flapping = len(flapping_periods) > 0
    return is_flapping, len(changes), flapping_periods

def check_all_devices():
    """Check all enabled devices for flapping"""
    conn = get_db_connection()
    cur = conn.cursor()

    # Get all enabled devices
    cur.execute("""
        SELECT id, name, ip, down_since
        FROM standalone_devices
        WHERE enabled = true
        ORDER BY name
    """)

    devices = cur.fetchall()
    flapping_devices = []

    print(f"Checking {len(devices)} devices for flapping behavior...")
    print("-" * 80)

    for device_id, name, ip, down_since in devices:
        # Get metrics for last 30 minutes
        values = get_device_metrics(ip, minutes=30)

        if values:
            is_flapping, change_count, periods = analyze_flapping(values)

            if is_flapping:
                current_status = "DOWN" if down_since else "UP"
                flapping_devices.append({
                    'name': name,
                    'ip': ip,
                    'current_status': current_status,
                    'change_count': change_count,
                    'flapping_periods': len(periods)
                })

                print(f"⚠️  FLAPPING: {name} ({ip})")
                print(f"   Current: {current_status}")
                print(f"   Changes in last 30 min: {change_count}")
                print(f"   Flapping periods detected: {len(periods)}")

                if periods:
                    latest = periods[-1]
                    print(f"   Latest: {latest['changes']} changes starting at {latest['start_time'].strftime('%H:%M:%S')}")
                print()

    cur.close()
    conn.close()

    return flapping_devices

def generate_report(flapping_devices):
    """Generate summary report"""
    print("=" * 80)
    print("FLAPPING DETECTION SUMMARY")
    print("=" * 80)
    print()

    if not flapping_devices:
        print("✅ No flapping devices detected!")
        print("   All devices show stable connectivity over the last 30 minutes.")
    else:
        print(f"⚠️  Found {len(flapping_devices)} flapping device(s):")
        print()

        # Sort by change count (most unstable first)
        flapping_devices.sort(key=lambda x: x['change_count'], reverse=True)

        for i, device in enumerate(flapping_devices, 1):
            print(f"{i}. {device['name']} ({device['ip']})")
            print(f"   - Status changes: {device['change_count']}")
            print(f"   - Current status: {device['current_status']}")
            print(f"   - Flapping periods: {device['flapping_periods']}")

        print()
        print("RECOMMENDED ACTIONS:")
        print("1. Check physical network connections for these devices")
        print("2. Review switch/router logs for port flapping")
        print("3. Consider temporarily disabling alerts for these devices")
        print("4. Implement flapping suppression in monitoring system")

    print()
    print(f"Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def disable_alerts_for_device(device_ip):
    """Disable alerts for a specific flapping device"""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE standalone_devices
        SET alert_enabled = false
        WHERE ip = %s
        RETURNING name
    """, (device_ip,))

    result = cur.fetchone()
    if result:
        conn.commit()
        print(f"✅ Disabled alerts for {result[0]} ({device_ip})")
    else:
        print(f"❌ Device {device_ip} not found")

    cur.close()
    conn.close()

if __name__ == "__main__":
    print("WARD OPS - Flapping Device Detection")
    print("=====================================")
    print()

    # Check all devices
    flapping_devices = check_all_devices()

    # Generate report
    generate_report(flapping_devices)

    # Optional: Disable alerts for the worst offender
    if flapping_devices and flapping_devices[0]['change_count'] > 10:
        worst = flapping_devices[0]
        print()
        response = input(f"Disable alerts for {worst['name']} ({worst['ip']})? [y/N]: ")
        if response.lower() == 'y':
            disable_alerts_for_device(worst['ip'])