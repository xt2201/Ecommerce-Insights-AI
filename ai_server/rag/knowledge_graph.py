"""Knowledge Graph: Entity storage, relationship linking, and graph traversal."""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional

from ai_server.core.config import get_config_value
from ai_server.memory.vector_memory import VectorMemory
from ai_server.rag.entity_extractor import EntityExtractor, get_entity_extractor
from ai_server.rag.graph_storage import SQLiteGraphStorage
from ai_server.schemas.knowledge_graph_models import (
    GraphEntity,
    GraphRelationship,
    GraphQueryResult,
    ExtractionResult,
    ExtractedEntity,
    ExtractedRelationship,
)

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """
    Knowledge Graph with entity extraction, relationship linking, and hybrid search.
    
    Combines:
    - SQLite graph storage for entities and relationships
    - FAISS vector memory for semantic entity search
    - LLM-powered entity extraction
    """
    
    _instance: Optional["KnowledgeGraph"] = None
    
    def __new__(cls):
        """Singleton pattern for KnowledgeGraph."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the Knowledge Graph."""
        if self._initialized:
            return
        
        # Graph storage (SQLite)
        self.storage = SQLiteGraphStorage()
        
        # Vector memory for entity embeddings
        self.vector_memory = VectorMemory(collection_name="knowledge_graph_entities")
        
        # Entity extractor (lazy loaded)
        self._extractor: Optional[EntityExtractor] = None
        
        # Config
        self.max_hops = get_config_value("knowledge_graph.retrieval.max_hops", 2)
        self.top_k_entities = get_config_value("knowledge_graph.retrieval.top_k_entities", 10)
        self.min_confidence = get_config_value("knowledge_graph.extraction.min_confidence", 0.7)
        
        self._initialized = True
        logger.info(f"KnowledgeGraph initialized (entities: {self.storage.count_entities()}, relationships: {self.storage.count_relationships()})")
    
    @property
    def extractor(self) -> EntityExtractor:
        """Lazy load entity extractor."""
        if self._extractor is None:
            self._extractor = get_entity_extractor()
        return self._extractor
    
    # =========================================================================
    # Entity Management
    # =========================================================================
    
    def add_entity(
        self,
        name: str,
        entity_type: str,
        language: str = "en",
        aliases: Optional[List[str]] = None,
        properties: Optional[Dict[str, Any]] = None,
        source_id: Optional[str] = None,
    ) -> GraphEntity:
        """Add an entity to the graph.
        
        Args:
            name: Entity name.
            entity_type: Type of entity.
            language: Entity language.
            aliases: Alternative names.
            properties: Additional properties.
            source_id: Source document ID.
            
        Returns:
            The created or updated GraphEntity.
        """
        name = name.lower().strip()
        
        # Check if entity already exists
        existing = self.storage.get_entity_by_name(name, entity_type, language)
        
        if existing:
            # Merge with existing
            if aliases:
                for alias in aliases:
                    if alias.lower().strip() not in existing.aliases:
                        existing.aliases.append(alias.lower().strip())
            if properties:
                existing.properties.update(properties)
            if source_id and source_id not in existing.source_ids:
                existing.source_ids.append(source_id)
            existing.source_count += 1
            
            self.storage.update_entity(existing)
            logger.debug(f"Updated existing entity: {name}")
            return existing
        
        # Create new entity
        entity = GraphEntity(
            name=name,
            entity_type=entity_type,
            language=language,
            aliases=[a.lower().strip() for a in (aliases or [])],
            properties=properties or {},
            source_ids=[source_id] if source_id else [],
        )
        
        self.storage.add_entity(entity)
        
        # Add to vector memory for semantic search
        self._index_entity(entity)
        
        logger.debug(f"Added new entity: {name} ({entity_type})")
        return entity
    
    def _index_entity(self, entity: GraphEntity) -> None:
        """Index entity in vector memory for semantic search."""
        # Create searchable text from entity
        text_parts = [entity.name]
        text_parts.extend(entity.aliases)
        if entity.properties:
            text_parts.extend(str(v) for v in entity.properties.values() if v)
        
        text = " | ".join(text_parts)
        
        self.vector_memory.add_turn(
            text=text,
            metadata={
                "entity_id": entity.id,
                "entity_type": entity.entity_type,
                "language": entity.language,
                "name": entity.name,
            }
        )
    
    def get_entity(self, entity_id: str) -> Optional[GraphEntity]:
        """Get entity by ID."""
        return self.storage.get_entity(entity_id)
    
    def find_entity(
        self,
        name: str,
        entity_type: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Optional[GraphEntity]:
        """Find entity by name."""
        return self.storage.get_entity_by_name(name.lower().strip(), entity_type, language)
    
    def search_entities(
        self,
        query: str,
        entity_type: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 10,
        use_semantic: bool = True,
    ) -> List[GraphEntity]:
        """Search entities by query.
        
        Args:
            query: Search query.
            entity_type: Filter by entity type.
            language: Filter by language.
            limit: Maximum results.
            use_semantic: Use vector search (True) or text search (False).
            
        Returns:
            List of matching entities.
        """
        if use_semantic:
            # Semantic search via vector memory
            results = self.vector_memory.search(
                query=query,
                k=limit * 2,  # Get more, then filter
                filter_metadata={"entity_type": entity_type} if entity_type else None,
            )
            
            entities = []
            seen_ids = set()
            
            for result in results:
                entity_id = result.get("metadata", {}).get("entity_id")
                if entity_id and entity_id not in seen_ids:
                    entity = self.storage.get_entity(entity_id)
                    if entity:
                        if language and entity.language != language:
                            continue
                        entities.append(entity)
                        seen_ids.add(entity_id)
                        
                        if len(entities) >= limit:
                            break
            
            return entities
        
        # Text-based search
        return self.storage.search_entities(
            query=query,
            entity_type=entity_type,
            language=language,
            limit=limit,
        )
    
    # =========================================================================
    # Relationship Management
    # =========================================================================
    
    def add_relationship(
        self,
        source_entity: str,
        target_entity: str,
        relationship_type: str,
        source_type: Optional[str] = None,
        target_type: Optional[str] = None,
        language: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        bidirectional: bool = False,
        source_doc_id: Optional[str] = None,
    ) -> Optional[GraphRelationship]:
        """Add a relationship between entities.
        
        Args:
            source_entity: Source entity name.
            target_entity: Target entity name.
            relationship_type: Type of relationship.
            source_type: Optional source entity type.
            target_type: Optional target entity type.
            language: Language filter for entity lookup.
            properties: Additional properties.
            bidirectional: Whether relationship goes both ways.
            source_doc_id: Source document ID.
            
        Returns:
            The created GraphRelationship, or None if entities not found.
        """
        # Find source entity
        source = self.storage.get_entity_by_name(source_entity.lower().strip(), source_type, language)
        if not source:
            logger.warning(f"Source entity not found: {source_entity}")
            return None
        
        # Find target entity
        target = self.storage.get_entity_by_name(target_entity.lower().strip(), target_type, language)
        if not target:
            logger.warning(f"Target entity not found: {target_entity}")
            return None
        
        # Create relationship
        relationship = GraphRelationship(
            source_id=source.id,
            target_id=target.id,
            relationship_type=relationship_type,
            properties=properties or {},
            bidirectional=bidirectional,
            source_doc_ids=[source_doc_id] if source_doc_id else [],
        )
        
        self.storage.add_relationship(relationship)
        logger.debug(f"Added relationship: {source_entity} -> {relationship_type} -> {target_entity}")
        
        return relationship
    
    def get_entity_relationships(
        self,
        entity_name: str,
        direction: str = "both",
        relationship_type: Optional[str] = None,
    ) -> List[GraphRelationship]:
        """Get relationships for an entity."""
        entity = self.storage.get_entity_by_name(entity_name.lower().strip())
        if not entity:
            return []
        
        return self.storage.get_relationships_for_entity(
            entity.id,
            direction=direction,
            relationship_type=relationship_type,
        )
    
    # =========================================================================
    # Extraction & Ingestion
    # =========================================================================
    
    def extract_and_store(
        self,
        text: str,
        doc_id: Optional[str] = None,
        doc_type: str = "unknown",
        category: str = "general",
        language: Optional[str] = None,
    ) -> ExtractionResult:
        """Extract entities and relationships from text and store in graph.
        
        Args:
            text: Text to extract from.
            doc_id: Document ID.
            doc_type: Document type.
            category: Document category.
            language: Language hint (auto-detected if None).
            
        Returns:
            ExtractionResult with extracted entities and relationships.
        """
        # Detect language if not provided
        if language is None:
            language = self.extractor.detect_language(text)
        
        # Extract entities and relationships
        result = self.extractor.extract(
            text=text,
            doc_id=doc_id,
            doc_type=doc_type,
            category=category,
            language=language,
        )
        
        if not result.entities:
            logger.debug("No entities extracted from text")
            return result
        
        # Store entities
        entity_name_to_id: Dict[str, str] = {}
        
        for extracted in result.entities:
            if extracted.confidence < self.min_confidence:
                continue
            
            entity = self.add_entity(
                name=extracted.name,
                entity_type=extracted.entity_type,
                language=extracted.language,
                aliases=extracted.aliases,
                properties=extracted.properties,
                source_id=doc_id,
            )
            entity_name_to_id[extracted.name.lower()] = entity.id
        
        # Store relationships
        for rel in result.relationships:
            if rel.confidence < self.min_confidence:
                continue
            
            self.add_relationship(
                source_entity=rel.source_entity,
                target_entity=rel.target_entity,
                relationship_type=rel.relationship_type,
                language=language,
                properties=rel.properties,
                bidirectional=rel.bidirectional,
                source_doc_id=doc_id,
            )
        
        logger.info(
            f"Stored {len(entity_name_to_id)} entities and "
            f"{len(result.relationships)} relationships from doc {doc_id}"
        )
        
        return result
    
    def ingest_from_documents(
        self,
        documents: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        """Ingest multiple documents into the knowledge graph.
        
        Args:
            documents: List of documents with 'id', 'text', 'type', 'category', 'language'.
            
        Returns:
            Statistics dict with 'documents', 'entities', 'relationships' counts.
        """
        stats = {"documents": 0, "entities": 0, "relationships": 0}
        
        for doc in documents:
            result = self.extract_and_store(
                text=doc.get("text", ""),
                doc_id=doc.get("id"),
                doc_type=doc.get("type", "unknown"),
                category=doc.get("category", "general"),
                language=doc.get("language"),
            )
            
            stats["documents"] += 1
            stats["entities"] += result.entity_count
            stats["relationships"] += result.relationship_count
        
        logger.info(f"Ingested {stats['documents']} documents: {stats['entities']} entities, {stats['relationships']} relationships")
        return stats
    
    # =========================================================================
    # Graph Queries
    # =========================================================================
    
    def query_related(
        self,
        entity_names: List[str],
        max_hops: Optional[int] = None,
        relationship_types: Optional[List[str]] = None,
        include_source_entities: bool = True,
    ) -> GraphQueryResult:
        """Query entities related to given entity names.
        
        Args:
            entity_names: List of entity names to start from.
            max_hops: Maximum traversal depth.
            relationship_types: Filter by relationship types.
            include_source_entities: Include source entities in result.
            
        Returns:
            GraphQueryResult with related entities and relationships.
        """
        max_hops = max_hops or self.max_hops
        
        all_entities: Dict[str, GraphEntity] = {}
        all_relationships: Dict[str, GraphRelationship] = {}
        
        for name in entity_names:
            entity = self.storage.get_entity_by_name(name.lower().strip())
            if not entity:
                continue
            
            if include_source_entities:
                all_entities[entity.id] = entity
            
            # Get neighbors
            result = self.storage.get_neighbors(
                entity.id,
                max_hops=max_hops,
                relationship_types=relationship_types,
            )
            
            for e in result.entities:
                if e.id not in all_entities:
                    all_entities[e.id] = e
            
            for r in result.relationships:
                if r.id not in all_relationships:
                    all_relationships[r.id] = r
        
        return GraphQueryResult(
            entities=list(all_entities.values()),
            relationships=list(all_relationships.values()),
        )
    
    def get_entity_context(
        self,
        query: str,
        language: Optional[str] = None,
        max_entities: Optional[int] = None,
        max_hops: Optional[int] = None,
    ) -> str:
        """Get context text for a query from the knowledge graph.
        
        This is the main method for RAG integration - returns formatted
        text context from related entities and relationships.
        
        Args:
            query: User query.
            language: Language filter.
            max_entities: Maximum entities to include.
            max_hops: Maximum relationship hops.
            
        Returns:
            Formatted context string for LLM.
        """
        max_entities = max_entities or self.top_k_entities
        max_hops = max_hops or self.max_hops
        
        # Search for relevant entities
        entities = self.search_entities(
            query=query,
            language=language,
            limit=max_entities,
            use_semantic=True,
        )
        
        if not entities:
            return ""
        
        # Get related context
        result = self.query_related(
            entity_names=[e.name for e in entities],
            max_hops=max_hops,
            include_source_entities=True,
        )
        
        return result.context_text
    
    def find_path(
        self,
        source_name: str,
        target_name: str,
        max_hops: int = 3,
    ) -> List[List[str]]:
        """Find paths between two entities.
        
        Args:
            source_name: Source entity name.
            target_name: Target entity name.
            max_hops: Maximum path length.
            
        Returns:
            List of paths (each path is list of entity names).
        """
        source = self.storage.get_entity_by_name(source_name.lower().strip())
        target = self.storage.get_entity_by_name(target_name.lower().strip())
        
        if not source or not target:
            return []
        
        paths = self.storage.find_path(source.id, target.id, max_hops)
        
        # Convert entity IDs to names
        named_paths = []
        for path in paths:
            named_path = []
            for entity_id in path:
                entity = self.storage.get_entity(entity_id)
                if entity:
                    named_path.append(entity.name)
            if len(named_path) == len(path):
                named_paths.append(named_path)
        
        return named_paths
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge graph statistics."""
        return {
            "total_entities": self.storage.count_entities(),
            "total_relationships": self.storage.count_relationships(),
            "entities_by_type": {
                etype: self.storage.count_entities(etype)
                for etype in ["policy", "faq", "action", "condition", "time_period", "category"]
            },
            "vector_index_size": self.vector_memory.count,
        }
    
    def clear(self) -> bool:
        """Clear all data from the knowledge graph."""
        self.storage.clear()
        self.vector_memory.clear()
        logger.info("Knowledge graph cleared")
        return True


# Convenience function
def get_knowledge_graph() -> KnowledgeGraph:
    """Get the singleton KnowledgeGraph instance."""
    return KnowledgeGraph()
