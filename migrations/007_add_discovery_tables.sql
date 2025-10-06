-- Migration 007: Add Auto-Discovery Tables
-- Purpose: Network scanning and device auto-discovery
-- Date: 2024-10-06

-- ============================================
-- Discovery Rules Table
-- ============================================
CREATE TABLE IF NOT EXISTS discovery_rules (
    id UUID PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    enabled BOOLEAN DEFAULT TRUE,

    -- Network Configuration
    network_ranges TEXT NOT NULL,  -- JSON array: ["192.168.1.0/24", "10.0.0.0/16"]
    excluded_ips TEXT,             -- JSON array: ["192.168.1.1", "192.168.1.254"]

    -- Discovery Methods
    use_ping BOOLEAN DEFAULT TRUE,
    use_snmp BOOLEAN DEFAULT TRUE,
    use_ssh BOOLEAN DEFAULT FALSE,

    -- SNMP Configuration
    snmp_communities TEXT,          -- JSON array: ["public", "private"]
    snmp_v3_credentials TEXT,       -- JSON array of v3 credential objects
    snmp_ports TEXT DEFAULT '[161]', -- JSON array: [161, 1161]

    -- SSH Configuration (optional)
    ssh_port INTEGER DEFAULT 22,
    ssh_credentials TEXT,           -- JSON array of SSH credential objects

    -- Scheduling
    schedule_enabled BOOLEAN DEFAULT FALSE,
    schedule_cron VARCHAR(100),     -- Cron expression: "0 */6 * * *" (every 6 hours)
    last_run TIMESTAMP,
    next_run TIMESTAMP,

    -- Auto-Import Settings
    auto_import BOOLEAN DEFAULT FALSE,
    auto_assign_template BOOLEAN DEFAULT TRUE,
    default_monitoring_profile UUID,

    -- Metadata
    created_by UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (default_monitoring_profile) REFERENCES monitoring_profiles(id) ON DELETE SET NULL
);

CREATE INDEX idx_discovery_rules_enabled ON discovery_rules(enabled);
CREATE INDEX idx_discovery_rules_schedule ON discovery_rules(schedule_enabled, next_run);

-- ============================================
-- Discovery Results Table
-- ============================================
CREATE TABLE IF NOT EXISTS discovery_results (
    id UUID PRIMARY KEY,
    rule_id UUID NOT NULL,

    -- Device Information
    ip VARCHAR(45) NOT NULL,
    hostname VARCHAR(200),
    mac_address VARCHAR(17),
    vendor VARCHAR(100),
    device_type VARCHAR(100),
    model VARCHAR(200),
    os_version VARCHAR(200),

    -- Discovery Details
    discovered_via VARCHAR(50),     -- 'ping', 'snmp', 'ssh'
    ping_responsive BOOLEAN DEFAULT FALSE,
    ping_latency_ms FLOAT,
    snmp_responsive BOOLEAN DEFAULT FALSE,
    snmp_version VARCHAR(10),       -- 'v1', 'v2c', 'v3'
    snmp_community VARCHAR(100),    -- Community that worked
    ssh_responsive BOOLEAN DEFAULT FALSE,

    -- SNMP Data
    sys_descr TEXT,
    sys_name VARCHAR(200),
    sys_oid VARCHAR(200),
    sys_uptime BIGINT,
    sys_contact VARCHAR(200),
    sys_location VARCHAR(200),

    -- Status
    status VARCHAR(50) DEFAULT 'discovered', -- 'discovered', 'imported', 'ignored', 'failed'
    import_status VARCHAR(50),               -- 'pending', 'success', 'failed'
    imported_device_id UUID,                 -- Reference to standalone_devices.id
    failure_reason TEXT,

    -- Metadata
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    imported_at TIMESTAMP,

    FOREIGN KEY (rule_id) REFERENCES discovery_rules(id) ON DELETE CASCADE,
    FOREIGN KEY (imported_device_id) REFERENCES standalone_devices(id) ON DELETE SET NULL
);

CREATE INDEX idx_discovery_results_rule ON discovery_results(rule_id);
CREATE INDEX idx_discovery_results_ip ON discovery_results(ip);
CREATE INDEX idx_discovery_results_status ON discovery_results(status);
CREATE INDEX idx_discovery_results_discovered_at ON discovery_results(discovered_at);

