"""
Enhanced Session Memory Models

Provides rich conversation memory for multi-turn context awareness.
Key difference from previous: Stores structured SearchIntent, not just shown products.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field


class ShownProduct(BaseModel):
    """Product that was shown to user."""
    asin: str
    title: str
    price: Optional[float] = None
    image_url: Optional[str] = None
    rating: Optional[float] = None
    
    def to_context_string(self) -> str:
        """Format for LLM context."""
        parts = [f"- {self.title}"]
        if self.price:
            parts[0] += f" (${self.price})"
        if self.rating:
            parts[0] += f" [{self.rating}★]"
        return parts[0]


class SearchIntent(BaseModel):
    """
    Tracks the active search intent across conversation turns.
    
    This is the key innovation: instead of just remembering keywords,
    we track structured intent that can be refined incrementally.
    """
    # Core search parameters
    category: Optional[str] = None  # "shoes", "jacket", "hat"
    keywords: List[str] = Field(default_factory=list)  # ["running", "sports"]
    keywords_en: List[str] = Field(default_factory=list)  # English translation
    
    # Accumulated constraints (refined over turns)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    # Example: {
    #   "gender": "female",
    #   "color": "white", 
    #   "use_case": "running",
    #   "price_max": 100,
    #   "brand": "Nike"
    # }
    
    # History tracking
    original_query: str = ""  # First query that started this intent
    refinements: List[str] = Field(default_factory=list)  # Subsequent refinement queries
    
    # State
    is_active: bool = True  # False when user starts completely new search
    created_at: datetime = Field(default_factory=datetime.now)
    
    def merge_constraints(self, new_constraints: Dict[str, Any]) -> None:
        """Merge new constraints with existing ones."""
        for key, value in new_constraints.items():
            if value is not None:
                self.constraints[key] = value
    
    def add_refinement(self, query: str) -> None:
        """Track a refinement query."""
        self.refinements.append(query)
    
    def to_search_query(self) -> str:
        """Build English search query from intent."""
        parts = []
        
        # Add constraints first (more specific)
        if self.constraints.get("gender"):
            parts.append(self.constraints["gender"])
        if self.constraints.get("use_case"):
            parts.append(self.constraints["use_case"])
        
        # Add category
        if self.category:
            parts.append(self.category)
        
        # Add keywords
        if self.keywords_en:
            parts.extend(self.keywords_en[:3])
        elif self.keywords:
            parts.extend(self.keywords[:3])
        
        # Add other constraints
        if self.constraints.get("color"):
            parts.append(self.constraints["color"])
        if self.constraints.get("brand"):
            parts.append(self.constraints["brand"])
        
        return " ".join(parts)
    
    def to_context_string(self) -> str:
        """Format for LLM context."""
        lines = []
        if self.original_query:
            lines.append(f"Original search: \"{self.original_query}\"")
        if self.category:
            lines.append(f"Category: {self.category}")
        if self.constraints:
            constraints_str = ", ".join(f"{k}={v}" for k, v in self.constraints.items())
            lines.append(f"Constraints: {constraints_str}")
        if self.refinements:
            lines.append(f"Refinements: {self.refinements}")
        return "\n".join(lines) if lines else "No active search intent"


class ConversationTurn(BaseModel):
    """A single turn in the conversation."""
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    intent_type: Optional[str] = None  # What was detected for this turn


class SessionMemory(BaseModel):
    """
    Rich conversation memory for multi-turn context awareness.
    
    This replaces the simpler ConversationContext with a more
    capable memory system that tracks structured search intent.
    """
    # Identity
    session_id: str
    user_id: Optional[str] = None
    
    # Current state
    current_intent: Optional[SearchIntent] = None
    shown_products: List[ShownProduct] = Field(default_factory=list)
    
    # Conversation history
    turns: List[ConversationTurn] = Field(default_factory=list)
    conversation_summary: str = ""  # LLM-generated summary
    
    # Metadata
    turn_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    
    def add_user_message(self, message: str, intent_type: Optional[str] = None) -> None:
        """Add user message to history."""
        self.turns.append(ConversationTurn(
            role="user",
            content=message,
            intent_type=intent_type
        ))
        self.turn_count += 1
        self.last_updated = datetime.now()
    
    def add_assistant_message(self, message: str) -> None:
        """Add assistant response to history."""
        self.turns.append(ConversationTurn(
            role="assistant",
            content=message
        ))
        self.last_updated = datetime.now()
    
    def add_shown_products(self, products: List[ShownProduct]) -> None:
        """Track products shown to user."""
        self.shown_products.extend(products)
        self.last_updated = datetime.now()
    
    def clear_shown_products(self) -> None:
        """Clear shown products (for new search)."""
        self.shown_products = []
    
    def start_new_intent(self, query: str, category: Optional[str] = None) -> SearchIntent:
        """Start a new search intent, replacing old one."""
        self.current_intent = SearchIntent(
            original_query=query,
            category=category,
            is_active=True
        )
        self.shown_products = []  # Clear old products
        return self.current_intent
    
    def has_shown_products(self) -> bool:
        """Check if any products have been shown."""
        return len(self.shown_products) > 0
    
    def get_recent_turns(self, n: int = 5) -> List[ConversationTurn]:
        """Get last N conversation turns."""
        return self.turns[-n:] if self.turns else []
    
    def to_context_string(self) -> str:
        """Format full context for LLM."""
        sections = []
        
        # Current intent
        if self.current_intent:
            sections.append("## Current Search Intent")
            sections.append(self.current_intent.to_context_string())
        
        # Shown products
        if self.shown_products:
            sections.append("\n## Products Shown to User")
            for p in self.shown_products[:10]:  # Limit to 10
                sections.append(p.to_context_string())
        
        # Recent conversation
        if self.turns:
            sections.append("\n## Recent Conversation")
            for turn in self.get_recent_turns(5):
                prefix = "User" if turn.role == "user" else "Assistant"
                # Truncate long messages
                content = turn.content[:100] + "..." if len(turn.content) > 100 else turn.content
                sections.append(f"{prefix}: {content}")
        
        # Summary if available
        if self.conversation_summary:
            sections.append(f"\n## Summary: {self.conversation_summary}")
        
        return "\n".join(sections) if sections else "New conversation, no context yet."
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for storage."""
        return self.model_dump(mode='json')
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionMemory":
        """Deserialize from storage."""
        return cls.model_validate(data)
