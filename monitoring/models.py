"""
WARD FLUX - Monitoring Database Models

SQLAlchemy models for standalone monitoring engine.
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from database import Base


class MonitoringMode(enum.Enum):
    """Monitoring mode enumeration"""

    ZABBIX = "zabbix"
    STANDALONE = "standalone"
    HYBRID = "hybrid"


class AlertSeverity(enum.Enum):
    """Alert severity levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class MonitoringProfile(Base):
    """
    Monitoring profile - defines which monitoring mode is active
    """

    __tablename__ = "monitoring_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    mode = Column(SQLEnum(MonitoringMode), nullable=False, default=MonitoringMode.STANDALONE)
    is_active = Column(Boolean, default=False, nullable=False)
    description = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<MonitoringProfile(name='{self.name}', mode='{self.mode.value}', active={self.is_active})>"


class SNMPCredential(Base):
    """
    SNMP credentials for devices
    Supports SNMPv2c and SNMPv3 with encrypted storage
    """

    __tablename__ = "snmp_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    version = Column(String(10), nullable=False)  # "v2c" or "v3"

    # SNMPv2c
    community_encrypted = Column(Text)  # Encrypted community string

    # SNMPv3
    username = Column(String(100))
    auth_protocol = Column(String(20))  # MD5, SHA, SHA224, SHA256, SHA384, SHA512
    auth_key_encrypted = Column(Text)  # Encrypted authentication key
    priv_protocol = Column(String(20))  # DES, 3DES, AES, AES192, AES256
    priv_key_encrypted = Column(Text)  # Encrypted privacy key
    security_level = Column(String(20))  # noAuthNoPriv, authNoPriv, authPriv

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    device = relationship("Device", backref="snmp_credentials")

    def __repr__(self):
        return f"<SNMPCredential(device_id='{self.device_id}', version='{self.version}')>"


class MonitoringTemplate(Base):
    """
    Monitoring templates with items and triggers
    """

    __tablename__ = "monitoring_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text)
    vendor = Column(String(100))  # Cisco, Fortinet, Generic, etc.
    device_types = Column(JSON)  # ["router", "switch", "firewall"]
    items = Column(JSON, nullable=False)  # List of monitoring items
    triggers = Column(JSON)  # List of alert triggers
    is_builtin = Column(Boolean, default=False)  # Built-in vs custom template

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<MonitoringTemplate(name='{self.name}', vendor='{self.vendor}')>"


class MonitoringItem(Base):
    """
    Individual monitoring items (metrics to collect)
    """

    __tablename__ = "monitoring_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("monitoring_templates.id", ondelete="SET NULL"))

    name = Column(String(200), nullable=False)
    oid = Column(String(200), nullable=False)
    interval_seconds = Column(Integer, default=60, nullable=False)
    value_type = Column(String(20), nullable=False)  # integer, counter32, counter64, string, gauge
    units = Column(String(20))
    is_table = Column(Boolean, default=False)  # Is this a table OID (walk required)
    enabled = Column(Boolean, default=True, nullable=False)

    # Custom parameters
    params = Column(JSON)  # Additional parameters (thresholds, calculations, etc.)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    device = relationship("Device", backref="monitoring_items")
    template = relationship("MonitoringTemplate", backref="monitoring_items")

    def __repr__(self):
        return f"<MonitoringItem(name='{self.name}', oid='{self.oid}', device_id='{self.device_id}')>"


class AlertRule(Base):
    """
    Alert rules with trigger expressions
    """

    __tablename__ = "alert_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    expression = Column(Text, nullable=False)  # Alert trigger expression
    severity = Column(SQLEnum(AlertSeverity), nullable=False, default=AlertSeverity.MEDIUM)
    enabled = Column(Boolean, default=True, nullable=False)

    # Notification settings
    notification_channels = Column(JSON)  # ["email", "webhook", "sms"]
    notification_recipients = Column(JSON)  # Email addresses, webhook URLs, etc.

    # Conditions
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"))  # Optional: specific device
    device_group = Column(String(100))  # Optional: device group filter
    monitoring_item_id = Column(UUID(as_uuid=True), ForeignKey("monitoring_items.id", ondelete="CASCADE"))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    device = relationship("Device", backref="alert_rules")
    monitoring_item = relationship("MonitoringItem", backref="alert_rules")

    def __repr__(self):
        return f"<AlertRule(name='{self.name}', severity='{self.severity.value}', enabled={self.enabled})>"


class AlertHistory(Base):
    """
    Alert history and acknowledgments
    """

    __tablename__ = "alert_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)

    severity = Column(SQLEnum(AlertSeverity), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSON)  # Additional alert details

    # Status
    triggered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    rule = relationship("AlertRule", backref="alert_history")
    device = relationship("Device", backref="alert_history")

    def __repr__(self):
        return f"<AlertHistory(rule_id='{self.rule_id}', severity='{self.severity.value}', triggered={self.triggered_at})>"


class DiscoveryRule(Base):
    """
    Network discovery rules
    """

    __tablename__ = "discovery_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    network_range = Column(String(100), nullable=False)  # CIDR notation: "192.168.1.0/24"
    enabled = Column(Boolean, default=True, nullable=False)

    # Schedule (cron expression)
    schedule = Column(String(100))  # e.g., "0 2 * * *" for daily at 2 AM

    # Discovery settings
    snmp_discovery = Column(Boolean, default=True)
    snmp_communities = Column(JSON)  # List of community strings to try
    ping_only = Column(Boolean, default=False)  # Just ping or full SNMP discovery

    # Last run
    last_run = Column(DateTime)
    last_devices_found = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<DiscoveryRule(name='{self.name}', network='{self.network_range}', enabled={self.enabled})>"


class DiscoveryResult(Base):
    """
    Discovery scan results
    """

    __tablename__ = "discovery_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("discovery_rules.id", ondelete="CASCADE"), nullable=False)

    ip_address = Column(String(45), nullable=False)  # Supports IPv4 and IPv6
    hostname = Column(String(255))
    mac_address = Column(String(17))

    # Detection results
    snmp_reachable = Column(Boolean, default=False)
    snmp_version = Column(String(10))  # v1, v2c, v3
    vendor = Column(String(100))
    device_type = Column(String(50))  # router, switch, firewall, server, etc.
    sys_descr = Column(Text)
    sys_object_id = Column(String(200))

    # Status
    discovered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    added_to_monitoring = Column(Boolean, default=False)
    added_at = Column(DateTime)

    # Relationships
    rule = relationship("DiscoveryRule", backref="discovery_results")

    def __repr__(self):
        return f"<DiscoveryResult(ip='{self.ip_address}', vendor='{self.vendor}', type='{self.device_type}')>"


class MetricBaseline(Base):
    """
    Performance baselines for anomaly detection
    """

    __tablename__ = "metric_baselines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    monitoring_item_id = Column(UUID(as_uuid=True), ForeignKey("monitoring_items.id", ondelete="CASCADE"))

    metric_name = Column(String(200), nullable=False)

    # Baseline statistics
    min_value = Column(String(50))
    max_value = Column(String(50))
    avg_value = Column(String(50))
    std_deviation = Column(String(50))

    # Calculation period
    sample_count = Column(Integer, nullable=False)
    calculated_from = Column(DateTime, nullable=False)
    calculated_to = Column(DateTime, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    device = relationship("Device", backref="metric_baselines")
    monitoring_item = relationship("MonitoringItem", backref="metric_baselines")

    def __repr__(self):
        return f"<MetricBaseline(device_id='{self.device_id}', metric='{self.metric_name}')>"
