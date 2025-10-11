-- Ward OPS Core PostgreSQL Schema (draft)
-- Generated 2025-10-11 to support migration from SQLite

-- Enable UUID generation helpers
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================================================
-- =========================================================
-- Organizations & System Config
-- =========================================================

CREATE TABLE IF NOT EXISTS organizations (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    subdomain       VARCHAR(100) UNIQUE,
    zabbix_url      VARCHAR(500) NOT NULL,
    zabbix_user     VARCHAR(255) NOT NULL,
    zabbix_password VARCHAR(255) NOT NULL,
    monitored_groups JSONB NOT NULL DEFAULT '[]'::JSONB,
    logo_url        VARCHAR(500),
    primary_color   VARCHAR(7) NOT NULL DEFAULT '#5EBBA8',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_setup_complete BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS system_config (
    id          SERIAL PRIMARY KEY,
    key         VARCHAR(100) NOT NULL UNIQUE,
    value       TEXT,
    description VARCHAR(500),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS setup_wizard_state (
    id              SERIAL PRIMARY KEY,
    step_1_welcome  BOOLEAN NOT NULL DEFAULT FALSE,
    step_2_zabbix   BOOLEAN NOT NULL DEFAULT FALSE,
    step_3_groups   BOOLEAN NOT NULL DEFAULT FALSE,
    step_4_admin    BOOLEAN NOT NULL DEFAULT FALSE,
    step_5_complete BOOLEAN NOT NULL DEFAULT FALSE,
    is_complete     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ
);

-- =========================================================
-- Users & Auth
-- =========================================================

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(50) NOT NULL UNIQUE,
    email           VARCHAR(100) NOT NULL UNIQUE,
    full_name       VARCHAR(100),
    hashed_password VARCHAR(255) NOT NULL,
    role            VARCHAR(32) NOT NULL DEFAULT 'viewer',
    organization_id INTEGER REFERENCES organizations(id) ON DELETE SET NULL,
    is_superuser    BOOLEAN NOT NULL DEFAULT FALSE,
    region          VARCHAR(50),
    branches        TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login      TIMESTAMPTZ,
    theme_preference VARCHAR(10) NOT NULL DEFAULT 'auto',
    language        VARCHAR(10) NOT NULL DEFAULT 'en',
    timezone        VARCHAR(50) NOT NULL DEFAULT 'UTC',
    notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    dashboard_layout JSONB
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

-- =========================================================
-- Branches & Device Inventory
-- =========================================================

CREATE TABLE IF NOT EXISTS branches (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name         VARCHAR(200) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    region       VARCHAR(100),
    branch_code  VARCHAR(10),
    address      TEXT,
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    device_count INTEGER NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_branches_region ON branches(region);
CREATE INDEX IF NOT EXISTS idx_branches_active ON branches(is_active);

CREATE TABLE IF NOT EXISTS standalone_devices (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(200) NOT NULL,
    ip              VARCHAR(45) NOT NULL,
    hostname        VARCHAR(255),
    vendor          VARCHAR(100),
    device_type     VARCHAR(100),
    model           VARCHAR(100),
    location        VARCHAR(200),
    description     TEXT,
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    discovered_at   TIMESTAMPTZ,
    last_seen       TIMESTAMPTZ,
    tags            JSONB DEFAULT '[]'::JSONB,
    custom_fields   JSONB DEFAULT '{}'::JSONB,
    branch_id       UUID REFERENCES branches(id) ON DELETE SET NULL,
    normalized_name VARCHAR(200),
    device_subtype  VARCHAR(100),
    floor_info      VARCHAR(50),
    unit_number     INTEGER,
    original_name   VARCHAR(200),
    ssh_port        INTEGER NOT NULL DEFAULT 22,
    ssh_username    VARCHAR(100),
    ssh_enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_standalone_devices_branch ON standalone_devices(branch_id);
CREATE INDEX IF NOT EXISTS idx_standalone_devices_type ON standalone_devices(device_type);
CREATE INDEX IF NOT EXISTS idx_standalone_devices_subtype ON standalone_devices(device_subtype);

-- =========================================================
-- Reference Data & Host Group Configuration
-- =========================================================

CREATE TABLE IF NOT EXISTS monitored_hostgroups (
    id          SERIAL PRIMARY KEY,
    groupid     VARCHAR(64) NOT NULL UNIQUE,
    name        VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_monitored_hostgroups_active ON monitored_hostgroups(is_active);

CREATE TABLE IF NOT EXISTS georgian_regions (
    id         SERIAL PRIMARY KEY,
    name_en    VARCHAR(100) NOT NULL UNIQUE,
    name_ka    VARCHAR(100),
    latitude   NUMERIC(9,6) NOT NULL,
    longitude  NUMERIC(9,6) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS georgian_cities (
    id         SERIAL PRIMARY KEY,
    name_en    VARCHAR(100) NOT NULL UNIQUE,
    name_ka    VARCHAR(100),
    region_id  INTEGER NOT NULL REFERENCES georgian_regions(id) ON DELETE CASCADE,
    latitude   NUMERIC(9,6) NOT NULL,
    longitude  NUMERIC(9,6) NOT NULL,
    is_active  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_georgian_cities_region ON georgian_cities(region_id);
CREATE INDEX IF NOT EXISTS idx_georgian_cities_name ON georgian_cities(name_en);
CREATE INDEX IF NOT EXISTS idx_standalone_devices_enabled ON standalone_devices(enabled);

CREATE TABLE IF NOT EXISTS ping_results (
    id                BIGSERIAL PRIMARY KEY,
    device_ip         VARCHAR(50) NOT NULL,
    device_name       VARCHAR(255),
    packets_sent      INTEGER NOT NULL DEFAULT 5,
    packets_received  INTEGER NOT NULL DEFAULT 0,
    packet_loss_percent INTEGER NOT NULL DEFAULT 100,
    min_rtt_ms        INTEGER,
    avg_rtt_ms        INTEGER,
    max_rtt_ms        INTEGER,
    is_reachable      BOOLEAN NOT NULL DEFAULT FALSE,
    timestamp         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ping_results_device_ip ON ping_results(device_ip);
CREATE INDEX IF NOT EXISTS idx_ping_results_timestamp ON ping_results(timestamp);

-- =========================================================
-- Monitoring Templates & Items
-- =========================================================

CREATE TABLE IF NOT EXISTS monitoring_profiles (
    id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name      VARCHAR(100) NOT NULL UNIQUE,
    mode      VARCHAR(20) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS monitoring_templates (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    vendor      VARCHAR(100),
    device_types JSONB DEFAULT '[]'::JSONB,
    items       JSONB DEFAULT '[]'::JSONB,
    triggers    JSONB DEFAULT '[]'::JSONB,
    is_builtin  BOOLEAN NOT NULL DEFAULT FALSE,
    is_default  BOOLEAN NOT NULL DEFAULT FALSE,
    created_by  UUID,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS monitoring_items (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id    UUID NOT NULL REFERENCES standalone_devices(id) ON DELETE CASCADE,
    template_id  UUID REFERENCES monitoring_templates(id) ON DELETE SET NULL,
    oid_name     VARCHAR(100) NOT NULL,
    oid          VARCHAR(200) NOT NULL,
    interval     INTEGER NOT NULL DEFAULT 60,
    value_type   VARCHAR(20) NOT NULL DEFAULT 'integer',
    units        VARCHAR(20),
    enabled      BOOLEAN NOT NULL DEFAULT TRUE,
    last_poll    TIMESTAMPTZ,
    last_value   TEXT,
    last_error   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_monitoring_items_device ON monitoring_items(device_id);

CREATE TABLE IF NOT EXISTS snmp_credentials (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id             UUID NOT NULL REFERENCES standalone_devices(id) ON DELETE CASCADE,
    version               VARCHAR(10) NOT NULL,
    community_encrypted   TEXT,
    username              VARCHAR(100),
    auth_protocol         VARCHAR(20),
    auth_key_encrypted    TEXT,
    priv_protocol         VARCHAR(20),
    priv_key_encrypted    TEXT,
    security_level        VARCHAR(20),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_snmp_credentials_device ON snmp_credentials(device_id);

-- =========================================================
-- Alerting
-- =========================================================

CREATE TABLE IF NOT EXISTS alert_rules (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id               UUID REFERENCES standalone_devices(id) ON DELETE CASCADE,
    branch_id               UUID REFERENCES branches(id) ON DELETE CASCADE,
    name                    VARCHAR(200) NOT NULL,
    description             TEXT,
    expression              VARCHAR(500) NOT NULL,
    severity                VARCHAR(20) NOT NULL,
    notification_channels   JSONB DEFAULT '[]'::JSONB,
    notification_recipients JSONB DEFAULT '[]'::JSONB,
    device_group            VARCHAR(100),
    monitoring_item_id      UUID REFERENCES monitoring_items(id) ON DELETE SET NULL,
    enabled                 BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_alert_rules_device ON alert_rules(device_id);
CREATE INDEX IF NOT EXISTS idx_alert_rules_branch ON alert_rules(branch_id);

CREATE TABLE IF NOT EXISTS alert_history (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id          UUID NOT NULL REFERENCES alert_rules(id) ON DELETE CASCADE,
    device_id        UUID REFERENCES standalone_devices(id) ON DELETE SET NULL,
    severity         VARCHAR(20) NOT NULL,
    message          TEXT NOT NULL,
    value            VARCHAR(100),
    rule_name        VARCHAR(200),
    threshold        VARCHAR(500),
    triggered_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged     BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged_by  UUID,
    acknowledged_at  TIMESTAMPTZ,
    resolved_at      TIMESTAMPTZ,
    notifications_sent JSONB DEFAULT '[]'::JSONB,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_history_rule ON alert_history(rule_id);
CREATE INDEX IF NOT EXISTS idx_alert_history_device ON alert_history(device_id);

-- =========================================================
-- Discovery & Topology
-- =========================================================

CREATE TABLE IF NOT EXISTS discovery_rules (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name               VARCHAR(200) NOT NULL,
    description        TEXT,
    network_range      VARCHAR(100) NOT NULL,
    enabled            BOOLEAN NOT NULL DEFAULT TRUE,
    schedule           VARCHAR(100),
    snmp_discovery     BOOLEAN NOT NULL DEFAULT TRUE,
    snmp_communities   JSONB,
    ping_only          BOOLEAN NOT NULL DEFAULT FALSE,
    last_run           TIMESTAMPTZ,
    last_devices_found INTEGER NOT NULL DEFAULT 0,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS discovery_results (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id         UUID NOT NULL REFERENCES discovery_rules(id) ON DELETE CASCADE,
    ip_address      VARCHAR(45) NOT NULL,
    hostname        VARCHAR(255),
    mac_address     VARCHAR(17),
    vendor          VARCHAR(100),
    device_type     VARCHAR(50),
    snmp_reachable  BOOLEAN NOT NULL DEFAULT FALSE,
    snmp_version    VARCHAR(10),
    sys_descr       TEXT,
    sys_object_id   VARCHAR(200),
    discovered_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    added_to_monitoring BOOLEAN NOT NULL DEFAULT FALSE,
    added_at        TIMESTAMPTZ,
    imported_device_id UUID REFERENCES standalone_devices(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_discovery_results_rule ON discovery_results(rule_id);

CREATE TABLE IF NOT EXISTS discovery_jobs (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id           UUID NOT NULL REFERENCES discovery_rules(id) ON DELETE CASCADE,
    status            VARCHAR(50) NOT NULL DEFAULT 'running',
    total_ips         INTEGER NOT NULL DEFAULT 0,
    scanned_ips       INTEGER NOT NULL DEFAULT 0,
    discovered_devices INTEGER NOT NULL DEFAULT 0,
    imported_devices  INTEGER NOT NULL DEFAULT 0,
    failed_ips        INTEGER NOT NULL DEFAULT 0,
    started_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at      TIMESTAMPTZ,
    duration_seconds  INTEGER,
    error_message     TEXT,
    scan_summary      JSONB,
    triggered_by      VARCHAR(50),
    triggered_by_user UUID
);

CREATE INDEX IF NOT EXISTS idx_discovery_jobs_status ON discovery_jobs(status);

CREATE TABLE IF NOT EXISTS discovery_credentials (
    id                       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                     VARCHAR(200) NOT NULL,
    credential_type          VARCHAR(50) NOT NULL,
    community_encrypted      TEXT,
    username                 VARCHAR(100),
    auth_protocol            VARCHAR(20),
    auth_key_encrypted       TEXT,
    priv_protocol            VARCHAR(20),
    priv_key_encrypted       TEXT,
    ssh_username             VARCHAR(100),
    ssh_password_encrypted   TEXT,
    ssh_key_encrypted        TEXT,
    success_count            INTEGER NOT NULL DEFAULT 0,
    failure_count            INTEGER NOT NULL DEFAULT 0,
    last_success             TIMESTAMPTZ,
    created_by               UUID,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_discovery_credentials_type ON discovery_credentials(credential_type);

CREATE TABLE IF NOT EXISTS network_topology (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_ip         VARCHAR(45) NOT NULL,
    source_device_id  UUID REFERENCES standalone_devices(id) ON DELETE CASCADE,
    target_ip         VARCHAR(45) NOT NULL,
    target_device_id  UUID REFERENCES standalone_devices(id) ON DELETE CASCADE,
    connection_type   VARCHAR(50),
    interface_name    VARCHAR(100),
    target_interface  VARCHAR(100),
    vlan_id           INTEGER,
    discovered_via    VARCHAR(50),
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    last_seen         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    first_discovered  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_network_topology_source ON network_topology(source_ip);
CREATE INDEX IF NOT EXISTS idx_network_topology_target ON network_topology(target_ip);

-- =========================================================
-- Performance Baselines & Traces (optional tables)
-- =========================================================

CREATE TABLE IF NOT EXISTS performance_baselines (
    id                          BIGSERIAL PRIMARY KEY,
    device_ip                   VARCHAR(50) NOT NULL UNIQUE,
    device_name                 VARCHAR(255),
    baseline_latency_avg        INTEGER,
    baseline_latency_stddev     INTEGER,
    baseline_packet_loss        INTEGER NOT NULL DEFAULT 0,
    latency_warning_threshold   INTEGER,
    latency_critical_threshold  INTEGER,
    packet_loss_threshold       INTEGER NOT NULL DEFAULT 5,
    samples_count               INTEGER NOT NULL DEFAULT 0,
    last_calculated             TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS metric_baselines (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id     UUID NOT NULL,
    metric_name   VARCHAR(100) NOT NULL,
    avg_value     INTEGER,
    min_value     INTEGER,
    max_value     INTEGER,
    std_dev       INTEGER,
    time_period   VARCHAR(20),
    hour_of_day   INTEGER,
    day_of_week   INTEGER,
    sample_count  INTEGER,
    last_updated  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_metric_baselines_device ON metric_baselines(device_id);

CREATE TABLE IF NOT EXISTS traceroute_results (
    id             BIGSERIAL PRIMARY KEY,
    device_ip      VARCHAR(50) NOT NULL,
    device_name    VARCHAR(255),
    hop_number     INTEGER NOT NULL,
    hop_ip         VARCHAR(50),
    hop_hostname   VARCHAR(255),
    latency_ms     INTEGER,
    packet_loss    INTEGER NOT NULL DEFAULT 0,
    timestamp      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mtr_results (
    id                  BIGSERIAL PRIMARY KEY,
    device_ip           VARCHAR(50) NOT NULL,
    device_name         VARCHAR(255),
    hop_number          INTEGER NOT NULL,
    hop_ip              VARCHAR(50),
    hop_hostname        VARCHAR(255),
    packets_sent        INTEGER NOT NULL DEFAULT 0,
    packets_received    INTEGER NOT NULL DEFAULT 0,
    packet_loss_percent INTEGER NOT NULL DEFAULT 0,
    latency_avg         INTEGER,
    latency_min         INTEGER,
    latency_max         INTEGER,
    latency_stddev      INTEGER,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- End of core schema draft
