"""Configuration loader for the Amazon Smart Shopping Assistant.

API keys are loaded from .env file (using python-dotenv)
Configuration settings are loaded from config.yaml
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv


class ConfigurationError(RuntimeError):
    """Raised when the application configuration is missing or invalid."""


# Load environment variables from .env file
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.yaml"


def get_api_key(key_name: str) -> str:
    """Get API key from environment variables.
    
    Args:
        key_name: Name of the environment variable (e.g., 'SERP_API_KEY')
        
    Returns:
        API key value
        
    Raises:
        ConfigurationError: If API key is not found or empty
    """
    value = os.getenv(key_name)
    if not value or not value.strip():
        raise ConfigurationError(
            f"API key '{key_name}' not found in environment. "
            f"Please set it in .env file or environment variables."
        )
    return value.strip()


@lru_cache(maxsize=1)
def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load and cache the application configuration from YAML.
    
    Args:
        config_path: Optional path to config file (default: config.yaml)
        
    Returns:
        Dictionary containing all configuration settings
        
    Raises:
        ConfigurationError: If config file is missing or invalid
    """
    target_path = config_path or _DEFAULT_CONFIG_PATH
    if not target_path.exists():
        raise ConfigurationError(f"Configuration file not found at {target_path}")

    with target_path.open("r", encoding="utf-8") as stream:
        raw = yaml.safe_load(stream) or {}

    if not isinstance(raw, dict):
        raise ConfigurationError("Configuration file must contain a mapping at the top level.")

    return raw


def get_config_value(key_path: str, default: Any = None) -> Any:
    """Get configuration value by dot-separated path.
    
    Args:
        key_path: Dot-separated path (e.g., 'models.gemini.temperature')
        default: Default value if key not found
        
    Returns:
        Configuration value or default
        
    Example:
        >>> get_config_value('models.gemini.temperature')
        0.1
        >>> get_config_value('models.provider')
        'gemini'
    """
    config = load_config()
    keys = key_path.split('.')
    value = config
    
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
            if value is None:
                return default
        else:
            return default
    
    return value


# Backward compatibility type (deprecated - use load_config() dict directly)
AppConfig = Dict[str, Any]


__all__ = [
    "ConfigurationError",
    "get_api_key", 
    "load_config",
    "get_config_value",
    "AppConfig",
]
