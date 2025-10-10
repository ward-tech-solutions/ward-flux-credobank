import os
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from main import app
from database import SessionLocal, init_db, PingResult, TracerouteResult


@pytest.fixture(autouse=True)
def setup_database_fixture():
    # Ensure tables exist
    init_db()
    yield
    # Clean up inserted diagnostics records to avoid cross-test contamination
    session = SessionLocal()
    try:
        session.query(PingResult).delete()
        session.query(TracerouteResult).delete()
        session.commit()
    finally:
        session.close()


def insert_sample_diagnostics():
    session = SessionLocal()
    now = datetime.utcnow()
    try:
        session.add(
            PingResult(
                device_ip="192.0.2.10",
                device_name="Tbilisi Core Router",
                packets_sent=5,
                packets_received=5,
                packet_loss_percent=0,
                min_rtt_ms=12,
                avg_rtt_ms=18,
                max_rtt_ms=30,
                is_reachable=True,
                timestamp=now,
            )
        )
        session.add(
            PingResult(
                device_ip="192.0.2.45",
                device_name="Batumi ATM 1",
                packets_sent=5,
                packets_received=4,
                packet_loss_percent=20,
                min_rtt_ms=40,
                avg_rtt_ms=60,
                max_rtt_ms=85,
                is_reachable=True,
                timestamp=now - timedelta(minutes=5),
            )
        )

        session.add_all(
            [
                TracerouteResult(
                    device_ip="192.0.2.10",
                    device_name="Tbilisi Core Router",
                    hop_number=1,
                    hop_ip="192.0.2.10",
                    hop_hostname="Core-Router-TBS",
                    latency_ms=5,
                    timestamp=now,
                ),
                TracerouteResult(
                    device_ip="192.0.2.10",
                    device_name="Tbilisi Core Router",
                    hop_number=2,
                    hop_ip="192.0.2.1",
                    hop_hostname="Didube-Gateway",
                    latency_ms=12,
                    timestamp=now,
                ),
            ]
        )
        session.commit()
    finally:
        session.close()


def test_diagnostics_summary_returns_aggregated_data():
    insert_sample_diagnostics()
    client = TestClient(app)

    response = client.get("/api/v1/diagnostics/dashboard/summary")
    assert response.status_code == 200
    data = response.json()

    assert data["status_cards"]["ping"]["total"] >= 2
    assert any(region["region"] == "Tbilisi" for region in data["region_latency"])
    assert data["recent_traceroutes"]
    assert data["timeline"]


def test_traceroute_map_returns_coordinates():
    insert_sample_diagnostics()
    client = TestClient(app)

    response = client.get("/api/v1/diagnostics/traceroute/map", params={"ip": "192.0.2.10"})
    assert response.status_code == 200
    payload = response.json()

    assert payload["device_ip"] == "192.0.2.10"
    assert any(hop["coordinates"] for hop in payload["hops"])
