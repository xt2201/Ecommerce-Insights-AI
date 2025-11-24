"""Structured output models for agent responses."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class ProductSummary(BaseModel):
    asin: str = Field(..., description="Amazon Standard Identification Number")
    title: str
    url: HttpUrl
    price: Optional[float] = Field(None)
    rating: Optional[float] = Field(None)
    reviews_count: Optional[int] = Field(None)
    highlights: List[str] = Field(default_factory=list)
    source: Dict[str, Any] = Field(default_factory=dict)


class Recommendation(BaseModel):
    product: ProductSummary
    score: float = Field(...)
    rationale: str


class AnalysisSnapshot(BaseModel):
    cheapest: Optional[ProductSummary] = None
    highest_rated: Optional[ProductSummary] = None
    best_value: Optional[Recommendation] = None
    noteworthy_insights: List[str] = Field(default_factory=list)


class ResponsePayload(BaseModel):
    summary: str
    recommendations: List[Recommendation]
    analysis: AnalysisSnapshot
    raw_products: List[ProductSummary]
