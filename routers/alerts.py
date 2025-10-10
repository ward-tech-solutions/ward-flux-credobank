"""
WARD Tech Solutions - Alerts Router
Standalone alerts API for alert_history table
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import and_, or_, desc
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, Query

from auth import get_current_active_user
from database import User, get_db
from monitoring.models import AlertHistory, StandaloneDevice, AlertRule
from pydantic import BaseModel
import uuid

logger = logging.getLogger(__name__)

# Create routers
router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])
rules_router = APIRouter(prefix="/api/v1/alert-rules", tags=["alert-rules"])


# Pydantic models for request/response
class AlertRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    expression: str  # e.g., "ping_unreachable >= 5" or "avg_ping_ms > 200"
    severity: str  # critical, high, medium, low, info
    enabled: bool = True
    device_id: Optional[str] = None  # Null for global rules

class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    expression: Optional[str] = None
    severity: Optional[str] = None
    enabled: Optional[bool] = None


@router.get("")
async def get_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity: info, warning, critical"),
    status: Optional[str] = Query(None, description="Filter by status: active, resolved"),
    limit: int = Query(100, le=1000, description="Maximum number of alerts to return"),
    offset: int = Query(0, description="Number of alerts to skip"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get alerts from alert_history table with filtering"""

    # Build query
    query = db.query(AlertHistory, StandaloneDevice).join(
        StandaloneDevice, AlertHistory.device_id == StandaloneDevice.id
    )

    # Filter by status (resolved or active)
    if status == "resolved":
        query = query.filter(AlertHistory.resolved_at.isnot(None))
    elif status == "active":
        query = query.filter(AlertHistory.resolved_at.is_(None))

    # Filter by severity
    if severity:
        query = query.filter(AlertHistory.severity == severity.lower())

    # Order by most recent first
    query = query.order_by(desc(AlertHistory.triggered_at))

    # Apply pagination
    query = query.limit(limit).offset(offset)

    # Execute query
    results = query.all()

    # Format response
    alerts = []
    for alert, device in results:
        custom_fields = device.custom_fields or {}

        # Calculate duration if resolved
        duration = None
        if alert.resolved_at and alert.triggered_at:
            duration = int((alert.resolved_at - alert.triggered_at).total_seconds())

        alerts.append({
            "id": str(alert.id),
            "device_id": str(alert.device_id),
            "device_name": device.name,
            "device_ip": device.ip,
            "device_location": custom_fields.get("region", device.location or "Unknown"),
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
    if status == "resolved":
        count_query = count_query.filter(AlertHistory.resolved_at.isnot(None))
    elif status == "active":
        count_query = count_query.filter(AlertHistory.resolved_at.is_(None))
    if severity:
        count_query = count_query.filter(AlertHistory.severity == severity.lower())

    total = count_query.count()

    return {
        "alerts": alerts,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/stats")
async def get_alert_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get alert statistics"""

    # Get counts by severity for active alerts
    active_alerts = db.query(AlertHistory).filter(AlertHistory.resolved_at.is_(None)).all()

    critical_count = sum(1 for a in active_alerts if a.severity == "critical")
    warning_count = sum(1 for a in active_alerts if a.severity == "warning")
    info_count = sum(1 for a in active_alerts if a.severity == "info")

    # Get recent resolved count (last 24h)
    yesterday = datetime.utcnow() - timedelta(hours=24)
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
    alert.acknowledged_at = datetime.utcnow()

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
        alert.resolved_at = datetime.utcnow()
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
    """Get all alert rules"""
    rules = db.query(AlertRule).order_by(AlertRule.created_at.desc()).all()

    return {
        "rules": [
            {
                "id": str(rule.id),
                "name": rule.name,
                "description": rule.description,
                "expression": rule.expression,
                "severity": rule.severity,
                "enabled": rule.enabled,
                "device_id": str(rule.device_id) if rule.device_id else None,
                "created_at": rule.created_at.isoformat() if rule.created_at else None,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
            }
            for rule in rules
        ]
    }


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
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
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

    rule.updated_at = datetime.utcnow()

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
    rule.updated_at = datetime.utcnow()

    db.commit()

    status = "enabled" if rule.enabled else "disabled"
    logger.info(f"Toggled alert rule: {rule.name} to {status} by {current_user.username}")

    return {"success": True, "enabled": rule.enabled, "rule_name": rule.name}
