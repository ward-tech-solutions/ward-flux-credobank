"""
Add alert trigger tracking columns to alert_rules table

This migration adds columns to track when alert rules are triggered:
- last_triggered_at: Timestamp of last trigger
- trigger_count_24h: Count of triggers in last 24 hours
- trigger_count_7d: Count of triggers in last 7 days
- affected_devices_count: Count of currently affected devices

Run with: python migrations/add_alert_trigger_tracking.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from sqlalchemy import text

def run_migration():
    """Add alert trigger tracking columns"""
    db = SessionLocal()

    try:
        print("Adding alert trigger tracking columns...")

        # Add columns one by one
        migrations = [
            "ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS last_triggered_at TIMESTAMP",
            "ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS trigger_count_24h INTEGER DEFAULT 0",
            "ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS trigger_count_7d INTEGER DEFAULT 0",
            "ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS affected_devices_count INTEGER DEFAULT 0"
        ]

        for migration in migrations:
            try:
                db.execute(text(migration))
                db.commit()
                print(f"✓ {migration.split('ADD COLUMN')[1].split()[2]}")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"  - {migration.split('ADD COLUMN')[1].split()[2]} (already exists)")
                else:
                    raise

        print("\n✅ Migration completed successfully!")
        print("\nNew columns added:")
        print("  - last_triggered_at (TIMESTAMP)")
        print("  - trigger_count_24h (INTEGER, default 0)")
        print("  - trigger_count_7d (INTEGER, default 0)")
        print("  - affected_devices_count (INTEGER, default 0)")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
