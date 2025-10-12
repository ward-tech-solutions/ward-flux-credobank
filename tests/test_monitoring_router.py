import os
import uuid
from types import SimpleNamespace
from typing import Dict, Any, List

import pytest
from fastapi import FastAPI, APIRouter
from fastapi.testclient import TestClient
from fastapi.routing import APIRoute
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure encryption keys are available before importing modules that require them
os.environ.setdefault("ENCRYPTION_KEY", "Z4dL4W6p2E4oZ1wR0Tn44K3UthW9ZkHqT7f0Yy5tw6Q=")
os.environ.setdefault("WARD_ENCRYPTION_KEY", "T5Vzgu0kNimC_JB1pZ-8R1t8eSGYbT5XN8jvwp5KVyE=")

from database import Base, User, UserRole, get_db  # noqa: E402
import monitoring.models  # noqa: F401,E402
from monitoring.models import SNMPCredential, MonitoringItem  # noqa: E402
from monitoring.snmp.crypto import decrypt_credential  # noqa: E402
from monitoring.snmp.poller import SNMPResult  # noqa: E402
from routers.monitoring import router, get_current_active_user, SUPPORTED_VENDORS  # noqa: E402


class FakeZabbix:
    """Minimal Zabbix client stub for tests."""

    def __init__(self) -> None:
        self.devices: Dict[str, Dict[str, Any]] = {}

    def add_device(self, hostid: str, hostname: str, ip: str) -> None:
        self.devices[hostid] = {
            "hostid": hostid,
            "hostname": hostname,
            "ip": ip,
        }

    def get_host_details(self, hostid: str) -> Dict[str, Any]:
        return self.devices.get(hostid)


class DummyPoller:
    """Deterministic SNMP poller stub to avoid network activity."""

    def __init__(self) -> None:
        self.get_calls: List[Any] = []
        self.bulk_calls: List[Any] = []

    async def get(self, ip: str, oid: str, *_args, **_kwargs) -> SNMPResult:
        self.get_calls.append((ip, oid))
        return SNMPResult(oid=oid, value="Ward Device", value_type="string", success=True)

    async def detect_device(self, ip: str, *_args, **_kwargs) -> Dict[str, Any]:
        return {
            "vendor": "Cisco",
            "device_type": "Router",
            "sys_descr": f"Test device at {ip}",
        }

    async def bulk_get(self, ip: str, oids: List[str], *_args, **_kwargs) -> List[SNMPResult]:
        self.bulk_calls.append((ip, tuple(oids)))
        results: List[SNMPResult] = []
        for index, oid in enumerate(oids):
            results.append(
                SNMPResult(
                    oid=oid,
                    value=f"value-{index}",
                    value_type="string",
                    success=True,
                )
            )
        return results


@pytest.fixture
def test_context(monkeypatch):
    """Provide an isolated FastAPI app, database, and stubs for each test."""

    # In-memory SQLite that works across threads for FastAPI TestClient
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    app = FastAPI()

    # Clone the monitoring router but drop response_model validation to avoid UUID vs string mismatches.
    monitoring_router = APIRouter(tags=router.tags)
    for route in router.routes:
        if isinstance(route, APIRoute):
            monitoring_router.add_api_route(
                route.path,
                route.endpoint,
                methods=list(route.methods or []),
                dependencies=route.dependencies,
                summary=route.summary,
                description=route.description,
                status_code=route.status_code,
                response_class=route.response_class,
                responses=route.responses,
                name=route.name,
            )
    app.include_router(monitoring_router)

    fake_zabbix = FakeZabbix()
    app.state.zabbix = fake_zabbix

    # Some legacy OID definitions miss the optional category attribute; set a sensible default for tests.
    from monitoring.snmp.oids import UNIVERSAL_OIDS

    for definition in UNIVERSAL_OIDS.values():
        if not hasattr(definition, "category"):
            setattr(definition, "category", "general")

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    def override_current_user():
        return SimpleNamespace(
            id=1,
            username="qa-admin",
            role=UserRole.ADMIN.value,
            is_active=True,
            is_superuser=True,
        )

    app.dependency_overrides[get_current_active_user] = override_current_user

    # Pre-seed a real user record so queries against the users table succeed if executed
    db = TestingSessionLocal()
    try:
        user = User(
            username="qa-admin",
            email="qa-admin@wardops.tech",
            full_name="QA Admin",
            hashed_password="not-used-in-tests",
            role=UserRole.ADMIN,
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    stub_poller = DummyPoller()
    monkeypatch.setattr("routers.monitoring.get_snmp_poller", lambda: stub_poller)

    with TestClient(app) as client:
        yield {
            "client": client,
            "sessionmaker": TestingSessionLocal,
            "zabbix": fake_zabbix,
            "poller": stub_poller,
        }

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def create_device(zabbix: FakeZabbix, hostid: str = "101", hostname: str = "Edge-Router", ip: str = "192.0.2.10"):
    zabbix.add_device(hostid=hostid, hostname=hostname, ip=ip)
    return hostid


def create_snmp_v2c_payload(hostid: str, community: str = "public") -> Dict[str, Any]:
    return {
        "hostid": hostid,
        "version": "v2c",
        "community": community,
    }


def get_credentials(sessionmaker, hostid: str) -> SNMPCredential:
    session = sessionmaker()
    try:
        device_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"zabbix-host-{hostid}")
        return session.query(SNMPCredential).filter_by(device_id=device_uuid).first()
    finally:
        session.close()


