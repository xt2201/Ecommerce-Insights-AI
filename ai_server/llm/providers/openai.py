"""OpenAI LLM Provider."""

from __future__ import annotations

import logging
from typing import Any, Optional

from langchain_openai import ChatOpenAI

from ai_server.core.config import get_api_key, get_config_value

logger = logging.getLogger(__name__)


def get_openai_llm(
    agent_name: Optional[str] = None,
    use_fallback_config: bool = False
) -> ChatOpenAI:
    """Get OpenAI LLM instance.
    
    Args:
        agent_name: Agent name for agent-specific config
        use_fallback_config: If True, use llm_fallback.openai config instead of agent config
    
    Returns:
        LangChain ChatOpenAI instance
        
    Raises:
        ValueError: If required configuration is missing
    """
    # Get OpenAI API key from environment
    api_key = get_api_key("OPENAI_API_KEY")
    
    # Get model settings from config
    if use_fallback_config:
        # Use llm_fallback.openai config
        config_prefix = "llm_fallback.openai"
        logger.info(f"Creating OpenAI LLM for fallback: using {config_prefix} config")
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
            f"Add: {config_prefix}.model_name: 'gpt-4o-mini'"
        )
    if temperature is None:
        temperature = 0.1  # Default fallback
    
    # Set defaults for optional settings
    if not max_tokens:
        max_tokens = 4000
    
    if use_fallback_config:
        logger.info(
            f"Creating OpenAI LLM for fallback: "
            f"{model_name}, temp={temperature}, max_tokens={max_tokens}"
        )
    else:
        logger.info(
            f"Creating OpenAI LLM for {agent_name}: "
            f"{model_name}, temp={temperature}, max_tokens={max_tokens}"
        )
    
    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key,
    )
