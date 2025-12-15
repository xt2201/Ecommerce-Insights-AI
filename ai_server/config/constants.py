"""
Centralized Constants for AI Server
All magic numbers and thresholds should be defined here.
"""
from typing import Final


# =============================================================================
# INTENT CLASSIFICATION
# =============================================================================

class IntentConfig:
    """Configuration for intent classification."""
    
    # Word count thresholds
    MAX_GREETING_WORDS: Final[int] = 8  # Max words to consider as greeting
    MAX_CONFIRMATION_WORDS: Final[int] = 3  # Max words for simple confirmation
    MIN_PRODUCT_SEARCH_WORDS: Final[int] = 5  # Min words to assume product search
    MAX_VAGUE_QUERY_WORDS: Final[int] = 4  # Max words for vague query detection
    
    # Confidence scores
    HIGH_CONFIDENCE: Final[float] = 0.9
    MEDIUM_CONFIDENCE: Final[float] = 0.8
    LOW_CONFIDENCE: Final[float] = 0.7
    DEFAULT_CONFIDENCE: Final[float] = 0.5


# =============================================================================
# CLARIFICATION
# =============================================================================

class ClarificationConfig:
    """Configuration for clarification agent."""
    
    # Conversation limits
    MAX_CLARIFICATION_ROUNDS: Final[int] = 3  # Max turns before forcing search
    MAX_QUESTIONS_PER_TURN: Final[int] = 2  # Max clarification questions at once
    
    # Query thresholds
    SHORT_QUERY_THRESHOLD: Final[int] = 4  # Words count for "short" query
    
    # Confidence scores
    READY_CONFIDENCE: Final[float] = 0.9
    DEFAULT_CONFIDENCE: Final[float] = 0.8
    CLARIFICATION_CONFIDENCE: Final[float] = 0.7


# =============================================================================
# SEARCH & SCORING
# =============================================================================

class SearchConfig:
    """Configuration for search and scoring."""
    
    # Search limits
    MAX_SEARCH_RESULTS: Final[int] = 20
    TOP_PICKS_LIMIT: Final[int] = 5
    MAX_CANDIDATES_DISPLAY: Final[int] = 10
    
    # Default scores
    DEFAULT_DOMAIN_SCORE: Final[float] = 0.5
    DEFAULT_QUALITY_SCORE: Final[float] = 0.5
    FALLBACK_SCORE: Final[float] = 0.3
    
    # Quality thresholds
    LOW_RATING_THRESHOLD: Final[float] = 3.5
    REJECTED_QUALITY_SCORE: Final[float] = 0.3
    APPROVED_QUALITY_SCORE: Final[float] = 0.7


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitBreakerConfig:
    """Configuration for circuit breaker and safety limits."""
    
    MAX_LOOPS: Final[int] = 6  # Max graph iterations
    MAX_SEARCH_ATTEMPTS: Final[int] = 3  # Max search retries
    MAX_LLM_RETRIES: Final[int] = 2  # Max LLM call retries


# =============================================================================
# PRODUCT CONTEXT
# =============================================================================

class ProductContextConfig:
    """Configuration for product context management."""
    
    # Product display limits
    MAX_SHOWN_PRODUCTS: Final[int] = 10
    MAX_PRODUCTS_FOR_CONTEXT: Final[int] = 5
    MAX_PRODUCTS_FOR_ADVICE: Final[int] = 5
    MAX_PRODUCTS_TO_TRACK: Final[int] = 10  # Max products to track in context
    
    # Reference matching
    PRICE_MATCH_TOLERANCE: Final[float] = 1.0  # Dollar tolerance for price matching
    MIN_FUZZY_MATCH_SCORE: Final[int] = 2  # Min score for keyword fuzzy match
    
    # Query parsing
    MAX_KEYWORDS: Final[int] = 5


# =============================================================================
# RESPONSE GENERATION
# =============================================================================

class ResponseConfig:
    """Configuration for response generation."""
    
    # Product recommendations
    TOP_PICKS_LIMIT: Final[int] = 5  # Max products in final recommendations
    
    # Follow-up suggestions
    NUM_FOLLOW_UP_SUGGESTIONS: Final[int] = 3
    MAX_FOLLOW_UP_CONTEXT_CHARS: Final[int] = 500


# =============================================================================
# EXPORTS - All config classes
# =============================================================================

__all__ = [
    'IntentConfig',
    'ClarificationConfig', 
    'SearchConfig',
    'CircuitBreakerConfig',
    'ProductContextConfig',
    'ResponseConfig',
]
