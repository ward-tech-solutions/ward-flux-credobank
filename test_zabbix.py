#!/usr/bin/env python3
"""
Diagnostic script to test Zabbix connection and group IDs
"""
import sqlite3
from zabbix_client import ZabbixClient

def test_connection():
    print("="*60)
    print("WARD OPS - Zabbix Connection Diagnostic")
    print("="*60)

    # Test 1: Check database
    print("\n[1] Checking database for monitored groups...")
    try:
        conn = sqlite3.connect('data/ward_ops.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT groupid, name, display_name, is_active
            FROM monitored_hostgroups
        """)
        groups = cursor.fetchall()

        if not groups:
            print("   ❌ No groups found in database!")
            print("   → Go to http://localhost:5001/config and click 'Fetch from Zabbix'")
        else:
            print(f"   ✅ Found {len(groups)} groups in database:")
            for g in groups:
                status = "✅ ACTIVE" if g['is_active'] else "❌ INACTIVE"
                print(f"      - {g['display_name']} (ID: {g['groupid']}) {status}")

        conn.close()
    except Exception as e:
        print(f"   ❌ Database error: {e}")
        return

    # Test 2: Connect to Zabbix
    print("\n[2] Testing Zabbix connection...")
    try:
        zabbix = ZabbixClient()
        print("   ✅ Successfully connected to Zabbix")
        print(f"   URL: {zabbix.url}")
        print(f"   User: {zabbix.user}")
    except Exception as e:
        print(f"   ❌ Failed to connect: {e}")
        return

    # Test 3: Get all host groups from Zabbix
    print("\n[3] Fetching host groups from Zabbix...")
    try:
        all_groups = zabbix.zapi.hostgroup.get(
            output=['groupid', 'name']
        )
        print(f"   ✅ Found {len(all_groups)} groups in Zabbix:")

        # Show groups that match our database
        if groups:
            db_groupids = {str(g['groupid']) for g in groups if g['is_active']}
            print(f"\n   Configured groups (from database):")
            for zg in all_groups:
                if str(zg['groupid']) in db_groupids:
                    print(f"      ✅ {zg['name']} (ID: {zg['groupid']})")

    except Exception as e:
        print(f"   ❌ Error fetching groups: {e}")
        return

    # Test 4: Get hosts from configured groups
    if groups:
        print("\n[4] Fetching hosts from configured groups...")
        try:
            active_groupids = [g['groupid'] for g in groups if g['is_active']]
            print(f"   Querying for group IDs: {active_groupids}")

            hosts = zabbix.get_all_hosts(group_ids=active_groupids)

            if not hosts:
                print(f"   ❌ No hosts found in these groups!")
                print(f"   → Check if hosts exist in Zabbix for these groups")
            else:
                print(f"   ✅ Found {len(hosts)} hosts")
                print(f"\n   Sample devices:")
                for host in hosts[:5]:
                    status = host.get('ping_status', 'Unknown')
                    print(f"      - {host['display_name']} ({host['ip']}) - {status}")

                if len(hosts) > 5:
                    print(f"      ... and {len(hosts) - 5} more")

        except Exception as e:
            print(f"   ❌ Error fetching hosts: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print("Diagnostic complete!")
    print("="*60)

if __name__ == "__main__":
    test_connection()
