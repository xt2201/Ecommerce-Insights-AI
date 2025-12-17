"""Knowledge Graph data models for entity extraction and relationship linking."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Literal

from pydantic import BaseModel, Field


# =============================================================================
# Entity & Relationship Types
# =============================================================================

EntityType = Literal[
    "policy",           # Store policies (returns, shipping, etc.)
    "faq",              # FAQ items
    "product",          # Product mentions
    "brand",            # Brand names
    "category",         # Product categories
    "feature",          # Product features
    "price_point",      # Price ranges or values
    "use_case",         # Usage scenarios
    "attribute",        # Other attributes (color, size, etc.)
    "time_period",      # Time-related (30 days, 24 hours, etc.)
    "condition",        # Conditions (unused, original packaging, etc.)
    "action",           # Actions (refund, exchange, return, etc.)
]

RelationshipType = Literal[
    # Policy relationships
    "has_condition",        # Policy → Condition
    "has_time_limit",       # Policy → TimePeriod
    "allows_action",        # Policy → Action
    "applies_to",           # Policy → Category/Product
    "requires",             # Policy/Action → Condition
    "results_in",           # Action → Action (return → refund)
    
    # Product relationships
    "is_brand_of",          # Brand → Product
    "belongs_to_category",  # Product → Category
    "has_feature",          # Product → Feature
    "competes_with",        # Product ↔ Product
    "is_alternative_to",    # Product → Product
    "is_variant_of",        # Product → Product
    "recommended_for",      # Product → UseCase
    
    # FAQ relationships
    "answers_question",     # FAQ → Topic
    "related_to",           # FAQ ↔ Policy
    "see_also",             # Any ↔ Any
]


# =============================================================================
# Pydantic Models for LLM Extraction
# =============================================================================

class ExtractedEntity(BaseModel):
    """Entity extracted by LLM from text."""
    
    name: str = Field(..., description="Normalized entity name (lowercase)")
    entity_type: str = Field(..., description="Type of entity")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    aliases: List[str] = Field(default_factory=list, description="Alternative names")
    properties: Dict[str, Any] = Field(default_factory=dict)
    language: str = Field(default="en", description="Entity language: en, vi")
    
    class Config:
        extra = "allow"


class ExtractedRelationship(BaseModel):
    """Relationship extracted by LLM."""
    
    source_entity: str = Field(..., description="Source entity name")
    target_entity: str = Field(..., description="Target entity name")
    relationship_type: str = Field(..., description="Type of relationship")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    properties: Dict[str, Any] = Field(default_factory=dict)
    bidirectional: bool = Field(default=False, description="If true, relationship goes both ways")
    
    class Config:
        extra = "allow"


class ExtractionResult(BaseModel):
    """Complete extraction result from LLM."""
    
    entities: List[ExtractedEntity] = Field(default_factory=list)
    relationships: List[ExtractedRelationship] = Field(default_factory=list)
    reasoning: str = Field(default="", description="LLM's reasoning for extraction")
    source_text: str = Field(default="", description="Original text that was analyzed")
    language_detected: str = Field(default="en", description="Detected language of source")
    
    @property
    def entity_count(self) -> int:
        return len(self.entities)
    
    @property
    def relationship_count(self) -> int:
        return len(self.relationships)
    
    def get_entities_by_type(self, entity_type: str) -> List[ExtractedEntity]:
        return [e for e in self.entities if e.entity_type == entity_type]


# =============================================================================
# Dataclass Models for Persistent Storage
# =============================================================================

@dataclass
class GraphEntity:
    """Persisted entity in the knowledge graph."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    entity_type: str = ""
    aliases: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    language: str = "en"
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    source_count: int = 1  # How many times extracted from different sources
    confidence: float = 0.8
    source_ids: List[str] = field(default_factory=list)  # Document IDs that mention this entity
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type,
            "aliases": self.aliases,
            "properties": self.properties,
            "language": self.language,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "source_count": self.source_count,
            "confidence": self.confidence,
            "source_ids": self.source_ids,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GraphEntity:
        data = data.copy()
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        data.pop("embedding", None)  # Don't include embedding in from_dict
        return cls(**data)
    
    @classmethod
    def from_extracted(cls, extracted: ExtractedEntity, source_id: Optional[str] = None) -> GraphEntity:
        """Create GraphEntity from ExtractedEntity."""
        return cls(
            name=extracted.name.lower().strip(),
            entity_type=extracted.entity_type,
            aliases=[a.lower().strip() for a in extracted.aliases],
            properties=extracted.properties,
            language=extracted.language,
            confidence=extracted.confidence,
            source_ids=[source_id] if source_id else [],
        )
    
    def merge_with(self, other: GraphEntity) -> None:
        """Merge another entity into this one (same entity, different sources)."""
        # Merge aliases
        for alias in other.aliases:
            if alias not in self.aliases and alias != self.name:
                self.aliases.append(alias)
        
        # Merge properties
        self.properties.update(other.properties)
        
        # Merge source IDs
        for sid in other.source_ids:
            if sid not in self.source_ids:
                self.source_ids.append(sid)
        
        # Update metadata
        self.source_count += 1
        self.confidence = min(1.0, (self.confidence + other.confidence) / 2 + 0.05)
        self.updated_at = datetime.now()


