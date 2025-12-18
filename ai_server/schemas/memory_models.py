"""Memory and personalization data models for Phase 3."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

from ai_server.schemas.agent_state import SearchPlan
from ai_server.schemas.conversation_context import ConversationContext

if TYPE_CHECKING:
    from ai_server.schemas.session_memory import SessionMemory


@dataclass
class ConversationTurn:
    """Represents a single turn in a conversation."""
    
    timestamp: datetime
    user_query: str
    search_plan: Optional[SearchPlan] = None
    products_found: int = 0
    top_recommendation: Optional[str] = None
    matched_products: List[Dict[str, Any]] = field(default_factory=list)
    user_feedback: Optional[str] = None  # "liked", "disliked", "bought", "ignored"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "user_query": self.user_query,
            "search_plan": self.search_plan,
            "products_found": self.products_found,
            "top_recommendation": self.top_recommendation,
            "matched_products": self.matched_products,
            "user_feedback": self.user_feedback,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ConversationTurn:
        """Create from dictionary."""
        data = data.copy()
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class ConversationHistory:
    """Complete conversation history for a session."""
    
    session_id: str
    turns: List[ConversationTurn] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_turn(self, turn: ConversationTurn) -> None:
        """Add a new conversation turn."""
        self.turns.append(turn)
        self.updated_at = datetime.now()
    
    def get_recent_turns(self, n: int = 5) -> List[ConversationTurn]:
        """Get the N most recent turns."""
        return self.turns[-n:]
    
    def get_recent_queries(self, n: int = 5) -> List[str]:
        """Get the N most recent queries."""
        recent = self.get_recent_turns(n)
        return [turn.user_query for turn in recent]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "turns": [turn.to_dict() for turn in self.turns],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ConversationHistory:
        """Create from dictionary."""
        data = data.copy()
        data["turns"] = [ConversationTurn.from_dict(t) for t in data.get("turns", [])]
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)


@dataclass
class UserPreferences:
    """User preferences learned from interaction history."""
    
    session_id: str
    
    # Price preferences
    preferred_price_range: Optional[Tuple[float, float]] = None
    max_budget: Optional[float] = None
    
    # Brand preferences (brand name -> confidence score)
    liked_brands: Dict[str, float] = field(default_factory=dict)
    disliked_brands: Dict[str, float] = field(default_factory=dict)
    
    # Feature preferences (feature -> confidence score)
    must_have_features: Dict[str, float] = field(default_factory=dict)
    nice_to_have_features: Dict[str, float] = field(default_factory=dict)
    
    # Category preferences (category -> interaction count)
    frequent_categories: Dict[str, int] = field(default_factory=dict)
    
    # Quality preferences
    min_rating: Optional[float] = None
    min_reviews: Optional[int] = None
    
    # Learning metadata
    confidence: float = 0.0  # 0-1, overall confidence in preferences
    last_updated: datetime = field(default_factory=datetime.now)
    
    def update_brand_preference(self, brand: str, liked: bool, confidence: float = 0.5) -> None:
        """Update brand preference."""
        if liked:
            self.liked_brands[brand] = self.liked_brands.get(brand, 0.0) + confidence
        else:
            self.disliked_brands[brand] = self.disliked_brands.get(brand, 0.0) + confidence
        self.last_updated = datetime.now()
    
    def update_feature_preference(self, feature: str, must_have: bool, confidence: float = 0.5) -> None:
        """Update feature preference."""
        if must_have:
            self.must_have_features[feature] = self.must_have_features.get(feature, 0.0) + confidence
        else:
            self.nice_to_have_features[feature] = self.nice_to_have_features.get(feature, 0.0) + confidence
        self.last_updated = datetime.now()
    
    def update_price_preference(self, price: float) -> None:
        """Update price preference based on observed price."""
        if self.max_budget is None or price < self.max_budget:
            self.max_budget = price
        
        if self.preferred_price_range is None:
            self.preferred_price_range = (price * 0.8, price * 1.2)
        else:
            # Expand range to include new price
            min_price, max_price = self.preferred_price_range
            self.preferred_price_range = (
                min(min_price, price * 0.8),
                max(max_price, price * 1.2)
            )
        self.last_updated = datetime.now()
    
    def get_top_brands(self, n: int = 3) -> List[Tuple[str, float]]:
        """Get top N preferred brands."""
        sorted_brands = sorted(self.liked_brands.items(), key=lambda x: x[1], reverse=True)
        return sorted_brands[:n]
    
    def get_top_features(self, n: int = 5) -> List[Tuple[str, float]]:
        """Get top N must-have features."""
        sorted_features = sorted(self.must_have_features.items(), key=lambda x: x[1], reverse=True)
        return sorted_features[:n]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "preferred_price_range": self.preferred_price_range,
            "max_budget": self.max_budget,
            "liked_brands": self.liked_brands,
            "disliked_brands": self.disliked_brands,
            "must_have_features": self.must_have_features,
            "nice_to_have_features": self.nice_to_have_features,
            "frequent_categories": self.frequent_categories,
            "min_rating": self.min_rating,
            "min_reviews": self.min_reviews,
            "confidence": self.confidence,
            "last_updated": self.last_updated.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> UserPreferences:
        """Create from dictionary."""
        data = data.copy()
        if "preferred_price_range" in data and data["preferred_price_range"]:
            data["preferred_price_range"] = tuple(data["preferred_price_range"])
        data["last_updated"] = datetime.fromisoformat(data["last_updated"])
        return cls(**data)


@dataclass
class SessionState:
    """Complete session state including history and preferences."""
    
    session_id: str
    user_id: Optional[str] = None
    title: str = ""  # Session title (auto-generated from first query or user-renamed)
    conversation_history: ConversationHistory = field(default_factory=lambda: ConversationHistory(session_id=""))
    user_preferences: UserPreferences = field(default_factory=lambda: UserPreferences(session_id=""))
    # Added ConversationContext for multi-turn state persistence
    conversation_context: ConversationContext = field(default_factory=ConversationContext)
    # SessionMemory data for graph state persistence (stored as dict to avoid circular import)
    session_memory_data: Optional[Dict[str, Any]] = None
    context_summary: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize nested objects with correct session_id."""
        if not self.conversation_history.session_id:
            self.conversation_history.session_id = self.session_id
        if not self.user_preferences.session_id:
            self.user_preferences.session_id = self.session_id
        if not self.conversation_context.session_id:
            self.conversation_context.session_id = self.session_id
    
    def is_expired(self) -> bool:
        """Check if session has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def add_turn(self, turn: ConversationTurn) -> None:
        """Add a conversation turn."""
        self.conversation_history.add_turn(turn)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "title": self.title,
            "conversation_history": self.conversation_history.to_dict(),
            "user_preferences": self.user_preferences.to_dict(),
            "conversation_context": self.conversation_context.model_dump(),
            "session_memory_data": self.session_memory_data,
            "context_summary": self.context_summary,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SessionState:
        """Create from dictionary."""
        data = data.copy()
        data["conversation_history"] = ConversationHistory.from_dict(data["conversation_history"])
        data["user_preferences"] = UserPreferences.from_dict(data["user_preferences"])
        if "conversation_context" in data:
            data["conversation_context"] = ConversationContext.model_validate(data["conversation_context"])
        else:
            data["conversation_context"] = ConversationContext()
        # session_memory_data is already a dict, no conversion needed
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("expires_at"):
            data["expires_at"] = datetime.fromisoformat(data["expires_at"])
        return cls(**data)
