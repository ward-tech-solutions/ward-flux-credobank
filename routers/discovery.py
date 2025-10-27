"""
Discovery Router
Auto-discovery of network devices via ICMP ping and SNMP
"""
import uuid
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel, Field

from database import get_db, User
from auth import get_current_active_user, require_tech_or_admin
from models import (
    DiscoveryRule, DiscoveryResult, DiscoveryJob,
    NetworkTopology, DiscoveryCredential, StandaloneDevice
)
from monitoring.discovery.network_scanner import NetworkScanner, PingResult
from monitoring.discovery.snmp_scanner import SNMPScanner, SNMPDiscoveryResult
# from monitoring.encryption import encrypt_credential, decrypt_credential

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])


# ============================================
# Pydantic Models
# ============================================

class DiscoveryRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    enabled: bool = True
    network_ranges: List[str]  # ["192.168.1.0/24"]
    excluded_ips: Optional[List[str]] = []
    use_ping: bool = True
    use_snmp: bool = True
    use_ssh: bool = False
    snmp_communities: Optional[List[str]] = ["public"]
    snmp_ports: Optional[List[int]] = [161]
    schedule_enabled: bool = False
    schedule_cron: Optional[str] = None
    auto_import: bool = False
    auto_assign_template: bool = True


class DiscoveryRuleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    enabled: bool
    network_ranges: List[str]
    excluded_ips: Optional[List[str]]
    use_ping: bool
    use_snmp: bool
    use_ssh: bool
    schedule_enabled: bool
    schedule_cron: Optional[str]
    auto_import: bool
    created_at: datetime

    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=str(obj.id),
            name=obj.name,
            description=obj.description,
            enabled=obj.enabled,
            network_ranges=obj.network_ranges or [],
            excluded_ips=obj.excluded_ips or [],
            use_ping=obj.use_ping,
            use_snmp=obj.use_snmp,
            use_ssh=obj.use_ssh,
            schedule_enabled=obj.schedule_enabled,
            schedule_cron=obj.schedule_cron,
            auto_import=obj.auto_import,
            created_at=obj.created_at
        )


class DiscoveryResultResponse(BaseModel):
    id: str
    ip: str
    hostname: Optional[str]
    vendor: Optional[str]
    device_type: Optional[str]
    sys_descr: Optional[str]
    ping_responsive: bool
    ping_latency_ms: Optional[float]
    snmp_responsive: bool
    snmp_version: Optional[str]
    status: str
    discovered_at: datetime

    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=str(obj.id),
            ip=obj.ip,
            hostname=obj.hostname,
            vendor=obj.vendor,
            device_type=obj.device_type,
            sys_descr=obj.sys_descr,
            ping_responsive=obj.ping_responsive or False,
            ping_latency_ms=obj.ping_latency_ms,
            snmp_responsive=obj.snmp_responsive or False,
            snmp_version=obj.snmp_version,
            status=obj.status,
            discovered_at=obj.discovered_at
        )


class DiscoveryJobResponse(BaseModel):
    id: str
    rule_id: str
    status: str
    total_ips: int
    scanned_ips: int
    discovered_devices: int
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]

    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=str(obj.id),
            rule_id=str(obj.rule_id),
            status=obj.status,
            total_ips=obj.total_ips or 0,
            scanned_ips=obj.scanned_ips or 0,
            discovered_devices=obj.discovered_devices or 0,
            started_at=obj.started_at,
            completed_at=obj.completed_at,
            duration_seconds=obj.duration_seconds
        )


class ScanRequest(BaseModel):
    network_ranges: List[str]
    use_ping: bool = True
    use_snmp: bool = True
    snmp_communities: Optional[List[str]] = ["public"]
    auto_import: bool = False


class ImportDeviceRequest(BaseModel):
    result_ids: List[str]
    assign_template: bool = True


# ============================================
# Discovery Rules CRUD
# ============================================