@dataclass
class GraphRelationship:
    """Persisted relationship in the knowledge graph."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""  # GraphEntity ID
    target_id: str = ""  # GraphEntity ID
    relationship_type: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    bidirectional: bool = False
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    weight: float = 1.0  # Relationship strength
    confidence: float = 0.8
    source_doc_ids: List[str] = field(default_factory=list)  # Documents that establish this relationship
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "properties": self.properties,
            "bidirectional": self.bidirectional,
            "created_at": self.created_at.isoformat(),
            "weight": self.weight,
            "confidence": self.confidence,
            "source_doc_ids": self.source_doc_ids,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GraphRelationship:
        data = data.copy()
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


@dataclass
class GraphQueryResult:
    """Result from a knowledge graph query."""
    
    entities: List[GraphEntity] = field(default_factory=list)
    relationships: List[GraphRelationship] = field(default_factory=list)
    paths: List[List[str]] = field(default_factory=list)  # Entity ID paths for traversal
    relevance_scores: Dict[str, float] = field(default_factory=dict)  # entity_id → score
    
    @property
    def context_text(self) -> str:
        """Format result as text context for LLM prompts."""
        if not self.entities:
            return ""
        
        parts = []
        
        # Group entities by type
        entities_by_type: Dict[str, List[GraphEntity]] = {}
        for entity in self.entities:
            if entity.entity_type not in entities_by_type:
                entities_by_type[entity.entity_type] = []
            entities_by_type[entity.entity_type].append(entity)
        
        for etype, entities in entities_by_type.items():
            parts.append(f"\n## {etype.title()}s:")
            for e in entities:
                props = ", ".join(f"{k}: {v}" for k, v in e.properties.items()) if e.properties else ""
                aliases = f" (also: {', '.join(e.aliases)})" if e.aliases else ""
                parts.append(f"- {e.name}{aliases}{' | ' + props if props else ''}")
        
        if self.relationships:
            parts.append("\n## Relationships:")
            for rel in self.relationships:
                source = next((e.name for e in self.entities if e.id == rel.source_id), rel.source_id)
                target = next((e.name for e in self.entities if e.id == rel.target_id), rel.target_id)
                arrow = "↔" if rel.bidirectional else "→"
                parts.append(f"- {source} {arrow} [{rel.relationship_type}] {arrow} {target}")
        
        return "\n".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
            "paths": self.paths,
            "relevance_scores": self.relevance_scores,
            "context_text": self.context_text,
        }


# =============================================================================
# Document Models for KnowledgeBase
# =============================================================================

@dataclass
class PolicyDocument:
    """A policy document for the knowledge base."""
    
    id: str = ""
    text: str = ""
    category: str = ""  # returns, shipping, payment, warranty, account
    subcategory: str = ""
    language: str = "en"
    keywords: List[str] = field(default_factory=list)
    last_updated: str = ""
    related_ids: List[str] = field(default_factory=list)  # Links to related docs
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "metadata": {
                "type": "policy",
                "category": self.category,
                "subcategory": self.subcategory,
                "language": self.language,
                "keywords": self.keywords,
                "last_updated": self.last_updated,
                "related_ids": self.related_ids,
            }
        }


@dataclass
class FAQDocument:
    """A FAQ document for the knowledge base."""
    
    id: str = ""
    question: str = ""
    answer: str = ""
    category: str = ""
    language: str = "en"
    keywords: List[str] = field(default_factory=list)
    related_policy_ids: List[str] = field(default_factory=list)
    
    @property
    def text(self) -> str:
        """Combined Q&A for embedding."""
        return f"Q: {self.question}\nA: {self.answer}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "metadata": {
                "type": "faq",
                "category": self.category,
                "question": self.question,
                "language": self.language,
                "keywords": self.keywords,
                "related_policy_ids": self.related_policy_ids,
            }
        }
