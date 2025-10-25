-- ============================================
-- INTERFACE DISCOVERY - Database Migration
-- ============================================
-- Purpose: Add device_interfaces table for SNMP interface discovery
-- Date: 2025-10-26
-- Phase: 1 (Interface Discovery Implementation)
-- ============================================

-- Create device_interfaces table
CREATE TABLE IF NOT EXISTS device_interfaces (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign key to devices
    device_id UUID NOT NULL REFERENCES standalone_devices(id) ON DELETE CASCADE,

    -- SNMP interface data (from IF-MIB)
    if_index INTEGER NOT NULL,              -- ifIndex: Unique interface number
    if_name VARCHAR(255),                   -- ifName: Gi0/0/0, Fa0/1, etc. (from ifXTable)
    if_descr VARCHAR(255),                  -- ifDescr: Interface description (legacy)
    if_alias VARCHAR(500),                  -- ifAlias: User-configured description (CRITICAL - contains ISP info!)
    if_type VARCHAR(100),                   -- ifType: ethernet, tunnel, loopback, etc.

    -- Parsed/classified data (from interface_parser.py)
    interface_type VARCHAR(50),             -- isp, trunk, access, server_link, branch_link, other
    isp_provider VARCHAR(50),               -- magti, silknet, veon, beeline, geocell, other
    is_critical BOOLEAN DEFAULT false,      -- Critical interfaces (ISP uplinks)
    parser_confidence FLOAT,                -- Parser confidence score (0.0 - 1.0)

    -- Interface status (from SNMP)
    admin_status INTEGER,                   -- ifAdminStatus: 1=up, 2=down, 3=testing
    oper_status INTEGER,                    -- ifOperStatus: 1=up, 2=down, 3=testing, 4=unknown, 5=dormant, 6=notPresent, 7=lowerLayerDown
    speed BIGINT,                           -- ifSpeed: Interface speed in bits/second
    mtu INTEGER,                            -- ifMtu: Maximum transmission unit
    duplex VARCHAR(20),                     -- full, half, auto (if available from proprietary MIBs)

    -- MAC address and physical info
    phys_address VARCHAR(17),               -- ifPhysAddress: MAC address (00:11:22:33:44:55)

    -- Topology and relationships
    connected_to_device_id UUID REFERENCES standalone_devices(id) ON DELETE SET NULL,
    connected_to_interface_id UUID REFERENCES device_interfaces(id) ON DELETE SET NULL,
    lldp_neighbor_name VARCHAR(255),        -- LLDP neighbor device name
    lldp_neighbor_port VARCHAR(255),        -- LLDP neighbor port

    -- Discovery metadata
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_status_change TIMESTAMP WITH TIME ZONE,  -- When oper_status last changed

    -- Configuration
    enabled BOOLEAN DEFAULT true,           -- Whether to monitor this interface
    monitoring_enabled BOOLEAN DEFAULT true, -- Whether to collect metrics for this interface

    -- Tags and custom fields
    tags JSON,                              -- ["critical", "isp", "primary-uplink"]
    custom_fields JSON,                     -- Flexible key-value storage

    -- Notes
    notes TEXT,                             -- User notes about this interface

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    UNIQUE(device_id, if_index)             -- One row per device per interface index
);

-- ============================================
-- Indexes for performance
-- ============================================

-- Primary lookup: Get all interfaces for a device
CREATE INDEX IF NOT EXISTS idx_device_interfaces_device_id
    ON device_interfaces(device_id);

-- Filter by interface type (get all ISP interfaces)
CREATE INDEX IF NOT EXISTS idx_device_interfaces_type
    ON device_interfaces(interface_type)
    WHERE interface_type IS NOT NULL;

-- Filter by ISP provider (get all Magti interfaces)
CREATE INDEX IF NOT EXISTS idx_device_interfaces_isp
    ON device_interfaces(isp_provider)
    WHERE isp_provider IS NOT NULL;

-- Find critical interfaces quickly
CREATE INDEX IF NOT EXISTS idx_device_interfaces_critical
    ON device_interfaces(is_critical)
    WHERE is_critical = true;

-- Find interfaces by operational status
CREATE INDEX IF NOT EXISTS idx_device_interfaces_oper_status
    ON device_interfaces(oper_status);

-- Composite index for common queries: "Show all critical ISP interfaces"
CREATE INDEX IF NOT EXISTS idx_device_interfaces_type_critical
    ON device_interfaces(interface_type, is_critical, device_id);

-- Index for topology queries (find connected devices)
CREATE INDEX IF NOT EXISTS idx_device_interfaces_topology
    ON device_interfaces(connected_to_device_id)
    WHERE connected_to_device_id IS NOT NULL;

-- Index for last_seen (cleanup old interfaces)
CREATE INDEX IF NOT EXISTS idx_device_interfaces_last_seen
    ON device_interfaces(last_seen);

-- ============================================
-- Create interface_metrics_summary table (optional - for caching)
-- ============================================
-- This table can cache aggregated metrics from VictoriaMetrics
-- Useful for quick dashboards without querying VM

CREATE TABLE IF NOT EXISTS interface_metrics_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interface_id UUID NOT NULL REFERENCES device_interfaces(id) ON DELETE CASCADE,

    -- Traffic metrics (last 24 hours)
    avg_in_mbps FLOAT,                      -- Average inbound traffic (Mbps)
    avg_out_mbps FLOAT,                     -- Average outbound traffic (Mbps)
    max_in_mbps FLOAT,                      -- Peak inbound traffic (Mbps)
    max_out_mbps FLOAT,                     -- Peak outbound traffic (Mbps)
    total_in_gb FLOAT,                      -- Total inbound traffic (GB)
    total_out_gb FLOAT,                     -- Total outbound traffic (GB)

    -- Error metrics (last 24 hours)
    in_errors INTEGER,                      -- Input errors
    out_errors INTEGER,                     -- Output errors
    in_discards INTEGER,                    -- Input discards
    out_discards INTEGER,                   -- Output discards

    -- Utilization
    utilization_percent FLOAT,              -- Interface utilization (%)

    -- Timestamps
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Unique constraint
    UNIQUE(interface_id)
);

-- Index for metrics summary
CREATE INDEX IF NOT EXISTS idx_interface_metrics_interface_id
    ON interface_metrics_summary(interface_id);

-- ============================================
-- Add trigger to update updated_at timestamp
-- ============================================

CREATE OR REPLACE FUNCTION update_device_interfaces_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_device_interfaces_updated_at
    BEFORE UPDATE ON device_interfaces
    FOR EACH ROW
    EXECUTE FUNCTION update_device_interfaces_updated_at();

-- ============================================
-- Migration complete
-- ============================================

-- Verify tables were created
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'device_interfaces') THEN
        RAISE NOTICE 'Migration 010: device_interfaces table created successfully';
    ELSE
        RAISE EXCEPTION 'Migration 010: Failed to create device_interfaces table';
    END IF;

    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'interface_metrics_summary') THEN
        RAISE NOTICE 'Migration 010: interface_metrics_summary table created successfully';
    ELSE
        RAISE EXCEPTION 'Migration 010: Failed to create interface_metrics_summary table';
    END IF;
END $$;
