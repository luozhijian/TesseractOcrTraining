# Username Validation for Cross-Platform Directory Safety

## Overview

This guide explains why username validation is crucial when usernames are used as directory names in cross-platform applications, and details the reserved names that must be avoided on Windows and Linux systems.

## Why Username Validation Matters

When your application creates user-specific directories (like `/files/username/`), the username becomes part of the file system path. Invalid usernames can cause:

1. **File system errors** - Some names are reserved by the OS
2. **Security vulnerabilities** - Path traversal attacks
3. **Command line issues** - Special characters breaking shell commands
4. **Cross-platform incompatibility** - Different restrictions on Windows vs Linux

## Windows Reserved Names

### Device Names (Always Reserved)
Windows reserves these names regardless of extension:

- **`CON`** - Console input/output
- **`PRN`** - Default printer  
- **`AUX`** - Auxiliary device
- **`NUL`** - Null device

### Communication Ports
- **`COM1` to `COM9`** - Serial communication ports
- **`LPT1` to `LPT9`** - Parallel ports (Line Printer)

### Examples of Problems
```
CON.txt     ❌ Reserved (Windows treats as CON device)
con         ❌ Reserved (case-insensitive)
COM1.dat    ❌ Reserved (extension ignored)
```

## Linux Reserved/Problematic Names

### System Users
Common system accounts that should be avoided:
- **`root`** - System administrator
- **`daemon`, `bin`, `sys`** - System service accounts
- **`mail`, `www`, `ftp`** - Service-specific accounts
- **`nobody`** - Unprivileged user account

### System Directories
Critical system directories:
- **`home`, `tmp`, `var`, `etc`** - Core system directories
- **`usr`, `bin`, `sbin`** - System binaries
- **`dev`, `proc`, `sys`** - Virtual file systems
- **`boot`, `lib`, `opt`** - System components

### Device Files
Virtual device files from `/dev/`:
- **`null`, `zero`, `random`** - Special devices
- **`stdin`, `stdout`, `stderr`** - Standard I/O streams
- **`tty`, `console`** - Terminal devices

### Service Accounts
Common service usernames to avoid:
- **`apache`, `nginx`** - Web servers
- **`mysql`, `postgres`** - Databases  
- **`git`, `svn`** - Version control
- **`docker`, `jenkins`** - DevOps tools

## Character Restrictions

### Invalid Characters (Both Platforms)
```
< > : " | ? * \ /     ❌ Windows filesystem restrictions
Control characters    ❌ ASCII 0-31 (including \0, \t, \n)
```

### Path Safety Rules
```
..            ❌ Path traversal  
.username     ❌ Hidden file/directory
username.     ❌ Ends with dot
user name     ❌ Contains space
 username     ❌ Leading/trailing whitespace
```

## Validation Rules Implemented

Our `username_isvalid()` function enforces:

1. **Length**: 1-30 characters
2. **Character set**: Only `a-z`, `A-Z`, `0-9`, `_`, `-`
3. **Start character**: Must be alphanumeric (not `_` or `-`)
4. **No reserved names**: Windows + Linux + application-specific
5. **No path traversal**: No `..`, leading/trailing dots
6. **No spaces**: Safer for command line operations
7. **No control characters**: No tabs, newlines, null bytes

## Safe Username Examples

✅ **Valid usernames:**
```
user1
john_doe
alice-smith
test123
ValidUser2024
a1b2c3
```

❌ **Invalid usernames:**
```
con           (Windows reserved)
root          (Linux system user)
user name     (contains space)
.user         (starts with dot)
_user         (starts with underscore)
user/path     (contains slash)
COM1          (Windows reserved)
null          (Linux device)
```

## Implementation Benefits

By implementing this validation:

1. **Cross-platform compatibility** - Works on both Windows and Linux
2. **Security** - Prevents path traversal and injection attacks
3. **Reliability** - Avoids file system conflicts and errors
4. **Maintainability** - Consistent naming reduces support issues
5. **User experience** - Clear error messages for invalid usernames

## Error Handling

When validation fails, users receive a helpful message:
```
"Invalid username. Use only letters, numbers, hyphens, and underscores. Must start with letter/number."
```

This guides users toward creating valid usernames without exposing security details.

## Testing

Run the included test script to verify validation:
```bash
python test_username_validation.py
```

The test covers 100+ edge cases including all reserved names, invalid characters, and boundary conditions.



