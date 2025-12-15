"""
Domain Knowledge Provider - LLM Context
Provides domain knowledge (categories, brands, etc.) as context for LLM prompts.

This module loads knowledge from keywords.yaml and formats it for LLM consumption.
NO regex, NO keyword matching - only provides context for LLM prompts.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml

logger = logging.getLogger(__name__)

# Module-level cache
_domain_knowledge: Optional['DomainKnowledge'] = None


def get_domain_knowledge() -> 'DomainKnowledge':
    """Get singleton DomainKnowledge instance."""
    global _domain_knowledge
    if _domain_knowledge is None:
        _domain_knowledge = DomainKnowledge()
    return _domain_knowledge


class DomainKnowledge:
    """
    Domain knowledge provider for LLM prompts.
    
    Loads knowledge from keywords.yaml and provides formatted context
    for LLM to use in classification and extraction tasks.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Load domain knowledge from YAML file."""
        if config_path is None:
            config_path = Path(__file__).parent / "keywords.yaml"
        
        self._data: Dict[str, Any] = {}
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._data = yaml.safe_load(f) or {}
            logger.info(f"DomainKnowledge: Loaded from {config_path}")
        except Exception as e:
            logger.warning(f"DomainKnowledge: Failed to load {config_path}: {e}")
            self._data = {}
    
    # ===== Context Providers for LLM Prompts =====
    
    def get_categories_context(self) -> str:
        """Get product categories as context for LLM."""
        categories = self._data.get('categories', {})
        if not categories:
            return "Available categories: clothing, electronics, shoes, accessories"
        
        lines = ["Available product categories:"]
        for cat_name, keywords in categories.items():
            if isinstance(keywords, list):
                examples = ", ".join(keywords[:5])
                lines.append(f"- {cat_name}: includes {examples}")
            else:
                lines.append(f"- {cat_name}")
        
        return "\n".join(lines)
    
    def get_brands_context(self) -> str:
        """Get known brands as context for LLM."""
        brands = self._data.get('brands', [])
        if not brands:
            return "Common brands: Nike, Adidas, Apple, Samsung, Zara, H&M"
        
        return f"Known brands: {', '.join(brands[:30])}"
    
    def get_styles_context(self) -> str:
        """Get fashion styles as context for LLM."""
        styles = self._data.get('styles', {})
        if not styles:
            return "Fashion styles: casual, formal, sporty, streetwear"
        
        lines = ["Fashion styles:"]
        for style_name, keywords in styles.items():
            if isinstance(keywords, list):
                aliases = ", ".join(keywords[:3])
                lines.append(f"- {style_name} (also: {aliases})")
            else:
                lines.append(f"- {style_name}")
        
        return "\n".join(lines)
    
    def get_intents_context(self) -> str:
        """Get intent examples as context for LLM."""
        intents = self._data.get('intents', {})
        if not intents:
            return ""
        
        lines = ["Intent examples:"]
        for intent_name, examples in intents.items():
            if isinstance(examples, list) and examples:
                ex_str = ", ".join(f'"{e}"' for e in examples[:3])
                lines.append(f"- {intent_name}: {ex_str}")
        
        return "\n".join(lines)
    
    def get_full_context(self) -> str:
        """Get all domain knowledge as context for LLM."""
        parts = [
            self.get_categories_context(),
            self.get_brands_context(),
            self.get_styles_context(),
        ]
        return "\n\n".join(p for p in parts if p)
    
    # ===== Raw Data Access =====
    
    def get_categories(self) -> Dict[str, List[str]]:
        """Get raw categories dictionary."""
        return self._data.get('categories', {})
    
    def get_brands(self) -> List[str]:
        """Get raw brands list."""
        return self._data.get('brands', [])
    
    def get_styles(self) -> Dict[str, List[str]]:
        """Get raw styles dictionary."""
        return self._data.get('styles', {})
    
    def get_intents(self) -> Dict[str, List[str]]:
        """Get raw intents dictionary."""
        return self._data.get('intents', {})
    
    def get_raw_data(self) -> Dict[str, Any]:
        """Get all raw data."""
        return self._data.copy()


# Legacy compatibility - these will be deprecated
def get_keywords_manager() -> DomainKnowledge:
    """Legacy alias for get_domain_knowledge."""
    logger.warning("get_keywords_manager is deprecated, use get_domain_knowledge instead")
    return get_domain_knowledge()


class KeywordsManager(DomainKnowledge):
    """Legacy alias for DomainKnowledge."""
    pass
