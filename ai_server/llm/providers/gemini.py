"""Gemini LLM Provider."""

from __future__ import annotations

import logging
from typing import Any, Optional

from langchain_google_genai import ChatGoogleGenerativeAI

from ai_server.core.config import get_api_key, get_config_value

logger = logging.getLogger(__name__)


def get_gemini_llm(
    agent_name: Optional[str] = None,
    use_fallback_config: bool = False
) -> ChatGoogleGenerativeAI:
    """Get Gemini LLM instance.
    
    Args:
        agent_name: Agent name for agent-specific config
        use_fallback_config: If True, use llm_fallback.gemini config instead of agent config
    
    Returns:
        LangChain ChatGoogleGenerativeAI instance
        
    Raises:
        ValueError: If required configuration is missing
    """
    # Get Gemini API key from environment
    api_key = get_api_key("GEMINI_API_KEY")
    
    # Get model settings from config
    if use_fallback_config:
        # Use llm_fallback.gemini config
        config_prefix = "llm_fallback.gemini"
        logger.info(f"Creating Gemini LLM for fallback: using {config_prefix} config")
    else:
        # Use agent-specific config (REQUIRED)
        config_prefix = f"agents.{agent_name}"
    
    model_name = get_config_value(f"{config_prefix}.model_name")
    temperature = get_config_value(f"{config_prefix}.temperature")
    max_tokens = get_config_value(f"{config_prefix}.max_tokens")
    convert_system = get_config_value(f"{config_prefix}.convert_system_message_to_human")
    
    # Validate required settings
    if not model_name:
        raise ValueError(
            f"Missing 'model_name' in {config_prefix} config.yaml.\n"
            f"Add: {config_prefix}.model_name: 'gemini-2.0-flash-exp'"
        )
    if temperature is None:
        temperature = 0.1  # Default fallback
    
    # Set defaults for optional settings
    if not max_tokens:
        max_tokens = 8000
    if convert_system is None:
        convert_system = True
    
    if use_fallback_config:
        logger.info(
            f"Creating Gemini LLM for fallback: "
            f"{model_name}, temp={temperature}, max_tokens={max_tokens}"
        )
    else:
        logger.info(
            f"Creating Gemini LLM for {agent_name}: "
            f"{model_name}, temp={temperature}, max_tokens={max_tokens}"
        )
    
    return ChatGoogleGenerativeAI(
        model=model_name,
        api_key=api_key,  # type: ignore
        temperature=temperature,
        max_tokens=max_tokens,  # type: ignore
        convert_system_message_to_human=convert_system
    )


__all__ = ["get_gemini_llm"]
