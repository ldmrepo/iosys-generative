"""
IML file reader with encoding auto-detection.

Korean IML files may be encoded in EUC-KR, CP949, or UTF-8.
This module tries multiple encodings to read the file correctly.
"""
import os
from typing import Optional


ENCODINGS = ['euc-kr', 'cp949', 'utf-8', 'utf-8-sig']


def read_iml_file(path: str) -> str:
    """
    Read an IML file with automatic encoding detection.

    Args:
        path: Full path to the IML file

    Returns:
        File contents as a string

    Raises:
        FileNotFoundError: If the file does not exist
        ValueError: If the file cannot be decoded with any known encoding
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"IML file not found: {path}")

    with open(path, 'rb') as f:
        raw_bytes = f.read()

    # Try each encoding
    for encoding in ENCODINGS:
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue

    # Last resort: decode with replacement characters
    return raw_bytes.decode('utf-8', errors='replace')


def find_iml_file(base_path: str, source_file: str) -> Optional[str]:
    """
    Find the full path to an IML file.

    The source_file from the database may be:
    - An absolute path
    - A relative path from the data directory

    Args:
        base_path: Base directory for IML data
        source_file: Source file path from database

    Returns:
        Full path to the IML file, or None if not found
    """
    # If source_file is absolute and exists, use it
    if os.path.isabs(source_file) and os.path.exists(source_file):
        return source_file

    # Try combining with base path
    full_path = os.path.join(base_path, source_file)
    if os.path.exists(full_path):
        return full_path

    # Try stripping leading directory components that might be duplicated
    # e.g., if source_file is "poc/data/file.iml" but base_path already ends in "poc"
    parts = source_file.replace('\\', '/').split('/')
    for i in range(len(parts)):
        partial = os.path.join(base_path, *parts[i:])
        if os.path.exists(partial):
            return partial

    return None
