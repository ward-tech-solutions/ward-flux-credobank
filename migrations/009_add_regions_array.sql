-- Migration: Add regions array column for multi-region support
-- Replaces single region field with regions JSON array

-- Add regions column (JSON array)
ALTER TABLE users ADD COLUMN IF NOT EXISTS regions TEXT;

-- Migrate existing region data to regions array
UPDATE users
SET regions = CASE
    WHEN region IS NOT NULL AND region != '' THEN '["' || region || '"]'
    ELSE NULL
END
WHERE regions IS NULL;
