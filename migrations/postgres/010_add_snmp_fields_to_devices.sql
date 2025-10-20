-- Migration 010: Add SNMP fields to standalone_devices table
-- Created: 2025-10-20
-- Description: Adds snmp_community and snmp_version columns for denormalized SNMP access

-- Add SNMP community string column
ALTER TABLE standalone_devices
ADD COLUMN IF NOT EXISTS snmp_community VARCHAR(255);

-- Add SNMP version column
ALTER TABLE standalone_devices
ADD COLUMN IF NOT EXISTS snmp_version VARCHAR(10);

-- Add comment for documentation
COMMENT ON COLUMN standalone_devices.snmp_community IS 'SNMP community string for v2c access (denormalized from snmp_credentials for performance)';
COMMENT ON COLUMN standalone_devices.snmp_version IS 'SNMP version: v1, v2c, or v3';

-- Create index for SNMP-enabled devices
CREATE INDEX IF NOT EXISTS idx_standalone_devices_snmp_community
ON standalone_devices(snmp_community)
WHERE snmp_community IS NOT NULL;
