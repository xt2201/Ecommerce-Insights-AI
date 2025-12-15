"""Cerebras LLM Provider with Key Rotation."""

from __future__ import annotations

import logging
from typing import Any, Optional

from langchain_cerebras import ChatCerebras

from ai_server.core.config import get_config_value
from ai_server.core.api_key_manager import (
    get_cerebras_key,
    report_cerebras_error,
    report_cerebras_success
)

logger = logging.getLogger(__name__)

# Track current key for error reporting
_current_key: Optional[str] = None


def get_cerebras_llm(
    agent_name: Optional[str] = None, 
    use_fallback_config: bool = False
) -> Any:
    """Get Cerebras LLM instance with auto-rotating API keys.
    
    Uses the api_key_manager for intelligent key rotation:
    - Round-robin between available keys
    - Skips keys with recent errors
    - Auto-recovery after timeout
    
    Args:
        agent_name: Agent name for agent-specific config
        use_fallback_config: If True, use llm_fallback.cerebras config
    
    Returns:
        LangChain ChatCerebras instance
        
    Raises:
        ValueError: If required configuration is missing
    """
    global _current_key
    
    # Get API key using rotation manager
    api_key = get_cerebras_key()
    _current_key = api_key
    
    # Get model settings from config
    if use_fallback_config:
        # Use llm_fallback.cerebras config
        config_prefix = "llm_fallback.cerebras"
        logger.info(f"Creating Cerebras LLM for fallback: using {config_prefix} config")
    else:
        # Use agent-specific config (REQUIRED)
        config_prefix = f"agents.{agent_name}"
    
    model_name = get_config_value(f"{config_prefix}.model_name")
    temperature = get_config_value(f"{config_prefix}.temperature")
    max_tokens = get_config_value(f"{config_prefix}.max_tokens")
    
    # Validate required settings
    if not model_name:
        raise ValueError(
            f"Missing 'model_name' in {config_prefix} config.yaml.\n"
            f"Add: {config_prefix}.model_name: 'qwen-3-32b'"
        )
    if temperature is None:
        temperature = 0.1  # Default fallback
    
    # Set default for optional settings
    if not max_tokens:
        max_tokens = 8000
    
    if use_fallback_config:
        logger.info(
            f"Creating Cerebras LLM for fallback: "
            f"{model_name}, temp={temperature}, max_tokens={max_tokens}"
        )
    else:
        logger.info(
            f"Creating Cerebras LLM for {agent_name}: "
            f"{model_name}, temp={temperature}, max_tokens={max_tokens}"
        )
    
    # Cerebras reasoning models currently reject "stream=true" when paired with
    # structured outputs (tools_mode JSON schemas). Force streaming off at the
    # client level so downstream `with_structured_output` calls comply.
    return ChatCerebras(
        model=model_name,
        api_key=api_key,  # type: ignore
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=False,
        disable_streaming="tool_calling",
    )


def on_cerebras_error(error: Exception) -> None:
    """Call this when a Cerebras API call fails.
    
    This helps the rotation manager skip problematic keys.
    
    Args:
        error: The exception that occurred
    """
    global _current_key
    if _current_key:
        is_rate_limit = "rate" in str(error).lower() or "429" in str(error)
        report_cerebras_error(_current_key, is_rate_limit=is_rate_limit)
        logger.warning(f"Reported error for Cerebras key: {_current_key[:8]}...")


def on_cerebras_success() -> None:
    """Call this when a Cerebras API call succeeds.
    
    This resets the error count for the current key.
    """
    global _current_key
    if _current_key:
        report_cerebras_success(_current_key)


__all__ = ["get_cerebras_llm", "on_cerebras_error", "on_cerebras_success"]
