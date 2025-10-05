# WARD FLUX - Universal Vendor Support Strategy

## 🎯 Goal: Support ALL Network Equipment

Instead of Cisco-specific monitoring, we'll build a **universal monitoring engine** that automatically detects and monitors any SNMP-capable device.

---

## 🌐 Supported Vendors & Equipment

### Network Equipment
- **Cisco** - Routers, Switches, ASA Firewalls, Wireless Controllers
- **Fortinet** - FortiGate Firewalls, FortiSwitch, FortiAP
- **Juniper** - Routers, Switches, SRX Firewalls
- **HP/Aruba** - Switches, Wireless Controllers
- **Huawei** - Routers, Switches
- **MikroTik** - Routers, Switches
- **Ubiquiti** - UniFi, EdgeRouter
- **Palo Alto** - Firewalls
- **Dell/Force10** - Switches
- **Arista** - Data Center Switches
- **Extreme Networks** - Switches
- **Checkpoint** - Firewalls

### Servers
- **Linux** - Any distribution with Net-SNMP
- **Windows** - Windows Server 2012+
- **FreeBSD/Unix** - With Net-SNMP
- **VMware ESXi** - Hypervisors

### Other Equipment
- **UPS** - APC, Eaton, CyberPower
- **Printers** - HP, Canon, Xerox, Ricoh
- **Environmental Sensors** - Temperature, Humidity
- **Power Distribution Units (PDU)**
- **IP Cameras** - Axis, Hikvision, Dahua
- **Storage** - NAS, SAN devices

---

## 📊 Universal OID Strategy

### Standard MIB-II OIDs (Work on ALL devices)

These are **universal** and work on any SNMP-capable device:

```python
UNIVERSAL_OIDS = {
    # System Information (RFC 1213 - MIB-II)
    "sysDescr": "1.3.6.1.2.1.1.1.0",          # Device description
    "sysObjectID": "1.3.6.1.2.1.1.2.0",       # Vendor identifier
    "sysUpTime": "1.3.6.1.2.1.1.3.0",         # Uptime in timeticks
    "sysContact": "1.3.6.1.2.1.1.4.0",        # Contact info
    "sysName": "1.3.6.1.2.1.1.5.0",           # Hostname
    "sysLocation": "1.3.6.1.2.1.1.6.0",       # Location

    # Network Interfaces (RFC 1213 - MIB-II)
    "ifNumber": "1.3.6.1.2.1.2.1.0",          # Number of interfaces
    "ifDescr": "1.3.6.1.2.1.2.2.1.2",         # Interface description
    "ifType": "1.3.6.1.2.1.2.2.1.3",          # Interface type
    "ifMtu": "1.3.6.1.2.1.2.2.1.4",           # MTU
    "ifSpeed": "1.3.6.1.2.1.2.2.1.5",         # Speed in bps
    "ifPhysAddress": "1.3.6.1.2.1.2.2.1.6",   # MAC address
    "ifAdminStatus": "1.3.6.1.2.1.2.2.1.7",   # Admin status (1=up)
    "ifOperStatus": "1.3.6.1.2.1.2.2.1.8",    # Operational status
    "ifInOctets": "1.3.6.1.2.1.2.2.1.10",     # Bytes received
    "ifOutOctets": "1.3.6.1.2.1.2.2.1.16",    # Bytes transmitted
    "ifInErrors": "1.3.6.1.2.1.2.2.1.14",     # Input errors
    "ifOutErrors": "1.3.6.1.2.1.2.2.1.20",    # Output errors

    # IP Information
    "ipForwarding": "1.3.6.1.2.1.4.1.0",      # IP forwarding enabled
    "ipInReceives": "1.3.6.1.2.1.4.3.0",      # IP packets received
    "ipOutRequests": "1.3.6.1.2.1.4.10.0",    # IP packets sent

    # ICMP Statistics
    "icmpInMsgs": "1.3.6.1.2.1.5.1.0",        # ICMP messages received
    "icmpOutMsgs": "1.3.6.1.2.1.5.14.0",      # ICMP messages sent

    # TCP Connections
    "tcpCurrEstab": "1.3.6.1.2.1.6.9.0",      # Current TCP connections
    "tcpInSegs": "1.3.6.1.2.1.6.10.0",        # TCP segments received
    "tcpOutSegs": "1.3.6.1.2.1.6.11.0",       # TCP segments sent
}
```

