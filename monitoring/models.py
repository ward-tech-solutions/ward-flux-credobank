"""
WARD FLUX - Monitoring Models
Database models for standalone monitoring system
"""

import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, JSON, UUID as SQLAlchemyUUID, Enum as SQLAlchemyEnum, func, Float, BigInteger, ARRAY
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

    # Flapping detection fields
    is_flapping = Column(Boolean, default=False, nullable=False)  # Currently flapping?
    flap_count = Column(Integer, default=0)  # Number of status changes in monitoring window
    last_flap_detected = Column(DateTime)  # Last time flapping was detected
    flapping_since = Column(DateTime)  # When flapping started
    status_change_times = Column(ARRAY(DateTime))  # Array of recent status change timestamps

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


# ============================================
# Interface Discovery Models
# ============================================

class DeviceInterface(Base):
    """Network interface discovered via SNMP (IF-MIB)"""
    __tablename__ = "device_interfaces"

    # Primary key
    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key to devices
    device_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("standalone_devices.id", ondelete="CASCADE"), nullable=False, index=True)

    # SNMP interface data (from IF-MIB)
    if_index = Column(Integer, nullable=False)  # ifIndex: Unique interface number
    if_name = Column(String(255))  # ifName: Gi0/0/0, Fa0/1, etc. (from ifXTable)
    if_descr = Column(String(255))  # ifDescr: Interface description (legacy)
    if_alias = Column(String(500))  # ifAlias: User-configured description (CRITICAL - contains ISP info!)
    if_type = Column(String(100))  # ifType: ethernet, tunnel, loopback, etc.

    # Parsed/classified data (from interface_parser.py)
    interface_type = Column(String(50))  # isp, trunk, access, server_link, branch_link, other
    isp_provider = Column(String(50))  # magti, silknet, veon, beeline, geocell, other
    is_critical = Column(Boolean, default=False)  # Critical interfaces (ISP uplinks)
    parser_confidence = Column(Float)  # Parser confidence score (0.0 - 1.0)

    # Interface status (from SNMP)
    admin_status = Column(Integer)  # ifAdminStatus: 1=up, 2=down, 3=testing
    oper_status = Column(Integer)  # ifOperStatus: 1=up, 2=down, 3=testing, 4=unknown, 5=dormant, 6=notPresent, 7=lowerLayerDown
    speed = Column(BigInteger)  # ifSpeed: Interface speed in bits/second
    mtu = Column(Integer)  # ifMtu: Maximum transmission unit
    duplex = Column(String(20))  # full, half, auto (if available from proprietary MIBs)

    # MAC address and physical info
    phys_address = Column(String(17))  # ifPhysAddress: MAC address (00:11:22:33:44:55)

    # Topology and relationships
    connected_to_device_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("standalone_devices.id", ondelete="SET NULL"))
    connected_to_interface_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("device_interfaces.id", ondelete="SET NULL"))
    lldp_neighbor_name = Column(String(255))  # LLDP neighbor device name
    lldp_neighbor_port = Column(String(255))  # LLDP neighbor port

    # Discovery metadata
    discovered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_status_change = Column(DateTime)  # When oper_status last changed

    # Configuration
    enabled = Column(Boolean, default=True)  # Whether to monitor this interface
    monitoring_enabled = Column(Boolean, default=True)  # Whether to collect metrics for this interface

    # Tags and custom fields
    tags = Column(JSON)  # ["critical", "isp", "primary-uplink"]
    custom_fields = Column(JSON)  # Flexible key-value storage

    # Notes
    notes = Column(Text)  # User notes about this interface

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class InterfaceMetricsSummary(Base):
    """Cached interface metrics summary (from VictoriaMetrics)"""
    __tablename__ = "interface_metrics_summary"

    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interface_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("device_interfaces.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Traffic metrics (last 24 hours)
    avg_in_mbps = Column(Float)  # Average inbound traffic (Mbps)
    avg_out_mbps = Column(Float)  # Average outbound traffic (Mbps)
    max_in_mbps = Column(Float)  # Peak inbound traffic (Mbps)
    max_out_mbps = Column(Float)  # Peak outbound traffic (Mbps)
    total_in_gb = Column(Float)  # Total inbound traffic (GB)
    total_out_gb = Column(Float)  # Total outbound traffic (GB)

    # Error metrics (last 24 hours)
    in_errors = Column(Integer)  # Input errors
    out_errors = Column(Integer)  # Output errors
    in_discards = Column(Integer)  # Input discards
    out_discards = Column(Integer)  # Output discards

    # Utilization
    utilization_percent = Column(Float)  # Interface utilization (%)

    # Timestamps
    calculated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class InterfaceBaseline(Base):
    """Learned traffic baselines for anomaly detection"""
    __tablename__ = "interface_baselines"

    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interface_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("device_interfaces.id", ondelete="CASCADE"), nullable=False, index=True)

    # Time context
    hour_of_day = Column(Integer, nullable=False)  # 0-23
    day_of_week = Column(Integer, nullable=False)  # 0-6 (Monday=0)

    # Traffic baselines (inbound)
    avg_in_mbps = Column(Float)
    std_dev_in_mbps = Column(Float)
    min_in_mbps = Column(Float)
    max_in_mbps = Column(Float)

    # Traffic baselines (outbound)
    avg_out_mbps = Column(Float)
    std_dev_out_mbps = Column(Float)
    min_out_mbps = Column(Float)
    max_out_mbps = Column(Float)

    # Error rate baselines
    avg_error_rate = Column(Float)
    std_dev_error_rate = Column(Float)

    # Metadata
    sample_count = Column(Integer)  # Number of samples used for baseline
    confidence = Column(Float)  # 0.0-1.0 (more samples = higher confidence)
    last_updated = Column(DateTime)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
