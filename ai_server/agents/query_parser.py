"""
Query Parser Module
Extracts structured search parameters from natural language queries.
"""
from __future__ import annotations

import logging
import json
import re
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from ai_server.llm.llm_factory import get_llm
from ai_server.utils.prompt_loader import load_prompts_as_dict

logger = logging.getLogger(__name__)


class SearchPlan(BaseModel):
    """Structured search parameters extracted from user query."""
    keywords: List[str] = Field(description="Search keywords/terms")
    category: Optional[str] = Field(default=None, description="Product category (laptop, phone, etc)")
    price_min: Optional[float] = Field(default=None, description="Minimum price")
    price_max: Optional[float] = Field(default=None, description="Maximum price")
    brands: List[str] = Field(default_factory=list, description="Preferred brands")
    features: List[str] = Field(default_factory=list, description="Required features/specs")
    search_type: Literal["buy", "compare", "research"] = Field(default="buy", description="User's intent")
    sort_by: Optional[str] = Field(default=None, description="Sort preference (price, rating, etc)")
    condition: Optional[str] = Field(default=None, description="Product condition (new, refurbished, used)")


class QueryParser:
    """
    LLM-based query parser that extracts search parameters from natural language.
    Replaces hardcoded search config with dynamic extraction.
    """
    
    def __init__(self):
        self.llm = get_llm(agent_name="manager")  # Reuse manager config
        self.parser = JsonOutputParser()
        try:
            self.prompts = load_prompts_as_dict("query_parser_prompts")
        except Exception:
            self.prompts = {}
    
    def parse(self, query: str, context: Optional[Dict[str, Any]] = None) -> SearchPlan:
        """
        Parse natural language query into structured SearchPlan.
        
        Args:
            query: User's search query
            context: Optional context (user preferences, budget, etc)
            
        Returns:
            SearchPlan with extracted parameters
        """
        logger.info(f"QueryParser: Parsing query: {query}")
        
        # Build context string
        context_str = ""
        if context:
            if context.get("budget"):
                context_str += f"- User budget: ${context.get('budget')}\n"
            if context.get("preferred_brands"):
                context_str += f"- Preferred brands: {', '.join(context.get('preferred_brands', []))}\n"
        
        system_prompt = self._get_system_prompt()
        user_prompt = self._get_user_prompt(query, context_str)
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            content = response.content
            
            # Clean <think> blocks if present
            if "<think>" in content:
                content = content.split("</think>")[-1].strip()
            
            # Parse response
            parsed = self.parser.parse(content)
            
            # Convert to SearchPlan
            keywords = parsed.get("keywords", [query])
            
            # Translate Vietnamese keywords to English for Amazon search
            keywords = self._translate_keywords_if_needed(keywords)
            
            plan = SearchPlan(
                keywords=keywords,
                category=parsed.get("category"),
                price_min=parsed.get("price_min"),
                price_max=parsed.get("price_max"),
                brands=parsed.get("brands", []),
                features=parsed.get("features", []),
                search_type=parsed.get("search_type", "buy"),
                sort_by=parsed.get("sort_by"),
                condition=parsed.get("condition")
            )
            
            logger.info(f"QueryParser: Extracted - keywords={plan.keywords}, category={plan.category}, price_max={plan.price_max}")
            return plan
            
        except Exception as e:
            logger.error(f"QueryParser: LLM parsing failed: {e}. Using fallback.")
            return self._fallback_parse(query)
    
    def _translate_keywords_if_needed(self, keywords: List[str]) -> List[str]:
        """Translate Vietnamese keywords to English for Amazon search."""
        # Check if any keyword contains Vietnamese characters
        vietnamese_pattern = r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]'
        import re
        
        has_vietnamese = any(re.search(vietnamese_pattern, kw.lower()) for kw in keywords)
        if not has_vietnamese:
            return keywords
        
        logger.info(f"QueryParser: Translating Vietnamese keywords: {keywords}")
        
        try:
            prompt = f"""Translate these Vietnamese product keywords to English for Amazon search.
Only output the English translations, comma-separated. No explanation.

Vietnamese: {', '.join(keywords)}
English:"""
            
            response = self.llm.invoke([HumanMessage(content=prompt)])
            translated = response.content.strip()
            
            # Clean <think> blocks if present
            if "<think>" in translated:
                translated = translated.split("</think>")[-1].strip()
            
            # Parse comma-separated translations
            english_keywords = [k.strip() for k in translated.split(',') if k.strip()]
            
            if english_keywords:
                logger.info(f"QueryParser: Translated to English: {english_keywords}")
                return english_keywords
            else:
                return keywords
                
        except Exception as e:
            logger.error(f"QueryParser: Translation failed: {e}")
            return keywords
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for query parser."""
        if "system_prompt" in self.prompts:
            return self.prompts["system_prompt"]
        
        return """You are a Query Parser for an e-commerce shopping assistant.
Your job is to extract structured search parameters from natural language queries.

Output a JSON object with these fields:
{
    "keywords": ["list", "of", "search", "terms"],
    "category": "product category or null",
    "price_min": number or null,
    "price_max": number or null,
    "brands": ["list", "of", "brands"],
    "features": ["required", "features"],
    "search_type": "buy" | "compare" | "research",
    "sort_by": "price" | "rating" | "reviews" | null,
    "condition": "new" | "refurbished" | "used" | null
}

