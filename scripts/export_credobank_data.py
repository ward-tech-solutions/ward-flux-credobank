#!/usr/bin/env python3
"""Export CredoBank devices to seed files"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from monitoring.models import StandaloneDevice, SNMPCredential, AlertRule, MonitoringProfile
from models import Branch, DiscoveryRule, DiscoveryCredential
from sqlalchemy import text

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is required")
    print("\nUsage:")
    print("  export DATABASE_URL='postgresql://user:pass@host:5432/dbname'")
    print("  python scripts/export_credobank_data.py")
    sys.exit(1)

def json_serial(obj):
    """JSON serializer for objects not serializable by default"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, 'hex'):  # UUID
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")

def export_model(session, model, filename):
    """Export a model to JSON"""
    records = session.query(model).all()
    data = []

    for record in records:
        item = {}
        for column in record.__table__.columns:
            value = getattr(record, column.name)
            item[column.name] = value
        data.append(item)

    output_dir = Path(__file__).parent.parent / "seeds" / "credobank"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, default=json_serial)

    print(f"✅ {filename:30} {len(data):5} records")
    return len(data)

def export_table(session, table_name, filename):
    """Export a raw SQL table to JSON

    Note: table_name must be from a trusted source (hard-coded values only).
    SQLAlchemy text() doesn't support table name parameters.
    """
    # Whitelist of allowed table names to prevent SQL injection
    ALLOWED_TABLES = {
        "georgian_regions",
        "georgian_cities",
        "branches",
        "standalone_devices",
        "alert_rules",
        "snmp_credentials",
        "discovery_rules",
        "discovery_credentials",
    }

    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"Table '{table_name}' is not in the allowed list")

    result = session.execute(text(f"SELECT * FROM {table_name}"))
    columns = result.keys()
    data = []

    for row in result:
        item = dict(zip(columns, row))
        data.append(item)

    output_dir = Path(__file__).parent.parent / "seeds" / "credobank"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, default=json_serial)

    print(f"✅ {filename:30} {len(data):5} records")
    return len(data)

def main():
    print("🔄 Connecting to local PostgreSQL database...\n")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    print("📦 Exporting CredoBank data:\n")

    try:
        total = 0
        # Geographic reference data (raw SQL tables without models)
        total += export_table(session, "georgian_regions", "georgian_regions.json")
        total += export_table(session, "georgian_cities", "georgian_cities.json")

        # Core CredoBank data
        total += export_model(session, Branch, "branches.json")
        total += export_model(session, StandaloneDevice, "devices.json")
        total += export_model(session, AlertRule, "alert_rules.json")

        # Optional/empty tables (included for completeness)
        total += export_model(session, SNMPCredential, "snmp_credentials.json")
        total += export_model(session, DiscoveryRule, "discovery_rules.json")
        total += export_model(session, DiscoveryCredential, "discovery_credentials.json")

        print(f"\n✨ Total: {total} records exported")
        print(f"📁 Location: seeds/credobank/\n")

        print("🚀 Next steps:")
        print("   1. git add seeds/credobank/")
        print("   2. git commit -m 'Add CredoBank 875 devices seed data'")
        print("   3. git push")
        print("   4. Wait for CI/CD (~15 min)")
        print("   5. Redeploy on server with new image")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        session.close()

if __name__ == "__main__":
    sys.exit(main())
