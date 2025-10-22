-- ============================================
-- WARD OPS Performance Optimization Indexes
-- Migration 012: Add critical indexes for query performance
-- SIMPLIFIED VERSION - No fancy syntax, just basic indexes
-- ============================================

-- 1. Composite index for ping_results (device_ip, timestamp DESC)
CREATE INDEX IF NOT EXISTS idx_ping_results_device_timestamp ON ping_results(device_ip, timestamp DESC);

-- 2. Composite index for standalone_devices (enabled, vendor)
CREATE INDEX IF NOT EXISTS idx_standalone_devices_enabled_vendor ON standalone_devices(enabled, vendor) WHERE enabled = true;

-- 3. Foreign key index for standalone_devices(branch_id)
CREATE INDEX IF NOT EXISTS idx_standalone_devices_branch_id ON standalone_devices(branch_id) WHERE branch_id IS NOT NULL;

-- 4. Composite index for alert_history (device_id, resolved_at)
CREATE INDEX IF NOT EXISTS idx_alert_history_device_resolved ON alert_history(device_id, resolved_at);

-- 5. Partial index for active alerts
CREATE INDEX IF NOT EXISTS idx_alert_history_active ON alert_history(triggered_at DESC) WHERE resolved_at IS NULL;

-- 6. Composite index for monitoring_items (device_id, enabled)
CREATE INDEX IF NOT EXISTS idx_monitoring_items_device_enabled ON monitoring_items(device_id, enabled) WHERE enabled = true;

-- 7. Index for standalone_devices (down_since)
CREATE INDEX IF NOT EXISTS idx_standalone_devices_down_since ON standalone_devices(down_since) WHERE down_since IS NOT NULL;

-- 8. Index for ping_results cleanup
CREATE INDEX IF NOT EXISTS idx_ping_results_timestamp ON ping_results(timestamp);

-- 9. Composite index for alert_history cleanup
CREATE INDEX IF NOT EXISTS idx_alert_history_created_at ON alert_history(created_at);
