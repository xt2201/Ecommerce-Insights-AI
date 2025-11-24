"""LLM Factory - Centralized LLM management across agents.

This module provides a factory function to get LLM instances configured
for specific agents based on the config.yaml file.

Features:
- Automatic fallback between providers on errors (rate limits, API failures)
- Agent-specific LLM configurations
- Support for multiple providers (Cerebras, Gemini)
"""

from __future__ import annotations

import logging
from typing import Any, Optional, List

from ai_server.core.config import get_config_value
from ai_server.llm.providers import get_cerebras_llm, get_gemini_llm, get_openai_llm
from ai_server.llm.fallback_llm import FallbackLLM

logger = logging.getLogger(__name__)


def get_llm(agent_name: Optional[str] = None, enable_fallback: bool = True) -> Any:
    """Get LLM instance with automatic fallback on errors.
    
    When enable_fallback=True (default), returns FallbackLLM that automatically
    switches providers on rate limits or API errors.
    
    Fallback order (configurable per agent):
    1. Primary provider (from config)
    2. Fallback providers from llm_fallback config
    
    Supports:
    - cerebras: Cerebras AI (fast inference)
    - gemini: Google Gemini
    - openai: OpenAI (GPT models)
    
    Args:
        agent_name: Agent name for agent-specific config (REQUIRED)
                   (e.g., 'planning', 'collection', 'analysis', 'response', 'router')
        enable_fallback: Enable automatic provider fallback (default: True)
    
    Returns:
        LangChain LLM instance (FallbackLLM if enable_fallback=True)
        
    Raises:
        ValueError: If agent_name is not provided or agent has no provider configured
    """
    if not agent_name:
        raise ValueError(
            "agent_name is required. Each agent must specify its provider in config.yaml.\n"
            "Example: get_llm(agent_name='planning')"
        )
    
    # Get agent-specific provider (REQUIRED)
    provider = get_config_value(f"agents.{agent_name}.provider")
    
    if not provider:
        raise ValueError(
            f"Agent '{agent_name}' does not have a provider configured.\n"
            f"Please add 'provider' to agents.{agent_name} section in config.yaml.\n"
            f"Example:\n"
            f"  agents:\n"
            f"    {agent_name}:\n"
            f"      provider: 'gemini'  # or 'cerebras'\n"
            f"      model_name: 'gemini-2.0-flash-exp'\n"
            f"      temperature: 0.1"
        )
    
    provider = provider.lower()
    logger.info(f"Agent '{agent_name}' using provider: {provider}")
    
    # Get primary LLM
    if provider == "cerebras":
        primary_llm = get_cerebras_llm(agent_name)
    elif provider == "gemini":
        primary_llm = get_gemini_llm(agent_name)
    elif provider == "openai":
        primary_llm = get_openai_llm(agent_name)
    else:
        raise ValueError(
            f"Unknown provider '{provider}' for agent '{agent_name}'.\n"
            f"Supported providers: 'cerebras', 'gemini', 'openai'"
        )
    
    # Return without fallback if disabled
    if not enable_fallback:
        return primary_llm
    
    # Build fallback list using llm_fallback config
    fallback_llms: List[Any] = []
    
    # Get available fallback providers from config
    fallback_config = get_config_value("llm_fallback")
    
    if not fallback_config:
        logger.warning(
            f"Agent '{agent_name}' fallback enabled but no llm_fallback config found. "
            f"Add llm_fallback section to config.yaml"
        )
        return primary_llm
    
    # Get configured fallback providers (use all available except primary)
    # Get configured fallback providers (use all available)
    available_fallbacks = []
    
    # Prioritize Cerebras fallback (try different key/model within Cerebras first)
    if "cerebras" in fallback_config:
        available_fallbacks.append("cerebras")
        
    if "gemini" in fallback_config and provider != "gemini":
        available_fallbacks.append("gemini")
        
    if "openai" in fallback_config and provider != "openai":
        available_fallbacks.append("openai")
    
    # Build fallback LLMs using llm_fallback config
    for fallback_provider in available_fallbacks:
        try:
            if fallback_provider == "cerebras":
                fallback_llm = get_cerebras_llm(agent_name=None, use_fallback_config=True)
                fallback_llms.append(fallback_llm)
            elif fallback_provider == "gemini":
                fallback_llm = get_gemini_llm(agent_name=None, use_fallback_config=True)
                fallback_llms.append(fallback_llm)
            elif fallback_provider == "openai":
                fallback_llm = get_openai_llm(agent_name=None, use_fallback_config=True)
                fallback_llms.append(fallback_llm)
        except Exception as e:
            logger.warning(f"Failed to initialize {fallback_provider} fallback: {e}")
    
    # Return FallbackLLM with automatic provider switching
    if fallback_llms:
        logger.info(
            f"Agent '{agent_name}' configured with {len(fallback_llms)} fallback provider(s): "
            f"{', '.join(available_fallbacks)}"
        )
        return FallbackLLM(primary_llm=primary_llm, fallback_llms=fallback_llms)
    else:
        logger.warning(
            f"Agent '{agent_name}' has no fallback providers available, "
            f"using primary provider only"
        )
        return primary_llm


__all__ = ["get_llm"]
