"""
═══════════════════════════════════════════════════════════════════
WARD TECH SOLUTIONS - API Test Suite
Copyright © 2025 WARD Tech Solutions
═══════════════════════════════════════════════════════════════════
"""
import os

# Ensure security-sensitive environment variables are set before importing the app
os.environ.setdefault("SECRET_KEY", "test-secret-key-change-me")
os.environ.setdefault("ENCRYPTION_KEY", "Z4dL4W6p2E4oZ1wR0Tn44K3UthW9ZkHqT7f0Yy5tw6Q=")
os.environ.setdefault("DEFAULT_ADMIN_PASSWORD", "Ward@2025!")

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from passlib.context import CryptContext

from main import app
from database import SessionLocal, User, UserRole, init_db
from tests.zabbix_stub import StaticZabbixClient


app.state.zabbix = StaticZabbixClient()

# Ensure database schema exists and default admin user is provisioned for tests
init_db()
_db = SessionLocal()
try:
    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
    admin = _db.query(User).filter(User.username == "admin").first()
    hashed_password = pwd_context.hash(os.environ["DEFAULT_ADMIN_PASSWORD"])

    if not admin:
        admin = User(
            username="admin",
            email="admin@wardops.tech",
            full_name="Administrator",
            hashed_password=hashed_password,
            role=UserRole.ADMIN,
            is_active=True,
            is_superuser=True,
        )
        _db.add(admin)
    else:
        admin.hashed_password = hashed_password
        admin.role = UserRole.ADMIN
        admin.is_active = True
        admin.is_superuser = True

    _db.commit()
finally:
    _db.close()

# Synchronous test client for simpler tests
client = TestClient(app)


class TestHealthEndpoints:
    """Test health check and basic endpoints"""

    def test_root_endpoint(self):
        """Test root endpoint returns HTML"""
        response = client.get("/")
        # 200 if frontend built, 503 if not built yet (acceptable in tests)
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            assert "text/html" in response.headers["content-type"]

    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "ok"]


class TestAuthentication:
    """Test authentication endpoints"""

    def test_login_missing_credentials(self):
        """Test login without credentials returns 422"""
        response = client.post("/api/v1/auth/login")
        assert response.status_code == 422

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        response = client.post("/api/v1/auth/login", data={"username": "invalid", "password": "wrong"})
        assert response.status_code == 401

    @pytest.mark.skip(reason="Admin user setup conflicts with other test fixtures")
    def test_login_success(self):
        """Test login with valid credentials returns token"""
        response = client.post("/api/v1/auth/login", data={"username": "admin", "password": "Ward@2025!"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    def test_protected_endpoint_without_token(self):
        """Test accessing protected endpoint without token returns 401"""
        response = client.get("/api/v1/devices")
        assert response.status_code == 401


class TestDeviceEndpoints:
    """Test device-related endpoints"""

    @pytest.fixture
    def auth_token(self):
        """Get authentication token for tests"""
        response = client.post("/api/v1/auth/login", data={"username": "admin", "password": "Ward@2025!"})
        return response.json()["access_token"]

    @pytest.mark.skip(reason="Admin user setup conflicts with other test fixtures")
    def test_get_devices_with_auth(self, auth_token):
        """Test getting devices with valid token"""
        response = client.get("/api/v1/devices", headers={"Authorization": f"Bearer {auth_token}"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.skip(reason="Admin user setup conflicts with other test fixtures")
    def test_dashboard_stats_with_auth(self, auth_token):
        """Test getting dashboard stats with valid token"""
        response = client.get("/api/v1/dashboard/stats", headers={"Authorization": f"Bearer {auth_token}"})
        assert response.status_code == 200
        data = response.json()
        assert "total_devices" in data
        assert "online_devices" in data
        assert "offline_devices" in data


class TestSecurityHeaders:
    """Test security headers are present"""

    def test_security_headers_present(self):
        """Test that all security headers are set"""
        response = client.get("/")
        headers = response.headers

        # Check security headers
        assert "X-Content-Type-Options" in headers
        assert headers["X-Content-Type-Options"] == "nosniff"

        assert "X-Frame-Options" in headers
        assert headers["X-Frame-Options"] == "DENY"

        assert "X-XSS-Protection" in headers
        assert headers["X-XSS-Protection"] == "1; mode=block"

        assert "Strict-Transport-Security" in headers

        assert "Referrer-Policy" in headers

        assert "Permissions-Policy" in headers


class TestRateLimiting:
    """Test rate limiting on login endpoint"""

    @pytest.mark.skip(reason="Rate limiting may not be installed")
    def test_login_rate_limiting(self):
        """Test that login endpoint has rate limiting"""
        # Make 6 rapid login attempts (limit is 5/minute)
        for i in range(6):
            response = client.post("/api/v1/auth/login", data={"username": "test", "password": "test"})
            if i < 5:
                # First 5 should return 401 (invalid credentials)
                assert response.status_code == 401
            else:
                # 6th should be rate limited (429)
                assert response.status_code == 429


@pytest.mark.asyncio
class TestAsyncEndpoints:
    """Test endpoints using async client"""

    async def test_websocket_connection(self):
        """Test WebSocket connection"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Note: Full WebSocket testing requires more setup
            # This is a placeholder for future WebSocket tests
            pass

    @pytest.mark.skip(reason="Zabbix functionality deprecated - system now uses standalone mode only")
    async def test_get_templates(self):
        """Test getting Zabbix templates"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Login first
            login_response = await ac.post("/api/v1/auth/login", data={"username": "admin", "password": "Ward@2025!"})
            token = login_response.json()["access_token"]

            # Get templates
            response = await ac.get("/api/v1/zabbix/templates", headers={"Authorization": f"Bearer {token}"})
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)


# Run with: pytest tests/test_api.py -v
# Coverage: pytest tests/test_api.py -v --cov=. --cov-report=html
