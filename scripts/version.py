# -*- coding: utf-8 -*-
"""
Version information for Tesseract OCR Training application
"""

__version__ = "1.0.1"
__version_info__ = (1, 0, 1)

# Version details
VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION_PATCH = 1

# Build and release information
RELEASE_NAME = "Forum Edition"
BUILD_DATE = "2025-01-11"

def get_version():
    """Return the version string"""
    return __version__

def get_version_info():
    """Return version as tuple (major, minor, patch)"""
    return __version_info__

def get_full_version_info():
    """Return detailed version information"""
    return {
        "version": __version__,
        "version_tuple": __version_info__,
        "release_name": RELEASE_NAME,
        "build_date": BUILD_DATE,
        "major": VERSION_MAJOR,
        "minor": VERSION_MINOR,
        "patch": VERSION_PATCH
    }

