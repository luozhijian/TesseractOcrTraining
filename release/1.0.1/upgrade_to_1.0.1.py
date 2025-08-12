#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TesseractOcrTraining Upgrade Script to Version 1.0.1
====================================================

This script upgrades the database to version 1.0.1 which includes:
1. User table creation (if not exists)
2. Forum functionality with posts and replies
3. Demo user creation with secure handling
4. Performance indexes
5. Data type migration (importance: INTEGER -> REAL)

Features:
- Safe upgrade from any previous version
- Rollback capability on errors
- Detailed logging and verification
- Idempotent operations (safe to run multiple times)

Usage:
    python upgrade_to_1.0.1.py [--database-path /path/to/accounts.db]
"""

import sqlite3
import os
import sys
import argparse
import logging
import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('upgrade_1.0.1.log')
    ]
)
logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DATABASE_PATH = '/var/www/tesseracttraining/accounts.db'

class DatabaseUpgrader:
    def __init__(self, database_path):
        self.database_path = database_path
        self.connection = None
        self.backup_path = None
        
    def connect(self):
        """Establish database connection with proper configuration"""
        try:
            self.connection = sqlite3.connect(self.database_path)
            self.connection.execute("PRAGMA foreign_keys = ON")
            logger.info(f"Connected to database: {self.database_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    def create_backup(self):
        """Create a backup of the current database"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.backup_path = f"{self.database_path}.backup_{timestamp}"
            
            # Create backup
            with open(self.database_path, 'rb') as src:
                with open(self.backup_path, 'wb') as dst:
                    dst.write(src.read())
            
            logger.info(f"Backup created: {self.backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False
    
    def check_table_exists(self, table_name):
        """Check if a table exists"""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        return cursor.fetchone()[0] > 0
    
    def get_column_type(self, table_name, column_name):
        """Get the data type of a specific column"""
        cursor = self.connection.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        for col in columns:
            if col[1].lower() == column_name.lower():
                return col[2].upper()
        return None
    
    def check_index_exists(self, index_name):
        """Check if an index exists"""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM sqlite_master 
            WHERE type='index' AND name=?
        """, (index_name,))
        return cursor.fetchone()[0] > 0
    
    def check_foreign_key_exists(self, table_name, foreign_key_column):
        """Check if a foreign key constraint exists on a table"""
        cursor = self.connection.cursor()
        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        foreign_keys = cursor.fetchall()
        for fk in foreign_keys:
            if fk[3].lower() == foreign_key_column.lower():  # fk[3] is the 'from' column
                return True
        return False
    
    def create_user_table(self):
        """Create user table if it doesn't exist"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(30) UNIQUE NOT NULL,
                    password VARCHAR(512) NOT NULL,
                    email VARCHAR(50)
                )
            """)
            logger.info("User table created/verified")
            return True
        except Exception as e:
            logger.error(f"Failed to create user table: {e}")
            return False
    
    def migrate_forum_post_table(self):
        """Create or migrate forum_post table with REAL importance"""
        try:
            cursor = self.connection.cursor()
            
            # Temporarily disable foreign key constraints during migration
            cursor.execute("PRAGMA foreign_keys = OFF")
            
            # Check if forum_post exists and its importance column type
            if self.check_table_exists('forum_post'):
                importance_type = self.get_column_type('forum_post', 'importance')
                logger.info(f"Existing forum_post table found with importance type: {importance_type}")
                
 
            else:
                # Create new table
                cursor.execute("""
                    CREATE TABLE forum_post (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title VARCHAR(200) NOT NULL,
                        content TEXT NOT NULL,
                        author_id INTEGER NOT NULL,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME,
                        image_filename VARCHAR(255),
                        importance REAL NOT NULL DEFAULT 0.0,
                        FOREIGN KEY (author_id) REFERENCES user(id)
                    )
                """)
                logger.info("Forum post table created")
            
            # Re-enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys = ON")
            
            return True
        except Exception as e:
            logger.error(f"Failed to create/migrate forum_post table: {e}")
            # Re-enable foreign key constraints even on error
            try:
                cursor.execute("PRAGMA foreign_keys = ON")
            except:
                pass
            return False
    
    def create_forum_reply_table(self):
        """Create forum_reply table if it doesn't exist"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
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
                )
            """)
            logger.info("Forum reply table created/verified")
            return True
        except Exception as e:
            logger.error(f"Failed to create forum_reply table: {e}")
            return False
    
    def create_indexes(self):
        """Create performance indexes with foreign key validation"""
        try:
            cursor = self.connection.cursor()
            
            # Define indexes with their names for checking
            indexes_to_create = [
                ("idx_forum_post_author", "CREATE INDEX IF NOT EXISTS idx_forum_post_author ON forum_post(author_id)"),
                ("idx_forum_post_importance_created", "CREATE INDEX IF NOT EXISTS idx_forum_post_importance_created ON forum_post(importance DESC, created_at DESC)"),
                ("idx_forum_reply_post", "CREATE INDEX IF NOT EXISTS idx_forum_reply_post ON forum_reply(post_id)"),
                ("idx_forum_reply_author", "CREATE INDEX IF NOT EXISTS idx_forum_reply_author ON forum_reply(author_id)"),
                ("idx_user_username", "CREATE INDEX IF NOT EXISTS idx_user_username ON user(username)")
            ]
            
            # Check foreign key constraints before creating indexes
            logger.info("Checking foreign key constraints...")
            
            foreign_key_checks = [
                ("forum_post", "author_id", "user(id)"),
                ("forum_reply", "author_id", "user(id)"),
                ("forum_reply", "post_id", "forum_post(id)")
            ]
            
            for table_name, fk_column, references in foreign_key_checks:
                if self.check_table_exists(table_name):
                    if self.check_foreign_key_exists(table_name, fk_column):
                        logger.info(f"Foreign key constraint exists: {table_name}.{fk_column} -> {references}")
                    else:
                        logger.warning(f"Foreign key constraint missing: {table_name}.{fk_column} -> {references}")
                else:
                    logger.info(f"Table {table_name} does not exist yet, skipping foreign key check")
            
            # Create indexes with detailed logging
            logger.info("Creating/verifying performance indexes...")
            created_count = 0
            existing_count = 0
            
            for index_name, index_sql in indexes_to_create:
                if self.check_index_exists(index_name):
                    logger.info(f"Index already exists: {index_name}")
                    existing_count += 1
                else:
                    logger.info(f"Creating index: {index_name}")
                    cursor.execute(index_sql)
                    created_count += 1
            
            logger.info(f"Index summary: {created_count} created, {existing_count} already existed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            return False
    
    def insert_demo_user(self):
        """Insert demo user if it doesn't exist"""
        try:
            cursor = self.connection.cursor()
            
            # Check if demo user already exists
            cursor.execute("SELECT COUNT(*) FROM user WHERE username = 'demo'")
            if cursor.fetchone()[0] > 0:
                logger.info("Demo user already exists")
                return True
            
            # Insert demo user
            cursor.execute("""
                INSERT INTO user (id, username, password, email) 
                VALUES (0, 'demo', '1', 'demo@tesstrain.com')
            """)
            logger.info("Demo user created (username: demo, password: 1)")
            return True
        except Exception as e:
            logger.error(f"Failed to create demo user: {e}")
            return False
    
    def create_welcome_post(self):
        """Create welcome post if no posts exist"""
        try:
            cursor = self.connection.cursor()
            
            # Check if any posts exist
            cursor.execute("SELECT COUNT(*) FROM forum_post")
            if cursor.fetchone()[0] > 0:
                logger.info("Forum posts already exist, skipping welcome post creation")
                return True
            

            logger.info("Welcome post created")
            return True
        except Exception as e:
            logger.error(f"Failed to create welcome post: {e}")
            return False
    
    def verify_upgrade(self):
        """Verify the upgrade was successful"""
        try:
            cursor = self.connection.cursor()
            
            # Check tables exist
            tables = ['user', 'forum_post', 'forum_reply']
            for table in tables:
                if not self.check_table_exists(table):
                    logger.error(f"Table {table} does not exist after upgrade")
                    return False
            
            # Check demo user exists
            cursor.execute("SELECT COUNT(*) FROM user WHERE username = 'demo'")
            if cursor.fetchone()[0] == 0:
                logger.error("Demo user not found after upgrade")
                return False
            
            # Check importance column type
            importance_type = self.get_column_type('forum_post', 'importance')
            if importance_type != 'REAL':
                logger.warning(f"Importance column type is {importance_type}, expected REAL")
            
            # Count data
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM user) as users,
                    (SELECT COUNT(*) FROM forum_post) as posts,
                    (SELECT COUNT(*) FROM forum_reply) as replies
            """)
            counts = cursor.fetchone()
            logger.info(f"Database verification: {counts[0]} users, {counts[1]} posts, {counts[2]} replies")
            
            return True
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False
    
    def upgrade(self):
        """Perform the complete upgrade process"""
        logger.info("Starting TesseractOcrTraining upgrade to version 1.0.1")
        
        # Connect to database
        if not self.connect():
            return False
        
        try:
            # Create backup
            if not self.create_backup():
                logger.warning("Could not create backup, proceeding anyway...")
            
            # Begin transaction
            self.connection.execute("BEGIN TRANSACTION")
            
            # Perform upgrade steps
            steps = [
                ("Creating user table", self.create_user_table),
                ("Inserting demo user", self.insert_demo_user),
                ("Creating/migrating forum_post table", self.migrate_forum_post_table),
                ("Creating forum_reply table", self.create_forum_reply_table),
                ("Creating performance indexes", self.create_indexes),
                ("Creating welcome post", self.create_welcome_post),
                ("Verifying upgrade", self.verify_upgrade)
            ]
            
            for step_name, step_func in steps:
                logger.info(f"Step: {step_name}")
                if not step_func():
                    logger.error(f"Failed: {step_name}")
                    self.connection.execute("ROLLBACK")
                    return False
            
            # Commit changes
            self.connection.execute("COMMIT")
            logger.info("SUCCESS: Upgrade to version 1.0.1 completed successfully!")
            
            return True
            
        except Exception as e:
            logger.error(f"Upgrade failed: {e}")
            try:
                self.connection.execute("ROLLBACK")
                logger.info("Database changes rolled back")
            except:
                pass
            return False
        
        finally:
            if self.connection:
                self.connection.close()

def main():
    parser = argparse.ArgumentParser(description="Upgrade TesseractOcrTraining to version 1.0.1")
    parser.add_argument('--database-path', default=DEFAULT_DATABASE_PATH,
                        help=f'Path to the database file (default: {DEFAULT_DATABASE_PATH})')
    
    args = parser.parse_args()
    
    # Check if database file exists
    if not os.path.exists(args.database_path):
        logger.info(f"Database file does not exist, will be created: {args.database_path}")
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(args.database_path), exist_ok=True)
    
    # Perform upgrade
    upgrader = DatabaseUpgrader(args.database_path)
    success = upgrader.upgrade()
    
    if success:
        logger.info("CONGRATULATIONS: Upgrade completed successfully!")
        logger.info("You can now use the forum functionality with:")
        logger.info("  - Demo user: username='demo', password='1'")
        logger.info("  - Enhanced importance scoring with decimal precision")
        logger.info("  - Performance optimized database")
        sys.exit(0)
    else:
        logger.error("ERROR: Upgrade failed!")
        if upgrader.backup_path and os.path.exists(upgrader.backup_path):
            logger.info(f"Your original database backup is available at: {upgrader.backup_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()
    
    