### Vendor Detection via sysObjectID

```python
VENDOR_DETECTION = {
    # Cisco
    "1.3.6.1.4.1.9": "Cisco",

    # Fortinet
    "1.3.6.1.4.1.12356": "Fortinet",

    # Juniper
    "1.3.6.1.4.1.2636": "Juniper",

    # HP/Aruba
    "1.3.6.1.4.1.11": "HP",
    "1.3.6.1.4.1.14823": "Aruba",

    # Huawei
    "1.3.6.1.4.1.2011": "Huawei",

    # MikroTik
    "1.3.6.1.4.1.14988": "MikroTik",

    # Ubiquiti
    "1.3.6.1.4.1.41112": "Ubiquiti",

    # Palo Alto
    "1.3.6.1.4.1.25461": "Palo Alto",

    # Dell
    "1.3.6.1.4.1.674": "Dell",

    # Arista
    "1.3.6.1.4.1.30065": "Arista",

    # Linux (Net-SNMP)
    "1.3.6.1.4.1.8072": "Linux/Net-SNMP",

    # Windows
    "1.3.6.1.4.1.311": "Microsoft Windows",

    # APC UPS
    "1.3.6.1.4.1.318": "APC",
}
```

### Vendor-Specific OIDs (Auto-loaded based on detection)

#### Cisco
```python
CISCO_OIDS = {
    # CPU
    "cpmCPUTotal5sec": "1.3.6.1.4.1.9.9.109.1.1.1.1.3",      # CPU 5sec avg
    "cpmCPUTotal1min": "1.3.6.1.4.1.9.9.109.1.1.1.1.4",      # CPU 1min avg
    "cpmCPUTotal5min": "1.3.6.1.4.1.9.9.109.1.1.1.1.5",      # CPU 5min avg

    # Memory
    "ciscoMemoryPoolUsed": "1.3.6.1.4.1.9.9.48.1.1.1.5",     # Memory used
    "ciscoMemoryPoolFree": "1.3.6.1.4.1.9.9.48.1.1.1.6",     # Memory free

    # Temperature
    "ciscoEnvMonTemperature": "1.3.6.1.4.1.9.9.13.1.3.1.3",  # Temperature

    # Firewall (ASA)
    "cfwConnectionStatValue": "1.3.6.1.4.1.9.9.147.1.2.2.2.1.5",  # Connections
}
```

#### Fortinet (FortiGate)
```python
FORTINET_OIDS = {
    # System
    "fgSysVersion": "1.3.6.1.4.1.12356.101.4.1.1.0",         # Firmware version
    "fgSysCpuUsage": "1.3.6.1.4.1.12356.101.4.1.3.0",        # CPU usage
    "fgSysMemUsage": "1.3.6.1.4.1.12356.101.4.1.4.0",        # Memory usage
    "fgSysDiskUsage": "1.3.6.1.4.1.12356.101.4.1.6.0",       # Disk usage

    # Firewall
    "fgFwPolPktCount": "1.3.6.1.4.1.12356.101.5.1.2.1.1.3",  # Policy packets
    "fgFwPolByteCount": "1.3.6.1.4.1.12356.101.5.1.2.1.1.4", # Policy bytes

    # VPN
    "fgVpnTunEntStatus": "1.3.6.1.4.1.12356.101.12.2.2.1.20", # VPN status

    # HA
    "fgHaSystemMode": "1.3.6.1.4.1.12356.101.13.1.1.0",      # HA mode
    "fgHaStatsHostname": "1.3.6.1.4.1.12356.101.13.2.1.1.2", # HA member
}
```

