-- ═══════════════════════════════════════════════════════════════════
-- WARD FLUX - Monitoring Engine Tables Migration
-- Version: 005
-- Description: Add standalone monitoring engine tables with universal vendor support
-- ═══════════════════════════════════════════════════════════════════

-- Monitoring Profile Table
CREATE TABLE IF NOT EXISTS monitoring_profiles (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    mode VARCHAR(20) NOT NULL CHECK (mode IN ('zabbix', 'standalone', 'hybrid')),
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- SNMP Credentials Table (encrypted storage)
CREATE TABLE IF NOT EXISTS snmp_credentials (
    id UUID PRIMARY KEY,
    device_id UUID NOT NULL,
    version VARCHAR(10) NOT NULL CHECK (version IN ('v2c', 'v3')),
    -- SNMPv2c
    community_encrypted TEXT,
    -- SNMPv3
    username VARCHAR(100),
    auth_protocol VARCHAR(20),
    auth_key_encrypted TEXT,
    priv_protocol VARCHAR(20),
    priv_key_encrypted TEXT,
    security_level VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Monitoring Templates Table
CREATE TABLE IF NOT EXISTS monitoring_templates (
    id UUID PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,
    vendor VARCHAR(100),
    device_types JSON,
    items JSON NOT NULL,
    triggers JSON,
    is_builtin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Monitoring Items Table
CREATE TABLE IF NOT EXISTS monitoring_items (
    id UUID PRIMARY KEY,
    device_id UUID NOT NULL,
    template_id UUID,
    name VARCHAR(200) NOT NULL,
    oid VARCHAR(200) NOT NULL,
    interval_seconds INTEGER NOT NULL DEFAULT 60,
    value_type VARCHAR(20) NOT NULL,
    units VARCHAR(20),
    is_table BOOLEAN DEFAULT FALSE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    params JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Alert Rules Table
CREATE TABLE IF NOT EXISTS alert_rules (
    id UUID PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    expression TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    notification_channels JSON,
    notification_recipients JSON,
    device_id UUID,
    device_group VARCHAR(100),
    monitoring_item_id UUID,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Alert History Table
CREATE TABLE IF NOT EXISTS alert_history (
    id UUID PRIMARY KEY,
    rule_id UUID NOT NULL,
    device_id UUID NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    details JSON,
    triggered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged_by UUID,
    acknowledged_at TIMESTAMP,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Discovery Rules Table
CREATE TABLE IF NOT EXISTS discovery_rules (
    id UUID PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    network_range VARCHAR(100) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    schedule VARCHAR(100),
    snmp_discovery BOOLEAN DEFAULT TRUE,
    snmp_communities JSON,
    ping_only BOOLEAN DEFAULT FALSE,
    last_run TIMESTAMP,
    last_devices_found INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Discovery Results Table
CREATE TABLE IF NOT EXISTS discovery_results (
    id UUID PRIMARY KEY,
    rule_id UUID NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    hostname VARCHAR(255),
    mac_address VARCHAR(17),
    snmp_reachable BOOLEAN DEFAULT FALSE,
    snmp_version VARCHAR(10),
    vendor VARCHAR(100),
    device_type VARCHAR(50),
    sys_descr TEXT,
    sys_object_id VARCHAR(200),
    discovered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    added_to_monitoring BOOLEAN DEFAULT FALSE,
    added_at TIMESTAMP
);

-- Metric Baselines Table
CREATE TABLE IF NOT EXISTS metric_baselines (
    id UUID PRIMARY KEY,
    device_id UUID NOT NULL,
    monitoring_item_id UUID,
    metric_name VARCHAR(200) NOT NULL,
    min_value VARCHAR(50),
    max_value VARCHAR(50),
    avg_value VARCHAR(50),
    std_deviation VARCHAR(50),
    sample_count INTEGER NOT NULL,
    calculated_from TIMESTAMP NOT NULL,
    calculated_to TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_snmp_creds_device ON snmp_credentials(device_id);
CREATE INDEX IF NOT EXISTS idx_monitoring_items_device ON monitoring_items(device_id);
CREATE INDEX IF NOT EXISTS idx_monitoring_items_enabled ON monitoring_items(enabled);
CREATE INDEX IF NOT EXISTS idx_alert_rules_enabled ON alert_rules(enabled);
CREATE INDEX IF NOT EXISTS idx_alert_history_device ON alert_history(device_id);
CREATE INDEX IF NOT EXISTS idx_alert_history_triggered ON alert_history(triggered_at);
CREATE INDEX IF NOT EXISTS idx_discovery_results_ip ON discovery_results(ip_address);
CREATE INDEX IF NOT EXISTS idx_discovery_results_added ON discovery_results(added_to_monitoring);
CREATE INDEX IF NOT EXISTS idx_metric_baselines_device ON metric_baselines(device_id);

-- Create default monitoring profile
INSERT INTO monitoring_profiles (id, name, mode, is_active, description)
SELECT
    gen_random_uuid(),
    'Default Profile',
    'standalone',
    FALSE,
    'Default monitoring profile - activate to enable standalone monitoring'
WHERE NOT EXISTS (SELECT 1 FROM monitoring_profiles WHERE name = 'Default Profile');

-- Note: Foreign key constraints should be added after ensuring devices table exists
-- ALTER TABLE snmp_credentials ADD CONSTRAINT fk_snmp_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE;
-- ALTER TABLE monitoring_items ADD CONSTRAINT fk_item_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE;
-- ALTER TABLE monitoring_items ADD CONSTRAINT fk_item_template FOREIGN KEY (template_id) REFERENCES monitoring_templates(id) ON DELETE SET NULL;
-- ALTER TABLE alert_rules ADD CONSTRAINT fk_alert_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE;
-- ALTER TABLE alert_rules ADD CONSTRAINT fk_alert_item FOREIGN KEY (monitoring_item_id) REFERENCES monitoring_items(id) ON DELETE CASCADE;
-- ALTER TABLE alert_history ADD CONSTRAINT fk_alert_history_rule FOREIGN KEY (rule_id) REFERENCES alert_rules(id) ON DELETE CASCADE;
-- ALTER TABLE alert_history ADD CONSTRAINT fk_alert_history_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE;
-- ALTER TABLE alert_history ADD CONSTRAINT fk_alert_history_user FOREIGN KEY (acknowledged_by) REFERENCES users(id) ON DELETE SET NULL;
-- ALTER TABLE discovery_results ADD CONSTRAINT fk_discovery_rule FOREIGN KEY (rule_id) REFERENCES discovery_rules(id) ON DELETE CASCADE;
-- ALTER TABLE metric_baselines ADD CONSTRAINT fk_baseline_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE;
-- ALTER TABLE metric_baselines ADD CONSTRAINT fk_baseline_item FOREIGN KEY (monitoring_item_id) REFERENCES monitoring_items(id) ON DELETE CASCADE;
