-- Add user preference columns to users table
-- This migration adds theme, language, timezone, and notification preferences

-- SQLite version (for development)
ALTER TABLE users ADD COLUMN theme_preference VARCHAR(10) DEFAULT 'auto';
ALTER TABLE users ADD COLUMN language VARCHAR(10) DEFAULT 'en';
ALTER TABLE users ADD COLUMN timezone VARCHAR(50) DEFAULT 'UTC';
ALTER TABLE users ADD COLUMN notifications_enabled BOOLEAN DEFAULT 1;
ALTER TABLE users ADD COLUMN dashboard_layout VARCHAR(1000);

-- Note: For PostgreSQL, the migration tool will automatically convert this
-- PostgreSQL uses TRUE/FALSE instead of 1/0 for booleans