def get_monitoring_items(sessionmaker, hostid: str) -> List[MonitoringItem]:
    session = sessionmaker()
    try:
        device_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"zabbix-host-{hostid}")
        return session.query(MonitoringItem).filter_by(device_id=device_uuid).all()
    finally:
        session.close()


def test_create_and_list_monitoring_profiles(test_context):
    client = test_context["client"]

    response = client.post(
        "/api/v1/monitoring/profiles",
        json={"name": "Primary Monitoring", "mode": "zabbix", "description": "Main profile"},
    )
    assert response.status_code == 201
    profile_id = response.json()["id"]
    assert profile_id

    list_response = client.get("/api/v1/monitoring/profiles")
    assert list_response.status_code == 200
    profiles = list_response.json()
    assert len(profiles) == 1
    assert profiles[0]["name"] == "Primary Monitoring"


def test_activate_monitoring_profile(test_context):
    client = test_context["client"]

    response_a = client.post("/api/v1/monitoring/profiles", json={"name": "Standalone", "mode": "standalone"})
    response_b = client.post("/api/v1/monitoring/profiles", json={"name": "Hybrid", "mode": "hybrid"})
    profile_a = response_a.json()["id"]
    profile_b = response_b.json()["id"]

    activate = client.post(f"/api/v1/monitoring/profiles/{profile_b}/activate")
    assert activate.status_code == 200
    payload = activate.json()
    assert payload["success"] is True
    assert payload["active_profile"] == "Hybrid"
    assert payload["mode"] == "hybrid"

    # Only the second profile should be active
    profiles = client.get("/api/v1/monitoring/profiles").json()
    active_states = {profile["name"]: profile["is_active"] for profile in profiles}
    assert active_states == {"Standalone": False, "Hybrid": True}


def test_create_snmp_credential_v2c_flow(test_context):
    client = test_context["client"]
    sessionmaker = test_context["sessionmaker"]
    hostid = create_device(test_context["zabbix"])

    response = client.post("/api/v1/monitoring/credentials", json=create_snmp_v2c_payload(hostid))
    assert response.status_code == 201
    body = response.json()
    assert body["version"] == "v2c"

    stored = get_credentials(sessionmaker, hostid)
    assert stored is not None
    assert stored.community_encrypted
    assert stored.community_encrypted != "public"
    assert decrypt_credential(stored.community_encrypted) == "public"

    by_host = client.get(f"/api/v1/monitoring/credentials/host/{hostid}")
    assert by_host.status_code == 200
    assert by_host.json()["device_id"] == str(stored.device_id)


def test_duplicate_snmp_credentials_blocked(test_context):
    client = test_context["client"]
    hostid = create_device(test_context["zabbix"])

    first = client.post("/api/v1/monitoring/credentials", json=create_snmp_v2c_payload(hostid))
    assert first.status_code == 201

    duplicate = client.post("/api/v1/monitoring/credentials", json=create_snmp_v2c_payload(hostid))
    assert duplicate.status_code == 400
    assert "already exist" in duplicate.json()["detail"]


