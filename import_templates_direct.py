#!/usr/bin/env python3
"""
Import default templates directly to database
"""
import json
import uuid
from pathlib import Path
from datetime import datetime
from database import SessionLocal
from monitoring.models import MonitoringTemplate

db = SessionLocal()

templates_dir = Path("monitoring/templates")
imported = []
skipped = []
failed = []

for template_file in templates_dir.glob("*.json"):
    try:
        with open(template_file, 'r') as f:
            template_data = json.load(f)

        # Check if template already exists
        existing = db.query(MonitoringTemplate).filter_by(name=template_data["name"]).first()
        if existing:
            skipped.append(template_data["name"])
            print(f"⊘ Skipped: {template_data['name']} (already exists)")
            continue

        # Create template
        new_template = MonitoringTemplate(
            id=uuid.uuid4(),
            name=template_data["name"],
            description=template_data.get("description"),
            vendor=template_data.get("vendor"),
            device_types=template_data.get("device_types", []),
            items=template_data.get("items", []),
            triggers=template_data.get("triggers", []),
            is_default=template_data.get("is_default", True),
            created_by=None,  # System import
        )

        db.add(new_template)
        imported.append(template_data["name"])
        print(f"✓ Imported: {template_data['name']} ({template_data.get('vendor', 'Generic')})")

    except Exception as e:
        failed.append({"file": template_file.name, "error": str(e)})
        print(f"❌ Failed: {template_file.name} - {e}")

if imported:
    db.commit()
    print(f"\n✅ Committed {len(imported)} templates to database")
else:
    print(f"\nℹ️  No new templates to import")

db.close()

print(f"\nSummary:")
print(f"  Imported: {len(imported)}")
print(f"  Skipped: {len(skipped)}")
print(f"  Failed: {len(failed)}")
