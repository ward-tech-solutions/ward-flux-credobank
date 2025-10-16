-- Align alert_history table with application expectations

ALTER TABLE alert_history
  ADD COLUMN IF NOT EXISTS rule_name VARCHAR(200),
  ADD COLUMN IF NOT EXISTS threshold VARCHAR(500),
  ADD COLUMN IF NOT EXISTS notifications_sent JSONB DEFAULT '[]'::JSONB;
