"""
Translation Service

LLM-powered Vietnamese to English translation with caching.
Replaces hardcoded translation dictionaries.
"""
from __future__ import annotations

import logging
import re
from typing import Dict, Optional
from langchain_core.messages import SystemMessage, HumanMessage

from ai_server.llm.llm_factory import get_llm
from ai_server.utils.prompt_loader import load_prompts_as_dict
from ai_server.utils.logger import get_logger

logger = get_logger(__name__)


class TranslationService:
    """
    LLM-powered translation service with caching.
    
    Provides Vietnamese to English translation for e-commerce terms.
    Uses LLM for accurate context-aware translation.
    """
    
    # Static cache for common terms (bootstrap performance)
    COMMON_TERMS = {
        # Hats
        "nón kết": "baseball cap",
        "nón lưỡi trai": "baseball cap",
        "nón bucket": "bucket hat",
        "nón rộng vành": "wide brim hat",
        "nón": "hat",
        # Clothing
        "áo khoác": "jacket",
        "áo khoác gió": "windbreaker",
        "áo hoodie": "hoodie",
        "áo thun": "t-shirt",
        "áo sơ mi": "shirt",
        "áo": "shirt",
        "quần jeans": "jeans",
        "quần short": "shorts",
        "quần": "pants",
        # Shoes
        "giày thể thao": "sports shoes",
        "giày chạy bộ": "running shoes",
        "giày đi bộ": "walking shoes",
        "giày": "shoes",
        "dép": "sandals",
        # Accessories
        "túi xách": "handbag",
        "ba lô": "backpack",
        "ví": "wallet",
        "thắt lưng": "belt",
        "kính mát": "sunglasses",
        # Descriptors
        "cho nam": "for men",
        "cho nữ": "for women",
        "trẻ em": "for kids",
        "màu trắng": "white",
        "màu đen": "black",
        "màu đỏ": "red",
        "màu xanh": "blue",
    }
    
    # Vietnamese character pattern for detection
    VIETNAMESE_PATTERN = re.compile(
        r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]',
        re.IGNORECASE
    )
    
    def __init__(self):
        self.llm = None  # Lazy load
        self.prompts = None
        self.cache: Dict[str, str] = {}
        
        # Initialize cache with common terms
        self.cache.update(self.COMMON_TERMS)
    
    def _ensure_llm(self):
        """Lazy load LLM and prompts."""
        if self.llm is None:
            self.llm = get_llm(agent_name="manager")
            try:
                self.prompts = load_prompts_as_dict("translation_prompts")
            except Exception as e:
                logger.warning(f"TranslationService: Failed to load prompts: {e}")
                self.prompts = {}
    
    def has_vietnamese(self, text: str) -> bool:
        """Check if text contains Vietnamese characters."""
        return bool(self.VIETNAMESE_PATTERN.search(text))
    
    def translate(self, text: str, category_hint: Optional[str] = None) -> str:
        """
        Translate Vietnamese text to English.
        
        Uses cache first, then LLM for unknown terms.
        
        Args:
            text: Vietnamese text to translate
            category_hint: Product category for context
            
        Returns:
            English translation
        """
        if not text or not text.strip():
            return text
        
        text_lower = text.lower().strip()
        
        # Check cache first
        if text_lower in self.cache:
            logger.debug(f"TranslationService: Cache hit for '{text_lower}'")
            return self.cache[text_lower]
        
        # Check if contains Vietnamese
        if not self.has_vietnamese(text):
            return text
        
        # Try to find partial matches in cache
        for vi_term, en_term in self.COMMON_TERMS.items():
            if vi_term in text_lower:
                # Replace Vietnamese term with English
                result = text_lower.replace(vi_term, en_term)
                return result
        
        # Use LLM for unknown terms
        self._ensure_llm()
        
        try:
            system_prompt = self.prompts.get(
                "system_prompt",
                "Translate the following Vietnamese e-commerce term to English. "
                "Return ONLY the English translation, no explanation."
            )
            
            user_prompt = f"Translate: \"{text}\""
            if category_hint:
                user_prompt += f"\nProduct category context: {category_hint}"
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            translation = response.content.strip()
            
            # Clean response
            if "<think>" in translation:
                translation = translation.split("</think>")[-1].strip()
            
            # Remove quotes if present
            translation = translation.strip('"\'')
            
            # Cache the result
            self.cache[text_lower] = translation
            
            logger.info(f"TranslationService: Translated '{text}' → '{translation}'")
            return translation
            
        except Exception as e:
            logger.error(f"TranslationService: LLM translation failed: {e}")
            return text
    
    def translate_keywords(self, keywords: list) -> list:
        """Translate a list of keywords."""
        return [self.translate(kw) for kw in keywords]
    
    def clear_cache(self):
        """Clear the translation cache (except common terms)."""
        self.cache = dict(self.COMMON_TERMS)


# Singleton instance
_translation_service: Optional[TranslationService] = None


def get_translation_service() -> TranslationService:
    """Get the singleton translation service."""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service
