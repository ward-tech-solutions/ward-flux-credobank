-- Fix alert_history.rule_id to allow NULL for ping-based alerts
--
-- ISSUE: Ping monitoring creates alerts when devices go down, but these
--        alerts don't have a rule_id (they're generated from ping failures)
--        The database constraint requires rule_id to be NOT NULL, causing
--        all ping-based alerts to fail with IntegrityError
--
-- ERROR: null value in column "rule_id" of relation "alert_history" violates not-null constraint
--
-- FIX: Make rule_id nullable since not all alerts come from alert rules
--      Some alerts are generated directly from ping monitoring

ALTER TABLE alert_history
ALTER COLUMN rule_id DROP NOT NULL;

-- Verify the change
\d alert_history
