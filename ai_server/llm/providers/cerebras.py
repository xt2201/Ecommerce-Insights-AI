"""Cerebras LLM Provider."""

from __future__ import annotations

import logging
from typing import Any, Optional

from langchain_cerebras import ChatCerebras

from ai_server.core.config import get_api_key, get_config_value

logger = logging.getLogger(__name__)


def get_cerebras_llm(
    agent_name: Optional[str] = None, 
    use_fallback_config: bool = False
) -> Any:
    """Get Cerebras LLM instance.
    
    Args:
        agent_name: Agent name for agent-specific config
        use_fallback_config: If True, use llm_fallback.cerebras config instead of agent config
    
    Returns:
        LangChain ChatCerebras instance
        
    Raises:
        ValueError: If required configuration is missing
        ImportError: If langchain-cerebras is not installed
    """
    # Get Cerebras API key from environment (support multiple keys for rotation)
    import os
    import random
    
    keys = []
    # Check main key
    main_key = os.getenv("CEREBRAS_API_KEY")
    if main_key:
        keys.append(main_key)
        
    # Check numbered keys (1-5)
    for i in range(1, 10):
        key = os.getenv(f"CEREBRAS_API_KEY{i}")
        if key:
            keys.append(key)
            
    if not keys:
        # Fallback to get_api_key which raises error if missing
        api_key = get_api_key("CEREBRAS_API_KEY")
        print("DEBUG: No keys found in pool, using default")
    else:
        api_key = random.choice(keys)
        if len(keys) > 1:
            logger.info(f"Selected Cerebras API Key from pool of {len(keys)} keys")
    
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


__all__ = ["get_cerebras_llm"]