-- ============================================
-- Discovery Jobs Table (for tracking runs)
-- ============================================
CREATE TABLE IF NOT EXISTS discovery_jobs (
    id UUID PRIMARY KEY,
    rule_id UUID NOT NULL,

    -- Job Status
    status VARCHAR(50) DEFAULT 'running', -- 'running', 'completed', 'failed', 'cancelled'

    -- Progress Tracking
    total_ips INTEGER DEFAULT 0,
    scanned_ips INTEGER DEFAULT 0,
    discovered_devices INTEGER DEFAULT 0,
    imported_devices INTEGER DEFAULT 0,
    failed_ips INTEGER DEFAULT 0,

    -- Timing
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,

    -- Results
    error_message TEXT,
    scan_summary TEXT,              -- JSON summary of scan results

    -- Metadata
    triggered_by VARCHAR(50),       -- 'manual', 'scheduled', 'api'
    triggered_by_user UUID,

    FOREIGN KEY (rule_id) REFERENCES discovery_rules(id) ON DELETE CASCADE,
    FOREIGN KEY (triggered_by_user) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_discovery_jobs_rule ON discovery_jobs(rule_id);
CREATE INDEX idx_discovery_jobs_status ON discovery_jobs(status);
CREATE INDEX idx_discovery_jobs_started ON discovery_jobs(started_at);

-- ============================================
-- Network Topology Table (discovered connections)
-- ============================================
CREATE TABLE IF NOT EXISTS network_topology (
    id UUID PRIMARY KEY,

    -- Source Device
    source_ip VARCHAR(45) NOT NULL,
    source_device_id UUID,          -- Reference to standalone_devices.id

    -- Target Device
    target_ip VARCHAR(45) NOT NULL,
    target_device_id UUID,

    -- Connection Details
    connection_type VARCHAR(50),    -- 'direct', 'router', 'switch', 'vpn'
    interface_name VARCHAR(100),    -- Source interface
    target_interface VARCHAR(100),  -- Target interface
    vlan_id INTEGER,

    -- Discovery Method
    discovered_via VARCHAR(50),     -- 'arp', 'cdp', 'lldp', 'snmp', 'traceroute'

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    first_discovered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (source_device_id) REFERENCES standalone_devices(id) ON DELETE CASCADE,
    FOREIGN KEY (target_device_id) REFERENCES standalone_devices(id) ON DELETE CASCADE
);

CREATE INDEX idx_network_topology_source ON network_topology(source_ip);
CREATE INDEX idx_network_topology_target ON network_topology(target_ip);
CREATE INDEX idx_network_topology_active ON network_topology(is_active);

-- ============================================
-- Discovery Credentials Table
-- ============================================
CREATE TABLE IF NOT EXISTS discovery_credentials (
    id UUID PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    credential_type VARCHAR(50) NOT NULL, -- 'snmp_v2c', 'snmp_v3', 'ssh', 'telnet'

    -- SNMP v2c
    community_encrypted TEXT,

    -- SNMP v3
    username VARCHAR(100),
    auth_protocol VARCHAR(20),      -- 'MD5', 'SHA', 'SHA-224', 'SHA-256', 'SHA-384', 'SHA-512'
    auth_key_encrypted TEXT,
    priv_protocol VARCHAR(20),      -- 'DES', 'AES', 'AES-192', 'AES-256'
    priv_key_encrypted TEXT,

    -- SSH/Telnet
    ssh_username VARCHAR(100),
    ssh_password_encrypted TEXT,
    ssh_key_encrypted TEXT,

    -- Usage Stats
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    last_success TIMESTAMP,

    -- Metadata
    created_by UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_discovery_credentials_type ON discovery_credentials(credential_type);

-- ============================================
-- Comments
-- ============================================
COMMENT ON TABLE discovery_rules IS 'Auto-discovery rules for network scanning';
COMMENT ON TABLE discovery_results IS 'Discovered devices from network scans';
COMMENT ON TABLE discovery_jobs IS 'Discovery job execution tracking';
COMMENT ON TABLE network_topology IS 'Discovered network connections and topology';
COMMENT ON TABLE discovery_credentials IS 'Credentials for device discovery';
