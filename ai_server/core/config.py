"""Configuration loader for the Amazon Smart Shopping Assistant.

Simple configuration management:
- API keys from .env file
- Settings from config.yaml
- Key rotation support via api_key_manager
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

# Load .env at module import
try:
    from dotenv import load_dotenv
    
    for env_path in [Path(".env"), Path(__file__).parents[2] / ".env"]:
        if env_path.exists():
            load_dotenv(env_path)
            break
except ImportError:
    pass


class ConfigurationError(RuntimeError):
    """Raised when the application configuration is missing or invalid."""


_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.yaml"

# Lock for config reloading
_config_lock = threading.Lock()
_config_cache: Optional[Dict[str, Any]] = None


def get_api_key(key_name: str) -> str:
    """Get API key from environment.
    
    For keys with rotation (CEREBRAS_API_KEY, SERP_API_KEY), 
    use the api_key_manager module instead.
    
    Args:
        key_name: Name of the environment variable
        
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


def load_config(config_path: Optional[Path] = None, force_reload: bool = False) -> Dict[str, Any]:
    """Load the application configuration from YAML.
    
    Args:
        config_path: Optional path to config file (default: config.yaml)
        force_reload: If True, reload from disk even if cached
        
    Returns:
        Dictionary containing all configuration settings
        
    Raises:
        ConfigurationError: If config file is missing or invalid
    """
    global _config_cache
    
    with _config_lock:
        if _config_cache is not None and not force_reload:
            return _config_cache
        
        target_path = config_path or _DEFAULT_CONFIG_PATH
        if not target_path.exists():
            raise ConfigurationError(f"Configuration file not found at {target_path}")

        with target_path.open("r", encoding="utf-8") as stream:
            raw = yaml.safe_load(stream) or {}

        if not isinstance(raw, dict):
            raise ConfigurationError("Configuration file must contain a mapping at the top level.")

        _config_cache = raw
        return raw


def reload_config() -> Dict[str, Any]:
    """Force reload configuration from disk."""
    return load_config(force_reload=True)


def get_config_value(key_path: str, default: Any = None) -> Any:
    """Get configuration value by dot-separated path.
    
    Args:
        key_path: Dot-separated path (e.g., 'models.gemini.temperature')
        default: Default value if key not found
        
    Returns:
        Configuration value or default
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


# Backward compatibility
AppConfig = Dict[str, Any]


__all__ = [
    "ConfigurationError",
    "get_api_key", 
    "load_config",
    "reload_config",
    "get_config_value",
    "AppConfig",
]
