"""
WARD Tech Solutions - Diagnostics Router
Handles network diagnostics: ping, traceroute, MTR, DNS, port scanning, baselines, and anomaly detection
"""
import logging
import csv
import io
import re
import socket
import subprocess
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_active_user
from database import (
    MTRResult,
    PerformanceBaseline,
    PingResult,
    TracerouteResult,
    User,
    get_db,
)
from network_diagnostics import NetworkDiagnostics
from routers.utils import run_in_executor

# Create router
router = APIRouter(prefix="/api/v1/diagnostics", tags=["diagnostics"])


@router.post("/ping")
async def ping_device(
    request: Request,
    ip: str,
    count: int = 5,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Perform independent ICMP ping check

    Returns real-time ping results with packet loss and RTT
    """

    diag = NetworkDiagnostics()

    # Perform ping
    result = await run_in_executor(diag.ping, ip, count)

    # Get device name from Zabbix
    zabbix = request.app.state.zabbix
    try:
        devices = await run_in_executor(zabbix.get_all_hosts)
        device = next((d for d in devices if d.get("ip") == ip), None)
        device_name = device.get("display_name") if device else ip
    except Exception as e:
        logging.getLogger(__name__).error(f"Error: {e}")
        device_name = ip

    # Store in database
    ping_record = PingResult(
        device_ip=ip,
        device_name=device_name,
        packets_sent=result["packets_sent"],
        packets_received=result["packets_received"],
        packet_loss_percent=result["packet_loss_percent"],
        min_rtt_ms=result.get("min_rtt_ms"),
        avg_rtt_ms=result.get("avg_rtt_ms"),
        max_rtt_ms=result.get("max_rtt_ms"),
        is_reachable=result["is_reachable"],
    )
    db.add(ping_record)
    db.commit()

    return {**result, "device_name": device_name, "stored": True}


@router.post("/traceroute")
async def traceroute_device(
    request: Request,
    ip: str,
    max_hops: int = 30,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Perform traceroute to device

    Returns network path with all hops and latencies
    """

    diag = NetworkDiagnostics()

    # Perform traceroute
    result = await run_in_executor(diag.traceroute, ip, max_hops)

    # Get device name from Zabbix
    zabbix = request.app.state.zabbix
    try:
        devices = await run_in_executor(zabbix.get_all_hosts)
        device = next((d for d in devices if d.get("ip") == ip), None)
        device_name = device.get("display_name") if device else ip
    except Exception as e:
        logging.getLogger(__name__).error(f"Error: {e}")
        device_name = ip

    # Store each hop in database
    for hop in result.get("hops", []):
        hop_record = TracerouteResult(
            device_ip=ip,
            device_name=device_name,
            hop_number=hop["hop_number"],
            hop_ip=hop.get("ip"),
            hop_hostname=hop.get("hostname"),
            latency_ms=hop.get("latency_ms"),
        )
        db.add(hop_record)

    db.commit()

    return {**result, "device_name": device_name, "stored": True}


@router.get("/ping/history/{ip}")
async def get_ping_history(
    ip: str, limit: int = 10, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """Get ping history for a device"""

    results = (
        db.query(PingResult).filter(PingResult.device_ip == ip).order_by(PingResult.timestamp.desc()).limit(limit).all()
    )

    return [
        {
            "device_ip": r.device_ip,
            "device_name": r.device_name,
            "packet_loss_percent": r.packet_loss_percent,
            "avg_rtt_ms": r.avg_rtt_ms,
            "is_reachable": r.is_reachable,
            "timestamp": r.timestamp.isoformat(),
        }
        for r in results
    ]


@router.get("/traceroute/history/{ip}")
async def get_traceroute_history(
    ip: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """Get last traceroute result for a device"""
    from sqlalchemy import func

    # Get the most recent timestamp for this IP
    latest = db.query(func.max(TracerouteResult.timestamp)).filter(TracerouteResult.device_ip == ip).scalar()

    if not latest:
        return {"hops": [], "message": "No traceroute history found"}

    # Get all hops from that traceroute
    hops = (
        db.query(TracerouteResult)
        .filter(TracerouteResult.device_ip == ip, TracerouteResult.timestamp == latest)
        .order_by(TracerouteResult.hop_number)
        .all()
    )

    return {
        "device_ip": ip,
        "device_name": hops[0].device_name if hops else ip,
        "timestamp": latest.isoformat(),
        "hops": [
            {"hop_number": h.hop_number, "ip": h.hop_ip, "hostname": h.hop_hostname, "latency_ms": h.latency_ms}
            for h in hops
        ],
    }


# ============================================
# MTR MONITORING & HISTORICAL DATA
# ============================================


@router.post("/mtr/store")
async def store_mtr_data(
    request: Request, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """Store MTR monitoring data"""

    data = await request.json()
    device_ip = data.get("device_ip")
    device_name = data.get("device_name")
    hops = data.get("hops", [])

    for hop in hops:
        mtr_record = MTRResult(
            device_ip=device_ip,
            device_name=device_name,
            hop_number=hop.get("hop_number"),
            hop_ip=hop.get("hop_ip"),
            hop_hostname=hop.get("hop_hostname"),
            packets_sent=hop.get("packets_sent", 0),
            packets_received=hop.get("packets_received", 0),
            packet_loss_percent=hop.get("packet_loss_percent", 0),
            latency_avg=hop.get("latency_avg"),
            latency_min=hop.get("latency_min"),
            latency_max=hop.get("latency_max"),
            latency_stddev=hop.get("latency_stddev"),
        )
        db.add(mtr_record)

    db.commit()
    return {"success": True, "hops_stored": len(hops)}


@router.get("/mtr/history/{ip}")
async def get_mtr_history(
    ip: str, hours: int = 24, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """Get MTR history for a device over specified time period"""
    from datetime import timedelta

    since = datetime.utcnow() - timedelta(hours=hours)

    results = (
        db.query(MTRResult)
        .filter(MTRResult.device_ip == ip, MTRResult.timestamp >= since)
        .order_by(MTRResult.timestamp.desc(), MTRResult.hop_number)
        .all()
    )

    return [
        {
            "hop_number": r.hop_number,
            "hop_ip": r.hop_ip,
            "hop_hostname": r.hop_hostname,
            "latency_avg": r.latency_avg,
            "latency_min": r.latency_min,
            "latency_max": r.latency_max,
            "latency_stddev": r.latency_stddev,
            "packet_loss_percent": r.packet_loss_percent,
            "timestamp": r.timestamp.isoformat(),
        }
        for r in results
    ]


@router.get("/trends/{ip}")
async def get_latency_trends(
    ip: str, hours: int = 24, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """Get latency trends for charting"""
    from datetime import timedelta

    since = datetime.utcnow() - timedelta(hours=hours)

    results = (
        db.query(PingResult)
        .filter(PingResult.device_ip == ip, PingResult.timestamp >= since)
        .order_by(PingResult.timestamp)
        .all()
    )

    return {
        "device_ip": ip,
        "device_name": results[0].device_name if results else ip,
        "data_points": [
            {
                "timestamp": r.timestamp.isoformat(),
                "avg_latency": r.avg_rtt_ms,
                "min_latency": r.min_rtt_ms,
                "max_latency": r.max_rtt_ms,
                "packet_loss": r.packet_loss_percent,
            }
            for r in results
        ],
    }


# ============================================
# BULK DIAGNOSTICS OPERATIONS
# ============================================


@router.post("/bulk/ping")
async def bulk_ping_devices(
    request: Request, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """Run ping on multiple devices simultaneously"""
    import subprocess
    import re

    data = await request.json()
    device_ips = data.get("device_ips", [])
    count = data.get("count", 5)

    results = []

    for ip in device_ips:
        try:
            cmd = ["ping", "-c", str(count), ip]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            output = result.stdout

            packets_match = re.search(r"(\d+) packets transmitted, (\d+) received", output)
            rtt_match = re.search(r"min/avg/max/[\w]+\s*=\s*([\d.]+)/([\d.]+)/([\d.]+)", output)

            if packets_match and rtt_match:
                sent = int(packets_match.group(1))
                received = int(packets_match.group(2))
                loss = int(((sent - received) / sent) * 100)

                ping_data = {
                    "device_ip": ip,
                    "is_reachable": received > 0,
                    "packet_loss_percent": loss,
                    "min_rtt_ms": float(rtt_match.group(1)),
                    "avg_rtt_ms": float(rtt_match.group(2)),
                    "max_rtt_ms": float(rtt_match.group(3)),
                }

                # Store in DB
                ping_record = PingResult(device_ip=ip, packets_sent=sent, packets_received=received, **ping_data)
                db.add(ping_record)

                results.append(ping_data)
            else:
                results.append({"device_ip": ip, "is_reachable": False, "error": "Failed to parse"})

        except Exception as e:
            results.append({"device_ip": ip, "is_reachable": False, "error": str(e)})

    db.commit()
    return {
        "results": results,
        "total": len(device_ips),
        "successful": len([r for r in results if r.get("is_reachable")]),
    }


@router.post("/export")
async def export_diagnostic_results(
    request: Request,
    format: str = "csv",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Export diagnostic results to CSV or JSON"""
    import csv
    import io

    data = await request.json()
    device_ips = data.get("device_ips", [])

    results = (
        db.query(PingResult).filter(PingResult.device_ip.in_(device_ips)).order_by(PingResult.timestamp.desc()).all()
    )

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Device IP",
                "Device Name",
                "Packet Loss %",
                "Avg Latency (ms)",
                "Min Latency (ms)",
                "Max Latency (ms)",
                "Timestamp",
            ]
        )

        for r in results:
            writer.writerow(
                [
                    r.device_ip,
                    r.device_name or "",
                    r.packet_loss_percent,
                    r.avg_rtt_ms,
                    r.min_rtt_ms,
                    r.max_rtt_ms,
                    r.timestamp.isoformat(),
                ]
            )

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename=diagnostics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            },
        )

    else:  # JSON
        return [
            {
                "device_ip": r.device_ip,
                "device_name": r.device_name,
                "packet_loss_percent": r.packet_loss_percent,
                "avg_rtt_ms": r.avg_rtt_ms,
                "min_rtt_ms": r.min_rtt_ms,
                "max_rtt_ms": r.max_rtt_ms,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in results
        ]


# ============================================
# ADVANCED NETWORK TOOLS
# ============================================


@router.post("/dns/lookup")
async def dns_lookup(hostname: str, current_user: User = Depends(get_current_active_user)):
    """Perform DNS lookup"""
    import socket

    try:
        # Forward lookup
        ip_address = socket.gethostbyname(hostname)

        # Reverse lookup
        try:
            reverse_hostname = socket.gethostbyaddr(ip_address)[0]
        except Exception as e:
            logging.getLogger(__name__).error(f"Error: {e}")
            reverse_hostname = None

        # Get all addresses
        try:
            all_ips = socket.getaddrinfo(hostname, None)
            ip_list = list(set([addr[4][0] for addr in all_ips]))
        except Exception as e:
            logging.getLogger(__name__).error(f"Error: {e}")
            ip_list = [ip_address]

        return {
            "hostname": hostname,
            "ip_address": ip_address,
            "all_ips": ip_list,
            "reverse_hostname": reverse_hostname,
            "success": True,
        }
    except Exception as e:
        return {"hostname": hostname, "error": str(e), "success": False}


@router.post("/dns/reverse")
async def reverse_dns_lookup(ip: str, current_user: User = Depends(get_current_active_user)):
    """Perform reverse DNS lookup"""
    import socket

    try:
        hostname = socket.gethostbyaddr(ip)[0]
        return {"ip_address": ip, "hostname": hostname, "success": True}
    except Exception as e:
        return {"ip_address": ip, "error": str(e), "success": False}


@router.post("/portscan")
async def port_scan(ip: str, ports: str = "22,80,443,3389,8080", current_user: User = Depends(get_current_active_user)):
    """Scan specific ports on a device"""
    import socket

    port_list = [int(p.strip()) for p in ports.split(",")]
    results = []

    for port in port_list:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((ip, port))
            sock.close()

            is_open = result == 0
            results.append({"port": port, "status": "open" if is_open else "closed", "is_open": is_open})
        except Exception as e:
            results.append({"port": port, "status": "error", "is_open": False, "error": str(e)})

    return {
        "ip_address": ip,
        "ports_scanned": len(port_list),
        "open_ports": len([r for r in results if r["is_open"]]),
        "results": results,
    }


# ============================================
# PERFORMANCE BASELINES & ANOMALY DETECTION
# ============================================


@router.post("/baseline/calculate")
async def calculate_baseline(
    ip: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """Calculate performance baseline for a device"""
    from sqlalchemy import func
    from datetime import timedelta

    # Get data from last 7 days
    since = datetime.utcnow() - timedelta(days=7)

    results = (
        db.query(PingResult)
        .filter(PingResult.device_ip == ip, PingResult.timestamp >= since, PingResult.is_reachable == True)
        .all()
    )

    if len(results) < 10:
        return {"error": "Insufficient data for baseline calculation (minimum 10 samples required)", "success": False}

    # Calculate statistics
    latencies = [r.avg_rtt_ms for r in results if r.avg_rtt_ms]
    packet_losses = [r.packet_loss_percent for r in results]

    avg_latency = sum(latencies) / len(latencies)
    stddev_latency = (sum([(x - avg_latency) ** 2 for x in latencies]) / len(latencies)) ** 0.5
    avg_packet_loss = sum(packet_losses) / len(packet_losses)

    # Set thresholds (mean + 2*stddev for warning, mean + 3*stddev for critical)
    warning_threshold = int(avg_latency + 2 * stddev_latency)
    critical_threshold = int(avg_latency + 3 * stddev_latency)

    # Update or create baseline
    baseline = db.query(PerformanceBaseline).filter(PerformanceBaseline.device_ip == ip).first()

    if baseline:
        baseline.baseline_latency_avg = int(avg_latency)
        baseline.baseline_latency_stddev = int(stddev_latency)
        baseline.baseline_packet_loss = int(avg_packet_loss)
        baseline.latency_warning_threshold = warning_threshold
        baseline.latency_critical_threshold = critical_threshold
        baseline.samples_count = len(results)
        baseline.last_calculated = datetime.utcnow()
        baseline.updated_at = datetime.utcnow()
    else:
        baseline = PerformanceBaseline(
            device_ip=ip,
            device_name=results[0].device_name if results else ip,
            baseline_latency_avg=int(avg_latency),
            baseline_latency_stddev=int(stddev_latency),
            baseline_packet_loss=int(avg_packet_loss),
            latency_warning_threshold=warning_threshold,
            latency_critical_threshold=critical_threshold,
            samples_count=len(results),
        )
        db.add(baseline)

    db.commit()

    return {
        "success": True,
        "device_ip": ip,
        "baseline_latency_avg": int(avg_latency),
        "baseline_latency_stddev": int(stddev_latency),
        "baseline_packet_loss": int(avg_packet_loss),
        "warning_threshold": warning_threshold,
        "critical_threshold": critical_threshold,
        "samples_used": len(results),
    }


@router.get("/baseline/{ip}")
async def get_baseline(ip: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get performance baseline for a device"""

    baseline = db.query(PerformanceBaseline).filter(PerformanceBaseline.device_ip == ip).first()

    if not baseline:
        return {"error": "No baseline found for this device", "success": False}

    return {
        "device_ip": baseline.device_ip,
        "device_name": baseline.device_name,
        "baseline_latency_avg": baseline.baseline_latency_avg,
        "baseline_latency_stddev": baseline.baseline_latency_stddev,
        "baseline_packet_loss": baseline.baseline_packet_loss,
        "warning_threshold": baseline.latency_warning_threshold,
        "critical_threshold": baseline.latency_critical_threshold,
        "samples_count": baseline.samples_count,
        "last_calculated": baseline.last_calculated.isoformat(),
    }


@router.post("/anomaly/detect")
async def detect_anomaly(ip: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Detect anomalies by comparing current performance to baseline"""
    from datetime import timedelta

    # Get baseline
    baseline = db.query(PerformanceBaseline).filter(PerformanceBaseline.device_ip == ip).first()
    if not baseline:
        return {"error": "No baseline found. Calculate baseline first.", "success": False}

    # Get recent results (last hour)
    since = datetime.utcnow() - timedelta(hours=1)
    recent = (
        db.query(PingResult)
        .filter(PingResult.device_ip == ip, PingResult.timestamp >= since)
        .order_by(PingResult.timestamp.desc())
        .limit(10)
        .all()
    )

    if not recent:
        return {"error": "No recent data available", "success": False}

    # Calculate current metrics
    current_latency = sum([r.avg_rtt_ms for r in recent if r.avg_rtt_ms]) / len([r for r in recent if r.avg_rtt_ms])
    current_loss = sum([r.packet_loss_percent for r in recent]) / len(recent)

    # Detect anomalies
    anomalies = []

    if current_latency > baseline.latency_critical_threshold:
        anomalies.append(
            {
                "type": "latency",
                "severity": "critical",
                "message": f"Latency ({current_latency:.1f}ms) exceeds critical threshold ({baseline.latency_critical_threshold}ms)",
                "current_value": current_latency,
                "threshold": baseline.latency_critical_threshold,
            }
        )
    elif current_latency > baseline.latency_warning_threshold:
        anomalies.append(
            {
                "type": "latency",
                "severity": "warning",
                "message": f"Latency ({current_latency:.1f}ms) exceeds warning threshold ({baseline.latency_warning_threshold}ms)",
                "current_value": current_latency,
                "threshold": baseline.latency_warning_threshold,
            }
        )

    if current_loss > baseline.packet_loss_threshold:
        anomalies.append(
            {
                "type": "packet_loss",
                "severity": "warning",
                "message": f"Packet loss ({current_loss:.1f}%) exceeds threshold ({baseline.packet_loss_threshold}%)",
                "current_value": current_loss,
                "threshold": baseline.packet_loss_threshold,
            }
        )

    return {
        "success": True,
        "device_ip": ip,
        "current_latency": round(current_latency, 1),
        "current_packet_loss": round(current_loss, 1),
        "baseline_latency": baseline.baseline_latency_avg,
        "baseline_packet_loss": baseline.baseline_packet_loss,
        "anomalies_detected": len(anomalies),
        "anomalies": anomalies,
        "status": "anomaly" if anomalies else "normal",
    }
