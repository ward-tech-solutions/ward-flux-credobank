"""
WARD Tech Solutions - Reports Router
Handles downtime reports and MTTR analysis
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, Request

from auth import get_current_active_user
from database import User, UserRole, get_db, PingResult
from monitoring.models import StandaloneDevice, AlertHistory

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/downtime")
async def get_downtime_report(
    period: str = "weekly",
    region: Optional[str] = None,
    device_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Generate downtime report from standalone monitoring data"""

    # Calculate time range based on period
    period_hours = {"daily": 24, "weekly": 168, "monthly": 720}
    hours = period_hours.get(period, 168)
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    # Get all standalone devices
    query = db.query(StandaloneDevice)

    # Apply user permission filtering (non-admin users)
    if current_user.role != UserRole.ADMIN:
        if current_user.region:
            query = query.filter(StandaloneDevice.region == current_user.region)
        if current_user.branches:
            allowed_branches = [b.strip() for b in current_user.branches.split(",")]
            query = query.filter(StandaloneDevice.branch.in_(allowed_branches))

    # Apply additional filters
    if region:
        query = query.filter(StandaloneDevice.region == region)
    if device_type:
        query = query.filter(StandaloneDevice.device_type == device_type)

    devices = query.all()

    report = {
        "period": period,
        "generated_at": datetime.utcnow().isoformat(),
        "total_devices": len(devices),
        "summary": {"total_downtime_hours": 0, "average_availability": 0, "devices_with_downtime": 0},
        "devices": [],
    }

    for device in devices:
        # Calculate real availability from ping results
        ping_stats = (
            db.query(
                func.count(PingResult.id).label("total_pings"),
                func.sum(func.case((PingResult.is_reachable == True, 1), else_=0)).label("successful_pings"),
            )
            .filter(
                and_(
                    PingResult.device_ip == device.ip,
                    PingResult.timestamp >= cutoff_time
                )
            )
            .first()
        )

        total_pings = ping_stats.total_pings or 0
        successful_pings = ping_stats.successful_pings or 0

        if total_pings > 0:
            availability = round((successful_pings / total_pings) * 100, 2)
            downtime_hours = round(hours * (1 - availability / 100), 2)
        else:
            availability = 0.0
            downtime_hours = hours

        # Count incidents from alert history
        incident_count = (
            db.query(func.count(AlertHistory.id))
            .filter(
                and_(
                    AlertHistory.device_id == device.id,
                    AlertHistory.triggered_at >= cutoff_time
                )
            )
            .scalar() or 0
        )

        report["devices"].append(
            {
                "hostid": str(device.id),
                "name": device.name,
                "region": device.region or "Unknown",
                "branch": device.branch or "Unknown",
                "device_type": device.device_type or "Unknown",
                "downtime_hours": downtime_hours,
                "availability_percent": availability,
                "incidents": incident_count,
            }
        )

        report["summary"]["total_downtime_hours"] += downtime_hours
        if availability < 99.0:
            report["summary"]["devices_with_downtime"] += 1

    if len(devices) > 0:
        report["summary"]["average_availability"] = round(
            sum(d["availability_percent"] for d in report["devices"]) / len(devices), 2
        )
    else:
        report["summary"]["average_availability"] = 0.0

    return report


@router.get("/mttr-extended")
async def get_mttr_extended(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Extended MTTR trends and analysis from standalone monitoring"""

    # Calculate MTTR from resolved alerts in last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    resolved_alerts = (
        db.query(AlertHistory)
        .filter(
            and_(
                AlertHistory.resolved_at.isnot(None),
                AlertHistory.triggered_at >= thirty_days_ago
            )
        )
        .all()
    )

    if resolved_alerts:
        total_resolution_time = sum(
            (alert.resolved_at - alert.triggered_at).total_seconds() / 60
            for alert in resolved_alerts
        )
        avg_mttr_minutes = round(total_resolution_time / len(resolved_alerts), 2)
    else:
        avg_mttr_minutes = 0.0

    # Find top problem devices by incident count
    device_alerts = (
        db.query(
            AlertHistory.device_id,
            func.count(AlertHistory.id).label("incident_count"),
        )
        .filter(AlertHistory.triggered_at >= thirty_days_ago)
        .group_by(AlertHistory.device_id)
        .order_by(func.count(AlertHistory.id).desc())
        .limit(10)
        .all()
    )

    top_problem_devices = []
    for alert_stat in device_alerts:
        device = db.query(StandaloneDevice).filter_by(id=alert_stat.device_id).first()
        if device:
            top_problem_devices.append({
                "hostid": str(device.id),
                "name": device.name,
                "region": device.region or "Unknown",
                "incident_count": alert_stat.incident_count,
                "downtime_minutes": round(alert_stat.incident_count * 15, 2),  # Estimate 15 min avg per incident
            })

    return {
        "avg_mttr_minutes": avg_mttr_minutes,
        "total_alerts": len(resolved_alerts),
        "resolved_alerts": len(resolved_alerts),
        "unresolved_alerts": db.query(func.count(AlertHistory.id))
        .filter(AlertHistory.resolved_at.is_(None))
        .scalar() or 0,
        "top_problem_devices": top_problem_devices,
        "trends": {
            "improving": avg_mttr_minutes < 30,
            "recommendation": "Focus on preventive maintenance for top 10 problem devices" if top_problem_devices else "No major issues detected",
        },
    }
