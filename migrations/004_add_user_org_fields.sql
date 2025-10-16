-- Add organization_id and is_superuser to users table for multi-tenant support

-- Add organization_id column if it doesn't exist
ALTER TABLE users ADD COLUMN organization_id INTEGER DEFAULT NULL;

-- Add is_superuser column if it doesn't exist
ALTER TABLE users ADD COLUMN is_superuser BOOLEAN DEFAULT 0;