#### Juniper
```python
JUNIPER_OIDS = {
    # System
    "jnxOperatingDescr": "1.3.6.1.4.1.2636.3.1.2.0",         # Description
    "jnxOperatingCPU": "1.3.6.1.4.1.2636.3.1.13.1.8",        # CPU usage
    "jnxOperatingBuffer": "1.3.6.1.4.1.2636.3.1.13.1.11",    # Memory usage
    "jnxOperatingTemp": "1.3.6.1.4.1.2636.3.1.13.1.7",       # Temperature
}
```

#### HP/Aruba
```python
HP_OIDS = {
    # System
    "hpSwitchCpuStat": "1.3.6.1.4.1.11.2.14.11.5.1.9.6.1.0", # CPU usage
    "hpLocalMemTotalBytes": "1.3.6.1.4.1.11.2.14.11.5.1.1.2.1.1.1.5",
    "hpLocalMemFreeBytes": "1.3.6.1.4.1.11.2.14.11.5.1.1.2.1.1.1.6",
}
```

#### MikroTik
```python
MIKROTIK_OIDS = {
    # System
    "mtxrHealth": "1.3.6.1.4.1.14988.1.1.3",                 # Health metrics
    "mtxrCPULoad": "1.3.6.1.4.1.14988.1.1.3.11.0",           # CPU load
    "mtxrMemory": "1.3.6.1.4.1.14988.1.1.3.2.0",             # Total memory
    "mtxrMemoryUsed": "1.3.6.1.4.1.14988.1.1.3.3.0",         # Used memory
}
```

#### Linux (Net-SNMP)
```python
LINUX_OIDS = {
    # System
    "hrSystemUptime": "1.3.6.1.2.1.25.1.1.0",                # Uptime
    "hrSystemNumUsers": "1.3.6.1.2.1.25.1.5.0",              # Users logged in
    "hrSystemProcesses": "1.3.6.1.2.1.25.1.6.0",             # Running processes

    # CPU (UCD-SNMP)
    "ssCpuRawUser": "1.3.6.1.4.1.2021.11.50.0",              # CPU user time
    "ssCpuRawSystem": "1.3.6.1.4.1.2021.11.52.0",            # CPU system time
    "ssCpuRawIdle": "1.3.6.1.4.1.2021.11.53.0",              # CPU idle time
    "laLoad1": "1.3.6.1.4.1.2021.10.1.3.1",                  # Load average 1min
    "laLoad5": "1.3.6.1.4.1.2021.10.1.3.2",                  # Load average 5min

    # Memory (UCD-SNMP)
    "memTotalReal": "1.3.6.1.4.1.2021.4.5.0",                # Total RAM
    "memAvailReal": "1.3.6.1.4.1.2021.4.6.0",                # Available RAM
    "memBuffer": "1.3.6.1.4.1.2021.4.14.0",                  # Buffered memory
    "memCached": "1.3.6.1.4.1.2021.4.15.0",                  # Cached memory

    # Disk (UCD-SNMP)
    "dskPath": "1.3.6.1.4.1.2021.9.1.2",                     # Mount path
    "dskTotal": "1.3.6.1.4.1.2021.9.1.6",                    # Total space
    "dskAvail": "1.3.6.1.4.1.2021.9.1.7",                    # Available space
    "dskUsed": "1.3.6.1.4.1.2021.9.1.8",                     # Used space
    "dskPercent": "1.3.6.1.4.1.2021.9.1.9",                  # Usage %
}
```

#### Windows
```python
WINDOWS_OIDS = {
    # System
    "hrSystemUptime": "1.3.6.1.2.1.25.1.1.0",
    "hrSystemNumUsers": "1.3.6.1.2.1.25.1.5.0",
    "hrSystemProcesses": "1.3.6.1.2.1.25.1.6.0",

    # Storage
    "hrStorageDescr": "1.3.6.1.2.1.25.2.3.1.3",              # Storage description
    "hrStorageSize": "1.3.6.1.2.1.25.2.3.1.5",               # Total size
    "hrStorageUsed": "1.3.6.1.2.1.25.2.3.1.6",               # Used space

    # Processes
    "hrSWRunName": "1.3.6.1.2.1.25.4.2.1.2",                 # Process name
    "hrSWRunPerfCPU": "1.3.6.1.2.1.25.5.1.1.1",              # Process CPU
    "hrSWRunPerfMem": "1.3.6.1.2.1.25.5.1.1.2",              # Process memory
}
```

