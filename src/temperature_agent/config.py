"""
Configuration loading for the temperature agent.

Provides a centralized way to load config.json from the project root.
"""

import json
import os
import collections
from functools import lru_cache
from pathlib import Path


def find_project_root() -> Path:
    """Find the project root directory (where config.json lives)."""
    # Start from this file's directory and walk up
    current = Path(__file__).resolve().parent
    
    # Walk up until we find config.json or hit the filesystem root
    for _ in range(10):  # Safety limit
        if (current / "config.json").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    
    # Fallback: try common locations
    # From src/temperature_agent/config.py, root is 2 levels up
    fallback = Path(__file__).resolve().parent.parent.parent
    if (fallback / "config.json").exists():
        return fallback
    
    raise FileNotFoundError("Could not find config.json in project hierarchy")


@lru_cache(maxsize=1)
def get_config() -> dict:
    """
    Load configuration from config.json.
    
    Returns:
        dict: The configuration dictionary
        
    Raises:
        FileNotFoundError: If config.json is not found
        json.JSONDecodeError: If config.json is invalid
    """
    project_root = find_project_root()
    config_path = project_root / "config.json"
    
    with open(config_path, 'r') as f:
        return json.load(f, object_pairs_hook=collections.OrderedDict)


def get_project_root() -> Path:
    """Get the project root directory."""
    return find_project_root()


def reload_config() -> dict:
    """Force reload of configuration (clears cache)."""
    get_config.cache_clear()
    return get_config()
