"""Preference extraction from user queries and interactions."""

import re
from typing import Dict, List, Optional, Tuple

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from ai_server.llm.llm_factory import get_llm
from ai_server.schemas.memory_models import UserPreferences
from ai_server.utils.logger import get_agent_logger

logger = get_agent_logger()


class ExtractedPreferences(BaseModel):
    """Preferences extracted from a query."""
    
    price_max: Optional[float] = Field(None, description="Maximum price mentioned")
    price_min: Optional[float] = Field(None, description="Minimum price mentioned")
    brands: List[str] = Field(default_factory=list, description="Brand names mentioned")
    must_have_features: List[str] = Field(default_factory=list, description="Required features")
    nice_to_have_features: List[str] = Field(default_factory=list, description="Desired but optional features")
    min_rating: Optional[float] = Field(None, description="Minimum rating requirement")
    categories: List[str] = Field(default_factory=list, description="Product categories")
    confidence: float = Field(0.5, description="Confidence in extraction (0-1)")


class PreferenceExtractor:
    """Extract user preferences from queries using LLM and patterns."""
    
    def __init__(self):
        """Initialize preference extractor."""
        self.llm = get_llm("planning")  # Use planning agent's LLM
        self.parser = PydanticOutputParser(pydantic_object=ExtractedPreferences)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at extracting shopping preferences from user queries.
            
Extract the following information:
- Price range (min/max)
- Brand preferences
- Must-have features (explicitly required)
- Nice-to-have features (mentioned but not required)
- Minimum rating if mentioned
- Product categories

Be conservative - only extract what's clearly stated or strongly implied.
Assign confidence based on how explicit the preference is (explicit=0.9, implicit=0.5).

