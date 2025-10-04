"""
WARD TECH SOLUTIONS - Initialize Setup Database
Creates tables for multi-tenant setup wizard and runs SQL migrations
"""
import sqlite3
import os
from database import engine, Base, User
from models import Organization, SystemConfig, SetupWizardState

def run_sql_migrations():
    """Run SQL migration files"""
    print("Running SQL migrations...")

    migrations_dir = "migrations"
    if not os.path.exists(migrations_dir):
        print("⚠️  No migrations directory found")
        return

    # Get database path from engine URL
    db_path = str(engine.url).replace('sqlite:///', '')

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all SQL files in migrations directory
    sql_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])

    for sql_file in sql_files:
        sql_path = os.path.join(migrations_dir, sql_file)
        print(f"  Running {sql_file}...")

        with open(sql_path, 'r') as f:
            sql_script = f.read()

        try:
            cursor.executescript(sql_script)
            conn.commit()
            print(f"  ✅ {sql_file} completed")
        except Exception as e:
            print(f"  ⚠️  {sql_file} error (may be already applied): {e}")

    conn.close()
    print("✅ SQL migrations completed!")

def init_setup_tables():
    """Create all setup-related tables"""
    print("Creating setup wizard tables...")

    # Create all tables defined in models
    Base.metadata.create_all(bind=engine)

    print("✅ Setup tables created successfully!")
    print("\nTables created:")
    print("  - organizations")
    print("  - system_config")
    print("  - setup_wizard_state")
    print("  - users")

    # Run SQL migrations for georgian_cities, etc.
    run_sql_migrations()

if __name__ == "__main__":
    init_setup_tables()
