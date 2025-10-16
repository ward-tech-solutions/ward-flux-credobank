"""
WARD TECH SOLUTIONS - Initialize Setup Database
Creates tables for multi-tenant setup wizard and runs SQL migrations
"""
import logging
import sqlite3
import os
from database import engine, Base, User
from models import Organization, SystemConfig, SetupWizardState

logger = logging.getLogger(__name__)


def run_sql_migrations():
    """Run SQL migration files"""
    logger.info("Running SQL migrations...")

    migrations_dir = "migrations"
    if not os.path.exists(migrations_dir):
        logger.info("⚠️  No migrations directory found")
        return

    # Get database path from engine URL
    db_path = str(engine.url).replace("sqlite:///", "")

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all SQL files in migrations directory
    sql_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith(".sql")])

    for sql_file in sql_files:
        sql_path = os.path.join(migrations_dir, sql_file)
        logger.info(f"  Running {sql_file}...")

        with open(sql_path, "r") as f:
            sql_script = f.read()

        try:
            cursor.executescript(sql_script)
            conn.commit()
            logger.info(f"  ✅ {sql_file} completed")
        except Exception as e:
            logger.info(f"  ⚠️  {sql_file} error (may be already applied): {e}")

    conn.close()
    logger.info("✅ SQL migrations completed!")


def init_setup_tables():
    """Create all setup-related tables"""
    logger.info("Creating setup wizard tables...")

    # Create all tables defined in models
    Base.metadata.create_all(bind=engine)

    logger.info("✅ Setup tables created successfully!")
    logger.info("\nTables created:")
    logger.info("  - organizations")
    logger.info("  - system_config")
    logger.info("  - setup_wizard_state")
    logger.info("  - users")

    # Run SQL migrations for georgian_cities, etc.
    run_sql_migrations()


if __name__ == "__main__":
    init_setup_tables()
