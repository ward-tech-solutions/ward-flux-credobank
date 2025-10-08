#!/usr/bin/env python3
"""
Seed the WARD FLUX database with canonical baseline data.

This script is idempotent: running it multiple times will not duplicate rows.
It relies on structured JSON files in seeds/core and environment variables for sensitive values.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

logger = logging.getLogger("seed_core")


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


def ensure_default_password(record: Dict[str, Any]) -> str:
    password_env = record.get("default_password_env", "DEFAULT_ADMIN_PASSWORD")
    password = os.getenv(password_env)
    if not password:
        raise RuntimeError(
            f"Environment variable {password_env} must be set to seed user {record.get('username')}"
        )
    return password


def seed_users(session, users_path: Path) -> None:
    from database import User, UserRole  # Imported lazily after DB URL is configured
    from auth import get_password_hash

    for record in load_json(users_path):
        username = record["username"]
        existing = session.query(User).filter(User.username == username).one_or_none()
        if existing:
            logger.debug("User %s already present – skipping", username)
            continue

        password = ensure_default_password(record)
        user = User(
            username=username,
            email=record["email"],
            full_name=record.get("full_name"),
            role=UserRole(record.get("role", UserRole.ADMIN.value)),
            is_active=record.get("is_active", True),
            is_superuser=record.get("is_superuser", False),
            hashed_password=get_password_hash(password),
        )
        session.add(user)
        logger.info("Seeded user %s", username)


def seed_monitoring_profiles(session, profiles_path: Path) -> Optional[str]:
    from monitoring.models import MonitoringProfile, MonitoringMode

    active_profile_name: Optional[str] = None

    for record in load_json(profiles_path):
        profile = session.query(MonitoringProfile).filter_by(name=record["name"]).one_or_none()
        if profile:
            logger.debug("Monitoring profile %s already present – skipping", record["name"])
        else:
            profile = MonitoringProfile(
                name=record["name"],
                mode=MonitoringMode(record["mode"]),
                description=record.get("description"),
                is_active=record.get("is_active", False),
            )
            session.add(profile)
            logger.info("Seeded monitoring profile %s", record["name"])

        if record.get("is_active"):
            active_profile_name = record["name"]

    return active_profile_name


def activate_monitoring_profile(session, profile_name: Optional[str]) -> None:
    if not profile_name:
        return
    from monitoring.models import MonitoringProfile

    profile = session.query(MonitoringProfile).filter_by(name=profile_name).one_or_none()
    if not profile:
        logger.warning("Requested active profile %s missing, skipping activation", profile_name)
        return

    session.query(MonitoringProfile).update({"is_active": False})
    profile.is_active = True
    logger.info("Activated monitoring profile %s", profile_name)


def seed_system_config(session, config_path: Path) -> None:
    from models import SystemConfig

    for record in load_json(config_path):
        existing = session.query(SystemConfig).filter_by(key=record["key"]).one_or_none()
        if existing:
            logger.debug("System config %s already present – skipping", record["key"])
            continue

        entry = SystemConfig(
            key=record["key"],
            value=record.get("value"),
            description=record.get("description"),
        )
        session.add(entry)
        logger.info("Seeded system config %s", record["key"])


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed the WARD FLUX core database records.")
    parser.add_argument(
        "--database-url",
        dest="database_url",
        help="SQLAlchemy database URL. Overrides DATABASE_URL environment variable.",
    )
    parser.add_argument(
        "--seeds-dir",
        dest="seeds_dir",
        default="seeds/core",
        help="Path to directory containing JSON seed files (default: seeds/core)",
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
        seed_users(session, seeds_dir / "users.json")
        active_profile = seed_monitoring_profiles(session, seeds_dir / "monitoring_profiles.json")
        seed_system_config(session, seeds_dir / "system_config.json")
        if active_profile:
            activate_monitoring_profile(session, active_profile)
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Seeding failed. Rolled back transaction.")
        return 1
    finally:
        session.close()

    logger.info("Seeding completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
