-- Migration 006: Add standalone_devices table for true standalone monitoring
-- This enables monitoring without Zabbix dependency

-- Standalone Devices Table
CREATE TABLE IF NOT EXISTS standalone_devices (
    id UUID PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    ip VARCHAR(45) NOT NULL,
    hostname VARCHAR(255),
    vendor VARCHAR(100),
    device_type VARCHAR(100),
    model VARCHAR(100),
    location VARCHAR(200),
    description TEXT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    -- Auto-discovery metadata
    discovered_at TIMESTAMP,
    last_seen TIMESTAMP,

    -- Organization/grouping (JSON fields)
    tags TEXT,  -- JSON array: ["production", "core"]
    custom_fields TEXT,  -- JSON object: {"rack": "A1", "floor": "2"}

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_standalone_devices_ip ON standalone_devices(ip);
CREATE INDEX IF NOT EXISTS idx_standalone_devices_enabled ON standalone_devices(enabled);
CREATE INDEX IF NOT EXISTS idx_standalone_devices_vendor ON standalone_devices(vendor);
CREATE INDEX IF NOT EXISTS idx_standalone_devices_type ON standalone_devices(device_type);

-- Sample devices for testing (can be deleted)
-- Uncomment to add sample devices
/*
INSERT INTO standalone_devices (id, name, ip, vendor, device_type, enabled)
VALUES
    (gen_random_uuid(), 'Core-Router-01', '10.0.1.1', 'Cisco', 'router', TRUE),
    (gen_random_uuid(), 'Core-Switch-01', '10.0.1.2', 'Cisco', 'switch', TRUE),
    (gen_random_uuid(), 'Firewall-01', '10.0.1.254', 'Fortinet', 'firewall', TRUE)
WHERE NOT EXISTS (SELECT 1 FROM standalone_devices WHERE ip IN ('10.0.1.1', '10.0.1.2', '10.0.1.254'));
*/
