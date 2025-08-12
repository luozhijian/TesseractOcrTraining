#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup script for Forum database tables and demo user
Run this script to create the necessary tables and insert demo user
"""

import sqlite3
import os

# Database path (adjust if needed)
DATABASE_PATH = '/var/www/tesseracttraining/accounts.db'

def setup_forum_database():
    """Create forum tables and insert demo user if not exists"""
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        print("Setting up forum database...")
        
        # 1. Create User Table
        print("Creating user table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(30) UNIQUE NOT NULL,
                password VARCHAR(512) NOT NULL,
                email VARCHAR(50)
            )
        ''')
        
        # 2. Create Forum Post Table
        print("Creating forum_post table...")
        cursor.execute('''
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
            )
        ''')
        
        # 3. Create Forum Reply Table
        print("Creating forum_reply table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS forum_reply (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                author_id INTEGER NOT NULL,
                post_id INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME,
                FOREIGN KEY (author_id) REFERENCES user(id),
                FOREIGN KEY (post_id) REFERENCES forum_post(id) ON DELETE CASCADE
            )
        ''')
        
        # 4. Create Indexes
        print("Creating indexes...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_forum_post_author ON forum_post(author_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_forum_post_importance_created ON forum_post(importance DESC, created_at DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_forum_reply_post ON forum_reply(post_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_forum_reply_author ON forum_reply(author_id)')
        
        # 5. Insert Demo User (only if not exists)
        print("Inserting demo user...")
        cursor.execute('''
            INSERT OR IGNORE INTO user (id, username, password, email) 
            VALUES (0, 'demo', '1', 'demo@example.com')
        ''')
        
        # Commit all changes
        conn.commit()
        
        # Verify results
        print("\nVerification:")
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'forum%'")
        tables = cursor.fetchall()
        print(f"Forum tables created: {[table[0] for table in tables]}")
        
        # Check demo user
        cursor.execute("SELECT id, username, email FROM user WHERE username = 'demo'")
        demo_user = cursor.fetchone()
        if demo_user:
            print(f"Demo user: ID={demo_user[0]}, Username={demo_user[1]}, Email={demo_user[2]}")
        else:
            print("Demo user not found")
        
        print("\nSetup completed successfully!")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

def check_database_status():
    """Check current database status"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        print("Current database status:")
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in cursor.fetchall()]
        print(f"Existing tables: {tables}")
        
        # Check users
        if 'user' in tables:
            cursor.execute("SELECT COUNT(*) FROM user")
            user_count = cursor.fetchone()[0]
            print(f"Number of users: {user_count}")
            
            cursor.execute("SELECT username FROM user")
            usernames = [user[0] for user in cursor.fetchall()]
            print(f"Usernames: {usernames}")
        
        # Check forum posts
        if 'forum_post' in tables:
            cursor.execute("SELECT COUNT(*) FROM forum_post")
            post_count = cursor.fetchone()[0]
            print(f"Number of forum posts: {post_count}")
        
        # Check forum replies
        if 'forum_reply' in tables:
            cursor.execute("SELECT COUNT(*) FROM forum_reply")
            reply_count = cursor.fetchone()[0]
            print(f"Number of forum replies: {reply_count}")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Forum Database Setup Tool")
    print("=" * 40)
    
    # Check if database file exists
    if os.path.exists(DATABASE_PATH):
        print(f"Database file found: {DATABASE_PATH}")
    else:
        print(f"Database file will be created: {DATABASE_PATH}")
    
    print("\n1. Current Status:")
    check_database_status()
    
    print("\n2. Setting up forum tables and demo user:")
    setup_forum_database()
