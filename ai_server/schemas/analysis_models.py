"""Pydantic models for Analysis Agent - Chain-of-Thought Reasoning."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Literal, Dict, Any, Optional

# === Key-Value Models for Dict replacement ===
# Cerebras API rejects objects with only additionalProperties
# These models provide explicit properties instead

class StringValue(BaseModel):
    """Key-value pair with string value."""
    key: str = Field(..., description="The key")
    value: str = Field(..., description="The value")

class FloatValue(BaseModel):
    """Key-value pair with float value."""
    key: str = Field(..., description="The key")
    value: float = Field(..., description="The value")

class ListValue(BaseModel):
    """Key-value pair with list value."""
    key: str = Field(..., description="The key")
    value: List[str] = Field(..., description="List of values")

class AnyValue(BaseModel):
    """Key-value pair with any value."""
    key: str = Field(..., description="The key")
    value: Any = Field(..., description="The value (can be any type)")


class ReasoningStep(BaseModel):
    """A single step in chain-of-thought reasoning."""
    
    step_number: int = Field(...,
        description="Sequential step number"
    )
    
    thought: str = Field(...,
        description="The reasoning/thinking at this step"
    )
    
    action: str = Field(...,
        description="What action or analysis is performed"
    )
    
    observation: str = Field(...,
        description="What was learned or observed from this action"
    )
    
    confidence: float = Field(...,
        description="Confidence in this reasoning step"
    )


class ProductComparison(BaseModel):
    """Comparison analysis between multiple products."""
    
    products_compared: List[str] = Field(...,
        description="Product names/ASINs being compared"
    )
    
    reasoning_chain: List[ReasoningStep] = Field(...,
        description="Step-by-step comparison reasoning"
    )
    
    differentiating_features: List[ListValue] = Field(...,
        description="Key features as key-value pairs with list values"
    )
    
    value_rankings: str = Field(...,
        description="Products ranked by value with scores (JSON string format)"
    )
    
    trade_offs: str = Field(...,
        description="Trade-offs for each product as JSON string (key=product_id, value=pros/cons)"
    )
    
    recommendation: str = Field(...,
        description="Final recommendation with reasoning"
    )
    
    confidence: float = Field(...,
        description="Overall confidence in comparison"
    )


class ValueScore(BaseModel):
    """Value score calculation with reasoning."""
    
    product_id: str = Field(...,
        description="Product ASIN or identifier"
    )
    
    overall_score: float = Field(...,
        description="Final value score (0.0-1.0)"
    )
    
    component_scores: List[FloatValue] = Field(...,
        description="Individual component scores as key-value pairs"
    )
    
    reasoning: str = Field(...,
        description="Explanation of how score was calculated"
    )
    
    strengths: List[str] = Field(
        default=[],
        description="Product strengths that boosted score"
    )
    
    weaknesses: List[str] = Field(
        default=[],
        description="Product weaknesses that lowered score"
    )
    
    confidence: float = Field(...,
        description="Confidence in this scoring"
    )


class RecommendationExplanation(BaseModel):
    """Detailed explanation for a product recommendation."""
    
    product_id: str = Field(...,
        description="Recommended product ASIN"
    )
    
    product_name: str = Field(...,
        description="Product name"
    )
    
    why_recommended: str = Field(...,
        description="Primary reason for recommendation"
    )
    
    match_quality: float = Field(...,
        description="How well product matches user requirements"
    )
    
    satisfied_needs: List[str] = Field(...,
        description="User needs this product satisfies"
    )
    
    value_proposition: str = Field(...,
        description="What makes this product good value"
    )
    
    pros: List[str] = Field(...,
        description="Advantages of this product"
    )
    
    cons: List[str] = Field(...,
        description="Disadvantages or compromises"
    )
    
    alternatives_considered: List[str] = Field(
        default=[],
        description="Other products considered and why rejected"
    )
    
    confidence_breakdown: List[FloatValue] = Field(...,
        description="Confidence scores as key-value pairs"
    )
    
    overall_confidence: float = Field(...,
        description="Overall confidence in recommendation"
    )


class TradeoffAnalysis(BaseModel):
    """Analysis of tradeoffs between product options."""
    
    comparison_pairs: str = Field(...,
        description="Pairs of products being compared for tradeoffs (JSON string)"
    )
    
    budget_vs_quality: str = Field(...,
        description="Analysis of price vs quality tradeoffs"
    )
    
    features_vs_price: str = Field(...,
        description="Analysis of feature richness vs cost"
    )
    
    brand_vs_value: str = Field(...,
        description="Analysis of brand premium vs generic value"
    )
    
    recommendations: List[StringValue] = Field(...,
        description="Recommendations as key-value pairs"
    )
    
    best_budget: str = Field(...,
        description="Best budget-friendly option"
    )
    
    best_value: str = Field(...,
        description="Best overall value option"
    )
    
    best_premium: str = Field(...,
        description="Best premium/high-end option"
    )


class RedFlag(BaseModel):
    """A red flag or warning about a product."""
    
    product_id: str = Field(...,
        description="Product ASIN with the red flag"
    )
    
    flag_type: Literal[
        "price_anomaly",
        "rating_suspicious",
        "review_quality",
        "missing_info",
        "seller_issue"
    ] = Field(...,
        description="Type of red flag"
    )
    
    severity: Literal["low", "medium", "high"] = Field(...,
        description="How serious is this red flag"
    )
    
    description: str = Field(...,
        description="What the red flag is"
    )
    
    reasoning: str = Field(...,
        description="Why this is concerning"
    )
    
    recommendation: str = Field(...,
        description="What user should do about it"
    )



class ReviewAnalysis(BaseModel):
    """Analysis of product reviews."""
    summary: str = Field(..., description="Brief summary of the analysis")
    sentiment_score: float = Field(..., description="Overall sentiment score (0.0-1.0)")
    pros: List[str] = Field(..., description="List of pros mentioned by users")
    cons: List[str] = Field(..., description="List of cons mentioned by users")
    aspect_sentiment: Dict[str, str] = Field(..., description="Sentiment for specific aspects (e.g. quality: positive)")


class AuthenticityCheck(BaseModel):
    """Check for fake reviews."""
    authenticity_score: float = Field(..., description="Score from 0-100 (100=authentic)")
    flags: List[str] = Field(..., description="List of suspicious flags detected")
    reasoning: str = Field(..., description="Explanation for the score")


class MarketAnalysis(BaseModel):
    """Market trend analysis."""
    market_segment: str = Field(default="Unknown", description="Market segment (e.g. Premium, Budget)")
    price_insight: str = Field(default="No insight available", description="Insight about pricing trends")
    brand_insight: str = Field(default="No insight available", description="Insight about brand dominance")
    gap_analysis: str = Field(default="No analysis available", description="Identified market gaps or opportunities")
    recommendation_strategy: str = Field(default="N/A", description="Strategic recommendation based on market analysis")


class PriceAnalysis(BaseModel):
    """Price history analysis."""
    recommendation: Literal["Buy Now", "Wait", "Neutral"] = Field(default="Neutral", description="Buy recommendation")
    confidence: float = Field(default=0.0, description="Confidence score (0.0-1.0)")
    price_status: Literal["All-Time Low", "Good Deal", "Fair Price", "Overpriced"] = Field(default="Fair Price", description="Current price status")
    savings_percentage: float = Field(default=0.0, description="Estimated savings vs average")
    reasoning: str = Field(default="Analysis incomplete", description="Explanation of the recommendation")


class AnalysisResult(BaseModel):
    """Complete analysis result with reasoning."""
    
    products_analyzed: int = Field(...,
        description="Number of products analyzed"
    )
    
    reasoning_chain: List[ReasoningStep] = Field(...,
        description="Overall analysis reasoning chain"
    )
    
    value_scores: List[ValueScore] = Field(...,
        description="Value scores for all products"
    )
    
    top_recommendation: RecommendationExplanation = Field(...,
        description="Detailed explanation of top recommendation"
    )
    
    tradeoff_analysis: TradeoffAnalysis = Field(...,
        description="Tradeoff analysis between options"
    )
    
    red_flags: List[RedFlag] = Field(
        default=[],
        description="Any red flags detected"
    )
    
    confidence: float = Field(...,
        description="Overall confidence in analysis"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional analysis metadata"
    )
    
    # Aggregated Intelligence Data
    review_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Aggregated review analysis results"
    )
    
    market_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Aggregated market analysis results"
    )
    
    price_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Aggregated price analysis results"
    )

# Rebuild model to resolve forward references
AnalysisResult.model_rebuild()
