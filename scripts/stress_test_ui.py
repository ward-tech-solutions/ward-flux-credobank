#!/usr/bin/env python3
"""
UI Stress Test - Simulate Regional Managers Using Ward-Ops

Simulates 10 regional managers (test1-test10) accessing the UI simultaneously:
- Login
- Navigate to Monitor page
- Filter devices by region
- Click on devices to view details
- Navigate to Dashboard
- Check alerts
- Logout

This stress tests:
- API authentication endpoints
- Device list queries with region filters
- Device detail queries
- Dashboard statistics
- Alert history queries
- Session management

Usage:
  python3 scripts/stress_test_ui.py --url https://your-wardops-domain.com --duration 300

Requirements:
  pip install requests
"""

import argparse
import random
import time
import threading
import requests
from datetime import datetime
from typing import Dict, List
import json
import sys


class RegionalManagerSimulator:
    """Simulates a regional manager using Ward-Ops UI"""

    def __init__(self, username: str, password: str, base_url: str, duration: int):
        self.username = username
        self.password = password
        self.base_url = base_url.rstrip('/')
        self.duration = duration
        self.session = requests.Session()
        self.token = None
        self.user_info = None
        self.stats = {
            'requests_sent': 0,
            'requests_succeeded': 0,
            'requests_failed': 0,
            'total_response_time': 0,
            'errors': []
        }

    def log(self, message: str):
        """Log with timestamp and username"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] [{self.username}] {message}")

    def login(self) -> bool:
        """Login and get JWT token"""
        try:
            self.log("Logging in...")
            start = time.time()

            # API uses OAuth2PasswordRequestForm, expects form data not JSON
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                data={"username": self.username, "password": self.password},
                timeout=10
            )

            elapsed = time.time() - start
            self.stats['requests_sent'] += 1
            self.stats['total_response_time'] += elapsed

            if response.status_code == 200:
                data = response.json()
                self.token = data.get('access_token')
                self.user_info = data.get('user', {})
                self.session.headers.update({'Authorization': f'Bearer {self.token}'})
                self.stats['requests_succeeded'] += 1
                self.log(f"✅ Logged in successfully ({elapsed:.2f}s) - Region: {self.user_info.get('region', 'N/A')}")
                return True
            else:
                self.stats['requests_failed'] += 1
                self.stats['errors'].append(f"Login failed: {response.status_code}")
                self.log(f"❌ Login failed: {response.status_code}")
                return False

        except Exception as e:
            self.stats['requests_failed'] += 1
            self.stats['errors'].append(f"Login error: {str(e)}")
            self.log(f"❌ Login error: {e}")
            return False

    def get_devices(self, region_filter: str = None) -> List[Dict]:
        """Get device list (simulates Monitor page load)"""
        try:
            start = time.time()

            params = {}
            if region_filter:
                params['region'] = region_filter

            response = self.session.get(
                f"{self.base_url}/api/v1/devices/standalone/list",
                params=params,
                timeout=15
            )

            elapsed = time.time() - start
            self.stats['requests_sent'] += 1
            self.stats['total_response_time'] += elapsed

            if response.status_code == 200:
                devices = response.json()
                self.stats['requests_succeeded'] += 1
                self.log(f"📋 Loaded {len(devices)} devices ({elapsed:.2f}s)")
                return devices
            else:
                self.stats['requests_failed'] += 1
                self.stats['errors'].append(f"Get devices failed: {response.status_code}")
                self.log(f"❌ Failed to get devices: {response.status_code}")
                return []

        except Exception as e:
            self.stats['requests_failed'] += 1
            self.stats['errors'].append(f"Get devices error: {str(e)}")
            self.log(f"❌ Get devices error: {e}")
            return []

    def get_device_details(self, device_id: str, device_name: str) -> bool:
        """Get device details (simulates clicking on a device)"""
        try:
            start = time.time()

            # Get device status history (last 7 days)
            response = self.session.get(
                f"{self.base_url}/api/v1/devices/standalone/{device_id}/history",
                params={'hours': 168},  # 7 days
                timeout=20
            )

            elapsed = time.time() - start
            self.stats['requests_sent'] += 1
            self.stats['total_response_time'] += elapsed

            if response.status_code == 200:
                self.stats['requests_succeeded'] += 1
                self.log(f"🔍 Viewed device '{device_name}' details ({elapsed:.2f}s)")
                return True
            else:
                self.stats['requests_failed'] += 1
                self.stats['errors'].append(f"Get device details failed: {response.status_code}")
                self.log(f"❌ Failed to get device details: {response.status_code}")
                return False

        except Exception as e:
            self.stats['requests_failed'] += 1
            self.stats['errors'].append(f"Get device details error: {str(e)}")
            self.log(f"❌ Get device details error: {e}")
            return False

    def get_dashboard_stats(self) -> bool:
        """Get dashboard statistics"""
        try:
            start = time.time()

            response = self.session.get(
                f"{self.base_url}/api/v1/dashboard/stats",
                timeout=15
            )

            elapsed = time.time() - start
            self.stats['requests_sent'] += 1
            self.stats['total_response_time'] += elapsed

            if response.status_code == 200:
                self.stats['requests_succeeded'] += 1
                stats = response.json()
                self.log(f"📊 Dashboard: {stats.get('total_devices', 0)} devices, "
                        f"{stats.get('devices_up', 0)} UP, {stats.get('devices_down', 0)} DOWN ({elapsed:.2f}s)")
                return True
            else:
                self.stats['requests_failed'] += 1
                self.stats['errors'].append(f"Get dashboard failed: {response.status_code}")
                self.log(f"❌ Failed to get dashboard: {response.status_code}")
                return False

        except Exception as e:
            self.stats['requests_failed'] += 1
            self.stats['errors'].append(f"Get dashboard error: {str(e)}")
            self.log(f"❌ Get dashboard error: {e}")
            return False

    def get_alerts(self) -> bool:
        """Get alert history"""
        try:
            start = time.time()

            response = self.session.get(
                f"{self.base_url}/api/v1/alerts/history",
                params={'limit': 50},
                timeout=15
            )

            elapsed = time.time() - start
            self.stats['requests_sent'] += 1
            self.stats['total_response_time'] += elapsed

            if response.status_code == 200:
                alerts = response.json()
                self.stats['requests_succeeded'] += 1
                self.log(f"🚨 Loaded {len(alerts)} alerts ({elapsed:.2f}s)")
                return True
            else:
                self.stats['requests_failed'] += 1
                self.stats['errors'].append(f"Get alerts failed: {response.status_code}")
                self.log(f"❌ Failed to get alerts: {response.status_code}")
                return False

        except Exception as e:
            self.stats['requests_failed'] += 1
            self.stats['errors'].append(f"Get alerts error: {str(e)}")
            self.log(f"❌ Get alerts error: {e}")
            return False

    def run_user_session(self):
        """Simulate a complete user session"""
        # Login
        if not self.login():
            self.log("⚠️  Login failed, stopping session")
            return

        start_time = time.time()
        iteration = 0

        try:
            while (time.time() - start_time) < self.duration:
                iteration += 1
                self.log(f"--- Iteration {iteration} ---")

                # 1. Load Monitor page (with region filter if user has region)
                user_region = self.user_info.get('region')
                devices = self.get_devices(region_filter=user_region)

                if devices:
                    # 2. Click on 2-3 random devices to view details
                    sample_size = min(3, len(devices))
                    sampled_devices = random.sample(devices, sample_size)

                    for device in sampled_devices:
                        self.get_device_details(device['id'], device['name'])
                        time.sleep(random.uniform(1, 3))  # Simulate reading time

                # 3. Navigate to Dashboard
                time.sleep(random.uniform(2, 4))
                self.get_dashboard_stats()

                # 4. Check Alerts
                time.sleep(random.uniform(1, 3))
                self.get_alerts()

                # 5. Wait before next iteration (simulate user thinking/reading)
                wait_time = random.uniform(5, 15)
                self.log(f"💤 Waiting {wait_time:.1f}s before next action...")
                time.sleep(wait_time)

        except KeyboardInterrupt:
            self.log("⚠️  Interrupted by user")
        except Exception as e:
            self.log(f"❌ Session error: {e}")

        # Print final stats
        self.print_stats()

    def print_stats(self):
        """Print session statistics"""
        avg_response_time = (
            self.stats['total_response_time'] / self.stats['requests_sent']
            if self.stats['requests_sent'] > 0
            else 0
        )

        success_rate = (
            (self.stats['requests_succeeded'] / self.stats['requests_sent'] * 100)
            if self.stats['requests_sent'] > 0
            else 0
        )

        print(f"\n{'='*60}")
        print(f"📊 Statistics for {self.username}")
        print(f"{'='*60}")
        print(f"Total Requests:    {self.stats['requests_sent']}")
        print(f"Successful:        {self.stats['requests_succeeded']} ({success_rate:.1f}%)")
        print(f"Failed:            {self.stats['requests_failed']}")
        print(f"Avg Response Time: {avg_response_time:.2f}s")

        if self.stats['errors']:
            print(f"\n⚠️  Errors ({len(self.stats['errors'])}):")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                print(f"   - {error}")
            if len(self.stats['errors']) > 5:
                print(f"   ... and {len(self.stats['errors']) - 5} more")

        print(f"{'='*60}\n")


class StressTestCoordinator:
    """Coordinates multiple regional manager simulations"""

    def __init__(self, base_url: str, num_users: int, duration: int):
        self.base_url = base_url
        self.num_users = num_users
        self.duration = duration
        self.threads = []
        self.simulators = []

    def run(self):
        """Run stress test with multiple users"""
        print(f"\n🚀 Starting UI Stress Test")
        print(f"{'='*60}")
        print(f"Target URL:    {self.base_url}")
        print(f"Users:         {self.num_users} (test1 - test{self.num_users})")
        print(f"Duration:      {self.duration} seconds ({self.duration/60:.1f} minutes)")
        print(f"Start Time:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        # Create simulators for each test user
        for i in range(1, self.num_users + 1):
            username = f"test{i}"
            password = f"test{i}"
            simulator = RegionalManagerSimulator(username, password, self.base_url, self.duration)
            self.simulators.append(simulator)

        # Start all threads with slight delay to avoid thundering herd
        for i, simulator in enumerate(self.simulators):
            thread = threading.Thread(target=simulator.run_user_session, daemon=True)
            self.threads.append(thread)
            thread.start()
            time.sleep(0.5)  # 500ms delay between starting each user

        # Wait for all threads to complete
        try:
            for thread in self.threads:
                thread.join()
        except KeyboardInterrupt:
            print("\n⚠️  Stress test interrupted by user. Waiting for threads to finish...")
            for thread in self.threads:
                thread.join(timeout=5)

        # Print aggregate stats
        self.print_aggregate_stats()

    def print_aggregate_stats(self):
        """Print aggregate statistics across all users"""
        total_requests = sum(s.stats['requests_sent'] for s in self.simulators)
        total_succeeded = sum(s.stats['requests_succeeded'] for s in self.simulators)
        total_failed = sum(s.stats['requests_failed'] for s in self.simulators)
        total_response_time = sum(s.stats['total_response_time'] for s in self.simulators)

        avg_response_time = (total_response_time / total_requests) if total_requests > 0 else 0
        success_rate = (total_succeeded / total_requests * 100) if total_requests > 0 else 0

        print(f"\n{'='*60}")
        print(f"📊 AGGREGATE STATISTICS - ALL USERS")
        print(f"{'='*60}")
        print(f"Total Users:       {self.num_users}")
        print(f"Total Requests:    {total_requests}")
        print(f"Successful:        {total_succeeded} ({success_rate:.1f}%)")
        print(f"Failed:            {total_failed}")
        print(f"Avg Response Time: {avg_response_time:.2f}s")
        print(f"Requests/Second:   {total_requests/self.duration:.2f}")
        print(f"{'='*60}\n")

        # Show per-user summary
        print(f"\n📋 Per-User Summary:")
        print(f"{'User':<10} {'Requests':<12} {'Success Rate':<15} {'Avg Response':<15}")
        print(f"{'-'*60}")
        for simulator in self.simulators:
            success_rate = (
                (simulator.stats['requests_succeeded'] / simulator.stats['requests_sent'] * 100)
                if simulator.stats['requests_sent'] > 0
                else 0
            )
            avg_time = (
                simulator.stats['total_response_time'] / simulator.stats['requests_sent']
                if simulator.stats['requests_sent'] > 0
                else 0
            )
            print(f"{simulator.username:<10} {simulator.stats['requests_sent']:<12} "
                  f"{success_rate:<14.1f}% {avg_time:<14.2f}s")

        print(f"\n✅ Stress test completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    parser = argparse.ArgumentParser(
        description='UI Stress Test - Simulate Regional Managers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with 10 users for 5 minutes
  python3 scripts/stress_test_ui.py --url http://localhost:5001 --users 10 --duration 300

  # Test production with 5 users for 2 minutes
  python3 scripts/stress_test_ui.py --url https://ward-ops.example.com --users 5 --duration 120

Notes:
  - Ensure test users (test1/test1 through test10/test10) are created in the system
  - Each user should have a different region assigned for realistic testing
  - Monitor system resources during the test
        """
    )

    parser.add_argument('--url', required=True, help='Ward-Ops base URL (e.g., http://localhost:5001)')
    parser.add_argument('--users', type=int, default=10, help='Number of concurrent users (default: 10)')
    parser.add_argument('--duration', type=int, default=300, help='Test duration in seconds (default: 300 = 5 minutes)')

    args = parser.parse_args()

    # Validate inputs
    if args.users < 1 or args.users > 10:
        print("❌ Error: Number of users must be between 1 and 10")
        sys.exit(1)

    if args.duration < 10:
        print("❌ Error: Duration must be at least 10 seconds")
        sys.exit(1)

    # Run stress test
    coordinator = StressTestCoordinator(args.url, args.users, args.duration)
    coordinator.run()


if __name__ == '__main__':
    main()
