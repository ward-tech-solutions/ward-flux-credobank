-- Migration: Add down_since column to track when devices first went offline
-- This enables accurate downtime calculation instead of using last_check

ALTER TABLE standalone_devices
ADD COLUMN down_since TIMESTAMP;

-- Add comment
COMMENT ON COLUMN standalone_devices.down_since IS 'Timestamp when device first went down (NULL when up)';
