"""Path utilities for ChatGPT Sidebar."""

import os
import pathlib
from typing import Optional


def get_profile_path() -> pathlib.Path:
    """Get the path to the user profile directory.
    
    Returns:
        pathlib.Path: Path to the profile directory
    """
    appdata = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
    profile_dir = pathlib.Path(appdata) / "ChatGPTSidebar" / "Profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    return profile_dir


def get_cache_path() -> pathlib.Path:
    """Get the path to the cache directory.
    
    Returns:
        pathlib.Path: Path to the cache directory
    """
    profile_dir = get_profile_path()
    cache_dir = profile_dir / "http_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_storage_path() -> pathlib.Path:
    """Get the path to the storage directory.
    
    Returns:
        pathlib.Path: Path to the storage directory
    """
    profile_dir = get_profile_path()
    storage_dir = profile_dir / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir

