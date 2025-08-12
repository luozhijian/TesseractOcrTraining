# TesseractOcrTraining Release 1.0.1 Upgrade

This directory contains upgrade scripts for TesseractOcrTraining version 1.0.1.

## What's New in 1.0.1

- **Forum Functionality**: Complete forum system with posts and replies  
- **Demo User**: Default demo account for testing  
- **Enhanced Importance Scoring**: Decimal precision for post importance  
- **Performance Optimizations**: Database indexes for better performance  
- **Improved Login Flow**: Direct redirect to forum after login  
- **Error Handling**: Better error messages in login form  

## Upgrade Options

You have two options for upgrading your database:

### Option 1: SQL Script (Recommended)
Use this if you prefer direct SQL execution or have database administration tools.

```bash
# Connect to your SQLite database and run:
sqlite3 /var/www/tesseracttraining/accounts.db < upgrade_to_1.0.1.sql
```

### Option 2: Python Script (Advanced)
Use this for more control, logging, and automatic backup creation.

```bash
# Run with default database path:
python3 upgrade_to_1.0.1.py

# Or specify custom database path:
python3 upgrade_to_1.0.1.py --database-path /path/to/your/accounts.db
```

## Features of the Python Script

- **Automatic Backup**: Creates timestamped backup before upgrade
- **Detailed Logging**: Comprehensive upgrade progress logging  
- **Rollback Support**: Automatic rollback on any errors
- **Idempotent**: Safe to run multiple times
- **Verification**: Validates upgrade success

## What Gets Created/Updated

### Tables
- `user` - User accounts (created if not exists)
- `forum_post` - Forum posts with REAL importance scoring
- `forum_reply` - Forum replies with image support  

### Indexes (for performance)
- `idx_forum_post_author` - Posts by author
- `idx_forum_post_importance_created` - Posts sorted by importance and date
- `idx_forum_reply_post` - Replies by post
- `idx_forum_reply_author` - Replies by author  
- `idx_user_username` - User lookup by username

### Demo Data
- **Demo User**: username=`demo`, password=`1`
- **Welcome Post**: Introductory forum post (only if no posts exist)

## Data Migration

### Importance Column Update
If you have existing forum_post data with INTEGER importance, the scripts will:
1. Convert INTEGER importance values to REAL (decimal)
2. Preserve all existing data
3. Update the column definition for future decimal precision

### Backward Compatibility
- All existing data is preserved
- New installations work immediately
- Existing installations are upgraded seamlessly

## Verification

After running either script, you can verify success:

```sql
-- Check tables exist
SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE 'forum%' OR name = 'user');

-- Verify demo user
SELECT id, username, email FROM user WHERE username = 'demo';

-- Check importance column type
PRAGMA table_info(forum_post);

-- Count data
SELECT 
    (SELECT COUNT(*) FROM user) as users,
    (SELECT COUNT(*) FROM forum_post) as posts,
    (SELECT COUNT(*) FROM forum_reply) as replies;
```

## Troubleshooting

### Python Script Issues
- Check Python 3 is installed: `python3 --version`
- Ensure database directory exists and is writable
- Check the generated log file: `upgrade_1.0.1.log`

### SQL Script Issues  
- Ensure SQLite3 is available: `sqlite3 --version`
- Verify database file path is correct
- Check database file permissions

### Backup and Recovery
The Python script automatically creates backups with format:
```
accounts.db.backup_YYYYMMDD_HHMMSS
```

To restore from backup if needed:
```bash
cp accounts.db.backup_YYYYMMDD_HHMMSS accounts.db
```

## Manual Installation (Alternative)

If you prefer to set up manually, the key components are:

1. **Create tables** using the SQL schema in `upgrade_to_1.0.1.sql`
2. **Add demo user**: INSERT INTO user VALUES (0, 'demo', '1', 'demo@example.com')
3. **Update app.py**: Ensure forum redirects are configured
4. **Update frontend**: Ensure error handling is implemented

## Support

- Check the main repository for issues: https://github.com/luozhijian/TesseractOcrTraining
- Review logs for detailed error information
- Ensure all dependencies are installed

## Version History

- **1.0.1**: Forum functionality, demo user, decimal importance, performance improvements
- **1.0.0**: Base OCR training functionality

---

**Note**: Always backup your database before upgrading in production environments!