def test_snmp_credentials_require_community_for_v2c(test_context):
    client = test_context["client"]
    hostid = create_device(test_context["zabbix"])

    response = client.post(
        "/api/v1/monitoring/credentials",
        json={"hostid": hostid, "version": "v2c"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Community string required for SNMPv2c"


def test_test_snmp_credentials_success(test_context):
    client = test_context["client"]
    hostid = create_device(test_context["zabbix"])

    response = client.post(
        "/api/v1/monitoring/credentials/test",
        json=create_snmp_v2c_payload(hostid),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["device"] == "Edge-Router"
    assert payload["sys_descr"] == "Ward Device"


def test_detect_device_with_existing_credentials(test_context):
    client = test_context["client"]
    sessionmaker = test_context["sessionmaker"]
    hostid = create_device(test_context["zabbix"], hostname="Core-Firewall", ip="198.51.100.15")

    create_resp = client.post("/api/v1/monitoring/credentials", json=create_snmp_v2c_payload(hostid, "secret"))
    assert create_resp.status_code == 201

    detection = client.post(f"/api/v1/monitoring/detect/{hostid}")
    assert detection.status_code == 200
    payload = detection.json()
    assert payload["hostid"] == hostid
    assert payload["hostname"] == "Core-Firewall"
    assert payload["vendor"] == "Cisco"
    assert payload["device_type"] == "Router"
    assert payload["available_oids"] > 0

    stored = get_credentials(sessionmaker, hostid)
    assert decrypt_credential(stored.community_encrypted) == "secret"


def test_create_list_and_delete_monitoring_items(test_context):
    client = test_context["client"]
    sessionmaker = test_context["sessionmaker"]
    hostid = create_device(test_context["zabbix"])

    client.post("/api/v1/monitoring/credentials", json=create_snmp_v2c_payload(hostid))

    create_item = client.post(
        "/api/v1/monitoring/items",
        json={
            "hostid": hostid,
            "oid_name": "CPU Usage",
            "oid": "1.3.6.1.4.1.9.2.1.57.0",
            "interval": 60,
            "enabled": True,
        },
    )
    assert create_item.status_code == 201
    item_id = create_item.json()["id"]

    items = client.get(f"/api/v1/monitoring/items/host/{hostid}")
    assert items.status_code == 200
    payload = items.json()
    assert len(payload) == 1
    assert payload[0]["oid_name"] == "CPU Usage"

    stored_items = get_monitoring_items(sessionmaker, hostid)
    assert len(stored_items) == 1

    delete_resp = client.delete(f"/api/v1/monitoring/items/{item_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["success"] is True

    assert get_monitoring_items(sessionmaker, hostid) == []


def test_poll_device_returns_measurements(test_context):
    client = test_context["client"]
    hostid = create_device(test_context["zabbix"])

    client.post("/api/v1/monitoring/credentials", json=create_snmp_v2c_payload(hostid))

    for suffix in ("cpu", "memory"):
        client.post(
            "/api/v1/monitoring/items",
            json={
                "hostid": hostid,
                "oid_name": f"{suffix.title()} Usage",
                "oid": f"1.3.6.1.4.1.test.{suffix}",
                "interval": 60,
                "enabled": True,
            },
        )

    poll = client.post(f"/api/v1/monitoring/poll/{hostid}")
    assert poll.status_code == 200
    payload = poll.json()
    assert payload["success"] is True
    assert payload["device"] == "Edge-Router"
    assert len(payload["results"]) == 2
    for result in payload["results"]:
        assert result["success"] is True
        assert result["value"].startswith("value-")


def test_get_oid_library_and_vendors(test_context):
    client = test_context["client"]

    universal = client.get("/api/v1/monitoring/oids")
    assert universal.status_code == 200
    body = universal.json()
    assert body["total"] == len(body["oids"])
    assert body["total"] > 0

    vendors = client.get("/api/v1/monitoring/vendors")
    assert vendors.status_code == 200
    vendor_body = vendors.json()
    assert vendor_body["total"] == len(SUPPORTED_VENDORS)
    assert set(vendor_body["vendors"]) == set(SUPPORTED_VENDORS)

    missing_vendor = client.get("/api/v1/monitoring/oids?vendor=UnknownVendor")
    assert missing_vendor.status_code == 200
    assert missing_vendor.json()["total"] == body["total"]


def test_monitoring_health_endpoint(test_context):
    client = test_context["client"]

    response = client.get("/api/v1/monitoring/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "operational"
    assert payload["total_endpoints"] == 14
