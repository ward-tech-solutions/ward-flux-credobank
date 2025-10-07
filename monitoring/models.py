"""
WARD FLUX - Monitoring Models
Database models for standalone monitoring system
"""

import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, JSON, UUID as SQLAlchemyUUID, Enum as SQLAlchemyEnum
from database import Base


# ============================================
# Enums
# ============================================

class MonitoringMode(str, Enum):
    """Monitoring mode selection"""
    ZABBIX = "ZABBIX"          # Use Zabbix API only
    STANDALONE = "STANDALONE"   # Use standalone monitoring only
    HYBRID = "HYBRID"          # Use both sources


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


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

    # Rule definition
    name = Column(String(200), nullable=False)
    description = Column(Text)
    expression = Column(String(500), nullable=False)  # e.g., "cpu_usage > 90"
    severity = Column(SQLAlchemyEnum(AlertSeverity), nullable=False)

    # Notification settings
    notification_channels = Column(JSON)  # ["email", "webhook", "sms"]
    notification_config = Column(JSON)  # Email addresses, webhook URLs, etc.

    # Rule behavior
    enabled = Column(Boolean, nullable=False, default=True)
    evaluation_interval = Column(Integer, default=60)  # seconds
    for_duration = Column(Integer, default=300)  # Alert after condition is true for X seconds

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlertHistory(Base):
    """Alert history - triggered alerts"""
    __tablename__ = "alert_history"

    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("alert_rules.id"), nullable=False)
    device_id = Column(SQLAlchemyUUID(as_uuid=True), index=True)

    # Alert details
    severity = Column(SQLAlchemyEnum(AlertSeverity), nullable=False)
    message = Column(Text, nullable=False)
    value = Column(String(100))  # Value that triggered the alert

    # Alert lifecycle
    triggered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(SQLAlchemyUUID(as_uuid=True))  # User ID
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)

    # Notification tracking
    notifications_sent = Column(JSON)  # [{"channel": "email", "sent_at": "..."}]

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class DiscoveryRule(Base):
    """Network discovery rules - auto-discover devices"""
    __tablename__ = "discovery_rules"
    __table_args__ = {'extend_existing': True}

    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)

    # Discovery scope
    network_range = Column(String(100), nullable=False)  # "192.168.1.0/24" or "10.0.0.1-10.0.0.254"

    # Discovery methods
    ping_scan = Column(Boolean, default=True)
    snmp_scan = Column(Boolean, default=True)
    port_scan = Column(Boolean, default=False)
    ports = Column(JSON)  # [22, 80, 443]

    # Scheduling
    enabled = Column(Boolean, default=True)
    schedule = Column(String(100))  # Cron expression: "0 2 * * *"
    last_run = Column(DateTime)
    next_run = Column(DateTime)

    # Auto-add settings
    auto_add_devices = Column(Boolean, default=False)
    default_template_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("monitoring_templates.id"))

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class DiscoveryResult(Base):
    """Discovery results - found devices"""
    __tablename__ = "discovery_results"
    __table_args__ = {'extend_existing': True}

    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("discovery_rules.id"), nullable=False)

    # Device info
    ip_address = Column(String(45), nullable=False)
    hostname = Column(String(255))
    mac_address = Column(String(17))

    # Detection results
    is_alive = Column(Boolean, default=False)
    snmp_reachable = Column(Boolean, default=False)
    snmp_version = Column(String(10))
    sys_descr = Column(Text)
    sys_object_id = Column(String(200))

    # Classification
    detected_vendor = Column(String(100))
    detected_type = Column(String(100))
    open_ports = Column(JSON)

    # Status
    discovered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    added_to_monitoring = Column(Boolean, default=False)
    added_at = Column(DateTime)
    device_id = Column(SQLAlchemyUUID(as_uuid=True))  # Link to created device


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
