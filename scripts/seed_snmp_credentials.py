#!/usr/bin/env python3
"""
Seed SNMP credentials for standalone devices.

Example:
    ./venv/bin/python scripts/seed_snmp_credentials.py --community XoNaz-Secret --tag Branches
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Iterable, List

from dotenv import load_dotenv

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import SessionLocal, init_db  # noqa: E402
from monitoring.models import SNMPCredential, StandaloneDevice  # noqa: E402
from monitoring.snmp.credentials import encrypt_credential  # noqa: E402

logger = logging.getLogger("seed_snmp_credentials")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed SNMP credentials for standalone devices")
    parser.add_argument("--community", required=True, help="SNMP community string (v2c)")
    parser.add_argument(
        "--tag",
        action="append",
        dest="tags",
        default=["Branches"],
        help="Device tag to filter on (repeatable). Defaults to 'Branches'.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing SNMP credentials instead of skipping",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without writing to the database",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    return parser.parse_args()


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


def device_has_tag(device: StandaloneDevice, tags: Iterable[str]) -> bool:
    device_tags = device.tags or []
    return any(tag in device_tags for tag in tags)


def seed_credentials(session, community: str, tags: List[str], overwrite: bool, dry_run: bool) -> dict:
    created = updated = skipped = 0

    devices: List[StandaloneDevice] = session.query(StandaloneDevice).all()
    logger.info("Found %s standalone devices", len(devices))

    for device in devices:
        if not device_has_tag(device, tags):
            continue

        existing = session.query(SNMPCredential).filter_by(device_id=device.id).one_or_none()

        if existing:
            if not overwrite:
                skipped += 1
                continue

            existing.version = "v2c"
            existing.community_encrypted = encrypt_credential(community)
            updated += 1
            logger.debug("Updated SNMP credential for %s (%s)", device.name, device.ip)
        else:
            credential = SNMPCredential(
                device_id=device.id,
                version="v2c",
                community_encrypted=encrypt_credential(community),
            )
            session.add(credential)
            created += 1
            logger.debug("Created SNMP credential for %s (%s)", device.name, device.ip)

    if dry_run:
        session.rollback()
    else:
        session.commit()

    return {"created": created, "updated": updated, "skipped": skipped}


def main() -> None:
    args = parse_args()
    configure_logging(args.verbose)
    load_dotenv()

    if not os.getenv("WARD_ENCRYPTION_KEY"):
        raise SystemExit(
            "WARD_ENCRYPTION_KEY environment variable is required for SNMP credential encryption."
        )

    init_db()
    session = SessionLocal()
    try:
        result = seed_credentials(session, args.community, args.tags, args.overwrite, args.dry_run)
        if args.dry_run:
            logger.info("Dry run complete. Use without --dry-run to apply changes.")
        logger.info("SNMP credential seeding summary: %s", result)
    finally:
        session.close()


if __name__ == "__main__":
    main()
