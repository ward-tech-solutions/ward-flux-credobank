#!/usr/bin/env python3
"""Minimal smoke test for Celery tasks.

Run this against a disposable database (never production) to ensure
`evaluate_alert_rules` and `cleanup_old_ping_results` behave as expected.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import text

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database import SessionLocal, PingResult
from monitoring.models import StandaloneDevice, AlertRule, AlertHistory
from monitoring.tasks import evaluate_alert_rules, cleanup_old_ping_results


def main() -> None:
    if os.getenv("DATABASE_URL", "").startswith("postgresql://") is False:
        raise SystemExit("DATABASE_URL must point to a PostgreSQL database")

    session = SessionLocal()

    existing_ping_rows = session.execute(text("SELECT COUNT(*) FROM ping_results")).scalar()
    if existing_ping_rows and not os.getenv("ALLOW_SMOKE_ON_REAL_DB"):
        session.close()
        raise SystemExit(
            "Refusing to run smoke test on a populated ping_results table. "
            "Set ALLOW_SMOKE_ON_REAL_DB=1 to override (only for disposable databases)."
        )

    smoke_device_id = uuid.uuid4()
    smoke_ip = "192.0.2.123"  # TEST-NET-1
    smoke_rule_id = uuid.uuid4()

    try:
        device = StandaloneDevice(
            id=smoke_device_id,
            name="SMOKE-TEST-DEVICE",
            ip=smoke_ip,
            enabled=True,
        )
        rule = AlertRule(
            id=smoke_rule_id,
            name="SMOKE-TEST-RULE",
            description="Ensures alert evaluation works",
            expression="ping_unreachable >= 1",
            severity="critical",
            enabled=True,
        )

        session.add_all([device, rule])
        session.commit()

        now = datetime.utcnow()
        session.add_all(
            [
                PingResult(
                    device_ip=smoke_ip,
                    device_name=device.name,
                    packets_sent=5,
                    packets_received=0,
                    packet_loss_percent=100,
                    min_rtt_ms=0,
                    avg_rtt_ms=0,
                    max_rtt_ms=0,
                    is_reachable=False,
                    timestamp=now - timedelta(minutes=i),
                )
                for i in range(3)
            ]
        )
        session.commit()

        result = evaluate_alert_rules()
        print("evaluate_alert_rules:", result)

        alerts_created = (
            session.query(AlertHistory)
            .filter(AlertHistory.rule_id == smoke_rule_id)
            .count()
        )
        if alerts_created == 0:
            raise SystemExit("Smoke test failed: no alerts created")

        cleanup = cleanup_old_ping_results(days=365)
        print("cleanup_old_ping_results:", cleanup)

    finally:
        # clean up inserted records
        session.execute(text("DELETE FROM alert_history WHERE rule_id = :rule"), {"rule": smoke_rule_id})
        session.execute(text("DELETE FROM ping_results WHERE device_ip = :ip"), {"ip": smoke_ip})
        session.execute(text("DELETE FROM alert_rules WHERE id = :rule"), {"rule": smoke_rule_id})
        session.execute(text("DELETE FROM standalone_devices WHERE id = :device"), {"device": smoke_device_id})
        session.commit()
        session.close()


if __name__ == "__main__":
    main()
