"""Abstract base class for graph storage backends."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from ai_server.schemas.knowledge_graph_models import (
    GraphEntity, GraphRelationship, GraphQueryResult
)


class GraphStorageBase(ABC):
    """Abstract base class for knowledge graph storage backends."""
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the storage backend (create tables, indexes, etc.)."""
        pass
    
    # =========================================================================
    # Entity Operations
    # =========================================================================
    
    @abstractmethod
    def add_entity(self, entity: GraphEntity) -> str:
        """Add an entity to the graph.
        
        Args:
            entity: The entity to add.
            
        Returns:
            The entity ID.
        """
        pass
    
    @abstractmethod
    def get_entity(self, entity_id: str) -> Optional[GraphEntity]:
        """Get an entity by ID.
        
        Args:
            entity_id: The entity ID.
            
        Returns:
            The entity, or None if not found.
        """
        pass
    
    @abstractmethod
    def get_entity_by_name(
        self, 
        name: str, 
        entity_type: Optional[str] = None,
        language: Optional[str] = None
    ) -> Optional[GraphEntity]:
        """Get an entity by name (and optionally type/language).
        
        Args:
            name: Entity name to search for.
            entity_type: Optional entity type filter.
            language: Optional language filter.
            
        Returns:
            The entity, or None if not found.
        """
        pass
    
    @abstractmethod
    def search_entities(
        self,
        query: Optional[str] = None,
        entity_type: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 10
    ) -> List[GraphEntity]:
        """Search for entities matching criteria.
        
        Args:
            query: Text query to match against name/aliases.
            entity_type: Optional entity type filter.
            language: Optional language filter.
            limit: Maximum number of results.
            
        Returns:
            List of matching entities.
        """
        pass
    
    @abstractmethod
    def update_entity(self, entity: GraphEntity) -> bool:
        """Update an existing entity.
        
        Args:
            entity: The entity with updated values.
            
        Returns:
            True if updated, False if not found.
        """
        pass
    
    @abstractmethod
    def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity and its relationships.
        
        Args:
            entity_id: The entity ID to delete.
            
        Returns:
            True if deleted, False if not found.
        """
        pass
    
    # =========================================================================
    # Relationship Operations
    # =========================================================================
    
    @abstractmethod
    def add_relationship(self, relationship: GraphRelationship) -> str:
        """Add a relationship between entities.
        
        Args:
            relationship: The relationship to add.
            
        Returns:
            The relationship ID.
        """
        pass
    
    @abstractmethod
    def get_relationship(self, relationship_id: str) -> Optional[GraphRelationship]:
        """Get a relationship by ID.
        
        Args:
            relationship_id: The relationship ID.
            
        Returns:
            The relationship, or None if not found.
        """
        pass
    
    @abstractmethod
    def get_relationships_for_entity(
        self,
        entity_id: str,
        direction: str = "both",  # "outgoing", "incoming", "both"
        relationship_type: Optional[str] = None
    ) -> List[GraphRelationship]:
        """Get all relationships for an entity.
        
        Args:
            entity_id: The entity ID.
            direction: Which relationships to return.
            relationship_type: Optional filter by relationship type.
            
        Returns:
            List of relationships.
        """
        pass
    
    @abstractmethod
    def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship.
        
        Args:
            relationship_id: The relationship ID to delete.
            
        Returns:
            True if deleted, False if not found.
        """
        pass
    
    # =========================================================================
    # Graph Traversal
    # =========================================================================
    
    @abstractmethod
    def get_neighbors(
        self,
        entity_id: str,
        max_hops: int = 1,
        relationship_types: Optional[List[str]] = None
    ) -> GraphQueryResult:
        """Get neighboring entities within N hops.
        
        Args:
            entity_id: Starting entity ID.
            max_hops: Maximum traversal depth.
            relationship_types: Optional filter by relationship types.
            
        Returns:
            GraphQueryResult with entities and relationships.
        """
        pass
    
    @abstractmethod
    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_hops: int = 3
    ) -> List[List[str]]:
        """Find paths between two entities.
        
        Args:
            source_id: Starting entity ID.
            target_id: Target entity ID.
            max_hops: Maximum path length.
            
        Returns:
            List of paths (each path is a list of entity IDs).
        """
        pass
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    @abstractmethod
    def count_entities(self, entity_type: Optional[str] = None) -> int:
        """Count entities in the graph.
        
        Args:
            entity_type: Optional filter by type.
            
        Returns:
            Number of entities.
        """
        pass
    
    @abstractmethod
    def count_relationships(self, relationship_type: Optional[str] = None) -> int:
        """Count relationships in the graph.
        
        Args:
            relationship_type: Optional filter by type.
            
        Returns:
            Number of relationships.
        """
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """Clear all data from the graph.
        
        Returns:
            True if successful.
        """
        pass
    
    @abstractmethod
    def export_to_dict(self) -> Dict[str, Any]:
        """Export the entire graph as a dictionary.
        
        Returns:
            Dictionary with 'entities' and 'relationships' keys.
        """
        pass
    
    @abstractmethod
    def import_from_dict(self, data: Dict[str, Any]) -> int:
        """Import graph data from a dictionary.
        
        Args:
            data: Dictionary with 'entities' and 'relationships' keys.
            
        Returns:
            Number of items imported.
        """
        pass