---

## 🤖 Auto-Detection Flow

```python
async def detect_device_vendor(ip: str, credentials: SNMPCredential):
    """
    Automatically detect device vendor and load appropriate OIDs
    """

    # Step 1: Get sysObjectID (universal)
    sys_object_id = await snmp_get(ip, "1.3.6.1.2.1.1.2.0", credentials)

    # Step 2: Match against vendor database
    vendor = None
    for oid_prefix, vendor_name in VENDOR_DETECTION.items():
        if sys_object_id.startswith(oid_prefix):
            vendor = vendor_name
            break

    # Step 3: Get sysDescr for additional info
    sys_descr = await snmp_get(ip, "1.3.6.1.2.1.1.1.0", credentials)

    # Step 4: Classify device type based on sysDescr
    device_type = classify_device_type(sys_descr)

    # Step 5: Load appropriate OID library
    oid_library = get_vendor_oids(vendor)

    return {
        "vendor": vendor,
        "device_type": device_type,
        "sys_descr": sys_descr,
        "oid_library": oid_library
    }


def classify_device_type(sys_descr: str) -> str:
    """
    Classify device based on description
    """
    sys_descr_lower = sys_descr.lower()

    if any(x in sys_descr_lower for x in ["router", "cisco ios"]):
        return "router"
    elif any(x in sys_descr_lower for x in ["switch", "catalyst"]):
        return "switch"
    elif any(x in sys_descr_lower for x in ["firewall", "fortigate", "asa", "srx"]):
        return "firewall"
    elif any(x in sys_descr_lower for x in ["linux", "ubuntu", "centos", "debian"]):
        return "server-linux"
    elif "windows" in sys_descr_lower:
        return "server-windows"
    elif any(x in sys_descr_lower for x in ["ups", "apc"]):
        return "ups"
    elif "printer" in sys_descr_lower:
        return "printer"
    else:
        return "generic"


def get_vendor_oids(vendor: str) -> dict:
    """
    Get vendor-specific OIDs plus universal OIDs
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

    # Always include universal OIDs
    oids = UNIVERSAL_OIDS.copy()

    # Add vendor-specific OIDs if available
    if vendor in vendor_map:
        oids.update(vendor_map[vendor])

    return oids
```

---

## 📋 Universal Monitoring Templates

### Generic SNMP Template (Works on EVERYTHING)

```json
{
  "name": "Universal SNMP Device",
  "description": "Basic monitoring for any SNMP device",
  "device_types": ["generic"],
  "items": [
    {
      "name": "Device Uptime",
      "oid": "1.3.6.1.2.1.1.3.0",
      "interval": 300,
      "value_type": "integer",
      "units": "timeticks"
    },
    {
      "name": "Interface Status",
      "oid": "1.3.6.1.2.1.2.2.1.8",
      "interval": 60,
      "value_type": "integer",
      "is_table": true
    },
    {
      "name": "Interface Traffic In",
      "oid": "1.3.6.1.2.1.2.2.1.10",
      "interval": 60,
      "value_type": "counter64",
      "units": "bytes",
      "is_table": true
    },
    {
      "name": "Interface Traffic Out",
      "oid": "1.3.6.1.2.1.2.2.1.16",
      "interval": 60,
      "value_type": "counter64",
      "units": "bytes",
      "is_table": true
    }
  ],
  "triggers": [
    {
      "name": "Interface Down",
      "expression": "ifOperStatus != 1",
      "severity": "high"
    }
  ]
}
```

### FortiGate Firewall Template

