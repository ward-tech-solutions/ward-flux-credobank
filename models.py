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
    """Network discovery rule configuration - matches actual DB schema"""

    __tablename__ = "discovery_rules"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    network_range = Column(String(100), nullable=False)  # Single range for now
    enabled = Column(Boolean, default=True)
    schedule = Column(String(100))  # Cron schedule
    snmp_discovery = Column(Boolean, default=True)
    snmp_communities = Column(JSON)  # ["public", "private"]
    ping_only = Column(Boolean, default=False)
    last_run = Column(DateTime)
    last_devices_found = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class DiscoveryResult(Base):
    """Discovered device from network scan - matches actual DB schema"""

    __tablename__ = "discovery_results"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey('discovery_rules.id', ondelete='CASCADE'), nullable=False)

    # Device Information
    ip_address = Column(String(45), nullable=False)  # DB uses ip_address not ip
    hostname = Column(String(255))
    mac_address = Column(String(17))
    vendor = Column(String(100))
    device_type = Column(String(50))

    # SNMP Data
    snmp_reachable = Column(Boolean, default=False)
    snmp_version = Column(String(10))
    sys_descr = Column(Text)
    sys_object_id = Column(String(200))

    # Metadata
    discovered_at = Column(DateTime, server_default=func.now())
    added_to_monitoring = Column(Boolean, default=False)
    added_at = Column(DateTime)


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
    triggered_by_user = Column(Integer, ForeignKey('users.id'))


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


# ============================================
# Branch Management Models
# ============================================

class Branch(Base):
    """Branch/Location organization for devices"""

    __tablename__ = "branches"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)  # UUID as string
    name = Column(String(200), nullable=False, unique=True, index=True)
    display_name = Column(String(200), nullable=False)
    region = Column(String(100), index=True)
    branch_code = Column(String(10))
    address = Column(Text)
    is_active = Column(Boolean, default=True, index=True)
    device_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


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
