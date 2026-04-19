#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TesseractOcrTraining Upgrade Script to Version 1.0.2

Adds two columns to user table:
- created_date (DATETIME)
- last_access_date (DATETIME)
"""

import argparse
import datetime
import logging
import os
import sqlite3
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('upgrade_1.0.2.log')
    ]
)
logger = logging.getLogger(__name__)

DEFAULT_DATABASE_PATH = '/var/www/tesseracttraining/accounts.db'


class DatabaseUpgrader:
    def __init__(self, database_path):
        self.database_path = database_path
        self.connection = None
        self.backup_path = None

    def connect(self):
        try:
            self.connection = sqlite3.connect(self.database_path)
            self.connection.execute("PRAGMA foreign_keys = ON")
            logger.info("Connected to database: %s", self.database_path)
            return True
        except Exception as e:
            logger.error("Failed to connect to database: %s", e)
            return False

    def create_backup(self):
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.backup_path = f"{self.database_path}.backup_{timestamp}"
            with open(self.database_path, 'rb') as src:
                with open(self.backup_path, 'wb') as dst:
                    dst.write(src.read())
            logger.info("Backup created: %s", self.backup_path)
            return True
        except Exception as e:
            logger.warning("Failed to create backup: %s", e)
            return False

    def table_exists(self, table_name):
        cur = self.connection.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return cur.fetchone()[0] > 0

    def column_exists(self, table_name, column_name):
        cur = self.connection.cursor()
        cur.execute(f"PRAGMA table_info({table_name})")
        return any(row[1].lower() == column_name.lower() for row in cur.fetchall())

    def ensure_user_table(self):
        return True 
        try:
            cur = self.connection.cursor()
            cur.execute("""
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
            logger.error("Failed to create/verify user table: %s", e)
            return False

    def add_missing_columns(self):
        try:
            cur = self.connection.cursor()

            if not self.column_exists('user', 'created_date'):
                cur.execute("ALTER TABLE user ADD COLUMN created_date DATETIME")
                logger.info("Added column user.created_date")
            else:
                logger.info("Column already exists: user.created_date")

            if not self.column_exists('user', 'last_access_date'):
                cur.execute("ALTER TABLE user ADD COLUMN last_access_date DATETIME")
                logger.info("Added column user.last_access_date")
            else:
                logger.info("Column already exists: user.last_access_date")

            cur.execute(
                "UPDATE user SET created_date = datetime('now') WHERE created_date IS NULL"
            )
            cur.execute(
                "UPDATE user SET last_access_date = datetime('now') WHERE last_access_date IS NULL"
            )
            logger.info("Backfilled missing datetime values")
            return True
        except Exception as e:
            logger.error("Failed adding/backfilling columns: %s", e)
            return False

    def verify(self):
        if not self.table_exists('user'):
            logger.error("Verification failed: user table does not exist")
            return False
        if not self.column_exists('user', 'created_date'):
            logger.error("Verification failed: created_date missing")
            return False
        if not self.column_exists('user', 'last_access_date'):
            logger.error("Verification failed: last_access_date missing")
            return False
        logger.info("Verification passed")
        return True

    def upgrade(self):
        logger.info("Starting upgrade to version 1.0.2")
        if not self.connect():
            return False
        try:
            self.create_backup()
            self.connection.execute("BEGIN TRANSACTION")

            steps = [
                ("Ensure user table", self.ensure_user_table),
                ("Add missing columns", self.add_missing_columns),
                ("Verify upgrade", self.verify),
            ]
            for step_name, step_func in steps:
                logger.info("Step: %s", step_name)
                if not step_func():
                    self.connection.execute("ROLLBACK")
                    logger.error("Upgrade failed at step: %s", step_name)
                    return False

            self.connection.execute("COMMIT")
            logger.info("SUCCESS: Upgrade to 1.0.2 completed")
            return True
        except Exception as e:
            logger.error("Upgrade exception: %s", e)
            try:
                self.connection.execute("ROLLBACK")
            except Exception:
                pass
            return False
        finally:
            if self.connection:
                self.connection.close()


def main():
    parser = argparse.ArgumentParser(description="Upgrade TesseractOcrTraining to 1.0.2")
    parser.add_argument(
        '--database-path',
        default=DEFAULT_DATABASE_PATH,
        help=f'Path to database file (default: {DEFAULT_DATABASE_PATH})'
    )
    args = parser.parse_args()

    if not os.path.exists(args.database_path):
        logger.info("Database file does not exist, will be created: %s", args.database_path)
        os.makedirs(os.path.dirname(args.database_path), exist_ok=True)

    upgrader = DatabaseUpgrader(args.database_path)
    if upgrader.upgrade():
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
