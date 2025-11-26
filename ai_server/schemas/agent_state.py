"""Shared LangGraph state definitions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from typing_extensions import TypedDict

from ai_server.schemas.output_models import AnalysisSnapshot, Recommendation, ResponsePayload


class SearchPlan(TypedDict, total=False):
    """Plan describing how data should be gathered from SerpAPI."""

    keywords: List[str]
    amazon_domain: str
    max_price: Optional[float]
    engines: List[str]
    asin_focus_list: List[str]
    notes: str


class CollectionPayload(TypedDict, total=False):
    """Raw payload returned from SerpAPI before enrichment."""

    search_results: Dict[str, Any]
    product_details: Dict[str, Any]
    review_details: Dict[str, Any]


class AgentState(TypedDict, total=False):
    """State flowing through the LangGraph workflow."""

    user_query: str
    search_plan: SearchPlan
    raw_payload: CollectionPayload
    products: List[Dict[str, Any]]
    analysis: AnalysisSnapshot
    recommendations: List[Recommendation]
    recommendations: List[Recommendation]
    response: ResponsePayload
    
    # New Data Fields (Phase 1 Upgrade)
    reviews_data: Dict[str, Any]  # Detailed review analysis
    market_data: Dict[str, Any]   # Market intelligence data
    price_history: Dict[str, Any] # Historical price data

    
    # Phase 2 additions
    analysis_result: Dict[str, Any]  # Analysis result with reasoning
    review_analysis: Dict[str, Any]  # Output from Review Agent
    market_analysis: Dict[str, Any]  # Output from Market Agent
    price_analysis: Dict[str, Any]   # Output from Price Agent
    recommended_products: List[Dict[str, Any]]  # Top recommendations with reasoning
    final_response: Dict[str, Any]  # Response structured output
    formatted_response: str  # Final markdown response
    
    # Routing and errors
    route: str  # Query route (simple/standard/complex/clarification)
    route_decision: str # The final decision (same as route, but explicit)
    confidence: float # Classification confidence
    reasoning: str # Classification reasoning
    plan: Dict[str, Any]  # Planning output
    analysis_error: str  # Analysis errors
    response_error: str  # Response errors
    debug_notes: List[str]  # Debug information
    
    # Phase 3: Memory & Personalization
    session_id: str  # Unique session identifier
    conversation_history: List[Dict[str, Any]]  # Previous conversation turns
    user_preferences: Any  # UserPreferences object (avoid circular import)
    context_summary: str  # Summary of conversation context
    previous_queries: List[str]  # Recent queries for context
    previous_recommendations: List[str]  # Recent recommendations
    is_followup: bool  # Whether this is a follow-up query
    reference_context: Dict[str, Any]  # Context from previous turn (for "cheaper", "similar", etc.)
    
    # Monitoring & Tracing
    trace_id: str  # Execution trace identifier for monitoring
