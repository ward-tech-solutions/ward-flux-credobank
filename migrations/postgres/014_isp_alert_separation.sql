-- WARD FLUX - ISP Alert Separation Migration
-- Adds ISP-specific fields to alert_rules and alert_history tables

-- Add ISP-specific fields to alert_rules
ALTER TABLE alert_rules
ADD COLUMN IF NOT EXISTS isp_provider VARCHAR(50),
ADD COLUMN IF NOT EXISTS scope VARCHAR(50) DEFAULT 'global',
ADD COLUMN IF NOT EXISTS interface_filter VARCHAR(255);

-- Add comments
COMMENT ON COLUMN alert_rules.isp_provider IS 'ISP provider name (magti, silknet) for ISP-specific alerts';
COMMENT ON COLUMN alert_rules.scope IS 'Alert scope: global, isp, device, or branch';
COMMENT ON COLUMN alert_rules.interface_filter IS 'Interface name pattern filter (e.g., Fa3, Fa4)';

-- Add ISP fields to alert_history
ALTER TABLE alert_history
ADD COLUMN IF NOT EXISTS isp_provider VARCHAR(50),
ADD COLUMN IF NOT EXISTS interface_id UUID,
ADD COLUMN IF NOT EXISTS fault_classification JSONB;

-- Add foreign key for interface_id
ALTER TABLE alert_history
ADD CONSTRAINT fk_alert_history_interface
FOREIGN KEY (interface_id) REFERENCES device_interfaces(id) ON DELETE CASCADE;

-- Add comments
COMMENT ON COLUMN alert_history.isp_provider IS 'ISP provider name if this is an ISP-related alert';
COMMENT ON COLUMN alert_history.interface_id IS 'Network interface ID if this alert is interface-specific';
COMMENT ON COLUMN alert_history.fault_classification IS 'JSON object with fault classification data (type, confidence, reason, action)';

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_alert_rules_isp_provider ON alert_rules(isp_provider);
CREATE INDEX IF NOT EXISTS idx_alert_rules_scope ON alert_rules(scope);
CREATE INDEX IF NOT EXISTS idx_alert_history_isp_provider ON alert_history(isp_provider);
CREATE INDEX IF NOT EXISTS idx_alert_history_interface_id ON alert_history(interface_id);

-- Create composite index for efficient ISP alert queries
CREATE INDEX IF NOT EXISTS idx_alert_history_isp_active
ON alert_history(isp_provider, resolved_at)
WHERE resolved_at IS NULL;

-- Seed default ISP alert rules
-- Note: Using expression column instead of metric_name (matches AlertRule model)
INSERT INTO alert_rules (
    name,
    description,
    expression,
    severity,
    enabled,
    scope,
    isp_provider,
    interface_filter,
    created_at,
    updated_at
) VALUES
-- Magti Link Down
(
    'Magti Link Down',
    'Alert when Magti ISP interface goes down on .5 routers',
    'if_oper_status == "down"',
    'CRITICAL',
    true,
    'isp',
    'magti',
    'Fa3',
    NOW(),
    NOW()
),
-- Silknet Link Down
(
    'Silknet Link Down',
    'Alert when Silknet ISP interface goes down on .5 routers',
    'if_oper_status == "down"',
    'CRITICAL',
    true,
    'isp',
    'silknet',
    'Fa4',
    NOW(),
    NOW()
),
-- Magti High Error Rate
(
    'Magti High Error Rate',
    'Alert when Magti interface has high input errors (>1000)',
    'if_in_errors > 1000',
    'HIGH',
    true,
    'isp',
    'magti',
    'Fa3',
    NOW(),
    NOW()
),
-- Silknet High Error Rate
(
    'Silknet High Error Rate',
    'Alert when Silknet interface has high input errors (>1000)',
    'if_in_errors > 1000',
    'HIGH',
    true,
    'isp',
    'silknet',
    'Fa4',
    NOW(),
    NOW()
)
ON CONFLICT DO NOTHING;

-- Output confirmation
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 014: ISP Alert Separation completed successfully';
    RAISE NOTICE '   - Added isp_provider, scope, interface_filter to alert_rules';
    RAISE NOTICE '   - Added isp_provider, interface_id, fault_classification to alert_history';
    RAISE NOTICE '   - Created performance indexes';
    RAISE NOTICE '   - Seeded 4 default ISP alert rules (Magti & Silknet)';
END $$;
