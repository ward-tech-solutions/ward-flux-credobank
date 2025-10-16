"""
Run migration 005 - Add monitoring tables
Supports both SQLite and PostgreSQL
"""
import sys
import uuid
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import engine, SessionLocal
from sqlalchemy import text

def run_migration():
    """Run monitoring tables migration"""
    db = SessionLocal()

    try:
        # Read SQL migration file
        sql_file = Path(__file__).parent / "005_add_monitoring_tables.sql"
        with open(sql_file) as f:
            sql_content = f.read()

        # Split into individual statements (skip the INSERT for now)
        statements = sql_content.split(';')

        # Execute each statement
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt:
                continue

            # Skip the INSERT statement (we'll handle it separately)
            if 'INSERT INTO monitoring_profiles' in stmt:
                continue

            # Execute CREATE TABLE and INDEX statements
            if stmt.startswith('CREATE') or stmt.startswith('--'):
                if not stmt.startswith('--'):
                    db.execute(text(stmt))

        # Insert default profile using Python UUID (works for both SQLite and PostgreSQL)
        check_query = "SELECT COUNT(*) FROM monitoring_profiles WHERE name = 'Default Profile'"
        result = db.execute(text(check_query)).scalar()

        if result == 0:
            default_profile_id = str(uuid.uuid4())
            insert_query = """
            INSERT INTO monitoring_profiles (id, name, mode, is_active, description, created_at, updated_at)
            VALUES (:id, :name, :mode, :is_active, :description, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            db.execute(text(insert_query), {
                'id': default_profile_id,
                'name': 'Default Profile',
                'mode': 'STANDALONE',  # Uppercase to match Python enum
                'is_active': False,
                'description': 'Default monitoring profile - activate to enable standalone monitoring'
            })

        db.commit()
        print("✓ Monitoring tables created successfully")
        print("✓ Default monitoring profile created")

    except Exception as e:
        db.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
