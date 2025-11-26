"""Pydantic models for Response Agent - Enhanced Response Generation."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal, Optional
from datetime import datetime


class ExecutiveSummary(BaseModel):
    """Concise summary of analysis and recommendation."""
    
    best_recommendation: str = Field(...,
        description="Name/ASIN of best recommended product"
    )
    
    key_reason: str = Field(...,
        description="Primary reason for recommendation (1 sentence)"
    )
    
    market_overview: str = Field(...,
        description="Brief overview of options available (1 sentence)"
    )
    
    confidence_statement: str = Field(...,
        description="Statement about confidence level (1 sentence)"
    )


class RecommendationDetails(BaseModel):
    """Detailed information about recommended product."""
    
    product_id: str = Field(...,
        description="Product ASIN"
    )
    
    product_name: str = Field(...,
        description="Product name"
    )
    
    price: Optional[float] = Field(None,
        description="Product price in USD (None if not available)"
    )
    
    rating: Optional[float] = Field(None,
        description="Product rating (None if not available)"
    )
    
    value_score: float = Field(...,
        description="Value score from analysis"
    )
    
    why_recommended: str = Field(...,
        description="Explanation of why this product is recommended"
    )
    
    key_specs: List[str] = Field(...,
        description="Key specifications (3-5 most important)"
    )
    
    pros: List[str] = Field(...,
        description="Advantages (3-5 points)"
    )
    
    cons: List[str] = Field(...,
        description="Disadvantages (2-3 points)"
    )
    
    best_for: str = Field(...,
        description="Who this product is best for"
    )
    
    purchase_link: str = Field(
        default="",
        description="Amazon link (if available)"
    )


class ComparisonRow(BaseModel):
    """Single row in comparison table."""
    
    rank: int = Field(...,
        description="Ranking position"
    )
    
    product_name: str = Field(...,
        description="Product name (truncated if needed)"
    )
    
    price: Optional[float] = Field(None,
        description="Price in USD (None if not available)"
    )
    
    rating: Optional[float] = Field(None,
        description="Product rating out of 5 (None if not available)"
    )
    
    reviews_count: int = Field(
        default=0,
        description="Number of reviews (0 if not available)"
    )
    
    key_features: List[str] = Field(...,
        description="3-4 most important features"
    )
    
    value_score: float = Field(...,
        description="Value score"
    )
    
    best_for: str = Field(...,
        description="Use case or user type"
    )
    
    pros: List[str] = Field(...,
        description="Key advantages (2-3)"
    )
    
    cons: List[str] = Field(...,
        description="Key disadvantages (2-3)"
    )
    
    purchase_link: str = Field(
        default="",
        description="Amazon product link"
    )


class ComparisonTable(BaseModel):
    """Structured comparison table."""
    
    columns: List[str] = Field(...,
        description="Column headers"
    )
    
    rows: List[ComparisonRow] = Field(...,
        description="Comparison rows for each product"
    )
    
    notes: List[str] = Field(
        default=[],
        description="Additional notes or context"
    )


class ReasoningSummary(BaseModel):
    """Summary explaining the analysis methodology."""
    
    data_collection: str = Field(...,
        description="What data sources were used (1-2 sentences)"
    )
    
    analysis_methodology: str = Field(...,
        description="How products were analyzed and scored (3-4 sentences)"
    )
    
    key_factors: List[str] = Field(...,
        description="Main factors considered (price, rating, features, etc.)"
    )
    
    confidence_assessment: str = Field(...,
        description="Overall confidence and any limitations (2-3 sentences)"
    )
    
    confidence_level: Literal["high", "medium", "low"] = Field(...,
        description="Overall confidence level"
    )


class FollowUpSuggestion(BaseModel):
    """A single follow-up suggestion."""
    
    suggestion_type: Literal[
        "refinement",
        "related_search",
        "alternative_scenario"
    ] = Field(...,
        description="Type of suggestion"
    )
    
    text: str = Field(...,
        description="The suggestion text (question or statement)"
    )
    
    example_query: str = Field(
        default="",
        description="Example query user could ask (optional)"
    )


class FollowUpSuggestions(BaseModel):
    """Collection of follow-up suggestions."""
    
    suggestions: List[FollowUpSuggestion] = Field(...,
        description="3-5 follow-up suggestions"
    )
    
    priority_suggestion: str = Field(
        default="",
        description="Most important next step (if any)"
    )


class RedFlagSummary(BaseModel):
    """Summary of red flags for user display."""
    
    has_red_flags: bool = Field(...,
        description="Whether any red flags were detected"
    )
    
    total_count: int = Field(...,
        description="Total number of red flags"
    )
    
    high_severity_count: int = Field(...,
        description="Number of high-severity flags"
    )
    
    summary_text: str = Field(...,
        description="Brief summary of red flags (2-3 sentences)"
    )
    
    warnings: List[str] = Field(
        default=[],
        description="Specific warnings to show user"
    )


class FinalResponse(BaseModel):
    """Complete response structure for user."""
    
    executive_summary: ExecutiveSummary = Field(...,
        description="Answer summary"
    )
    
    recommendations: List[RecommendationDetails] = Field(...,
        description="List of recommended products ranked by value (top 3-5). First item is the top recommendation."
    )
    
    comparison_table: ComparisonTable = Field(...,
        description="Comparison of top products"
    )
    
    reasoning_summary: ReasoningSummary = Field(...,
        description="Explanation of analysis methodology"
    )
    
    follow_up_suggestions: FollowUpSuggestions = Field(...,
        description="Next steps and suggestions"
    )
    
    red_flags: RedFlagSummary = Field(...,
        description="Red flags summary (if any)"
    )
    
    formatted_markdown: str = Field(
        default="",
        description="Fully formatted markdown response"
    )


class ResponseGenerationResult(BaseModel):
    """Result of response generation process."""
    
    success: bool = Field(...,
        description="Whether response generation succeeded"
    )
    
    final_response: FinalResponse = Field(...,
        description="Complete final response"
    )
    
    generation_time: float = Field(...,
        description="Time taken to generate response (seconds)"
    )
    
    tokens_used: int = Field(...,
        description="Estimated tokens used (if available)"
    )
    
    errors: List[str] = Field(
        default=[],
        description="Any errors encountered during generation"
    )
