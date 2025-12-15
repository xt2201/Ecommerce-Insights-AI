"""
Conversation Context Schema
Tracks conversation state for multi-turn dialogue support.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


ConversationStage = Literal[
    "greeting",      # Initial greeting
    "gathering",     # Collecting requirements
    "searching",     # Performing product search
    "consulting",    # Discussing shown products
    "completed"      # Conversation ended
]


class UserPreferences(BaseModel):
    """User preferences gathered during conversation."""
    gender: Optional[str] = None              # male, female, unisex
    age_group: Optional[str] = None           # teen, adult, senior
    style: Optional[str] = None               # casual, formal, sporty
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    preferred_brands: List[str] = Field(default_factory=list)
    preferred_colors: List[str] = Field(default_factory=list)
    size: Optional[str] = None
    use_case: Optional[str] = None            # gaming, work, travel
    
    def to_context_string(self) -> str:
        """Convert preferences to natural language context."""
        parts = []
        if self.gender:
            parts.append(f"Gender: {self.gender}")
        if self.age_group:
            parts.append(f"Age group: {self.age_group}")
        if self.style:
            parts.append(f"Style: {self.style}")
        if self.budget_max:
            parts.append(f"Budget: under ${self.budget_max}")
        if self.preferred_brands:
            parts.append(f"Brands: {', '.join(self.preferred_brands)}")
        return "; ".join(parts) if parts else "No preferences specified"


class ShownProduct(BaseModel):
    """A product that was shown to the user."""
    asin: str
    title: str
    price: Optional[float] = None
    shown_at: datetime = Field(default_factory=datetime.now)


class ConversationContext(BaseModel):
    """
    Tracks conversation state across multiple turns.
    Enables natural multi-turn dialogue with clarification and consultation.
    """
    # Conversation metadata
    session_id: Optional[str] = None
    stage: ConversationStage = "greeting"
    turn_count: int = 0
    
    # User information gathered
    user_preferences: UserPreferences = Field(default_factory=UserPreferences)
    gathered_info: List[str] = Field(default_factory=list)  # What we've learned
    
    # Current interaction state
    pending_clarifications: List[str] = Field(default_factory=list)  # Questions to ask
    last_user_message: Optional[str] = None
    last_ai_response: Optional[str] = None
    
    # Product context
    current_category: Optional[str] = None  # What category we're discussing
    shown_products: List[ShownProduct] = Field(default_factory=list)
    selected_product_asin: Optional[str] = None  # If user selected one
    
    # Search context
    last_search_query: Optional[str] = None
    search_completed: bool = False
    
    def add_gathered_info(self, info: str) -> None:
        """Add information that was gathered from user."""
        if info not in self.gathered_info:
            self.gathered_info.append(info)
    
    def add_shown_product(self, asin: str, title: str, price: Optional[float] = None) -> None:
        """Track a product that was shown to user."""
        self.shown_products.append(ShownProduct(asin=asin, title=title, price=price))
    
    def has_shown_products(self) -> bool:
        """Check if any products have been shown."""
        return len(self.shown_products) > 0
    
    def get_product_by_asin(self, asin: str) -> Optional[ShownProduct]:
        """Get a shown product by ASIN."""
        for p in self.shown_products:
            if p.asin == asin:
                return p
        return None
    
    def increment_turn(self) -> None:
        """Increment conversation turn counter."""
        self.turn_count += 1
    
    def is_ready_to_search(self) -> bool:
        """
        Check if we have enough information to search.
        Returns True if essential info is gathered or max clarification rounds reached.
        """
        # Check if we have all essential information for the category
        missing = self.get_missing_essentials()
        if not missing:
            return True
            
        # After 3 clarification rounds, just search with what we have
        if self.turn_count >= 3 and self.current_category:
            return True
        
        return False
    
    def get_missing_essentials(self) -> List[str]:
        """
        Get list of essential information that's still missing.
        Used to generate clarification questions.
        """
        missing = []
        
        # Category is always essential
        if not self.current_category:
            missing.append("category")
        
        # For clothing, gender is important
        if self.current_category in ["clothing", "fashion", "apparel"]:
            if not self.user_preferences.gender:
                missing.append("gender")
        
        # Budget is generally helpful
        if not self.user_preferences.budget_max and not self.user_preferences.budget_min:
            missing.append("budget")
        
        return missing
    
    def build_search_context(self) -> str:
        """Build a comprehensive search context string."""
        parts = []
        
        if self.current_category:
            parts.append(f"Looking for: {self.current_category}")
        
        pref_str = self.user_preferences.to_context_string()
        if pref_str != "No preferences specified":
            parts.append(pref_str)
        
        if self.gathered_info:
            parts.append(f"Additional info: {', '.join(self.gathered_info)}")
        
        return " | ".join(parts)
    
    def reset_for_new_search(self) -> None:
        """Reset search-related state for a new search."""
        self.shown_products = []
        self.search_completed = False
        self.selected_product_asin = None
        self.stage = "gathering"
    
    def get_recent_product_context(self, limit: int = 3) -> str:
        """
        Get a summary of recently shown products for context.
        Useful for related searches (e.g., "find pants to match this jacket").
        """
        if not self.shown_products:
            return ""
        
        recent = self.shown_products[-limit:]
        parts = []
        for p in recent:
            if p.price:
                parts.append(f"{p.title} (${p.price})")
            else:
                parts.append(p.title)
        
        return ", ".join(parts)
    
    def find_product_by_reference(self, reference: str) -> Optional[ShownProduct]:
        """
        Find a shown product by fuzzy reference.
        Handles cases like:
        - "cái thứ 2" -> second product
        - "áo bomber zara" -> match by keywords
        - "cái giá 25$" -> match by price
        
        Returns:
            Matching ShownProduct or None
        """
        import re
        reference_lower = reference.lower()
        
        # Check for ordinal reference ("cái thứ 2", "the second one")
        ordinal_match = re.search(r"thứ\s*(\d+)|#(\d+)|number\s*(\d+)", reference_lower)
        if ordinal_match:
            idx = int(ordinal_match.group(1) or ordinal_match.group(2) or ordinal_match.group(3)) - 1
            if 0 <= idx < len(self.shown_products):
                return self.shown_products[idx]
        
        # Check for price reference ("cái giá 25$", "the $25 one")
        price_match = re.search(r"\$?(\d+(?:\.\d{2})?)", reference_lower)
        if price_match:
            target_price = float(price_match.group(1))
            for p in self.shown_products:
                if p.price and abs(p.price - target_price) < 1:
                    return p
        
        # Fuzzy match by title keywords
        ref_words = set(reference_lower.split())
        best_match = None
        best_score = 0
        
        for p in self.shown_products:
            title_lower = p.title.lower()
            title_words = set(title_lower.split())
            # Count matching words
            score = len(ref_words.intersection(title_words))
            # Bonus for substring match
            for word in ref_words:
                if len(word) > 3 and word in title_lower:
                    score += 2
            
            if score > best_score:
                best_score = score
                best_match = p
        
        # Only return if we have a reasonable match
        if best_score >= 2:
            return best_match
        
        return None
    
    def get_products_in_budget(self, max_price: float) -> List[ShownProduct]:
        """
        Get shown products within a budget constraint.
        Useful for advice like "which one under $30?"
        """
        return [p for p in self.shown_products if p.price and p.price <= max_price]


# Category-specific required fields
CATEGORY_REQUIRED_FIELDS: Dict[str, List[str]] = {
    "clothing": ["type", "gender"],  # Must know: shirt/pants/jacket + male/female
    "shoes": ["type", "gender", "size"],
    "electronics": ["type", "use_case"],  # laptop for gaming? work?
    "phones": ["budget"],
    "laptops": ["use_case", "budget"],
    "accessories": ["type"],
    "default": ["type"]
}


def get_required_fields(category: Optional[str]) -> List[str]:
    """Get required clarification fields for a category."""
    if not category:
        return ["category"]
    
    category_lower = category.lower()
    for key in CATEGORY_REQUIRED_FIELDS:
        if key in category_lower:
            return CATEGORY_REQUIRED_FIELDS[key]
    
    return CATEGORY_REQUIRED_FIELDS["default"]
