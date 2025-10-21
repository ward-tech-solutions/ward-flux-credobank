-- Migration 011: Add SNMP port field to standalone_devices table
-- Created: 2025-10-20
-- Description: Adds snmp_port column with default value of 161

-- Add SNMP port column with default 161
ALTER TABLE standalone_devices
ADD COLUMN IF NOT EXISTS snmp_port INTEGER DEFAULT 161;

-- Add comment for documentation
COMMENT ON COLUMN standalone_devices.snmp_port IS 'SNMP port number (default 161 for SNMPv2c/v3)';
