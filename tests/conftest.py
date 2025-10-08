import os
import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-change-me")
os.environ.setdefault("ENCRYPTION_KEY", "Z4dL4W6p2E4oZ1wR0Tn44K3UthW9ZkHqT7f0Yy5tw6Q=")
os.environ.setdefault("DEFAULT_ADMIN_PASSWORD", "Ward@2025!")

from main import app
from tests.zabbix_stub import StaticZabbixClient


@pytest.fixture(scope="session", autouse=True)
def configure_app_state():
    """Ensure all tests rely on the deterministic Zabbix stub."""
    app.state.zabbix = StaticZabbixClient()
    yield
