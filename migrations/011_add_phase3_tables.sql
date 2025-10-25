-- ============================================
-- PHASE 3 - Database Migration
-- ============================================
-- Purpose: Add tables for topology discovery and baseline learning
-- Date: 2025-10-26
-- Phase: 3 (Topology & Analytics)
-- ============================================

-- Create interface_baselines table
CREATE TABLE IF NOT EXISTS interface_baselines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interface_id UUID NOT NULL REFERENCES device_interfaces(id) ON DELETE CASCADE,

    -- Time context
    hour_of_day INTEGER NOT NULL CHECK (hour_of_day >= 0 AND hour_of_day <= 23),
    day_of_week INTEGER NOT NULL CHECK (day_of_week >= 0 AND day_of_week <= 6),

    -- Traffic baselines (inbound)
    avg_in_mbps FLOAT,
    std_dev_in_mbps FLOAT,
    min_in_mbps FLOAT,
    max_in_mbps FLOAT,

    -- Traffic baselines (outbound)
    avg_out_mbps FLOAT,
    std_dev_out_mbps FLOAT,
    min_out_mbps FLOAT,
    max_out_mbps FLOAT,

    -- Error rate baselines
    avg_error_rate FLOAT,
    std_dev_error_rate FLOAT,

    -- Metadata
    sample_count INTEGER,
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    last_updated TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Unique constraint: one baseline per interface per hour per day
    UNIQUE(interface_id, hour_of_day, day_of_week)
);

-- Indexes for baselines table
CREATE INDEX IF NOT EXISTS idx_interface_baselines_interface_id
    ON interface_baselines(interface_id);

CREATE INDEX IF NOT EXISTS idx_interface_baselines_time_context
    ON interface_baselines(hour_of_day, day_of_week);

CREATE INDEX IF NOT EXISTS idx_interface_baselines_confidence
    ON interface_baselines(confidence)
    WHERE confidence >= 0.5;

-- Update trigger for baselines
CREATE OR REPLACE FUNCTION update_interface_baselines_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_interface_baselines_updated_at
    BEFORE UPDATE ON interface_baselines
    FOR EACH ROW
    EXECUTE FUNCTION update_interface_baselines_updated_at();

-- ============================================
-- Verify migration
-- ============================================

DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'interface_baselines') THEN
        RAISE NOTICE 'Migration 011: interface_baselines table created successfully';
    ELSE
        RAISE EXCEPTION 'Migration 011: Failed to create interface_baselines table';
    END IF;
END $$;
