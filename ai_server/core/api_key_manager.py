"""API Key Manager with Rotation Support.

Simple and practical API key rotation for services with multiple keys.
Reads directly from .env file without complex abstractions.

Usage:
    from ai_server.core.api_key_manager import get_cerebras_key, get_serp_key
    
    # Auto-rotates between available keys
    key = get_cerebras_key()
"""

from __future__ import annotations

import os
import logging
import threading
from typing import List, Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Ensure .env is loaded
try:
    from dotenv import load_dotenv
    
    # Try multiple locations
    for env_path in [Path(".env"), Path(__file__).parents[2] / ".env"]:
        if env_path.exists():
            load_dotenv(env_path)
            logger.debug(f"Loaded .env from {env_path}")
            break
except ImportError:
    logger.warning("python-dotenv not installed")


@dataclass
class KeyStatus:
    """Track status of an API key."""
    key: str
    env_var: str
    last_used: Optional[datetime] = None
    error_count: int = 0
    last_error: Optional[datetime] = None
    is_exhausted: bool = False  # For rate-limited keys
    
    def mark_used(self):
        self.last_used = datetime.now()
    
    def mark_error(self):
        self.error_count += 1
        self.last_error = datetime.now()
    
    def reset_errors(self):
        self.error_count = 0
        self.last_error = None
        self.is_exhausted = False


class APIKeyRotator:
    """Manages rotation between multiple API keys.
    
    Features:
    - Round-robin rotation
    - Tracks errors per key
    - Skips exhausted/rate-limited keys
    - Thread-safe
    """
    
    def __init__(
        self,
        key_prefix: str,
        key_variants: Optional[List[str]] = None,
        max_errors_before_skip: int = 3,
        error_reset_minutes: int = 60
    ):
        """Initialize key rotator.
        
        Args:
            key_prefix: Base name like 'CEREBRAS_API_KEY'
            key_variants: List of suffixes like ['', '1', '2', '3'] 
                         None = auto-detect from env
            max_errors_before_skip: Skip key after this many consecutive errors
            error_reset_minutes: Reset error count after this many minutes
        """
        self._prefix = key_prefix
        self._max_errors = max_errors_before_skip
        self._error_reset = timedelta(minutes=error_reset_minutes)
        self._lock = threading.Lock()
        self._current_index = 0
        
        # Load keys
        self._keys: List[KeyStatus] = []
        self._load_keys(key_variants)
        
        if not self._keys:
            logger.warning(f"No API keys found for {key_prefix}")
    
    def _load_keys(self, variants: Optional[List[str]] = None):
        """Load API keys from environment."""
        if variants is None:
            # Auto-detect: try base key and numbered variants
            variants = [''] + [str(i) for i in range(1, 20)]
        
        for suffix in variants:
            env_var = f"{self._prefix}{suffix}"
            value = os.getenv(env_var)
            
            if value and value.strip():
                self._keys.append(KeyStatus(
                    key=value.strip(),
                    env_var=env_var
                ))
                logger.debug(f"Loaded key: {env_var}")
    
    def get_key(self) -> Optional[str]:
        """Get next available API key using round-robin.
        
        Returns:
            API key string or None if no keys available
        """
        with self._lock:
            if not self._keys:
                return None
            
            # Reset old errors
            now = datetime.now()
            for key_status in self._keys:
                if (key_status.last_error and 
                    now - key_status.last_error > self._error_reset):
                    key_status.reset_errors()
            
            # Find next available key
            attempts = 0
            while attempts < len(self._keys):
                idx = self._current_index % len(self._keys)
                self._current_index += 1
                
                key_status = self._keys[idx]
                
                # Skip if too many errors
                if key_status.error_count >= self._max_errors:
                    logger.debug(f"Skipping {key_status.env_var}: too many errors")
                    attempts += 1
                    continue
                
                # Skip if marked exhausted
                if key_status.is_exhausted:
                    logger.debug(f"Skipping {key_status.env_var}: exhausted")
                    attempts += 1
                    continue
                
                key_status.mark_used()
                return key_status.key
            
            # All keys have errors, try first one anyway
            logger.warning(f"All {self._prefix} keys have errors, using first key")
            self._keys[0].reset_errors()
            self._keys[0].mark_used()
            return self._keys[0].key
    
    def report_error(self, key: str, is_rate_limit: bool = False):
        """Report an error for a specific key.
        
        Args:
            key: The API key that had an error
            is_rate_limit: True if this was a rate limit error
        """
        with self._lock:
            for key_status in self._keys:
                if key_status.key == key:
                    key_status.mark_error()
                    if is_rate_limit:
                        key_status.is_exhausted = True
                        logger.info(f"Marked {key_status.env_var} as rate-limited")
                    break
    
    def report_success(self, key: str):
        """Report successful use of a key (resets error count)."""
        with self._lock:
            for key_status in self._keys:
                if key_status.key == key:
                    key_status.reset_errors()
                    break
    
    @property
    def available_count(self) -> int:
        """Number of available (non-exhausted) keys."""
        return sum(
            1 for k in self._keys 
            if k.error_count < self._max_errors and not k.is_exhausted
        )
    
    @property
    def total_count(self) -> int:
        """Total number of configured keys."""
        return len(self._keys)
    
    def get_stats(self) -> Dict:
        """Get statistics about key usage."""
        return {
            "total": self.total_count,
            "available": self.available_count,
            "keys": [
                {
                    "env_var": k.env_var,
                    "error_count": k.error_count,
                    "is_exhausted": k.is_exhausted,
                    "last_used": k.last_used.isoformat() if k.last_used else None
                }
                for k in self._keys
            ]
        }


