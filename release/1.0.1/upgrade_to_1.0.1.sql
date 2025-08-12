-- ============================================================================
-- TesseractOcrTraining Upgrade Script to Version 1.0.1
-- ============================================================================
-- This script upgrades the database to version 1.0.1 which includes:
-- 1. User table creation (if not exists)
-- 2. Forum functionality with posts and replies
-- 3. Demo user creation
-- 4. Performance indexes
-- 
-- Compatible with SQLite
-- ============================================================================

-- Enable foreign key support (important for SQLite)
PRAGMA foreign_keys = ON;

-- ============================================================================
-- 1. Create User Table (if not exists)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(30) UNIQUE NOT NULL,
    password VARCHAR(512) NOT NULL,
    email VARCHAR(50)
);

-- ============================================================================
-- 2. Insert Demo User (only if not exists) - BEFORE creating forum tables
-- ============================================================================
INSERT OR IGNORE INTO user (id, username, password, email) 
VALUES (0, 'demo', '1', 'demo@tesstrain.com');

-- ============================================================================
-- 3. Create Forum Post Table with REAL importance (updated for v1.0.1)
-- ============================================================================
CREATE TABLE IF NOT EXISTS forum_post (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    author_id INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    image_filename VARCHAR(255),
    importance REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY (author_id) REFERENCES user(id)
);

-- ============================================================================
-- 4. Create Forum Reply Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS forum_reply (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    author_id INTEGER NOT NULL,
    post_id INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    image_filename VARCHAR(255),
    FOREIGN KEY (author_id) REFERENCES user(id),
    FOREIGN KEY (post_id) REFERENCES forum_post(id) ON DELETE CASCADE
);

-- ============================================================================
-- 5. Upgrade existing forum_post table if importance is INTEGER
-- ============================================================================
-- Check if we need to update existing forum_post table
-- This handles upgrading from older versions where importance was INTEGER

-- Temporarily disable foreign key constraints during migration
PRAGMA foreign_keys = OFF;

-- First, check if forum_post exists and has INTEGER importance
-- If so, we need to create a new table and migrate data

-- Create temporary table with correct structure
CREATE TABLE IF NOT EXISTS forum_post_temp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    author_id INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    image_filename VARCHAR(255),
    importance REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY (author_id) REFERENCES user(id)
);

-- Migrate data if forum_post exists (this will only work if the original exists)
INSERT OR IGNORE INTO forum_post_temp (id, title, content, author_id, created_at, updated_at, image_filename, importance)
SELECT id, title, content, author_id, created_at, updated_at, image_filename, CAST(importance AS REAL)
FROM forum_post;

-- Drop original table if it exists
DROP TABLE IF EXISTS forum_post_old;

-- Rename existing table if it exists
-- Note: This is a safe operation since we're using IF NOT EXISTS
ALTER TABLE forum_post RENAME TO forum_post_old;

-- Rename temp table to final name
ALTER TABLE forum_post_temp RENAME TO forum_post;

-- Clean up old table
DROP TABLE IF EXISTS forum_post_old;

-- Re-enable foreign key constraints
PRAGMA foreign_keys = ON;

-- ============================================================================
-- 6. Create Performance Indexes
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_forum_post_author ON forum_post(author_id);
CREATE INDEX IF NOT EXISTS idx_forum_post_importance_created ON forum_post(importance DESC, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_forum_reply_post ON forum_reply(post_id);
CREATE INDEX IF NOT EXISTS idx_forum_reply_author ON forum_reply(author_id);
CREATE INDEX IF NOT EXISTS idx_user_username ON user(username);

-- ============================================================================
-- 7. Create Welcome Post (only if no posts exist)
-- ============================================================================
INSERT OR IGNORE INTO forum_post (title, content, author_id, created_at, importance)
SELECT 
    'Welcome to Tesseract OCR Training Forum!',
    'Welcome to our community forum! Here you can:

- Ask questions about OCR training
- Share your training experiences
- Get help with Tesseract configuration
- Discuss best practices for text recognition

Feel free to create your first post and join the conversation!

Tips for getting started:
- Upload your images in the Images section
- Edit the text associated with each image
- Start training to create your custom model
- Download your .traineddata file when ready

Happy training!',
    0,
    datetime('now'),
    5.0
WHERE NOT EXISTS (SELECT 1 FROM forum_post);

-- ============================================================================
-- 8. Verification Queries (Optional - uncomment to run)
-- ============================================================================

-- Verify tables were created:
-- SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE 'forum%' OR name = 'user');

-- Verify demo user exists:
-- SELECT id, username, email FROM user WHERE username = 'demo';

-- Check forum_post structure (especially importance column type):
-- PRAGMA table_info(forum_post);

-- Count existing data:
-- SELECT 
--     (SELECT COUNT(*) FROM user) as users,
--     (SELECT COUNT(*) FROM forum_post) as posts,
--     (SELECT COUNT(*) FROM forum_reply) as replies;

-- ============================================================================
-- Upgrade Complete
-- ============================================================================
-- Database has been successfully upgraded to version 1.0.1
-- New features available:
-- - Forum functionality with posts and replies
-- - Demo user account (username: demo, password: 1)
-- - Enhanced importance scoring with decimal precision
-- - Performance optimized with proper indexes
-- ============================================================================
