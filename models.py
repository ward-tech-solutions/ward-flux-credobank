"""
WARD TECH SOLUTIONS - Database Models
Multi-tenant configuration support
"""
import logging
import uuid
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Float, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from database import Base

logger = logging.getLogger(__name__)


class Organization(Base):
    """Organization/Company configuration"""

    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    subdomain = Column(String(100), unique=True, nullable=True)

    # Zabbix Configuration
    zabbix_url = Column(String(500), nullable=False)
    zabbix_user = Column(String(255), nullable=False)
    zabbix_password = Column(String(255), nullable=False)

    # Selected host groups (JSON array of group IDs)
    monitored_groups = Column(JSON, default=list)

    # Company Branding
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), default="#5EBBA8")

    # Status
    is_active = Column(Boolean, default=True)
    is_setup_complete = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SystemConfig(Base):
    """System-wide configuration settings"""

    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    description = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SetupWizardState(Base):
    """Track setup wizard progress"""

    __tablename__ = "setup_wizard_state"

    id = Column(Integer, primary_key=True, index=True)

    # Setup steps
    step_1_welcome = Column(Boolean, default=False)
    step_2_zabbix = Column(Boolean, default=False)
    step_3_groups = Column(Boolean, default=False)
    step_4_admin = Column(Boolean, default=False)
    step_5_complete = Column(Boolean, default=False)

    # Overall status
    is_complete = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# Note: User model is defined in database.py
# We import it in setup_wizard.py when needed


# ============================================
# Auto-Discovery Models
# ============================================

class DiscoveryRule(Base):
    """Network discovery rule configuration"""

    __tablename__ = "discovery_rules"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    enabled = Column(Boolean, default=True)

    # Network Configuration
    network_ranges = Column(JSON, nullable=False)  # ["192.168.1.0/24", "10.0.0.0/16"]
    excluded_ips = Column(JSON)  # ["192.168.1.1", "192.168.1.254"]

    # Discovery Methods
    use_ping = Column(Boolean, default=True)
    use_snmp = Column(Boolean, default=True)
    use_ssh = Column(Boolean, default=False)

    # SNMP Configuration
    snmp_communities = Column(JSON)  # ["public", "private"]
    snmp_v3_credentials = Column(JSON)  # Array of v3 credential objects
    snmp_ports = Column(JSON, default=lambda: [161])  # [161, 1161]

    # SSH Configuration
    ssh_port = Column(Integer, default=22)
    ssh_credentials = Column(JSON)  # Array of SSH credential objects

    # Scheduling
    schedule_enabled = Column(Boolean, default=False)
    schedule_cron = Column(String(100))  # "0 */6 * * *"
    last_run = Column(DateTime)
    next_run = Column(DateTime)

    # Auto-Import Settings
    auto_import = Column(Boolean, default=False)
    auto_assign_template = Column(Boolean, default=True)
    default_monitoring_profile = Column(UUID(as_uuid=True), ForeignKey('monitoring_profiles.id'))

    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class DiscoveryResult(Base):
    """Discovered device from network scan"""

    __tablename__ = "discovery_results"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey('discovery_rules.id', ondelete='CASCADE'), nullable=False)

    # Device Information
    ip = Column(String(45), nullable=False, index=True)
    hostname = Column(String(200))
    mac_address = Column(String(17))
    vendor = Column(String(100))
    device_type = Column(String(100))
    model = Column(String(200))
    os_version = Column(String(200))

    # Discovery Details
    discovered_via = Column(String(50))  # 'ping', 'snmp', 'ssh'
    ping_responsive = Column(Boolean, default=False)
    ping_latency_ms = Column(Float)
    snmp_responsive = Column(Boolean, default=False)
    snmp_version = Column(String(10))  # 'v1', 'v2c', 'v3'
    snmp_community = Column(String(100))  # Community that worked
    ssh_responsive = Column(Boolean, default=False)

    # SNMP Data
    sys_descr = Column(Text)
    sys_name = Column(String(200))
    sys_oid = Column(String(200))
    sys_uptime = Column(BigInteger)
    sys_contact = Column(String(200))
    sys_location = Column(String(200))

    # Status
    status = Column(String(50), default='discovered')  # 'discovered', 'imported', 'ignored', 'failed'
    import_status = Column(String(50))  # 'pending', 'success', 'failed'
    imported_device_id = Column(UUID(as_uuid=True), ForeignKey('standalone_devices.id'))
    failure_reason = Column(Text)

    # Metadata
    discovered_at = Column(DateTime, server_default=func.now(), index=True)
    imported_at = Column(DateTime)


class DiscoveryJob(Base):
    """Discovery job execution tracking"""

    __tablename__ = "discovery_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey('discovery_rules.id', ondelete='CASCADE'), nullable=False)

    # Job Status
    status = Column(String(50), default='running', index=True)  # 'running', 'completed', 'failed', 'cancelled'

    # Progress Tracking
    total_ips = Column(Integer, default=0)
    scanned_ips = Column(Integer, default=0)
    discovered_devices = Column(Integer, default=0)
    imported_devices = Column(Integer, default=0)
    failed_ips = Column(Integer, default=0)

    # Timing
    started_at = Column(DateTime, server_default=func.now(), index=True)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)

    # Results
    error_message = Column(Text)
    scan_summary = Column(JSON)  # JSON summary of scan results

    # Metadata
    triggered_by = Column(String(50))  # 'manual', 'scheduled', 'api'
    triggered_by_user = Column(UUID(as_uuid=True), ForeignKey('users.id'))


class NetworkTopology(Base):
    """Discovered network connections and topology"""

    __tablename__ = "network_topology"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Source Device
    source_ip = Column(String(45), nullable=False, index=True)
    source_device_id = Column(UUID(as_uuid=True), ForeignKey('standalone_devices.id', ondelete='CASCADE'))

    # Target Device
    target_ip = Column(String(45), nullable=False, index=True)
    target_device_id = Column(UUID(as_uuid=True), ForeignKey('standalone_devices.id', ondelete='CASCADE'))

    # Connection Details
    connection_type = Column(String(50))  # 'direct', 'router', 'switch', 'vpn'
    interface_name = Column(String(100))
    target_interface = Column(String(100))
    vlan_id = Column(Integer)

    # Discovery Method
    discovered_via = Column(String(50))  # 'arp', 'cdp', 'lldp', 'snmp', 'traceroute'

    # Status
    is_active = Column(Boolean, default=True, index=True)
    last_seen = Column(DateTime, server_default=func.now())
    first_discovered = Column(DateTime, server_default=func.now())


class DiscoveryCredential(Base):
    """Credentials for device discovery"""

    __tablename__ = "discovery_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    credential_type = Column(String(50), nullable=False, index=True)  # 'snmp_v2c', 'snmp_v3', 'ssh'

    # SNMP v2c
    community_encrypted = Column(Text)

    # SNMP v3
    username = Column(String(100))
    auth_protocol = Column(String(20))  # 'MD5', 'SHA', 'SHA-256'
    auth_key_encrypted = Column(Text)
    priv_protocol = Column(String(20))  # 'DES', 'AES', 'AES-256'
    priv_key_encrypted = Column(Text)

    # SSH
    ssh_username = Column(String(100))
    ssh_password_encrypted = Column(Text)
    ssh_key_encrypted = Column(Text)

    # Usage Stats
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    last_success = Column(DateTime)

    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(DateTime, server_default=func.now())
