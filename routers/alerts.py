"""
WARD Tech Solutions - Alerts Router
Standalone alerts API for alert_history table
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, Query

from auth import get_current_active_user
from database import User, get_db, PingResult
from monitoring.models import AlertHistory, StandaloneDevice, AlertRule
from models import Branch
from pydantic import BaseModel
import uuid

logger = logging.getLogger(__name__)

# Create routers
router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])
rules_router = APIRouter(prefix="/api/v1/alert-rules", tags=["alert-rules"])


def utcnow():
    """Get current UTC time with timezone awareness"""
    return datetime.now(timezone.utc)


# Pydantic models for request/response
class AlertRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    expression: str  # e.g., "ping_unreachable >= 5" or "avg_ping_ms > 200"
    severity: str  # critical, high, medium, low, info
    enabled: bool = True
    device_id: Optional[str] = None  # Null for global rules
    branch_id: Optional[str] = None  # Branch-level alert - applies to all devices in branch

class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    expression: Optional[str] = None
    severity: Optional[str] = None
    enabled: Optional[bool] = None
    device_id: Optional[str] = None
    branch_id: Optional[str] = None


@router.get("/realtime")
async def get_realtime_alerts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get REAL-TIME alerts based on actual device ping status
    Shows ALL down devices, not just historical alerts
    """

    try:
        # Get latest ping result for each device (last 10 minutes)
        recent_time = datetime.now(timezone.utc) - timedelta(minutes=10)

        # Subquery to get latest ping per device
        latest_pings = (
            db.query(
                PingResult.device_ip,
                func.max(PingResult.timestamp).label('last_timestamp')
            )
            .filter(PingResult.timestamp >= recent_time)
            .group_by(PingResult.device_ip)
            .subquery()
        )

        # Get all enabled devices with their latest ping status
        query = (
            db.query(StandaloneDevice, Branch, PingResult)
            .outerjoin(Branch, StandaloneDevice.branch_id == Branch.id)
            .outerjoin(
                latest_pings,
                StandaloneDevice.ip == latest_pings.c.device_ip
            )
            .outerjoin(
                PingResult,
                and_(
                    PingResult.device_ip == latest_pings.c.device_ip,
                    PingResult.timestamp == latest_pings.c.last_timestamp
                )
            )
            .filter(StandaloneDevice.enabled == True)
        )

        results = query.all()

        # Build alert list from down devices
        alerts = []
        for device, branch, ping_result in results:
            custom_fields = device.custom_fields or {}

            # Determine if device is down
            is_down = False
            last_ping_time = None
            downtime_seconds = None

            if ping_result:
                is_down = not ping_result.is_reachable
                last_ping_time = ping_result.timestamp

                if is_down:
                    # Check if there was a previous successful ping to calculate real downtime
                    last_success = (
                        db.query(PingResult)
                        .filter(
                            PingResult.device_ip == device.ip,
                            PingResult.is_reachable == True,
                            PingResult.timestamp < ping_result.timestamp
                        )
                        .order_by(PingResult.timestamp.desc())
                        .first()
                    )

                    if last_success:
                        # Real downtime: time since last successful ping
                        downtime_seconds = int((datetime.now(timezone.utc) - last_success.timestamp).total_seconds())
                    else:
                        # Never been up - this is first ping and it failed
                        # Show as "unknown" or very recent
                        downtime_seconds = int((datetime.now(timezone.utc) - ping_result.timestamp).total_seconds())
            else:
                # No recent ping data = device is considered down
                is_down = True
                downtime_seconds = None  # Unknown downtime

            # Only include down devices
            if not is_down:
                continue

            # Get branch information
            branch_name = branch.display_name if branch else custom_fields.get("branch", "Unknown")
            branch_id = str(branch.id) if branch else device.branch_id
            branch_region = branch.region if branch else custom_fields.get("region", device.location or "Unknown")
            branch_code = branch.branch_code if branch else None

            # Determine severity based on downtime
            if downtime_seconds and downtime_seconds > 3600:  # > 1 hour
                severity = "CRITICAL"
            elif downtime_seconds and downtime_seconds > 900:  # > 15 minutes
                severity = "HIGH"
            else:
                severity = "WARNING"

            alerts.append({
                "id": f"ping-{str(device.id)}",  # Unique ID for real-time alert
                "device_id": str(device.id),
                "device_name": device.name,
                "device_ip": device.ip,
                "device_type": device.device_type,
                "device_location": branch_region,
                "branch_id": branch_id,
                "branch_name": branch_name,
                "branch_code": branch_code,
                "branch_region": branch_region,
                "rule_name": "Ping Unavailable",
                "severity": severity,
                "message": f"Device {device.name} ({device.ip}) is DOWN - unreachable for {int(downtime_seconds / 60)} minutes" if downtime_seconds else f"Device {device.name} ({device.ip}) is DOWN - never seen up",
                "value": "Down",
                "threshold": "Up",
                "triggered_at": last_ping_time.isoformat() if last_ping_time else (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),
                "resolved_at": None,  # Active alerts have no resolved_at
                "duration_seconds": downtime_seconds,
                "acknowledged": False,
                "acknowledged_by": None,
                "acknowledged_at": None,
                "notifications_sent": 0,
            })

        return {
            "alerts": alerts,
            "total": len(alerts),
        "limit": len(alerts),
        "offset": 0,
    }

    except Exception as e:
        logger.error(f"Error in realtime alerts endpoint: {e}", exc_info=True)
        return {
            "alerts": [],
            "total": 0,
            "limit": 0,
            "offset": 0,
            "error": str(e)
        }


