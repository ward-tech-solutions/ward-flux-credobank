"""
WARD FLUX - Universal OID Library

Comprehensive SNMP OID definitions for multi-vendor support.
Supports: Cisco, Fortinet, Juniper, HP/Aruba, Huawei, MikroTik, Ubiquiti,
          Palo Alto, Linux, Windows, and generic SNMP devices.

Architecture:
- Tier 1: Universal MIB-II OIDs (work on ALL SNMP devices)
- Tier 2: Vendor-specific OIDs (loaded based on auto-detection)
- Tier 3: Dynamic discovery for unknown devices
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OIDDefinition:
    """OID definition with metadata"""

    oid: str
    name: str
    description: str
    value_type: str  # integer, counter32, counter64, string, gauge
    units: str = ""
    is_table: bool = False


# ═══════════════════════════════════════════════════════════════════
# TIER 1: UNIVERSAL OIDs (MIB-II - RFC 1213)
# Work on ANY SNMP-capable device
# ═══════════════════════════════════════════════════════════════════

UNIVERSAL_OIDS: Dict[str, OIDDefinition] = {
    # System Information
    "sysDescr": OIDDefinition(
        oid="1.3.6.1.2.1.1.1.0",
        name="System Description",
        description="Device description and OS version",
        value_type="string",
    ),
    "sysObjectID": OIDDefinition(
        oid="1.3.6.1.2.1.1.2.0",
        name="System Object ID",
        description="Vendor identification OID",
        value_type="string",
    ),
    "sysUpTime": OIDDefinition(
        oid="1.3.6.1.2.1.1.3.0",
        name="System Uptime",
        description="Time since last reboot",
        value_type="integer",
        units="timeticks",
    ),
    "sysContact": OIDDefinition(
        oid="1.3.6.1.2.1.1.4.0", name="System Contact", description="Contact information", value_type="string"
    ),
    "sysName": OIDDefinition(
        oid="1.3.6.1.2.1.1.5.0", name="System Name", description="Hostname", value_type="string"
    ),
    "sysLocation": OIDDefinition(
        oid="1.3.6.1.2.1.1.6.0", name="System Location", description="Physical location", value_type="string"
    ),
    # Network Interfaces (ifTable)
    "ifNumber": OIDDefinition(
        oid="1.3.6.1.2.1.2.1.0",
        name="Interface Count",
        description="Number of network interfaces",
        value_type="integer",
    ),
    "ifDescr": OIDDefinition(
        oid="1.3.6.1.2.1.2.2.1.2",
        name="Interface Description",
        description="Interface name/description",
        value_type="string",
        is_table=True,
    ),
    "ifType": OIDDefinition(
        oid="1.3.6.1.2.1.2.2.1.3",
        name="Interface Type",
        description="Interface type (6=Ethernet)",
        value_type="integer",
        is_table=True,
    ),
    "ifMtu": OIDDefinition(
        oid="1.3.6.1.2.1.2.2.1.4",
        name="Interface MTU",
        description="Maximum transmission unit",
        value_type="integer",
        units="bytes",
        is_table=True,
    ),
    "ifSpeed": OIDDefinition(
        oid="1.3.6.1.2.1.2.2.1.5",
        name="Interface Speed",
        description="Interface bandwidth",
        value_type="gauge",
        units="bps",
        is_table=True,
    ),
    "ifPhysAddress": OIDDefinition(
        oid="1.3.6.1.2.1.2.2.1.6",
        name="Interface MAC Address",
        description="Physical MAC address",
        value_type="string",
        is_table=True,
    ),
    "ifAdminStatus": OIDDefinition(
        oid="1.3.6.1.2.1.2.2.1.7",
        name="Interface Admin Status",
        description="Admin status (1=up, 2=down, 3=testing)",
        value_type="integer",
        is_table=True,
    ),
    "ifOperStatus": OIDDefinition(
        oid="1.3.6.1.2.1.2.2.1.8",
        name="Interface Operational Status",
        description="Operational status (1=up, 2=down, 3=testing)",
        value_type="integer",
        is_table=True,
    ),
    "ifInOctets": OIDDefinition(
        oid="1.3.6.1.2.1.2.2.1.10",
        name="Interface Input Bytes",
        description="Total bytes received",
        value_type="counter32",
        units="bytes",
        is_table=True,
    ),
    "ifInUcastPkts": OIDDefinition(
        oid="1.3.6.1.2.1.2.2.1.11",
        name="Interface Input Unicast Packets",
        description="Unicast packets received",
        value_type="counter32",
        is_table=True,
    ),
    "ifInErrors": OIDDefinition(
        oid="1.3.6.1.2.1.2.2.1.14",
        name="Interface Input Errors",
        description="Input error count",
        value_type="counter32",
        is_table=True,
    ),
    "ifOutOctets": OIDDefinition(
        oid="1.3.6.1.2.1.2.2.1.16",
        name="Interface Output Bytes",
        description="Total bytes transmitted",
        value_type="counter32",
        units="bytes",
        is_table=True,
    ),
    "ifOutUcastPkts": OIDDefinition(
        oid="1.3.6.1.2.1.2.2.1.17",
        name="Interface Output Unicast Packets",
        description="Unicast packets transmitted",
        value_type="counter32",
        is_table=True,
    ),
    "ifOutErrors": OIDDefinition(
        oid="1.3.6.1.2.1.2.2.1.20",
        name="Interface Output Errors",
        description="Output error count",
        value_type="counter32",
        is_table=True,
    ),
    # IP Statistics
    "ipForwarding": OIDDefinition(
        oid="1.3.6.1.2.1.4.1.0",
        name="IP Forwarding",
        description="IP forwarding enabled (1=yes, 2=no)",
        value_type="integer",
    ),
    "ipInReceives": OIDDefinition(
        oid="1.3.6.1.2.1.4.3.0",
        name="IP Packets Received",
        description="Total IP packets received",
        value_type="counter32",
    ),
    "ipOutRequests": OIDDefinition(
        oid="1.3.6.1.2.1.4.10.0",
        name="IP Packets Sent",
        description="Total IP packets transmitted",
        value_type="counter32",
    ),
    # ICMP Statistics
    "icmpInMsgs": OIDDefinition(
        oid="1.3.6.1.2.1.5.1.0",
        name="ICMP Messages Received",
        description="Total ICMP messages received",
        value_type="counter32",
    ),
    "icmpOutMsgs": OIDDefinition(
        oid="1.3.6.1.2.1.5.14.0",
        name="ICMP Messages Sent",
        description="Total ICMP messages sent",
        value_type="counter32",
    ),
    # TCP Statistics
    "tcpCurrEstab": OIDDefinition(
        oid="1.3.6.1.2.1.6.9.0",
        name="TCP Established Connections",
        description="Current TCP connections",
        value_type="gauge",
    ),
    "tcpInSegs": OIDDefinition(
        oid="1.3.6.1.2.1.6.10.0",
        name="TCP Segments Received",
        description="Total TCP segments received",
        value_type="counter32",
    ),
    "tcpOutSegs": OIDDefinition(
        oid="1.3.6.1.2.1.6.11.0",
        name="TCP Segments Sent",
        description="Total TCP segments sent",
        value_type="counter32",
    ),
}


# ═══════════════════════════════════════════════════════════════════
# VENDOR DETECTION MAP
# Maps sysObjectID prefix to vendor name
# ═══════════════════════════════════════════════════════════════════

VENDOR_DETECTION: Dict[str, str] = {
    "1.3.6.1.4.1.9": "Cisco",
    "1.3.6.1.4.1.12356": "Fortinet",
    "1.3.6.1.4.1.2636": "Juniper",
    "1.3.6.1.4.1.11": "HP",
    "1.3.6.1.4.1.14823": "Aruba",
    "1.3.6.1.4.1.2011": "Huawei",
    "1.3.6.1.4.1.14988": "MikroTik",
    "1.3.6.1.4.1.41112": "Ubiquiti",
    "1.3.6.1.4.1.25461": "Palo Alto",
    "1.3.6.1.4.1.674": "Dell",
    "1.3.6.1.4.1.30065": "Arista",
    "1.3.6.1.4.1.1916": "Extreme Networks",
    "1.3.6.1.4.1.2272": "Checkpoint",
    "1.3.6.1.4.1.8072": "Linux/Net-SNMP",
    "1.3.6.1.4.1.311": "Microsoft Windows",
    "1.3.6.1.4.1.318": "APC",
    "1.3.6.1.4.1.534": "Eaton",
    "1.3.6.1.4.1.6876": "VMware",
}


# ═══════════════════════════════════════════════════════════════════
# TIER 2: VENDOR-SPECIFIC OIDs
# ═══════════════════════════════════════════════════════════════════

# Cisco IOS/IOS-XE/NX-OS
CISCO_OIDS: Dict[str, OIDDefinition] = {
    "cpmCPUTotal5sec": OIDDefinition(
        oid="1.3.6.1.4.1.9.9.109.1.1.1.1.3",
        name="CPU Usage 5 sec",
        description="CPU utilization last 5 seconds",
        value_type="gauge",
        units="%",
    ),
    "cpmCPUTotal1min": OIDDefinition(
        oid="1.3.6.1.4.1.9.9.109.1.1.1.1.4",
        name="CPU Usage 1 min",
        description="CPU utilization last 1 minute",
        value_type="gauge",
        units="%",
    ),
    "cpmCPUTotal5min": OIDDefinition(
        oid="1.3.6.1.4.1.9.9.109.1.1.1.1.5",
        name="CPU Usage 5 min",
        description="CPU utilization last 5 minutes",
        value_type="gauge",
        units="%",
    ),
    "ciscoMemoryPoolUsed": OIDDefinition(
        oid="1.3.6.1.4.1.9.9.48.1.1.1.5",
        name="Memory Used",
        description="Memory currently in use",
        value_type="gauge",
        units="bytes",
    ),
    "ciscoMemoryPoolFree": OIDDefinition(
        oid="1.3.6.1.4.1.9.9.48.1.1.1.6",
        name="Memory Free",
        description="Free memory available",
        value_type="gauge",
        units="bytes",
    ),
    "ciscoEnvMonTemperature": OIDDefinition(
        oid="1.3.6.1.4.1.9.9.13.1.3.1.3",
        name="Temperature",
        description="Device temperature",
        value_type="gauge",
        units="°C",
        is_table=True,
    ),
    "cfwConnectionStatValue": OIDDefinition(
        oid="1.3.6.1.4.1.9.9.147.1.2.2.2.1.5",
        name="Firewall Connections",
        description="Active firewall connections (ASA)",
        value_type="gauge",
    ),
}

# Fortinet FortiGate
FORTINET_OIDS: Dict[str, OIDDefinition] = {
    "fgSysVersion": OIDDefinition(
        oid="1.3.6.1.4.1.12356.101.4.1.1.0",
        name="Firmware Version",
        description="FortiOS version",
        value_type="string",
    ),
    "fgSysCpuUsage": OIDDefinition(
        oid="1.3.6.1.4.1.12356.101.4.1.3.0",
        name="CPU Usage",
        description="Current CPU utilization",
        value_type="gauge",
        units="%",
    ),
    "fgSysMemUsage": OIDDefinition(
        oid="1.3.6.1.4.1.12356.101.4.1.4.0",
        name="Memory Usage",
        description="Current memory utilization",
        value_type="gauge",
        units="%",
    ),
    "fgSysDiskUsage": OIDDefinition(
        oid="1.3.6.1.4.1.12356.101.4.1.6.0",
        name="Disk Usage",
        description="Current disk utilization",
        value_type="gauge",
        units="%",
    ),
    "fgSysSesCount": OIDDefinition(
        oid="1.3.6.1.4.1.12356.101.4.1.8.0",
        name="Active Sessions",
        description="Current active sessions",
        value_type="gauge",
    ),
    "fgVpnTunEntStatus": OIDDefinition(
        oid="1.3.6.1.4.1.12356.101.12.2.2.1.20",
        name="VPN Tunnel Status",
        description="VPN tunnel status (1=down, 2=up)",
        value_type="integer",
        is_table=True,
    ),
    "fgHaSystemMode": OIDDefinition(
        oid="1.3.6.1.4.1.12356.101.13.1.1.0",
        name="HA Mode",
        description="High Availability mode",
        value_type="integer",
    ),
}

# Juniper JunOS
JUNIPER_OIDS: Dict[str, OIDDefinition] = {
    "jnxOperatingDescr": OIDDefinition(
        oid="1.3.6.1.4.1.2636.3.1.2.0", name="Operating Description", description="Device description", value_type="string"
    ),
    "jnxOperatingCPU": OIDDefinition(
        oid="1.3.6.1.4.1.2636.3.1.13.1.8",
        name="CPU Usage",
        description="CPU utilization",
        value_type="gauge",
        units="%",
        is_table=True,
    ),
    "jnxOperatingBuffer": OIDDefinition(
        oid="1.3.6.1.4.1.2636.3.1.13.1.11",
        name="Memory Usage",
        description="Memory buffer utilization",
        value_type="gauge",
        units="%",
        is_table=True,
    ),
    "jnxOperatingTemp": OIDDefinition(
        oid="1.3.6.1.4.1.2636.3.1.13.1.7",
        name="Temperature",
        description="Operating temperature",
        value_type="gauge",
        units="°C",
        is_table=True,
    ),
}

# HP/Aruba Switches
HP_OIDS: Dict[str, OIDDefinition] = {
    "hpSwitchCpuStat": OIDDefinition(
        oid="1.3.6.1.4.1.11.2.14.11.5.1.9.6.1.0",
        name="CPU Usage",
        description="CPU utilization",
        value_type="gauge",
        units="%",
    ),
    "hpLocalMemTotalBytes": OIDDefinition(
        oid="1.3.6.1.4.1.11.2.14.11.5.1.1.2.1.1.1.5",
        name="Total Memory",
        description="Total memory bytes",
        value_type="gauge",
        units="bytes",
    ),
    "hpLocalMemFreeBytes": OIDDefinition(
        oid="1.3.6.1.4.1.11.2.14.11.5.1.1.2.1.1.1.6",
        name="Free Memory",
        description="Free memory bytes",
        value_type="gauge",
        units="bytes",
    ),
}

# MikroTik RouterOS
MIKROTIK_OIDS: Dict[str, OIDDefinition] = {
    "mtxrCPULoad": OIDDefinition(
        oid="1.3.6.1.4.1.14988.1.1.3.11.0", name="CPU Load", description="CPU load percentage", value_type="gauge", units="%"
    ),
    "mtxrMemory": OIDDefinition(
        oid="1.3.6.1.4.1.14988.1.1.3.2.0",
        name="Total Memory",
        description="Total system memory",
        value_type="gauge",
        units="bytes",
    ),
    "mtxrMemoryUsed": OIDDefinition(
        oid="1.3.6.1.4.1.14988.1.1.3.3.0",
        name="Used Memory",
        description="Memory currently in use",
        value_type="gauge",
        units="bytes",
    ),
    "mtxrHlTemperature": OIDDefinition(
        oid="1.3.6.1.4.1.14988.1.1.3.10.0",
        name="Temperature",
        description="System temperature",
        value_type="gauge",
        units="°C",
    ),
}

# Linux (Net-SNMP / UCD-SNMP)
LINUX_OIDS: Dict[str, OIDDefinition] = {
    "hrSystemUptime": OIDDefinition(
        oid="1.3.6.1.2.1.25.1.1.0",
        name="System Uptime",
        description="Time since last boot",
        value_type="integer",
        units="timeticks",
    ),
    "hrSystemNumUsers": OIDDefinition(
        oid="1.3.6.1.2.1.25.1.5.0",
        name="Logged Users",
        description="Number of users logged in",
        value_type="gauge",
    ),
    "hrSystemProcesses": OIDDefinition(
        oid="1.3.6.1.2.1.25.1.6.0",
        name="Running Processes",
        description="Number of running processes",
        value_type="gauge",
    ),
    "ssCpuRawUser": OIDDefinition(
        oid="1.3.6.1.4.1.2021.11.50.0",
        name="CPU User Time",
        description="CPU time in user mode",
        value_type="counter32",
    ),
    "ssCpuRawSystem": OIDDefinition(
        oid="1.3.6.1.4.1.2021.11.52.0",
        name="CPU System Time",
        description="CPU time in system mode",
        value_type="counter32",
    ),
    "ssCpuRawIdle": OIDDefinition(
        oid="1.3.6.1.4.1.2021.11.53.0",
        name="CPU Idle Time",
        description="CPU idle time",
        value_type="counter32",
    ),
    "laLoad1": OIDDefinition(
        oid="1.3.6.1.4.1.2021.10.1.3.1",
        name="Load Average 1min",
        description="1-minute load average",
        value_type="string",
    ),
    "laLoad5": OIDDefinition(
        oid="1.3.6.1.4.1.2021.10.1.3.2",
        name="Load Average 5min",
        description="5-minute load average",
        value_type="string",
    ),
    "memTotalReal": OIDDefinition(
        oid="1.3.6.1.4.1.2021.4.5.0", name="Total RAM", description="Total RAM", value_type="gauge", units="KB"
    ),
    "memAvailReal": OIDDefinition(
        oid="1.3.6.1.4.1.2021.4.6.0",
        name="Available RAM",
        description="Available RAM",
        value_type="gauge",
        units="KB",
    ),
    "memBuffer": OIDDefinition(
        oid="1.3.6.1.4.1.2021.4.14.0",
        name="Buffered Memory",
        description="Buffered memory",
        value_type="gauge",
        units="KB",
    ),
    "memCached": OIDDefinition(
        oid="1.3.6.1.4.1.2021.4.15.0",
        name="Cached Memory",
        description="Cached memory",
        value_type="gauge",
        units="KB",
    ),
    "dskPath": OIDDefinition(
        oid="1.3.6.1.4.1.2021.9.1.2",
        name="Disk Mount Path",
        description="Filesystem mount point",
        value_type="string",
        is_table=True,
    ),
    "dskTotal": OIDDefinition(
        oid="1.3.6.1.4.1.2021.9.1.6",
        name="Disk Total",
        description="Total disk space",
        value_type="gauge",
        units="KB",
        is_table=True,
    ),
    "dskAvail": OIDDefinition(
        oid="1.3.6.1.4.1.2021.9.1.7",
        name="Disk Available",
        description="Available disk space",
        value_type="gauge",
        units="KB",
        is_table=True,
    ),
    "dskPercent": OIDDefinition(
        oid="1.3.6.1.4.1.2021.9.1.9",
        name="Disk Usage",
        description="Disk usage percentage",
        value_type="gauge",
        units="%",
        is_table=True,
    ),
}

# Windows Server
WINDOWS_OIDS: Dict[str, OIDDefinition] = {
    "hrSystemUptime": OIDDefinition(
        oid="1.3.6.1.2.1.25.1.1.0",
        name="System Uptime",
        description="Time since last boot",
        value_type="integer",
        units="timeticks",
    ),
    "hrSystemNumUsers": OIDDefinition(
        oid="1.3.6.1.2.1.25.1.5.0",
        name="Logged Users",
        description="Number of users logged in",
        value_type="gauge",
    ),
    "hrSystemProcesses": OIDDefinition(
        oid="1.3.6.1.2.1.25.1.6.0",
        name="Running Processes",
        description="Number of running processes",
        value_type="gauge",
    ),
    "hrStorageDescr": OIDDefinition(
        oid="1.3.6.1.2.1.25.2.3.1.3",
        name="Storage Description",
        description="Storage device description",
        value_type="string",
        is_table=True,
    ),
    "hrStorageSize": OIDDefinition(
        oid="1.3.6.1.2.1.25.2.3.1.5",
        name="Storage Size",
        description="Total storage size",
        value_type="gauge",
        is_table=True,
    ),
    "hrStorageUsed": OIDDefinition(
        oid="1.3.6.1.2.1.25.2.3.1.6",
        name="Storage Used",
        description="Used storage space",
        value_type="gauge",
        is_table=True,
    ),
}


# ═══════════════════════════════════════════════════════════════════
# OID LIBRARY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════


def detect_vendor_from_oid(sys_object_id: str) -> Optional[str]:
    """
    Detect vendor from sysObjectID

    Args:
        sys_object_id: The sysObjectID value from device

    Returns:
        Vendor name or None if unknown
    """
    for oid_prefix, vendor_name in VENDOR_DETECTION.items():
        if sys_object_id.startswith(oid_prefix):
            logger.info(f"Detected vendor: {vendor_name} (OID: {sys_object_id})")
            return vendor_name

    logger.warning(f"Unknown vendor for sysObjectID: {sys_object_id}")
    return None


def get_vendor_oids(vendor: str) -> Dict[str, OIDDefinition]:
    """
    Get vendor-specific OIDs plus universal OIDs

    Args:
        vendor: Vendor name

    Returns:
        Dictionary of OID definitions
    """
    vendor_map = {
        "Cisco": CISCO_OIDS,
        "Fortinet": FORTINET_OIDS,
        "Juniper": JUNIPER_OIDS,
        "HP": HP_OIDS,
        "Aruba": HP_OIDS,
        "MikroTik": MIKROTIK_OIDS,
        "Linux/Net-SNMP": LINUX_OIDS,
        "Microsoft Windows": WINDOWS_OIDS,
    }

    # Always start with universal OIDs
    oids = UNIVERSAL_OIDS.copy()

    # Add vendor-specific OIDs if available
    if vendor in vendor_map:
        oids.update(vendor_map[vendor])
        logger.info(f"Loaded {len(vendor_map[vendor])} vendor-specific OIDs for {vendor}")

    logger.info(f"Total OIDs available: {len(oids)} (Universal + Vendor-Specific)")
    return oids


def get_oid_by_name(oid_name: str, vendor: Optional[str] = None) -> Optional[OIDDefinition]:
    """
    Get OID definition by name

    Args:
        oid_name: OID name (e.g., "sysDescr", "cpmCPUTotal5sec")
        vendor: Optional vendor name to include vendor-specific OIDs

    Returns:
        OID definition or None if not found
    """
    if vendor:
        oids = get_vendor_oids(vendor)
    else:
        oids = UNIVERSAL_OIDS

    return oids.get(oid_name)


def classify_device_type(sys_descr: str) -> str:
    """
    Classify device type based on sysDescr

    Args:
        sys_descr: System description string

    Returns:
        Device type classification
    """
    sys_descr_lower = sys_descr.lower()

    # Router detection
    if any(keyword in sys_descr_lower for keyword in ["router", "cisco ios"]):
        return "router"

    # Switch detection
    if any(keyword in sys_descr_lower for keyword in ["switch", "catalyst", "procurve"]):
        return "switch"

    # Firewall detection
    if any(keyword in sys_descr_lower for keyword in ["firewall", "fortigate", "asa", "srx", "checkpoint", "palo alto"]):
        return "firewall"

    # Server detection - Linux
    if any(keyword in sys_descr_lower for keyword in ["linux", "ubuntu", "centos", "debian", "redhat", "fedora"]):
        return "server-linux"

    # Server detection - Windows
    if "windows" in sys_descr_lower:
        return "server-windows"

    # Network appliances
    if any(keyword in sys_descr_lower for keyword in ["wireless", "wlan", "access point", "ap"]):
        return "wireless-ap"

    # UPS
    if any(keyword in sys_descr_lower for keyword in ["ups", "apc", "eaton"]):
        return "ups"

    # Printer
    if "printer" in sys_descr_lower:
        return "printer"

    # Generic fallback
    return "generic"


def get_all_universal_oid_strings() -> List[str]:
    """
    Get list of all universal OID strings (for bulk queries)

    Returns:
        List of OID strings
    """
    return [oid_def.oid for oid_def in UNIVERSAL_OIDS.values()]


def get_critical_oids() -> List[str]:
    """
    Get list of critical OIDs that should always be monitored

    Returns:
        List of critical OID strings
    """
    critical_oid_names = [
        "sysDescr",
        "sysObjectID",
        "sysUpTime",
        "sysName",
        "ifOperStatus",
        "ifInOctets",
        "ifOutOctets",
    ]

    return [UNIVERSAL_OIDS[name].oid for name in critical_oid_names if name in UNIVERSAL_OIDS]