# ============== Global Rotators ==============

# Cerebras has multiple keys (CEREBRAS_API_KEY, CEREBRAS_API_KEY1, ..., CEREBRAS_API_KEY6)
_cerebras_rotator: Optional[APIKeyRotator] = None

# SerpAPI has 2 keys (SERP_API_KEY, SERP_API_KEY2)
_serp_rotator: Optional[APIKeyRotator] = None


def _get_cerebras_rotator() -> APIKeyRotator:
    """Get or create Cerebras key rotator."""
    global _cerebras_rotator
    if _cerebras_rotator is None:
        _cerebras_rotator = APIKeyRotator(
            key_prefix="CEREBRAS_API_KEY",
            key_variants=['', '1', '2', '3', '4', '5', '6'],  # Match your .env
            max_errors_before_skip=3,
            error_reset_minutes=30  # Reset after 30 minutes
        )
        logger.info(f"Cerebras rotator initialized with {_cerebras_rotator.total_count} keys")
    return _cerebras_rotator


def _get_serp_rotator() -> APIKeyRotator:
    """Get or create SerpAPI key rotator."""
    global _serp_rotator
    if _serp_rotator is None:
        _serp_rotator = APIKeyRotator(
            key_prefix="SERP_API_KEY",
            key_variants=['', '2'],  # SERP_API_KEY and SERP_API_KEY2
            max_errors_before_skip=2,
            error_reset_minutes=60
        )
        logger.info(f"SerpAPI rotator initialized with {_serp_rotator.total_count} keys")
    return _serp_rotator


# ============== Public API ==============

def get_cerebras_key() -> str:
    """Get next available Cerebras API key.
    
    Returns:
        API key string
        
    Raises:
        ValueError: If no keys configured
    """
    key = _get_cerebras_rotator().get_key()
    if not key:
        raise ValueError(
            "No CEREBRAS_API_KEY found. "
            "Please set CEREBRAS_API_KEY in your .env file."
        )
    return key


def get_serp_key() -> str:
    """Get next available SerpAPI key.
    
    Returns:
        API key string
        
    Raises:
        ValueError: If no keys configured
    """
    key = _get_serp_rotator().get_key()
    if not key:
        raise ValueError(
            "No SERP_API_KEY found. "
            "Please set SERP_API_KEY in your .env file."
        )
    return key


def report_cerebras_error(key: str, is_rate_limit: bool = False):
    """Report error for a Cerebras key."""
    _get_cerebras_rotator().report_error(key, is_rate_limit)


def report_cerebras_success(key: str):
    """Report successful use of a Cerebras key."""
    _get_cerebras_rotator().report_success(key)


def report_serp_error(key: str, is_rate_limit: bool = False):
    """Report error for a SerpAPI key."""
    _get_serp_rotator().report_error(key, is_rate_limit)


def report_serp_success(key: str):
    """Report successful use of a SerpAPI key."""
    _get_serp_rotator().report_success(key)


def get_key_stats() -> Dict:
    """Get statistics for all key rotators."""
    return {
        "cerebras": _get_cerebras_rotator().get_stats(),
        "serpapi": _get_serp_rotator().get_stats()
    }


# Simple getters for non-rotated keys
def get_api_key(key_name: str) -> str:
    """Get a single API key from environment.
    
    For keys with rotation (CEREBRAS, SERP), use the specific getters.
    This is for single-key services like GEMINI, OPENAI, LANGSMITH.
    
    Args:
        key_name: Environment variable name
        
    Returns:
        API key value
        
    Raises:
        ValueError: If key not found
    """
    value = os.getenv(key_name)
    if not value or not value.strip():
        raise ValueError(
            f"API key '{key_name}' not found. "
            f"Please set it in your .env file."
        )
    return value.strip()
