#!/usr/bin/env python3
"""
Import Zabbix hosts into the standalone monitoring inventory.

Usage examples:
    python scripts/import_zabbix_to_standalone.py
    python scripts/import_zabbix_to_standalone.py --group "Branches" --group "ATM ICMP"
    python scripts/import_zabbix_to_standalone.py --reset --dry-run

Environment variables:
    ZABBIX_URL, ZABBIX_USER, ZABBIX_PASSWORD
"""
from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

from dotenv import load_dotenv
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[1]
import sys

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import SessionLocal, init_db
from monitoring.models import MonitoringMode, MonitoringProfile, StandaloneDevice
from zabbix_client import ZabbixClient

logger = logging.getLogger("import_zabbix_to_standalone")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Zabbix hosts into standalone inventory")
    parser.add_argument(
        "--group",
        dest="groups",
        action="append",
        help="Zabbix host group name to include (repeatable). Defaults to client defaults when omitted.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Simulate import without modifying the database")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing standalone device records before importing",
    )
    parser.add_argument(
        "--delete-missing",
        action="store_true",
        help="Remove standalone devices whose IPs are no longer present in Zabbix",
    )
    parser.add_argument(
        "--activate-standalone",
        action="store_true",
        help="Set the active monitoring profile to standalone mode after import",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging output")
    return parser.parse_args()


def require_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise SystemExit(f"Environment variable {key} is required")
    return value


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


def normalize_branch(branch: str | None, ip: str | None) -> str | None:
    if not branch:
        return None
    cleaned = branch.strip()
    if not cleaned or not ip:
        return cleaned
    cleaned = cleaned.replace(ip, "").strip()
    # Remove trailing punctuation or stray characters
    return cleaned.rstrip(" .")


def location_from_host(host: dict) -> str | None:
    region = (host.get("region") or "").strip()
    branch = normalize_branch(host.get("branch"), host.get("ip"))
    if region and branch:
        return f"{region} / {branch}"
    return branch or region or None


def fetch_hosts(client: ZabbixClient, groups: Iterable[str] | None) -> List[dict]:
    logger.info("Fetching hosts from Zabbix …")
    hosts = client.get_all_hosts(group_names=list(groups) if groups else None, use_cache=False)
    logger.info("Fetched %s hosts", len(hosts))
    return hosts


def update_or_create_device(session: Session, host: dict) -> str:
    ip = (host.get("ip") or "").strip()
    if not ip or ip in {"", "0.0.0.0", "N/A"}:
        logger.debug("Skipping host %s because it has no usable IP", host.get("display_name") or host.get("hostname"))
        return "skipped_no_ip"

    name = (host.get("display_name") or host.get("hostname") or ip).strip()
    existing = session.query(StandaloneDevice).filter(StandaloneDevice.ip == ip).one_or_none()

    updated_at = datetime.now(timezone.utc)
    last_check = host.get("last_check")
    last_seen = None
    if last_check:
        try:
            last_seen = datetime.fromtimestamp(int(last_check), tz=timezone.utc)
        except (TypeError, ValueError):
            last_seen = updated_at

    location = location_from_host(host)
    device_type = host.get("device_type") or "unknown"

    custom_fields = {
        "zabbix_hostid": host.get("hostid"),
        "status": host.get("status"),
        "available": host.get("available"),
        "ping_status": host.get("ping_status"),
        "branch": normalize_branch(host.get("branch"), ip),
        "region": host.get("region"),
        "latitude": host.get("latitude"),
        "longitude": host.get("longitude"),
        "problems": host.get("problems"),
        "source": "zabbix",
        "synced_at": updated_at.isoformat(),
    }

    enabled = (host.get("status") or "").lower() == "enabled"

    if existing:
        existing.name = name
        existing.device_type = device_type
        existing.vendor = existing.vendor or None
        existing.location = location
        existing.description = f"Imported from Zabbix host {host.get('hostid')}"
        existing.tags = host.get("groups", [])
        existing.custom_fields = custom_fields
        existing.enabled = enabled
        existing.last_seen = last_seen or updated_at
        existing.updated_at = updated_at
        result = "updated"
    else:
        device = StandaloneDevice(
            name=name,
            ip=ip,
            hostname=host.get("hostname"),
            vendor=None,
            device_type=device_type,
            model=None,
            location=location,
            description=f"Imported from Zabbix host {host.get('hostid')}",
            enabled=enabled,
            discovered_at=updated_at,
            last_seen=last_seen or updated_at,
            tags=host.get("groups", []),
            custom_fields=custom_fields,
            created_at=updated_at,
            updated_at=updated_at,
        )
        session.add(device)
        result = "created"

    return result


def delete_missing_devices(session: Session, zabbix_ips: set[str], dry_run: bool) -> int:
    devices = session.query(StandaloneDevice).all()
    removed = 0
    for device in devices:
        if (device.ip or "").strip() and device.ip not in zabbix_ips:
            logger.info("Removing standalone device %s (%s) – no longer present in Zabbix", device.name, device.ip)
            session.delete(device)
            removed += 1

    if dry_run:
        session.rollback()
    else:
        session.commit()
    return removed


def activate_standalone_profile(session: Session) -> None:
    profile = session.query(MonitoringProfile).filter_by(is_active=True).first()
    if profile:
        profile.mode = MonitoringMode.STANDALONE
        profile.is_active = True
        session.commit()
        logger.info("Activated existing monitoring profile in standalone mode")
        return

    profile = session.query(MonitoringProfile).first()
    if profile:
        profile.mode = MonitoringMode.STANDALONE
        profile.is_active = True
        session.commit()
        logger.info("Enabled monitoring profile '%s' in standalone mode", profile.name)
        return

    profile = MonitoringProfile(name="Standalone Profile", mode=MonitoringMode.STANDALONE, is_active=True)
    session.add(profile)
    session.commit()
    logger.info("Created new standalone monitoring profile")


def main() -> None:
    args = parse_args()
    configure_logging(args.verbose)
    load_dotenv()

    require_env("ZABBIX_URL")
    require_env("ZABBIX_USER")
    require_env("ZABBIX_PASSWORD")

    init_db()
    client = ZabbixClient()

    hosts = fetch_hosts(client, args.groups)
    if not hosts:
        logger.warning("No hosts returned from Zabbix. Nothing to import.")
        return

    session = SessionLocal()
    try:
        if args.reset and not args.dry_run:
            logger.info("Reset requested – clearing existing standalone devices")
            session.query(StandaloneDevice).delete()
            session.commit()

        created = updated = skipped = 0
        for host in hosts:
            action = update_or_create_device(session, host)
            if action == "created":
                created += 1
            elif action == "updated":
                updated += 1
            elif action == "skipped_no_ip":
                skipped += 1

        if not args.dry_run:
            session.commit()
        else:
            session.rollback()

        logger.info("Import summary: created=%s updated=%s skipped=%s", created, updated, skipped)

        if args.delete_missing:
            zabbix_ips = {host.get("ip") for host in hosts if host.get("ip")}
            removed = delete_missing_devices(session, zabbix_ips, args.dry_run)
            logger.info("Removed %s standalone devices not present in Zabbix", removed)

        if args.activate_standalone and not args.dry_run:
            activate_standalone_profile(session)

        logger.info("Done.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
