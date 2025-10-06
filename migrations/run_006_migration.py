"""
Run migration 006 - Add standalone_devices table
Supports both SQLite and PostgreSQL
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import engine, SessionLocal
from sqlalchemy import text

def run_migration():
    """Run standalone devices table migration"""
    db = SessionLocal()

    try:
        # Read SQL migration file
        sql_file = Path(__file__).parent / "006_add_standalone_devices.sql"
        with open(sql_file) as f:
            sql_content = f.read()

        # Remove comments
        lines = sql_content.split('\n')
        sql_clean = '\n'.join([line for line in lines if not line.strip().startswith('--') and line.strip()])

        # Split into individual statements
        statements = sql_clean.split(';')

        # Execute each statement
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt or '/*' in stmt:
                continue

            # Execute CREATE statements
            if stmt.upper().startswith('CREATE'):
                db.execute(text(stmt))

        db.commit()
        print("✓ standalone_devices table created successfully")

    except Exception as e:
        db.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