@router.post("/rules", response_model=DiscoveryRuleResponse, status_code=201)
async def create_discovery_rule(
    rule: DiscoveryRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tech_or_admin)
):
    """Create a new discovery rule"""

    new_rule = DiscoveryRule(
        id=uuid.uuid4(),
        name=rule.name,
        description=rule.description,
        enabled=rule.enabled,
        network_ranges=rule.network_ranges,
        excluded_ips=rule.excluded_ips or [],
        use_ping=rule.use_ping,
        use_snmp=rule.use_snmp,
        use_ssh=rule.use_ssh,
        snmp_communities=rule.snmp_communities or ["public"],
        snmp_ports=rule.snmp_ports or [161],
        schedule_enabled=rule.schedule_enabled,
        schedule_cron=rule.schedule_cron,
        auto_import=rule.auto_import,
        auto_assign_template=rule.auto_assign_template,
        created_by=current_user.id
    )

    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)

    return DiscoveryRuleResponse.from_orm(new_rule)


@router.get("/rules", response_model=List[DiscoveryRuleResponse])
async def list_discovery_rules(
    enabled: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all discovery rules"""
    try:
        query = db.query(DiscoveryRule)
        if enabled is not None:
            query = query.filter(DiscoveryRule.enabled == enabled)

        rules = query.order_by(desc(DiscoveryRule.created_at)).all()
        return [DiscoveryRuleResponse.from_orm(r) for r in rules]
    except Exception as e:
        logger.error(f"Error listing discovery rules: {e}")
        return []


@router.get("/rules/{rule_id}", response_model=DiscoveryRuleResponse)
async def get_discovery_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get discovery rule by ID"""

    rule = db.query(DiscoveryRule).filter_by(id=uuid.UUID(rule_id)).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Discovery rule not found")

    return DiscoveryRuleResponse.from_orm(rule)


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_discovery_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tech_or_admin)
):
    """Delete a discovery rule"""

    rule = db.query(DiscoveryRule).filter_by(id=uuid.UUID(rule_id)).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Discovery rule not found")

    db.delete(rule)
    db.commit()

    return None


# ============================================
# Discovery Execution
# ============================================

