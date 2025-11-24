"""Pydantic models for Collection Agent v2 - Search Strategy Optimization."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Tuple, Any


class SearchOptimization(BaseModel):
    """Recommendations for optimizing search parameters."""
    
    adjusted_keywords: List[str] = Field(...,
        description="Optimized keywords for better results"
    )
    
    max_price: Optional[float] = Field(
        None,
        description="Suggested maximum price (None = no limit)"
    )
    
    min_rating: Optional[float] = Field(
        None,
        description="Suggested minimum rating filter"
    )
    
    reasoning: str = Field(...,
        description="Explanation of optimization strategy"
    )
    
    expected_improvement: float = Field(...,
        description="Expected improvement score (0.0-1.0)"
    )
    
    alternative_approaches: List[str] = Field(
        default=[],
        description="Alternative search strategies to try"
    )


class SearchQualityAssessment(BaseModel):
    """Assessment of search result quality."""
    
    quality_score: float = Field(...,
        description="Overall quality score (0.0-1.0)"
    )
    
    is_sufficient: bool = Field(...,
        description="Whether results are sufficient to proceed"
    )
    
    issues: List[str] = Field(
        default=[],
        description="List of quality issues found"
    )
    
    strengths: List[str] = Field(
        default=[],
        description="Positive aspects of results"
    )
    
    should_retry: bool = Field(...,
        description="Whether search should be retried with different params"
    )
    
    retry_reason: Optional[str] = Field(
        None,
        description="Explanation if retry is recommended"
    )
    
    confidence: float = Field(...,
        description="Confidence in this assessment"
    )


class AlternativeKeywords(BaseModel):
    """Alternative keyword suggestions for improved search."""
    
    keyword_sets: List[List[str]] = Field(...,
        description="Alternative keyword combinations (1-5 sets)"
    )
    
    rationale: List[str] = Field(...,
        description="Explanation for each keyword set"
    )
    
    expected_relevance: List[float] = Field(...,
        description="Expected relevance score for each set (0.0-1.0)"
    )
    
    recommended_order: List[int] = Field(...,
        description="Indices of keyword sets in recommended try order"
    )


class SearchConfidence(BaseModel):
    """Confidence assessment for search strategy."""
    
    confidence_score: float = Field(...,
        description="Overall confidence in search strategy (0.0-1.0)"
    )
    
    factors: List[Any] = Field(...,
        description="Individual factor scores (use FloatValue model if importing from analysis_models)"
    )
    
    risk_level: Literal["low", "medium", "high"] = Field(...,
        description="Risk level of poor results"
    )
    
    reasoning: str = Field(...,
        description="Detailed explanation of confidence assessment"
    )
    
    recommendations: List[str] = Field(
        default=[],
        description="Recommendations to improve confidence"
    )


class SearchMetrics(BaseModel):
    """Metrics about search execution and results."""
    
    products_found: int = Field(...,
        description="Number of products returned"
    )
    
    data_completeness: float = Field(...,
        description="Percentage of products with complete data"
    )
    
    price_coverage: float = Field(...,
        description="Percentage of products with price data"
    )
    
    rating_coverage: float = Field(...,
        description="Percentage of products with rating data"
    )
    
    review_coverage: float = Field(...,
        description="Percentage of products with review counts"
    )
    
    price_range: Optional[Tuple[float, float]] = Field(
        None,
        description="Min and max prices found (min, max)"
    )
    
    rating_range: Optional[Tuple[float, float]] = Field(
        None,
        description="Min and max ratings found (min, max)"
    )
    
    search_time_ms: int = Field(...,
        description="Time taken for search in milliseconds"
    )