Rules:
1. Extract specific numbers for price constraints
2. Identify brand names mentioned
3. List required features/specs (RAM, storage, screen size, etc)
4. Determine if user wants to buy, compare options, or just research
5. Default search_type to "buy" if unclear
6. Keywords should be optimized for e-commerce search"""
    
    def _get_user_prompt(self, query: str, context_str: str) -> str:
        """Build user prompt."""
        prompt = f"User Query: {query}\n"
        if context_str:
            prompt += f"\nContext:\n{context_str}\n"
        prompt += "\nExtract search parameters. Output valid JSON only."
        return prompt
    
    def _fallback_parse(self, query: str) -> SearchPlan:
        """
        Fallback parser using regex patterns when LLM fails.
        """
        query_lower = query.lower()
        
        # Extract price constraints
        price_max = None
        price_min = None
        
        # Pattern: "under $1000", "below 1000", "less than $500"
        under_match = re.search(r"(?:under|below|less than|up to|max|maximum|<)\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)", query_lower)
        if under_match:
            price_max = float(under_match.group(1).replace(",", ""))
        
        # Pattern: "over $500", "above 500", "more than $300", "at least $200"
        over_match = re.search(r"(?:over|above|more than|at least|min|minimum|>)\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)", query_lower)
        if over_match:
            price_min = float(over_match.group(1).replace(",", ""))
        
        # Pattern: "$500 to $1000", "between $500 and $1000"
        range_match = re.search(r"\$?(\d+(?:,\d{3})*)\s*(?:to|-|and)\s*\$?(\d+(?:,\d{3})*)", query_lower)
        if range_match:
            price_min = float(range_match.group(1).replace(",", ""))
            price_max = float(range_match.group(2).replace(",", ""))
        
        # Extract category (order matters - more specific first)
        category = None
        categories = {
            "headphones": ["headphone", "headphones", "earbuds", "airpods", "earphone", "wireless earbuds"],
            "laptop": ["laptop", "notebook", "macbook", "chromebook"],
            "phone": ["phone", "smartphone", "iphone", "android phone", "mobile phone"],
            "tablet": ["tablet", "ipad"],
            "monitor": ["monitor", "display", "computer screen"],
            "keyboard": ["keyboard", "mechanical keyboard"],
            "mouse": ["mouse", "gaming mouse", "wireless mouse"],
            "camera": ["camera", "dslr", "mirrorless"],
            "tv": ["tv", "television", "smart tv"],
        }
        
        for cat, keywords in categories.items():
            if any(kw in query_lower for kw in keywords):
                category = cat
                break
        
        # Extract brands
        brands = []
        brand_list = [
            "apple", "samsung", "sony", "lg", "asus", "dell", "hp", "lenovo",
            "acer", "msi", "razer", "logitech", "corsair", "bose", "jbl",
            "microsoft", "google", "oneplus", "xiaomi", "huawei"
        ]
        for brand in brand_list:
            if brand in query_lower:
                brands.append(brand.capitalize())
        
        # Extract features
        features = []
        feature_patterns = [
            (r"(\d+)\s*(?:gb|g)\s*(?:ram|memory)", lambda m: f"{m.group(1)}GB RAM"),
            (r"(\d+)\s*(?:tb|t)\s*(?:ssd|storage|hdd)", lambda m: f"{m.group(1)}TB Storage"),
            (r"(\d+)\s*(?:gb|g)\s*(?:ssd|storage)", lambda m: f"{m.group(1)}GB Storage"),
            (r"(\d+)\s*(?:inch|\")", lambda m: f"{m.group(1)}\" Screen"),
            (r"(4k|1080p|1440p|hd|fhd|qhd)", lambda m: m.group(1).upper()),
            (r"(gaming|professional|business|student)", lambda m: f"For {m.group(1).capitalize()}"),
        ]
        
        for pattern, formatter in feature_patterns:
            match = re.search(pattern, query_lower)
            if match:
                features.append(formatter(match))
        
        # Determine search type
        search_type = "buy"
        if any(kw in query_lower for kw in ["compare", "vs", "versus", "difference"]):
            search_type = "compare"
        elif any(kw in query_lower for kw in ["research", "learn about", "what is", "tell me about"]):
            search_type = "research"
        
        # Generate keywords (remove filler words)
        stop_words = {"i", "want", "to", "buy", "find", "me", "a", "an", "the", "for", "please", "can", "you"}
        keywords = [w for w in query_lower.split() if w not in stop_words and not w.startswith("$")]
        if not keywords:
            keywords = [query]
        
        # Condition
        condition = None
        if "refurbished" in query_lower or "renewed" in query_lower:
            condition = "refurbished"
        elif "used" in query_lower or "second hand" in query_lower:
            condition = "used"
        elif "new" in query_lower:
            condition = "new"
        
        return SearchPlan(
            keywords=keywords[:5],  # Limit to 5 keywords
            category=category,
            price_min=price_min,
            price_max=price_max,
            brands=brands,
            features=features,
            search_type=search_type,
            condition=condition
        )
    
    def to_search_query(self, plan: SearchPlan) -> str:
        """
        Convert SearchPlan to a simple search query string.
        Useful for APIs that only accept text queries.
        """
        parts = []
        
        # Add category
        if plan.category:
            parts.append(plan.category)
        
        # Add keywords
        parts.extend(plan.keywords[:3])
        
        # Add brand if specified
        if plan.brands:
            parts.append(plan.brands[0])
        
        # Add key features
        if plan.features:
            parts.extend(plan.features[:2])
        
        return " ".join(parts)
