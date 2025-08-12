-- SQL Script to Create Forum Tables and Insert Demo User
-- Compatible with SQLite

-- ============================================================================
-- 1. Create User Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(30) UNIQUE NOT NULL,
    password VARCHAR(512) NOT NULL,
    email VARCHAR(50)
);

-- ============================================================================
-- 2. Create Forum Post Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS forum_post (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    author_id INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    image_filename VARCHAR(255),
    importance INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (author_id) REFERENCES user(id)
);

-- ============================================================================
-- 3. Create Forum Reply Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS forum_reply (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    author_id INTEGER NOT NULL,
    post_id INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    FOREIGN KEY (author_id) REFERENCES user(id),
    FOREIGN KEY (post_id) REFERENCES forum_post(id) ON DELETE CASCADE
);

-- ============================================================================
-- 4. Create Indexes for Better Performance
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_forum_post_author ON forum_post(author_id);
CREATE INDEX IF NOT EXISTS idx_forum_post_importance_created ON forum_post(importance DESC, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_forum_reply_post ON forum_reply(post_id);
CREATE INDEX IF NOT EXISTS idx_forum_reply_author ON forum_reply(author_id);

-- ============================================================================
-- 5. Insert Demo User (only if not exists)
-- ============================================================================
INSERT OR IGNORE INTO user (id, username, password, email) 
VALUES (0, 'demo', '1', 'demo@example.com');

-- Alternative method using NOT EXISTS (if you prefer this approach):
-- INSERT INTO user (id, username, password, email) 
-- SELECT 0, 'demo', '1', 'demo@example.com'
-- WHERE NOT EXISTS (SELECT 1 FROM user WHERE username = 'demo');

-- ============================================================================
-- 6. Verification Queries (Optional - for testing)
-- ============================================================================
-- Check if tables were created successfully:
-- SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'forum%';

-- Check if demo user was inserted:
-- SELECT id, username, email FROM user WHERE username = 'demo';

-- View table structures:
-- PRAGMA table_info(user);
-- PRAGMA table_info(forum_post);
-- PRAGMA table_info(forum_reply);