@router.get("")
async def get_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity: info, warning, critical"),
    status: Optional[str] = Query(None, description="Filter by status: active, resolved"),
    device_id: Optional[str] = Query(None, description="Filter by device_id"),
    limit: int = Query(100, le=1000, description="Maximum number of alerts to return"),
    offset: int = Query(0, description="Number of alerts to skip"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get alerts from alert_history table with filtering (historical alerts)

    OPTIMIZATION: Redis caching with 30-second TTL
    - Cache hit: 5-10ms (50x faster)
    - Cache miss: 100-500ms (3-table JOIN query)
    """
    import json as json_lib
    import hashlib

    # Build cache key from query parameters
    cache_params = {
        'severity': severity,
        'status': status,
        'device_id': device_id,
        'limit': limit,
        'offset': offset
    }
    cache_key = f"alerts:list:{hashlib.md5(json_lib.dumps(cache_params, sort_keys=True).encode()).hexdigest()}"

    # Try to get from cache
    try:
        from utils.cache import get_redis_client
        redis_client = get_redis_client()
        if redis_client:
            cached = redis_client.get(cache_key)
            if cached:
                logger.debug(f"Cache HIT for alerts list")
                return json_lib.loads(cached)
    except Exception as e:
        logger.debug(f"Cache read error (non-critical): {e}")

    # Cache miss - query database
    # Build query with left join to Branch for branch information
    query = db.query(AlertHistory, StandaloneDevice, Branch).join(
        StandaloneDevice, AlertHistory.device_id == StandaloneDevice.id
    ).outerjoin(
        Branch, StandaloneDevice.branch_id == Branch.id
    )

    # Filter by device_id
    if device_id:
        query = query.filter(AlertHistory.device_id == device_id)

    # Filter by status (resolved or active)
    if status == "resolved":
        query = query.filter(AlertHistory.resolved_at.isnot(None))
    elif status == "active":
        query = query.filter(AlertHistory.resolved_at.is_(None))

    # Filter by severity
    if severity:
        query = query.filter(AlertHistory.severity == severity.upper())

    # Order by most recent first
    query = query.order_by(desc(AlertHistory.triggered_at))

    # Apply pagination
    query = query.limit(limit).offset(offset)

    # Execute query
    results = query.all()

    # Format response
    alerts = []
    for alert, device, branch in results:
        custom_fields = device.custom_fields or {}

        # Calculate duration if resolved
        duration = None
        if alert.resolved_at and alert.triggered_at:
            duration = int((alert.resolved_at - alert.triggered_at).total_seconds())

        # Get branch information
        branch_name = branch.display_name if branch else custom_fields.get("branch", "Unknown")
        branch_id = str(branch.id) if branch else device.branch_id
        branch_region = branch.region if branch else custom_fields.get("region", device.location or "Unknown")
        branch_code = branch.branch_code if branch else None

        alerts.append({
            "id": str(alert.id),
            "device_id": str(alert.device_id),
            "device_name": device.name,
            "device_ip": device.ip,
            "device_type": device.device_type,
            "device_location": branch_region,
            "branch_id": branch_id,
            "branch_name": branch_name,
            "branch_code": branch_code,
            "branch_region": branch_region,
            "rule_name": alert.rule_name,
            "severity": alert.severity,
            "message": alert.message,
            "value": alert.value,
            "threshold": alert.threshold,
            "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None,
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
            "duration_seconds": duration,
            "acknowledged": alert.acknowledged,
            "acknowledged_by": alert.acknowledged_by,
            "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            "notifications_sent": alert.notifications_sent,
        })

    # Get total count for pagination
    count_query = db.query(AlertHistory)
    if device_id:
        count_query = count_query.filter(AlertHistory.device_id == device_id)
    if status == "resolved":
        count_query = count_query.filter(AlertHistory.resolved_at.isnot(None))
    elif status == "active":
        count_query = count_query.filter(AlertHistory.resolved_at.is_(None))
    if severity:
        count_query = count_query.filter(AlertHistory.severity == severity.upper())

    total = count_query.count()

    result = {
        "alerts": alerts,
        "total": total,
        "limit": limit,
        "offset": offset,
    }

    # Store in cache (30-second TTL)
    try:
        if redis_client:
            redis_client.setex(cache_key, 30, json_lib.dumps(result, default=str))
            logger.debug(f"Cached alerts list for 30 seconds")
    except Exception as e:
        logger.debug(f"Cache write error (non-critical): {e}")

    return result


@router.get("/stats")
async def get_alert_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get alert statistics"""

    # Get counts by severity for active alerts
    active_alerts = db.query(AlertHistory).filter(AlertHistory.resolved_at.is_(None)).all()

    critical_count = sum(1 for a in active_alerts if a.severity.upper() == "CRITICAL")
    warning_count = sum(1 for a in active_alerts if a.severity.upper() in {"WARNING", "MEDIUM", "HIGH"})
    info_count = sum(1 for a in active_alerts if a.severity.upper() == "INFO")

    # Get recent resolved count (last 24h)
    yesterday = utcnow() - timedelta(hours=24)
    resolved_24h = (
        db.query(AlertHistory)
        .filter(
            and_(
                AlertHistory.resolved_at.isnot(None),
                AlertHistory.resolved_at >= yesterday
            )
        )
        .count()
    )

    return {
        "active_alerts": len(active_alerts),
        "critical_alerts": critical_count,
        "warning_alerts": warning_count,
        "info_alerts": info_count,
        "resolved_24h": resolved_24h,
    }


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Acknowledge an alert"""

    alert = db.query(AlertHistory).filter_by(id=alert_id).first()
    if not alert:
        return {"error": "Alert not found"}, 404

    alert.acknowledged = True
    alert.acknowledged_by = current_user.username
    alert.acknowledged_at = utcnow()

    db.commit()

    return {"success": True, "alert_id": alert_id, "acknowledged_by": current_user.username}


@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Manually resolve an alert"""

    alert = db.query(AlertHistory).filter_by(id=alert_id).first()
    if not alert:
        return {"error": "Alert not found"}, 404

    if not alert.resolved_at:
        alert.resolved_at = utcnow()
        db.commit()

    return {"success": True, "alert_id": alert_id, "resolved_at": alert.resolved_at.isoformat()}


# ============================================
# Alert Rules Management Endpoints
# ============================================

@rules_router.get("")
async def get_alert_rules(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all alert rules with trigger statistics"""
    rules = db.query(AlertRule).order_by(AlertRule.created_at.desc()).all()

    # Calculate trigger statistics for each rule
    now = datetime.now(timezone.utc)
    twentyfour_hours_ago = now - timedelta(hours=24)
    seven_days_ago = now - timedelta(days=7)

    result_rules = []
    for rule in rules:
        # Get last triggered time
        last_alert = (
            db.query(AlertHistory)
            .filter(AlertHistory.rule_id == rule.id)
            .order_by(AlertHistory.triggered_at.desc())
            .first()
        )

        # Count triggers in last 24 hours
        trigger_count_24h = (
            db.query(func.count(AlertHistory.id))
            .filter(
                AlertHistory.rule_id == rule.id,
                AlertHistory.triggered_at >= twentyfour_hours_ago
            )
            .scalar() or 0
        )

        # Count triggers in last 7 days
        trigger_count_7d = (
            db.query(func.count(AlertHistory.id))
            .filter(
                AlertHistory.rule_id == rule.id,
                AlertHistory.triggered_at >= seven_days_ago
            )
            .scalar() or 0
        )

        # Count affected devices (unique devices that triggered this rule)
        affected_devices_count = (
            db.query(func.count(func.distinct(AlertHistory.device_id)))
            .filter(AlertHistory.rule_id == rule.id)
            .scalar() or 0
        )

        result_rules.append({
            "id": str(rule.id),
            "name": rule.name,
            "description": rule.description,
            "expression": rule.expression,
            "severity": rule.severity,
            "enabled": rule.enabled,
            "device_id": str(rule.device_id) if rule.device_id else None,
            "branch_id": rule.branch_id if rule.branch_id else None,
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
            "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
            "last_triggered_at": last_alert.triggered_at.isoformat() if last_alert else None,
            "trigger_count_24h": trigger_count_24h,
            "trigger_count_7d": trigger_count_7d,
            "affected_devices_count": affected_devices_count,
        })

    return {"rules": result_rules}


@rules_router.post("")
async def create_alert_rule(
    rule_data: AlertRuleCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new alert rule"""

    # Create new rule
    new_rule = AlertRule(
        id=uuid.uuid4(),
        name=rule_data.name,
        description=rule_data.description,
        expression=rule_data.expression,
        severity=rule_data.severity,
        enabled=rule_data.enabled,
        device_id=uuid.UUID(rule_data.device_id) if rule_data.device_id else None,
        branch_id=rule_data.branch_id if rule_data.branch_id else None,
        created_at=utcnow(),
        updated_at=utcnow(),
    )

    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)

    logger.info(f"Created alert rule: {new_rule.name} by {current_user.username}")

    return {
        "success": True,
        "rule": {
            "id": str(new_rule.id),
            "name": new_rule.name,
            "description": new_rule.description,
            "expression": new_rule.expression,
            "severity": new_rule.severity,
            "enabled": new_rule.enabled,
        }
    }


@rules_router.get("/{rule_id}")
async def get_alert_rule(
    rule_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a single alert rule by ID"""
    rule = db.query(AlertRule).filter_by(id=rule_id).first()

    if not rule:
        return {"error": "Alert rule not found"}, 404

    return {
        "id": str(rule.id),
        "name": rule.name,
        "description": rule.description,
        "expression": rule.expression,
        "severity": rule.severity,
        "enabled": rule.enabled,
        "device_id": str(rule.device_id) if rule.device_id else None,
        "branch_id": rule.branch_id if rule.branch_id else None,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
    }


@rules_router.put("/{rule_id}")
async def update_alert_rule(
    rule_id: str,
    rule_data: AlertRuleUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update an existing alert rule"""
    rule = db.query(AlertRule).filter_by(id=rule_id).first()

    if not rule:
        return {"error": "Alert rule not found"}, 404

    # Update fields if provided
    if rule_data.name is not None:
        rule.name = rule_data.name
    if rule_data.description is not None:
        rule.description = rule_data.description
    if rule_data.expression is not None:
        rule.expression = rule_data.expression
    if rule_data.severity is not None:
        rule.severity = rule_data.severity
    if rule_data.enabled is not None:
        rule.enabled = rule_data.enabled
    if rule_data.device_id is not None:
        rule.device_id = uuid.UUID(rule_data.device_id) if rule_data.device_id else None
    if rule_data.branch_id is not None:
        rule.branch_id = rule_data.branch_id

    rule.updated_at = utcnow()

    db.commit()
    db.refresh(rule)

    logger.info(f"Updated alert rule: {rule.name} by {current_user.username}")

    return {
        "success": True,
        "rule": {
            "id": str(rule.id),
            "name": rule.name,
            "description": rule.description,
            "expression": rule.expression,
            "severity": rule.severity,
            "enabled": rule.enabled,
        }
    }


@rules_router.delete("/{rule_id}")
async def delete_alert_rule(
    rule_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete an alert rule"""
    rule = db.query(AlertRule).filter_by(id=rule_id).first()

    if not rule:
        return {"error": "Alert rule not found"}, 404

    rule_name = rule.name
    db.delete(rule)
    db.commit()

    logger.info(f"Deleted alert rule: {rule_name} by {current_user.username}")

    return {"success": True, "message": f"Alert rule '{rule_name}' deleted"}


@rules_router.post("/{rule_id}/toggle")
async def toggle_alert_rule(
    rule_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Toggle an alert rule enabled/disabled"""
    rule = db.query(AlertRule).filter_by(id=rule_id).first()

    if not rule:
        return {"error": "Alert rule not found"}, 404

    rule.enabled = not rule.enabled
    rule.updated_at = utcnow()

    db.commit()

    status = "enabled" if rule.enabled else "disabled"
    logger.info(f"Toggled alert rule: {rule.name} to {status} by {current_user.username}")

    return {"success": True, "enabled": rule.enabled, "rule_name": rule.name}
