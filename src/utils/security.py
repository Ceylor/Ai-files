"""
Security utilities for safe filename and path handling.
Prevents path traversal attacks by sanitizing user-provided filenames and directory names.
"""
import re
from pathlib import Path

_FILENAME_RE = re.compile(r'[^\w.\- ]', re.UNICODE)
_CATEGORY_RE = re.compile(r'[^a-zA-Z0-9_\-]', re.UNICODE)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a user-provided filename to prevent path traversal.
    Strips directory components and dangerous characters.
    """
    name = Path(filename).name
    name = _FILENAME_RE.sub('_', name)
    name = name.strip(' .')
    if not name:
        name = "unnamed"
    return name


def sanitize_category(category: str) -> str:
    """
    Sanitize a category name for use as a directory name.
    Only allows alphanumeric, underscore, and hyphen.
    """
    name = _CATEGORY_RE.sub('_', category.strip())
    name = name.strip(' .')
    if not name:
        name = "default"
    return name
