"""
AI Server Configuration Module
Exports all configuration utilities.

LLM-Only Architecture:
- DomainKnowledge: Provides context for LLM prompts
- Constants: Configuration values (no rule-based logic)
"""
from ai_server.config.constants import (
    IntentConfig,
    ClarificationConfig,
    SearchConfig,
    CircuitBreakerConfig,
    ProductContextConfig,
    ResponseConfig,
)
from ai_server.config.keywords_loader import (
    DomainKnowledge,
    get_domain_knowledge,
    # Legacy aliases - deprecated
    KeywordsManager,
    get_keywords_manager,
)

__all__ = [
    # Constants
    'IntentConfig',
    'ClarificationConfig',
    'SearchConfig',
    'CircuitBreakerConfig',
    'ProductContextConfig',
    'ResponseConfig',
    # Domain Knowledge (LLM Context)
    'DomainKnowledge',
    'get_domain_knowledge',
    # Legacy (deprecated)
    'KeywordsManager',
    'get_keywords_manager',
]
