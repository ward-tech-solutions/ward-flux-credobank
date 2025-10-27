# This is the FIXED evaluate_alert_rules function
# Copy this to replace the existing one in tasks.py

@shared_task(bind=True, name="monitoring.tasks.evaluate_alert_rules")
def evaluate_alert_rules(self):
    """
    FIXED ALERT ENGINE - No SQL expression parsing
    Evaluates alerts based on device.down_since field
    Runs every 10 seconds for real-time detection
    """
    db = SessionLocal()
    try:
        from datetime import timezone
        import uuid

        logger.info("📊 Starting FIXED alert evaluation (no SQL parsing)...")

        stats = {
            'devices_evaluated': 0,
            'alerts_created': 0,
            'alerts_resolved': 0,
            'isp_links_evaluated': 0
        }

        # Get all enabled devices only
        devices = db.query(StandaloneDevice).filter(
            StandaloneDevice.enabled == True
        ).all()

        for device in devices:
            stats['devices_evaluated'] += 1

            # Check if ISP link (IP ends with .5)
            is_isp = device.ip and device.ip.endswith('.5')
            if is_isp:
                stats['isp_links_evaluated'] += 1

            # CHECK DOWN STATUS - using device.down_since as source of truth
            if device.down_since:
                # Ensure timezone awareness
                down_since = device.down_since
                if down_since.tzinfo is None:
                    down_since = down_since.replace(tzinfo=timezone.utc)

                down_duration = (utcnow() - down_since).total_seconds()

                if down_duration >= 10:  # Alert after 10 seconds
                    alert_name = 'ISP Link Down' if is_isp else 'Device Down'
                    severity = 'CRITICAL'

                    # Check if alert already exists
                    existing = db.query(AlertHistory).filter(
                        AlertHistory.device_id == device.id,
                        AlertHistory.rule_name == alert_name,
                        AlertHistory.resolved_at.is_(None)
                    ).first()

                    if not existing:
                        # Create new alert
                        new_alert = AlertHistory(
                            id=uuid.uuid4(),
                            device_id=device.id,
                            rule_name=alert_name,
                            severity=severity,
                            message=f"{'ISP Link' if is_isp else 'Device'} {device.name} ({device.ip}) is DOWN for {int(down_duration)} seconds",
                            value="DOWN",
                            threshold="10 seconds",
                            triggered_at=utcnow(),
                            acknowledged=False,
                            notifications_sent=[]
                        )
                        db.add(new_alert)
                        stats['alerts_created'] += 1
                        logger.critical(f"🚨 ALERT: {new_alert.message}")

            # AUTO-RESOLVE if device is UP
            else:
                # Find any unresolved DOWN alerts for this device
                unresolved = db.query(AlertHistory).filter(
                    AlertHistory.device_id == device.id,
                    AlertHistory.rule_name.in_(['Device Down', 'ISP Link Down']),
                    AlertHistory.resolved_at.is_(None)
                ).all()

                for alert in unresolved:
                    alert.resolved_at = utcnow()
                    stats['alerts_resolved'] += 1
                    logger.info(f"✅ Auto-resolved: {alert.rule_name} for {device.name}")

            # CHECK FLAPPING
            if hasattr(device, 'is_flapping') and device.is_flapping:
                flap_threshold = 2 if is_isp else 3

                if device.flap_count and device.flap_count >= flap_threshold:
                    alert_name = 'ISP Link Flapping' if is_isp else 'Device Flapping'
                    severity = 'CRITICAL' if is_isp else 'HIGH'

                    # Check if flapping alert exists
                    existing = db.query(AlertHistory).filter(
                        AlertHistory.device_id == device.id,
                        AlertHistory.rule_name == alert_name,
                        AlertHistory.resolved_at.is_(None)
                    ).first()

                    if not existing:
                        new_alert = AlertHistory(
                            id=uuid.uuid4(),
                            device_id=device.id,
                            rule_name=alert_name,
                            severity=severity,
                            message=f"{'ISP Link' if is_isp else 'Device'} {device.name} ({device.ip}) is flapping - {device.flap_count} changes in 5 minutes",
                            value=str(device.flap_count),
                            threshold=f"{flap_threshold} changes",
                            triggered_at=utcnow(),
                            acknowledged=False,
                            notifications_sent=[]
                        )
                        db.add(new_alert)
                        stats['alerts_created'] += 1
                        logger.warning(f"⚠️ FLAPPING ALERT: {new_alert.message}")

            # Auto-resolve flapping alerts if device stabilizes
            elif hasattr(device, 'is_flapping'):
                unresolved = db.query(AlertHistory).filter(
                    AlertHistory.device_id == device.id,
                    AlertHistory.rule_name.in_(['Device Flapping', 'ISP Link Flapping']),
                    AlertHistory.resolved_at.is_(None)
                ).all()

                for alert in unresolved:
                    alert.resolved_at = utcnow()
                    stats['alerts_resolved'] += 1
                    logger.info(f"✅ Auto-resolved flapping: {alert.rule_name} for {device.name}")

        # Commit all changes
        db.commit()

        # Get summary
        active_alerts = db.query(AlertHistory).filter(
            AlertHistory.resolved_at.is_(None)
        ).count()

        logger.info(
            f"📊 Alert Evaluation Complete: "
            f"Evaluated={stats['devices_evaluated']} devices "
            f"(ISP={stats['isp_links_evaluated']}), "
            f"Created={stats['alerts_created']}, "
            f"Resolved={stats['alerts_resolved']}, "
            f"Active={active_alerts}"
        )

        return stats

    except Exception as exc:
        db.rollback()
        logger.error(f"Error evaluating alert rules: {exc}", exc_info=True)
        raise
    finally:
        db.close()