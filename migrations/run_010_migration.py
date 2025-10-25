#!/usr/bin/env python3
"""
Migration Runner: 010_add_device_interfaces.sql
Purpose: Create device_interfaces table for SNMP interface discovery
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import engine
from sqlalchemy import text

def run_migration():
    """Run the device_interfaces migration"""
    print("=" * 60)
    print("Running Migration 010: Add device_interfaces table")
    print("=" * 60)

    migration_file = os.path.join(os.path.dirname(__file__), "010_add_device_interfaces.sql")

    print(f"Reading migration file: {migration_file}")
    with open(migration_file, "r") as f:
        migration_sql = f.read()

    print("\nExecuting migration...")
    try:
        with engine.begin() as conn:
            # Execute the migration SQL
            conn.execute(text(migration_sql))
            print("\n✅ Migration completed successfully!")

            # Verify tables were created
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('device_interfaces', 'interface_metrics_summary')
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]

            print("\n✅ Created tables:")
            for table in tables:
                print(f"   - {table}")

            # Count indexes
            result = conn.execute(text("""
                SELECT COUNT(*)
                FROM pg_indexes
                WHERE tablename IN ('device_interfaces', 'interface_metrics_summary')
            """))
            index_count = result.scalar()
            print(f"\n✅ Created {index_count} indexes")

            # Show table structure
            print("\n" + "=" * 60)
            print("device_interfaces table structure:")
            print("=" * 60)
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'device_interfaces'
                ORDER BY ordinal_position
            """))

            print(f"\n{'Column':<30} {'Type':<20} {'Nullable':<10} {'Default':<30}")
            print("-" * 90)
            for row in result:
                col_name, data_type, nullable, default = row
                default_str = str(default)[:28] + ".." if default and len(str(default)) > 30 else (default or "")
                print(f"{col_name:<30} {data_type:<20} {nullable:<10} {default_str:<30}")

    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        raise

    print("\n" + "=" * 60)
    print("Migration 010 complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Implement interface parser (monitoring/interface_parser.py)")
    print("2. Add DeviceInterface model (monitoring/models.py)")
    print("3. Create discovery task (monitoring/tasks_interface_discovery.py)")
    print("4. Wait for SNMP whitelist (network admins)")

if __name__ == "__main__":
    run_migration()
