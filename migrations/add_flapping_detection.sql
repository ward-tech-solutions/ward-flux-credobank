-- Add flapping detection columns to standalone_devices table
ALTER TABLE standalone_devices
ADD COLUMN IF NOT EXISTS is_flapping BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS flap_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_flap_detected TIMESTAMP,
ADD COLUMN IF NOT EXISTS flapping_since TIMESTAMP,
ADD COLUMN IF NOT EXISTS status_change_times TIMESTAMP[] DEFAULT '{}';

-- Create index for faster flapping queries
CREATE INDEX IF NOT EXISTS idx_devices_flapping ON standalone_devices(is_flapping) WHERE is_flapping = true;

-- Create status history table for tracking changes
CREATE TABLE IF NOT EXISTS device_status_history (
    id SERIAL PRIMARY KEY,
    device_id INTEGER NOT NULL REFERENCES standalone_devices(id) ON DELETE CASCADE,
    old_status VARCHAR(10),
    new_status VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    response_time_ms FLOAT
);

-- Index for quick history lookups
CREATE INDEX IF NOT EXISTS idx_status_history_device_time
ON device_status_history(device_id, timestamp DESC);

-- Function to get status change count in time window
CREATE OR REPLACE FUNCTION get_status_change_count(
    p_device_id INTEGER,
    p_minutes INTEGER DEFAULT 5
) RETURNS INTEGER AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)
        FROM device_status_history
        WHERE device_id = p_device_id
        AND timestamp > NOW() - INTERVAL '1 minute' * p_minutes
    );
END;
$$ LANGUAGE plpgsql;