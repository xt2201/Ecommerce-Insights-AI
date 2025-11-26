# Agent Output Models for Planning Agent

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class QueryIntentAnalysis(BaseModel):
    """Analysis of user query intent."""
    
    intent: str = Field(...,
        description="Intent type: product_search, comparison, or recommendation"
    )
    specificity: float = Field(...,
        description="How specific the query is (0=vague, 1=very specific)"
    )
    requires_clarification: bool = Field(...,
        description="Whether query needs clarification"
    )
    confidence: float = Field(...,
        description="Confidence level in this analysis"
    )


class ExpandedKeywords(BaseModel):
    """Alternative search keywords."""
    
    keywords: List[str] = Field(...,
        description="List of alternative search keywords")


class QueryRequirements(BaseModel):
    """Extracted requirements from query."""
    
    max_price: Optional[float] = Field(
        None,
        description="Maximum price constraint (null if not mentioned)"
    )
    min_rating: Optional[float] = Field(
        None,
        description="Minimum rating constraint (null if not mentioned)"
    )
    required_features: List[str] = Field(
        default_factory=list,
        description="List of required features"
    )
    brand_preferences: List[str] = Field(
        default_factory=list,
        description="Preferred brands"
    )
    
    @field_validator('required_features', 'brand_preferences', mode='before')
    @classmethod
    def convert_none_to_list(cls, v):
        """Convert None to empty list for list fields."""
        if v is None:
            return []
        return v


class QueryClassification(BaseModel):
    """Query classification for routing."""
    
    route: str = Field(...,
        description="Route: simple, standard, complex, or clarification"
    )
    confidence: float = Field(...,
        description="Confidence in this classification (0.0 to 1.0)"
    )
    reasoning: str = Field(...,
        description="Explanation for this classification"
    )


class ComprehensiveSearchPlan(BaseModel):
    """Unified search plan containing all analysis components."""
    
    intent_analysis: QueryIntentAnalysis = Field(..., description="Analysis of query intent")
    keywords: List[str] = Field(..., description="Optimized search keywords")
    requirements: QueryRequirements = Field(..., description="Extracted constraints and requirements")
    reasoning: str = Field(..., description="Reasoning behind the plan")
