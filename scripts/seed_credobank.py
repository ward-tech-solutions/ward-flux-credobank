#!/usr/bin/env python3
"""
Seed CredoBank-specific data into the WARD FLUX database.

This script handles:
- Branches (128)
- Standalone Devices (875)
- Alert Rules (4)
- Georgian geographic data (regions and cities)

Runtime data (ping_results, alert_history, etc.) is NOT seeded.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from datetime import datetime
from decimal import Decimal
import uuid

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("seed_credobank")


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


def load_json(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        logger.warning("Seed file %s missing – skipping", path)
        return []
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
        if not isinstance(data, list):
            raise ValueError(f"Seed file {path} must contain a JSON array")
        return data


def convert_value(value: Any) -> Any:
    """Convert JSON values to proper Python types"""
    if value is None:
        return None
    if isinstance(value, str):
        # Try to parse ISO datetime strings
        if "T" in value and ("Z" in value or "+" in value or value.endswith(":00")):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
    return value


def seed_branches(session, branches_path: Path) -> None:
    from models import Branch

    for record in load_json(branches_path):
        branch_id = record.get("id")
        if branch_id:
            existing = session.query(Branch).filter(Branch.id == branch_id).one_or_none()
        else:
            existing = session.query(Branch).filter(Branch.name == record["name"]).one_or_none()

        if existing:
            logger.debug("Branch %s already present – skipping", record.get("name"))
            continue

        branch = Branch(
            id=str(uuid.UUID(branch_id)) if branch_id else str(uuid.uuid4()),
            name=record["name"],
            display_name=record.get("display_name", record["name"]),
            region=record.get("region"),
            branch_code=record.get("branch_code"),
            address=record.get("address"),
            is_active=record.get("is_active", True),
            device_count=record.get("device_count", 0),
            created_at=convert_value(record.get("created_at")),
            updated_at=convert_value(record.get("updated_at")),
        )
        session.add(branch)
        logger.info("Seeded branch %s", record["name"])


def seed_devices(session, devices_path: Path) -> None:
    from monitoring.models import StandaloneDevice

    for record in load_json(devices_path):
        device_id = record.get("id")
        if device_id:
            existing = session.query(StandaloneDevice).filter(StandaloneDevice.id == device_id).one_or_none()
        else:
            existing = session.query(StandaloneDevice).filter(StandaloneDevice.ip == record["ip"]).one_or_none()

        if existing:
            logger.debug("Device %s (%s) already present – skipping", record.get("name"), record.get("ip"))
            continue

        device = StandaloneDevice(
            id=uuid.UUID(device_id) if device_id else uuid.uuid4(),
            name=record["name"],
            ip=record["ip"],
            hostname=record.get("hostname"),
            vendor=record.get("vendor"),
            device_type=record.get("device_type"),
            model=record.get("model"),
            location=record.get("location"),
            description=record.get("description"),
            enabled=record.get("enabled", True),
            discovered_at=convert_value(record.get("discovered_at")),
            last_seen=convert_value(record.get("last_seen")),
            tags=record.get("tags"),
            custom_fields=record.get("custom_fields"),
            branch_id=record.get("branch_id"),  # Already a string
            normalized_name=record.get("normalized_name"),
            device_subtype=record.get("device_subtype"),
            floor_info=record.get("floor_info"),
            unit_number=record.get("unit_number"),
            original_name=record.get("original_name"),
            ssh_port=record.get("ssh_port", 22),
            ssh_username=record.get("ssh_username"),
            ssh_enabled=record.get("ssh_enabled", True),
            created_at=convert_value(record.get("created_at")),
            updated_at=convert_value(record.get("updated_at")),
        )
        session.add(device)
        logger.debug("Seeded device %s (%s)", record["name"], record["ip"])

    # Log summary
    total = len(list(load_json(devices_path)))
    logger.info("Seeded %d standalone devices", total)


def seed_alert_rules(session, alert_rules_path: Path) -> None:
    from monitoring.models import AlertRule

    for record in load_json(alert_rules_path):
        rule_id = record.get("id")
        if rule_id:
            existing = session.query(AlertRule).filter(AlertRule.id == rule_id).one_or_none()
        else:
            existing = session.query(AlertRule).filter(AlertRule.name == record["name"]).one_or_none()

        if existing:
            logger.debug("Alert rule %s already present – skipping", record.get("name"))
            continue

        rule = AlertRule(
            id=uuid.UUID(rule_id) if rule_id else uuid.uuid4(),
            device_id=uuid.UUID(record["device_id"]) if record.get("device_id") else None,
            branch_id=record.get("branch_id"),
            name=record["name"],
            description=record.get("description"),
            expression=record["expression"],
            severity=record["severity"],
            notification_channels=record.get("notification_channels"),
            notification_recipients=record.get("notification_recipients"),
            device_group=record.get("device_group"),
            monitoring_item_id=uuid.UUID(record["monitoring_item_id"]) if record.get("monitoring_item_id") else None,
            enabled=record.get("enabled", True),
            created_at=convert_value(record.get("created_at")),
            updated_at=convert_value(record.get("updated_at")),
        )
        session.add(rule)
        logger.info("Seeded alert rule %s", record["name"])


def seed_georgian_regions(session, regions_path: Path) -> None:
    from sqlalchemy import text

    for record in load_json(regions_path):
        region_id = record.get("id")

        # Check if exists using raw SQL
        existing = session.execute(
            text("SELECT id FROM georgian_regions WHERE id = :id"),
            {"id": region_id}
        ).fetchone()

        if existing:
            logger.debug("Region %s already present – skipping", record.get("name_en"))
            continue

        # Insert using raw SQL
        session.execute(
            text("""
                INSERT INTO georgian_regions (id, name_en, name_ka, latitude, longitude, created_at)
                VALUES (:id, :name_en, :name_ka, :latitude, :longitude, :created_at)
            """),
            {
                "id": region_id,
                "name_en": record["name_en"],
                "name_ka": record.get("name_ka"),
                "latitude": record.get("latitude"),
                "longitude": record.get("longitude"),
                "created_at": convert_value(record.get("created_at"))
            }
        )
        logger.info("Seeded region %s", record["name_en"])


def seed_georgian_cities(session, cities_path: Path) -> None:
    from sqlalchemy import text

    count = 0
    for record in load_json(cities_path):
        city_id = record.get("id")

        # Check if exists using raw SQL
        existing = session.execute(
            text("SELECT id FROM georgian_cities WHERE id = :id"),
            {"id": city_id}
        ).fetchone()

        if existing:
            logger.debug("City %s already present – skipping", record.get("name_en"))
            continue

        # Insert using raw SQL
        session.execute(
            text("""
                INSERT INTO georgian_cities (id, name_en, name_ka, region_id, latitude, longitude, is_active, created_at)
                VALUES (:id, :name_en, :name_ka, :region_id, :latitude, :longitude, :is_active, :created_at)
            """),
            {
                "id": city_id,
                "name_en": record["name_en"],
                "name_ka": record.get("name_ka"),
                "region_id": record.get("region_id"),
                "latitude": record.get("latitude"),
                "longitude": record.get("longitude"),
                "is_active": record.get("is_active", True),
                "created_at": convert_value(record.get("created_at"))
            }
        )
        logger.debug("Seeded city %s", record["name_en"])
        count += 1

    if count > 0:
        logger.info("Seeded %d Georgian cities", count)


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed CredoBank data into WARD FLUX database.")
    parser.add_argument(
        "--database-url",
        dest="database_url",
        help="SQLAlchemy database URL. Overrides DATABASE_URL environment variable.",
    )
    parser.add_argument(
        "--seeds-dir",
        dest="seeds_dir",
        default="seeds/credobank",
        help="Path to directory containing JSON seed files (default: seeds/credobank)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    configure_logging(args.verbose)

    seeds_dir = Path(args.seeds_dir).resolve()
    if not seeds_dir.exists():
        logger.error("Seeds directory %s not found", seeds_dir)
        return 2

    from database import init_db, SessionLocal

    init_db()
    session = SessionLocal()

    try:
        logger.info("Starting CredoBank data seeding...")

        # Seed in order of dependencies
        seed_georgian_regions(session, seeds_dir / "georgian_regions.json")
        seed_georgian_cities(session, seeds_dir / "georgian_cities.json")
        seed_branches(session, seeds_dir / "branches.json")
        seed_devices(session, seeds_dir / "devices.json")
        seed_alert_rules(session, seeds_dir / "alert_rules.json")

        session.commit()
        logger.info("✅ CredoBank seeding completed successfully")

    except Exception:
        session.rollback()
        logger.exception("Seeding failed. Rolled back transaction.")
        return 1
    finally:
        session.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