@router.post("/scan", response_model=DiscoveryJobResponse, status_code=202)
async def start_discovery_scan(
    scan_request: ScanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tech_or_admin)
):
    """Start an ad-hoc discovery scan"""

    # Create temporary rule
    temp_rule = DiscoveryRule(
        id=uuid.uuid4(),
        name=f"Ad-hoc scan {datetime.utcnow().isoformat()}",
        enabled=True,
        network_ranges=scan_request.network_ranges,
        use_ping=scan_request.use_ping,
        use_snmp=scan_request.use_snmp,
        snmp_communities=scan_request.snmp_communities or ["public"],
        auto_import=scan_request.auto_import,
        created_by=current_user.id
    )
    db.add(temp_rule)

    # Create job
    job = DiscoveryJob(
        id=uuid.uuid4(),
        rule_id=temp_rule.id,
        status='running',
        triggered_by='manual',
        triggered_by_user=current_user.id
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Run scan in background
    background_tasks.add_task(
        run_discovery_scan,
        job_id=str(job.id),
        rule_id=str(temp_rule.id)
    )

    return DiscoveryJobResponse.from_orm(job)


@router.post("/rules/{rule_id}/run", response_model=DiscoveryJobResponse, status_code=202)
async def run_discovery_rule(
    rule_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tech_or_admin)
):
    """Run an existing discovery rule"""

    rule = db.query(DiscoveryRule).filter_by(id=uuid.UUID(rule_id)).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Discovery rule not found")

    if not rule.enabled:
        raise HTTPException(status_code=400, detail="Discovery rule is disabled")

    # Create job
    job = DiscoveryJob(
        id=uuid.uuid4(),
        rule_id=rule.id,
        status='running',
        triggered_by='manual',
        triggered_by_user=current_user.id
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Run scan in background
    background_tasks.add_task(
        run_discovery_scan,
        job_id=str(job.id),
        rule_id=rule_id
    )

    return DiscoveryJobResponse.from_orm(job)


# ============================================
# Discovery Results
# ============================================

@router.get("/results", response_model=List[DiscoveryResultResponse])
async def list_discovery_results(
    rule_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List discovery results"""
    try:
        query = db.query(DiscoveryResult)

        if rule_id:
            query = query.filter(DiscoveryResult.rule_id == uuid.UUID(rule_id))
        if status:
            query = query.filter(DiscoveryResult.status == status)

        results = query.order_by(desc(DiscoveryResult.discovered_at)).limit(limit).all()
        return [DiscoveryResultResponse.from_orm(r) for r in results]
    except Exception as e:
        logger.error(f"Error listing discovery results: {e}")
        return []


@router.get("/results/{result_id}", response_model=DiscoveryResultResponse)
async def get_discovery_result(
    result_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get discovery result by ID"""

    result = db.query(DiscoveryResult).filter_by(id=uuid.UUID(result_id)).first()
    if not result:
        raise HTTPException(status_code=404, detail="Discovery result not found")

    return DiscoveryResultResponse.from_orm(result)


@router.post("/import", status_code=200)
async def import_discovered_devices(
    import_request: ImportDeviceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tech_or_admin)
):
    """Import discovered devices as standalone devices"""

    imported_count = 0
    failed_count = 0
    errors = []

    for result_id_str in import_request.result_ids:
        try:
            result = db.query(DiscoveryResult).filter_by(id=uuid.UUID(result_id_str)).first()
            if not result:
                errors.append(f"Result {result_id_str} not found")
                failed_count += 1
                continue

            # Check if already imported
            if result.status == 'imported':
                errors.append(f"Device {result.ip} already imported")
                failed_count += 1
                continue

            # Create standalone device
            device = StandaloneDevice(
                id=uuid.uuid4(),
                name=result.hostname or result.sys_name or f"Device-{result.ip}",
                ip=result.ip,
                vendor=result.vendor,
                device_type=result.device_type,
                enabled=True,
                description=result.sys_descr,
                location=result.sys_location,
                contact=result.sys_contact
            )
            db.add(device)

            # Update result status
            result.status = 'imported'
            result.import_status = 'success'
            result.imported_device_id = device.id
            result.imported_at = datetime.utcnow()

            imported_count += 1

        except Exception as e:
            logger.error(f"Error importing device {result_id_str}: {e}")
            errors.append(f"Device {result_id_str}: {str(e)}")
            failed_count += 1

    db.commit()

    return {
        'imported': imported_count,
        'failed': failed_count,
        'errors': errors
    }


# ============================================
# Discovery Jobs
# ============================================

@router.get("/jobs", response_model=List[DiscoveryJobResponse])
async def list_discovery_jobs(
    rule_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List discovery jobs"""

    query = db.query(DiscoveryJob)

    if rule_id:
        query = query.filter(DiscoveryJob.rule_id == uuid.UUID(rule_id))
    if status:
        query = query.filter(DiscoveryJob.status == status)

    jobs = query.order_by(desc(DiscoveryJob.started_at)).limit(limit).all()
    return [DiscoveryJobResponse.from_orm(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=DiscoveryJobResponse)
async def get_discovery_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get discovery job by ID"""

    job = db.query(DiscoveryJob).filter_by(id=uuid.UUID(job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Discovery job not found")

    return DiscoveryJobResponse.from_orm(job)


# ============================================
# Background Discovery Function
# ============================================

async def run_discovery_scan(job_id: str, rule_id: str):
    """
    Background task to run discovery scan

    Args:
        job_id: Discovery job ID
        rule_id: Discovery rule ID
    """
    from database import SessionLocal

    db = SessionLocal()
    try:
        job = db.query(DiscoveryJob).filter_by(id=uuid.UUID(job_id)).first()
        rule = db.query(DiscoveryRule).filter_by(id=uuid.UUID(rule_id)).first()

        if not job or not rule:
            logger.error(f"Job {job_id} or rule {rule_id} not found")
            return

        logger.info(f"Starting discovery scan for job {job_id}")

        # Phase 1: Ping scan
        ping_results = []
        if rule.use_ping:
            logger.info(f"Running ping scan for {len(rule.network_ranges)} networks")
            scanner = NetworkScanner(timeout=2, max_concurrent=100)

            for network_range in rule.network_ranges:
                results = await scanner.scan_network(
                    network_range,
                    excluded_ips=rule.excluded_ips or []
                )
                ping_results.extend(results)

        # Phase 2: SNMP scan (on responsive hosts)
        snmp_results = []
        if rule.use_snmp:
            responsive_ips = [r.ip for r in ping_results if r.responsive]
            if responsive_ips:
                logger.info(f"Running SNMP scan on {len(responsive_ips)} responsive hosts")
                snmp_scanner = SNMPScanner(timeout=5)
                snmp_results = await snmp_scanner.scan_network(
                    responsive_ips,
                    communities=rule.snmp_communities or ["public"],
                    port=rule.snmp_ports[0] if rule.snmp_ports else 161
                )

        # Combine results and save
        total_ips = len(ping_results)
        discovered_devices = 0

        # Create results from ping + SNMP
        for ping_result in ping_results:
            # Find matching SNMP result
            snmp_result = next(
                (s for s in snmp_results if s.ip == ping_result.ip),
                None
            )

            if ping_result.responsive or (snmp_result and snmp_result.responsive):
                discovered_devices += 1

                discovery_result = DiscoveryResult(
                    id=uuid.uuid4(),
                    rule_id=rule.id,
                    ip=ping_result.ip,
                    hostname=ping_result.hostname or (snmp_result.sys_name if snmp_result else None),
                    ping_responsive=ping_result.responsive,
                    ping_latency_ms=ping_result.latency_ms,
                    snmp_responsive=snmp_result.responsive if snmp_result else False,
                    snmp_version=snmp_result.version if snmp_result else None,
                    snmp_community=snmp_result.community if snmp_result else None,
                    sys_descr=snmp_result.sys_descr if snmp_result else None,
                    sys_name=snmp_result.sys_name if snmp_result else None,
                    sys_oid=snmp_result.sys_oid if snmp_result else None,
                    sys_uptime=snmp_result.sys_uptime if snmp_result else None,
                    sys_contact=snmp_result.sys_contact if snmp_result else None,
                    sys_location=snmp_result.sys_location if snmp_result else None,
                    vendor=snmp_result.vendor if snmp_result else None,
                    device_type=snmp_result.device_type if snmp_result else None,
                    model=snmp_result.model if snmp_result else None,
                    os_version=snmp_result.os_version if snmp_result else None,
                    discovered_via='snmp' if (snmp_result and snmp_result.responsive) else 'ping',
                    status='discovered'
                )
                db.add(discovery_result)

        # Update job status
        job.status = 'completed'
        job.total_ips = total_ips
        job.scanned_ips = total_ips
        job.discovered_devices = discovered_devices
        job.completed_at = datetime.utcnow()
        job.duration_seconds = int((job.completed_at - job.started_at).total_seconds())
        job.scan_summary = {
            'ping_responsive': sum(1 for r in ping_results if r.responsive),
            'snmp_responsive': sum(1 for r in snmp_results if r.responsive),
            'total_discovered': discovered_devices
        }

        # Update rule last_run
        rule.last_run = datetime.utcnow()

        db.commit()
        logger.info(f"Discovery scan completed: {discovered_devices} devices found")

    except Exception as e:
        logger.error(f"Discovery scan failed: {e}", exc_info=True)
        if job:
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
