-- ============================================================================
-- TesseractOcrTraining Upgrade Script to Version 1.0.2
-- ============================================================================
-- This script upgrades the database to version 1.0.2 by adding:
-- 1. user.created_date
-- 2. user.last_access_date
--
-- Compatible with SQLite
-- ============================================================================

PRAGMA foreign_keys = ON;

-- Ensure user table exists.
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(30) UNIQUE NOT NULL,
    password VARCHAR(512) NOT NULL,
    email VARCHAR(50)
);

-- Add created_date if missing.
ALTER TABLE user ADD COLUMN created_date DATETIME;

-- Add last_access_date if missing.
ALTER TABLE user ADD COLUMN last_access_date DATETIME;

-- Backfill created_date for existing rows.
UPDATE user
SET created_date = datetime('now')
WHERE created_date IS NULL;

-- Backfill last_access_date for existing rows.
UPDATE user
SET last_access_date = datetime('now')
WHERE last_access_date IS NULL;
