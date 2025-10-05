"""
WARD TECH SOLUTIONS - Database Migration Tool
Migrate data from SQLite to PostgreSQL
"""
import logging
import os
import sys
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()


def migrate_sqlite_to_postgres(sqlite_path: str, postgres_url: str):
    """
    Migrate all data from SQLite to PostgreSQL

    Args:
        sqlite_path: Path to SQLite database file
        postgres_url: PostgreSQL connection string
    """
    logger.info("🔄 Starting database migration from SQLite to PostgreSQL...")

    # Create engines
    sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
    postgres_engine = create_engine(postgres_url)

    # Create sessions
    SqliteSession = sessionmaker(bind=sqlite_engine)
    PostgresSession = sessionmaker(bind=postgres_engine)

    sqlite_session = SqliteSession()
    postgres_session = PostgresSession()

    # Reflect metadata
    metadata = MetaData()
    metadata.reflect(bind=sqlite_engine)

    # Create all tables in PostgreSQL
    logger.info("📊 Creating tables in PostgreSQL...")
    from database import Base

    try:
        from models import Organization, SystemConfig, SetupWizardState
    except ImportError:
        pass

    Base.metadata.create_all(bind=postgres_engine)
    logger.info("✅ Tables created")

    # Migrate data table by table
    tables_migrated = 0
    total_rows = 0

    for table_name in metadata.tables:
        logger.info(f"📦 Migrating table: {table_name}...")

        table = Table(table_name, metadata, autoload_with=sqlite_engine)

        # Read all rows from SQLite
        sqlite_rows = sqlite_session.execute(table.select()).fetchall()

        if sqlite_rows:
            # Convert to dictionaries
            rows_data = []
            for row in sqlite_rows:
                row_dict = dict(row._mapping)
                rows_data.append(row_dict)

            # Insert into PostgreSQL
            try:
                postgres_session.execute(table.insert(), rows_data)
                postgres_session.commit()
                logger.info(f"   ✅ Migrated {len(rows_data)} rows")
                tables_migrated += 1
                total_rows += len(rows_data)
            except Exception as e:
                logger.info(f"   ⚠️  Error migrating {table_name}: {e}")
                postgres_session.rollback()
        else:
            logger.info(f"   ℹ️  No data to migrate")

    sqlite_session.close()
    postgres_session.close()

    logger.info(f"\n✅ Migration complete!")
    logger.info(f"   Tables migrated: {tables_migrated}")
    logger.info(f"   Total rows: {total_rows}")
    logger.info(f"   PostgreSQL is now ready to use!")


if __name__ == "__main__":
    # Default paths
    sqlite_path = "data/ward_ops.db"
    postgres_url = os.getenv("DATABASE_URL")

    # Check if PostgreSQL URL is provided
    if not postgres_url or not postgres_url.startswith("postgresql"):
        logger.info("❌ Error: DATABASE_URL must be set to a PostgreSQL connection string")
        logger.info("   Example: postgresql://user:password@localhost:5432/database")
        sys.exit(1)

    # Check if SQLite file exists
    if not os.path.exists(sqlite_path):
        logger.info(f"❌ Error: SQLite database not found at {sqlite_path}")
        logger.info("   If this is a fresh installation, no migration is needed.")
        sys.exit(1)

    # Confirm migration
    logger.info(f"📍 SQLite source: {sqlite_path}")
    logger.info(f"📍 PostgreSQL target: {postgres_url}")
    print()
    response = input("⚠️  This will migrate all data to PostgreSQL. Continue? (yes/no): ")

    if response.lower() in ["yes", "y"]:
        migrate_sqlite_to_postgres(sqlite_path, postgres_url)
    else:
        logger.info("❌ Migration cancelled")