{format_instructions}"""),
            ("user", "Query: {query}")
        ])
    
    def extract_from_query(self, query: str) -> ExtractedPreferences:
        """Extract preferences from a single query using LLM.
        
        Args:
            query: User's query text
            
        Returns:
            ExtractedPreferences object
        """
        try:
            # First try rule-based extraction for speed
            rule_based = self._rule_based_extraction(query)
            
            # Use LLM for complex extraction
            chain = self.prompt | self.llm | self.parser
            llm_result = chain.invoke({
                "query": query,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            # Merge rule-based and LLM results
            return self._merge_extractions(rule_based, llm_result)
            
        except Exception as e:
            logger.warning(
                f"Preference extraction error, falling back to rule-based",
                extra={"error": str(e), "query": query},
                exc_info=True
            )
            # Fall back to rule-based only
            return self._rule_based_extraction(query)
    
    def _rule_based_extraction(self, query: str) -> ExtractedPreferences:
        """Fast rule-based preference extraction.
        
        Args:
            query: User's query text
            
        Returns:
            ExtractedPreferences object
        """
        query_lower = query.lower()
        
        # Extract price
        price_max = self._extract_max_price(query)
        price_min = self._extract_min_price(query)
        
        # Extract brands (common tech brands)
        brands = self._extract_brands(query)
        
        # Extract features
        must_have = self._extract_must_have_features(query_lower)
        nice_to_have = self._extract_nice_to_have_features(query_lower)
        
        # Extract rating
        min_rating = self._extract_min_rating(query_lower)
        
        # Extract categories
        categories = self._extract_categories(query_lower)
        
        return ExtractedPreferences(
            price_max=price_max,
            price_min=price_min,
            brands=brands,
            must_have_features=must_have,
            nice_to_have_features=nice_to_have,
            min_rating=min_rating,
            categories=categories,
            confidence=0.7  # Rule-based has decent confidence
        )
    
    def _extract_max_price(self, query: str) -> Optional[float]:
        """Extract maximum price from query."""
        # Patterns: "under $50", "less than $50", "below $50", "$50 or less"
        patterns = [
            r'under\s*\$?(\d+(?:\.\d{2})?)',
            r'less than\s*\$?(\d+(?:\.\d{2})?)',
            r'below\s*\$?(\d+(?:\.\d{2})?)',
            r'cheaper than\s*\$?(\d+(?:\.\d{2})?)',
            r'max\s*\$?(\d+(?:\.\d{2})?)',
            r'\$?(\d+(?:\.\d{2})?)\s*or less',
            r'\$?(\d+(?:\.\d{2})?)\s*max',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                return float(match.group(1))
        
        return None
    
    def _extract_min_price(self, query: str) -> Optional[float]:
        """Extract minimum price from query."""
        patterns = [
            r'over\s*\$?(\d+(?:\.\d{2})?)',
            r'more than\s*\$?(\d+(?:\.\d{2})?)',
            r'above\s*\$?(\d+(?:\.\d{2})?)',
            r'at least\s*\$?(\d+(?:\.\d{2})?)',
            r'min\s*\$?(\d+(?:\.\d{2})?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                return float(match.group(1))
        
        return None
    
    def _extract_brands(self, query: str) -> List[str]:
        """Extract brand names from query."""
        # Common tech/electronics brands
        common_brands = [
            "Apple", "Samsung", "Sony", "LG", "Bose", "JBL", "Beats",
            "Anker", "Logitech", "Microsoft", "Dell", "HP", "Lenovo",
            "Asus", "Acer", "Razer", "Corsair", "HyperX", "SteelSeries",
            "Amazon", "Google", "Xiaomi", "OnePlus", "Huawei",
            "Canon", "Nikon", "GoPro", "DJI", "Roku", "Fire TV",
            "Philips", "Panasonic", "Vizio", "TCL", "Hisense"
        ]
        
        found_brands = []
        for brand in common_brands:
            if brand.lower() in query.lower():
                found_brands.append(brand)
        
        return found_brands
    
    def _extract_must_have_features(self, query_lower: str) -> List[str]:
        """Extract must-have features from query."""
        must_have = []
        
        # Explicit requirements
        if "wireless" in query_lower:
            must_have.append("wireless")
        if "bluetooth" in query_lower:
            must_have.append("bluetooth")
        if "anc" in query_lower or "noise cancel" in query_lower:
            must_have.append("ANC")
        if "waterproof" in query_lower or "water resistant" in query_lower:
            must_have.append("waterproof")
        if "rgb" in query_lower or "lighting" in query_lower:
            must_have.append("RGB")
        if "4k" in query_lower or "uhd" in query_lower:
            must_have.append("4K")
        if "fast charg" in query_lower:
            must_have.append("fast-charging")
        if "long battery" in query_lower or "battery life" in query_lower:
            must_have.append("long-battery")
        
        return must_have
    
    def _extract_nice_to_have_features(self, query_lower: str) -> List[str]:
        """Extract nice-to-have features from query."""
        nice_to_have = []
        
        # Features mentioned but not emphasized
        if "compact" in query_lower or "portable" in query_lower:
            nice_to_have.append("portable")
        if "durable" in query_lower:
            nice_to_have.append("durable")
        if "lightweight" in query_lower or "light weight" in query_lower:
            nice_to_have.append("lightweight")
        
        return nice_to_have
    
    def _extract_min_rating(self, query_lower: str) -> Optional[float]:
        """Extract minimum rating requirement."""
        patterns = [
            r'(\d+(?:\.\d)?)\s*stars?\s*or (higher|better|above)',
            r'at least\s*(\d+(?:\.\d)?)\s*stars?',
            r'minimum\s*(\d+(?:\.\d)?)\s*stars?',
            r'(\d+(?:\.\d)?)\+\s*stars?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                rating = float(match.group(1))
                if 0 <= rating <= 5:
                    return rating
        
        return None
    
    def _extract_categories(self, query_lower: str) -> List[str]:
        """Extract product categories from query."""
        categories = []
        
        category_keywords = {
            "earbuds": ["earbuds", "earbud", "in-ear"],
            "headphones": ["headphones", "headphone", "over-ear", "on-ear"],
            "speaker": ["speaker", "speakers", "bluetooth speaker"],
            "mouse": ["mouse", "mice", "gaming mouse"],
            "keyboard": ["keyboard", "mechanical keyboard"],
            "monitor": ["monitor", "display", "screen"],
            "laptop": ["laptop", "notebook"],
            "tablet": ["tablet", "ipad"],
            "phone": ["phone", "smartphone", "mobile"],
            "charger": ["charger", "charging cable"],
            "cable": ["cable", "cord", "usb"],
        }
        
        for category, keywords in category_keywords.items():
            if any(kw in query_lower for kw in keywords):
                categories.append(category)
        
        return categories
    
    def _merge_extractions(
        self, 
        rule_based: ExtractedPreferences,
        llm_result: ExtractedPreferences
    ) -> ExtractedPreferences:
        """Merge rule-based and LLM extractions.
        
        Args:
            rule_based: Rule-based extraction results
            llm_result: LLM extraction results
            
        Returns:
            Merged ExtractedPreferences
        """
        # Prefer LLM for price (more context-aware)
        price_max = llm_result.price_max or rule_based.price_max
        price_min = llm_result.price_min or rule_based.price_min
        
        # Combine brands (union)
        brands = list(set(rule_based.brands + llm_result.brands))
        
        # Combine features (union)
        must_have = list(set(rule_based.must_have_features + llm_result.must_have_features))
        nice_to_have = list(set(rule_based.nice_to_have_features + llm_result.nice_to_have_features))
        
        # Prefer LLM for rating
        min_rating = llm_result.min_rating or rule_based.min_rating
        
        # Combine categories
        categories = list(set(rule_based.categories + llm_result.categories))
        
        # Average confidence
        confidence = (rule_based.confidence + llm_result.confidence) / 2
        
        return ExtractedPreferences(
            price_max=price_max,
            price_min=price_min,
            brands=brands,
            must_have_features=must_have,
            nice_to_have_features=nice_to_have,
            min_rating=min_rating,
            categories=categories,
            confidence=confidence
        )
    
    def update_user_preferences(
        self,
        user_prefs: UserPreferences,
        extracted: ExtractedPreferences,
        learning_rate: float = 0.1
    ) -> None:
        """Update user preferences based on extracted preferences.
        
        Args:
            user_prefs: Existing user preferences to update
            extracted: Newly extracted preferences
            learning_rate: How quickly to adapt (0-1)
        """
        confidence = extracted.confidence * learning_rate
        
        # Update price preferences
        if extracted.price_max:
            user_prefs.update_price_preference(extracted.price_max)
        
        # Update brand preferences
        for brand in extracted.brands:
            user_prefs.update_brand_preference(brand, liked=True, confidence=confidence)
        
        # Update feature preferences
        for feature in extracted.must_have_features:
            user_prefs.update_feature_preference(feature, must_have=True, confidence=confidence)
        
        for feature in extracted.nice_to_have_features:
            user_prefs.update_feature_preference(feature, must_have=False, confidence=confidence * 0.5)
        
        # Update quality preferences
        if extracted.min_rating:
            if user_prefs.min_rating is None:
                user_prefs.min_rating = extracted.min_rating
            else:
                # Average with existing
                user_prefs.min_rating = (user_prefs.min_rating + extracted.min_rating) / 2
        
        # Update category tracking
        for category in extracted.categories:
            user_prefs.frequent_categories[category] = user_prefs.frequent_categories.get(category, 0) + 1
        
        # Update overall confidence
        if user_prefs.confidence == 0:
            user_prefs.confidence = extracted.confidence
        else:
            user_prefs.confidence = user_prefs.confidence * 0.9 + extracted.confidence * 0.1
