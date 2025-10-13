-- Add regions column to users table
-- This migration adds support for multi-region access control

ALTER TABLE users ADD COLUMN IF NOT EXISTS regions JSON;

-- Add comment for documentation
COMMENT ON COLUMN users.regions IS 'List of regions accessible to regional managers (JSON array). NULL = all regions access.';
