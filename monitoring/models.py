"""
WARD FLUX - Monitoring Models
Database models for standalone monitoring system
"""

import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, JSON, UUID as SQLAlchemyUUID, Enum as SQLAlchemyEnum, func
from database import Base


# ============================================
# Enums
# ============================================

class MonitoringMode(str, Enum):
    """Monitoring mode selection"""
    standalone = "standalone"  # Standalone ICMP + SNMP monitoring
    snmp_only = "snmp_only"    # SNMP polling only (no ICMP)


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# ============================================
# Core Models
# ============================================

class MonitoringProfile(Base):
    """Monitoring profile - defines which mode is active"""
    __tablename__ = "monitoring_profiles"

    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    mode = Column(SQLAlchemyEnum(MonitoringMode), nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
    description = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class StandaloneDevice(Base):
    """Standalone devices - independent of Zabbix"""
    __tablename__ = "standalone_devices"

    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    ip = Column(String(45), nullable=False)  # IPv4 or IPv6
    hostname = Column(String(255))
    vendor = Column(String(100))  # Cisco, Fortinet, Juniper, etc.
    device_type = Column(String(100))  # router, switch, firewall, server, etc.
    model = Column(String(100))
    location = Column(String(200))
    description = Column(Text)
    enabled = Column(Boolean, nullable=False, default=True)

    # Auto-discovery metadata
    discovered_at = Column(DateTime)
    last_seen = Column(DateTime)

    # Organization/grouping
    tags = Column(JSON)  # ["production", "core", "datacenter-1"]
    custom_fields = Column(JSON)  # Flexible key-value storage

    # Branch relationship and normalized naming
    branch_id = Column(String(36))  # Foreign key to branches table
    normalized_name = Column(String(200))  # Clean device name without PING-, IPs, etc.
    device_subtype = Column(String(100))  # More specific categorization
    floor_info = Column(String(50))  # Floor information if applicable
    unit_number = Column(Integer)  # Unit/instance number
    original_name = Column(String(200))  # Preserve original name

    # SSH Configuration
    ssh_port = Column(Integer, default=22)  # SSH port number
    ssh_username = Column(String(100))  # SSH username
    ssh_enabled = Column(Boolean, default=True)  # Whether SSH is available on this device

    # SNMP Configuration (denormalized for quick access)
    snmp_community = Column(String(255))  # SNMP community string (v2c)
    snmp_version = Column(String(10))  # SNMP version (v1, v2c, v3)
    snmp_port = Column(Integer, default=161)  # SNMP port (default 161)

    # Downtime tracking
    down_since = Column(DateTime)  # When the device first went down (set when Up -> Down, cleared when Down -> Up)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class SNMPCredential(Base):
    """SNMP credentials (v2c/v3) - encrypted storage"""
    __tablename__ = "snmp_credentials"

    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(SQLAlchemyUUID(as_uuid=True), nullable=False, index=True)
    version = Column(String(10), nullable=False)  # v2c or v3

    # SNMPv2c
    community_encrypted = Column(Text)

    # SNMPv3
    username = Column(String(100))
    auth_protocol = Column(String(20))  # MD5, SHA
    auth_key_encrypted = Column(Text)
    priv_protocol = Column(String(20))  # DES, AES
    priv_key_encrypted = Column(Text)
    security_level = Column(String(20))  # noAuthNoPriv, authNoPriv, authPriv

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# PingResult model is defined in database.py to avoid duplication

class MonitoringTemplate(Base):
    """Monitoring templates - pre-configured monitoring items"""
    __tablename__ = "monitoring_templates"

    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    vendor = Column(String(100))  # Cisco, Fortinet, etc.
    device_types = Column(JSON)  # ["router", "switch"]

    # Template items (OIDs to monitor)
    items = Column(JSON)  # [{"name": "CPU", "oid": "...", "interval": 60}]

    # Alert triggers
    triggers = Column(JSON)  # [{"name": "High CPU", "expression": "cpu > 90"}]

    # Metadata
    is_default = Column(Boolean, default=False)
    created_by = Column(SQLAlchemyUUID(as_uuid=True))

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class MonitoringItem(Base):
    """Individual monitoring items - what to monitor"""
    __tablename__ = "monitoring_items"

    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(SQLAlchemyUUID(as_uuid=True), nullable=False, index=True)
    template_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("monitoring_templates.id"))

    # Item definition
    oid_name = Column(String(100), nullable=False)
    oid = Column(String(200), nullable=False)
    interval = Column(Integer, nullable=False, default=60)  # seconds

    # Value processing
    value_type = Column(String(20), default="integer")  # integer, float, string, gauge, counter
    units = Column(String(20))  # %, bytes, bps, etc.

    # Item status
    enabled = Column(Boolean, nullable=False, default=True)
    last_poll = Column(DateTime)
    last_value = Column(Text)
    last_error = Column(Text)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlertRule(Base):
    """Alert rules - threshold-based alerting"""
    __tablename__ = "alert_rules"

    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(SQLAlchemyUUID(as_uuid=True), index=True)  # Nullable for global rules
    branch_id = Column(String(36), index=True)  # Branch-level alerts - affects all devices in branch

    # Rule definition
    name = Column(String(200), nullable=False)
    description = Column(Text)
    expression = Column(String(500), nullable=False)  # e.g., "cpu_usage > 90"
    severity = Column(String(20), nullable=False)  # Store as string to avoid enum caching issues

    # Notification settings
    notification_channels = Column(JSON)  # ["email", "webhook", "sms"]
    notification_recipients = Column(JSON)  # Email addresses, webhook URLs, etc.

    # Additional fields
    device_group = Column(String(100))
    monitoring_item_id = Column(SQLAlchemyUUID(as_uuid=True))

    # Rule behavior
    enabled = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlertHistory(Base):
    """Alert history - triggered alerts"""
    __tablename__ = "alert_history"

    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("alert_rules.id"), nullable=True)  # Nullable for ping-based alerts
    device_id = Column(SQLAlchemyUUID(as_uuid=True), index=True)
    rule_name = Column(String(200))

    # Alert details
    severity = Column(SQLAlchemyEnum(AlertSeverity), nullable=False)
    message = Column(Text, nullable=False)
    value = Column(String(100))  # Value that triggered the alert
    threshold = Column(String(500))

    # Alert lifecycle
    triggered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(SQLAlchemyUUID(as_uuid=True))  # User ID
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)

    # Notification tracking
    notifications_sent = Column(JSON, default=list)  # [{"channel": "email", "sent_at": "..."}]

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class DiscoveryRule(Base):
    """Network discovery rules - auto-discover devices - matches actual DB schema"""
    __tablename__ = "discovery_rules"
    __table_args__ = {'extend_existing': True}

    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    """Discovery results - found devices - matches actual DB schema"""
    __tablename__ = "discovery_results"
    __table_args__ = {'extend_existing': True}

    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("discovery_rules.id", ondelete='CASCADE'), nullable=False)

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


class MetricBaseline(Base):
    """Performance baselines - normal behavior tracking"""
    __tablename__ = "metric_baselines"

    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(SQLAlchemyUUID(as_uuid=True), nullable=False, index=True)
    metric_name = Column(String(100), nullable=False)  # cpu_usage, interface_traffic, etc.

    # Baseline statistics
    avg_value = Column(Integer)
    min_value = Column(Integer)
    max_value = Column(Integer)
    std_dev = Column(Integer)

    # Time context
    time_period = Column(String(20))  # hourly, daily, weekly
    hour_of_day = Column(Integer)  # For hourly baselines
    day_of_week = Column(Integer)  # For daily baselines

    # Metadata
    sample_count = Column(Integer)
    last_updated = Column(DateTime)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