```json
{
  "name": "Fortinet FortiGate Firewall",
  "description": "Complete FortiGate monitoring",
  "device_types": ["firewall"],
  "vendor": "Fortinet",
  "items": [
    {
      "name": "CPU Usage",
      "oid": "1.3.6.1.4.1.12356.101.4.1.3.0",
      "interval": 60,
      "value_type": "integer",
      "units": "%"
    },
    {
      "name": "Memory Usage",
      "oid": "1.3.6.1.4.1.12356.101.4.1.4.0",
      "interval": 60,
      "value_type": "integer",
      "units": "%"
    },
    {
      "name": "Active Sessions",
      "oid": "1.3.6.1.4.1.12356.101.4.1.8.0",
      "interval": 60,
      "value_type": "integer"
    },
    {
      "name": "VPN Tunnel Status",
      "oid": "1.3.6.1.4.1.12356.101.12.2.2.1.20",
      "interval": 120,
      "value_type": "integer",
      "is_table": true
    }
  ],
  "triggers": [
    {
      "name": "High CPU",
      "expression": "cpu_usage > 90",
      "severity": "critical"
    },
    {
      "name": "High Memory",
      "expression": "memory_usage > 85",
      "severity": "high"
    },
    {
      "name": "VPN Tunnel Down",
      "expression": "vpn_status == 1",
      "severity": "high"
    }
  ]
}
```

---

## 🔄 Dynamic OID Discovery

For devices where we don't have predefined OIDs, we can do **SNMP walk** and discover available metrics:

```python
async def discover_device_oids(ip: str, credentials: SNMPCredential):
    """
    Walk the entire SNMP tree and discover available OIDs
    """
    discovered = []

    # Walk common branches
    branches = [
        "1.3.6.1.2.1",      # MIB-II (standard)
        "1.3.6.1.4.1",      # Enterprise (vendor-specific)
    ]

    for branch in branches:
        results = await snmp_walk(ip, branch, credentials, max_results=1000)

        for oid, value in results:
            discovered.append({
                "oid": oid,
                "value": value,
                "name": oid_to_name(oid),  # Translate OID to human name
                "category": categorize_oid(oid)
            })

    return discovered
```

---

## 📊 Metric Normalization

Different vendors return metrics in different formats. We normalize them:

```python
def normalize_cpu_metric(vendor: str, value: int) -> float:
    """
    Normalize CPU metric to percentage (0-100)
    """
    if vendor == "Cisco":
        return float(value)  # Already in percentage
    elif vendor == "Fortinet":
        return float(value)  # Already in percentage
    elif vendor == "MikroTik":
        return float(value)  # Already in percentage
    elif vendor == "Linux/Net-SNMP":
        # Calculate from raw ticks
        return 100 - value  # Idle time, invert it
    else:
        return float(value)


def normalize_memory_metric(vendor: str, used: int, total: int) -> float:
    """
    Normalize memory to percentage
    """
    if total == 0:
        return 0.0

    if vendor in ["Cisco", "Fortinet"]:
        # Some vendors return percentage directly
        return float(used)
    else:
        # Calculate percentage
        return (used / total) * 100
```

---

## 🎯 Updated Implementation Priority

### Phase 1: Universal Foundation (Week 1)
1. ✅ Universal MIB-II OID support (works on ALL devices)
2. ✅ Vendor auto-detection via sysObjectID
3. ✅ Dynamic OID library loading
4. ✅ Generic SNMP template

### Phase 2: Top 5 Vendors (Week 2)
1. ✅ Cisco (IOS, IOS-XE, NX-OS, ASA)
2. ✅ Fortinet (FortiGate, FortiSwitch)
3. ✅ Juniper (JunOS)
4. ✅ Linux (Net-SNMP)
5. ✅ Windows Server

### Phase 3: Additional Vendors (Future)
- HP/Aruba, MikroTik, Ubiquiti, Palo Alto, etc.

---

## ✅ Benefits of Universal Approach

1. **Works out of the box** - Basic monitoring for ANY SNMP device
2. **Auto-optimizes** - Loads vendor-specific OIDs when detected
3. **Future-proof** - Easy to add new vendors
4. **Extensible** - Users can add custom OIDs via UI
5. **Fallback** - If vendor unknown, still get universal metrics

---

**This approach makes WARD FLUX truly universal!**

Should I proceed with this universal architecture?
