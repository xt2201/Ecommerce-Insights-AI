"""SQLite-based graph storage implementation."""

import json
import logging
import sqlite3
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from ai_server.core.config import get_config_value
from ai_server.schemas.knowledge_graph_models import (
    GraphEntity, GraphRelationship, GraphQueryResult
)
from ai_server.rag.graph_storage.base import GraphStorageBase

logger = logging.getLogger(__name__)


class SQLiteGraphStorage(GraphStorageBase):
    """SQLite-based knowledge graph storage."""
    
    _instance: Optional["SQLiteGraphStorage"] = None
    
    def __new__(cls, db_path: Optional[str] = None):
        """Singleton pattern for graph storage."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize SQLite graph storage.
        
        Args:
            db_path: Path to SQLite database file.
        """
        if self._initialized:
            return
        
        self.db_path = db_path or get_config_value(
            "knowledge_graph.storage.sqlite.db_path",
            "data/knowledge_graph.db"
        )
        
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._conn: Optional[sqlite3.Connection] = None
        self._initialized = True
        
        # Initialize database
        self.initialize()
        
        logger.info(f"SQLiteGraphStorage initialized at {self.db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            # Enable foreign keys
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn
    
    def initialize(self) -> None:
        """Create database tables and indexes."""
        conn = self._get_connection()
        
        # Create entities table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                aliases TEXT DEFAULT '[]',
                properties TEXT DEFAULT '{}',
                language TEXT DEFAULT 'en',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                source_count INTEGER DEFAULT 1,
                confidence REAL DEFAULT 0.8,
                source_ids TEXT DEFAULT '[]'
            )
        """)
        
        # Create relationships table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                properties TEXT DEFAULT '{}',
                bidirectional INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                confidence REAL DEFAULT 0.8,
                source_doc_ids TEXT DEFAULT '[]',
                FOREIGN KEY (source_id) REFERENCES entities(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES entities(id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for efficient querying
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_language ON entities(language)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(relationship_type)")
        
        conn.commit()
        logger.info("SQLite graph storage tables initialized")
    
    # =========================================================================
    # Entity Operations
    # =========================================================================
    
    def add_entity(self, entity: GraphEntity) -> str:
        """Add an entity to the graph."""
        conn = self._get_connection()
        
        try:
            conn.execute("""
                INSERT INTO entities (
                    id, name, entity_type, aliases, properties, language,
                    created_at, updated_at, source_count, confidence, source_ids
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entity.id,
                entity.name.lower().strip(),
                entity.entity_type,
                json.dumps(entity.aliases),
                json.dumps(entity.properties),
                entity.language,
                entity.created_at.isoformat(),
                entity.updated_at.isoformat(),
                entity.source_count,
                entity.confidence,
                json.dumps(entity.source_ids),
            ))
            conn.commit()
            logger.debug(f"Added entity: {entity.name} ({entity.entity_type})")
            return entity.id
        except sqlite3.IntegrityError:
            # Entity already exists, update instead
            self.update_entity(entity)
            return entity.id
    
    def get_entity(self, entity_id: str) -> Optional[GraphEntity]:
        """Get an entity by ID."""
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,))
        row = cursor.fetchone()
        
        if row:
            return self._row_to_entity(row)
        return None
    
    def get_entity_by_name(
        self,
        name: str,
        entity_type: Optional[str] = None,
        language: Optional[str] = None
    ) -> Optional[GraphEntity]:
        """Get an entity by name (and optionally type/language)."""
        conn = self._get_connection()
        
        query = "SELECT * FROM entities WHERE (name = ? OR aliases LIKE ?)"
        params: List[Any] = [name.lower().strip(), f'%"{name.lower().strip()}"%']
        
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        
        if language:
            query += " AND language = ?"
            params.append(language)
        
        cursor = conn.execute(query, params)
        row = cursor.fetchone()
        
        if row:
            return self._row_to_entity(row)
        return None
    
    def search_entities(
        self,
        query: Optional[str] = None,
        entity_type: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 10
    ) -> List[GraphEntity]:
        """Search for entities matching criteria."""
        conn = self._get_connection()
        
        sql = "SELECT * FROM entities WHERE 1=1"
        params: List[Any] = []
        
        if query:
            sql += " AND (name LIKE ? OR aliases LIKE ?)"
            search_term = f"%{query.lower()}%"
            params.extend([search_term, search_term])
        
        if entity_type:
            sql += " AND entity_type = ?"
            params.append(entity_type)
        
        if language:
            sql += " AND language = ?"
            params.append(language)
        
        sql += " ORDER BY confidence DESC, source_count DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(sql, params)
        return [self._row_to_entity(row) for row in cursor.fetchall()]
    
    def update_entity(self, entity: GraphEntity) -> bool:
        """Update an existing entity."""
        conn = self._get_connection()
        
        cursor = conn.execute("""
            UPDATE entities SET
                name = ?,
                entity_type = ?,
                aliases = ?,
                properties = ?,
                language = ?,
                updated_at = ?,
                source_count = ?,
                confidence = ?,
                source_ids = ?
            WHERE id = ?
        """, (
            entity.name.lower().strip(),
            entity.entity_type,
            json.dumps(entity.aliases),
            json.dumps(entity.properties),
            entity.language,
            datetime.now().isoformat(),
            entity.source_count,
            entity.confidence,
            json.dumps(entity.source_ids),
            entity.id,
        ))
        conn.commit()
        return cursor.rowcount > 0
    
    def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity and its relationships."""
        conn = self._get_connection()
        
        # Relationships are deleted via CASCADE
        cursor = conn.execute("DELETE FROM entities WHERE id = ?", (entity_id,))
        conn.commit()
        return cursor.rowcount > 0
    
    # =========================================================================
    # Relationship Operations
    # =========================================================================
    
    def add_relationship(self, relationship: GraphRelationship) -> str:
        """Add a relationship between entities."""
        conn = self._get_connection()
        
        try:
            conn.execute("""
                INSERT INTO relationships (
                    id, source_id, target_id, relationship_type, properties,
                    bidirectional, created_at, weight, confidence, source_doc_ids
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                relationship.id,
                relationship.source_id,
                relationship.target_id,
                relationship.relationship_type,
                json.dumps(relationship.properties),
                1 if relationship.bidirectional else 0,
                relationship.created_at.isoformat(),
                relationship.weight,
                relationship.confidence,
                json.dumps(relationship.source_doc_ids),
            ))
            conn.commit()
            logger.debug(f"Added relationship: {relationship.relationship_type}")
            return relationship.id
        except sqlite3.IntegrityError as e:
            logger.warning(f"Failed to add relationship: {e}")
            return relationship.id
    
    def get_relationship(self, relationship_id: str) -> Optional[GraphRelationship]:
        """Get a relationship by ID."""
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM relationships WHERE id = ?", (relationship_id,))
        row = cursor.fetchone()
        
        if row:
            return self._row_to_relationship(row)
        return None
    
    def get_relationships_for_entity(
        self,
        entity_id: str,
        direction: str = "both",
        relationship_type: Optional[str] = None
    ) -> List[GraphRelationship]:
        """Get all relationships for an entity."""
        conn = self._get_connection()
        
        if direction == "outgoing":
            sql = "SELECT * FROM relationships WHERE source_id = ?"
            params: List[Any] = [entity_id]
        elif direction == "incoming":
            sql = "SELECT * FROM relationships WHERE target_id = ?"
            params = [entity_id]
        else:  # both
            sql = "SELECT * FROM relationships WHERE source_id = ? OR target_id = ?"
            params = [entity_id, entity_id]
        
        if relationship_type:
            sql += " AND relationship_type = ?"
            params.append(relationship_type)
        
        cursor = conn.execute(sql, params)
        return [self._row_to_relationship(row) for row in cursor.fetchall()]
    
    def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship."""
        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM relationships WHERE id = ?", (relationship_id,))
        conn.commit()
        return cursor.rowcount > 0
    
    # =========================================================================
    # Graph Traversal
    # =========================================================================
    
    def get_neighbors(
        self,
        entity_id: str,
        max_hops: int = 1,
        relationship_types: Optional[List[str]] = None
    ) -> GraphQueryResult:
        """Get neighboring entities within N hops using BFS."""
        visited_entities: Dict[str, GraphEntity] = {}
        visited_relationships: Dict[str, GraphRelationship] = {}
        
        # BFS queue: (entity_id, current_depth)
        queue: deque = deque([(entity_id, 0)])
        visited_ids = {entity_id}
        
        # Get starting entity
        start_entity = self.get_entity(entity_id)
        if start_entity:
            visited_entities[entity_id] = start_entity
        
        while queue:
            current_id, depth = queue.popleft()
            
            if depth >= max_hops:
                continue
            
            # Get relationships for current entity
            relationships = self.get_relationships_for_entity(
                current_id,
                direction="both",
                relationship_type=relationship_types[0] if relationship_types and len(relationship_types) == 1 else None
            )
            
            for rel in relationships:
                # Filter by relationship types if specified
                if relationship_types and rel.relationship_type not in relationship_types:
                    continue
                
                visited_relationships[rel.id] = rel
                
                # Find neighbor ID
                neighbor_id = rel.target_id if rel.source_id == current_id else rel.source_id
                
                if neighbor_id not in visited_ids:
                    visited_ids.add(neighbor_id)
                    
                    # Get neighbor entity
                    neighbor = self.get_entity(neighbor_id)
                    if neighbor:
                        visited_entities[neighbor_id] = neighbor
                        queue.append((neighbor_id, depth + 1))
        
        return GraphQueryResult(
            entities=list(visited_entities.values()),
            relationships=list(visited_relationships.values()),
        )
    
    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_hops: int = 3
    ) -> List[List[str]]:
        """Find paths between two entities using BFS."""
        if source_id == target_id:
            return [[source_id]]
        
        paths: List[List[str]] = []
        queue: deque = deque([(source_id, [source_id])])
        
        while queue:
            current_id, path = queue.popleft()
            
            if len(path) > max_hops + 1:
                continue
            
            relationships = self.get_relationships_for_entity(current_id, direction="both")
            
            for rel in relationships:
                neighbor_id = rel.target_id if rel.source_id == current_id else rel.source_id
                
                if neighbor_id in path:
                    continue  # Avoid cycles
                
                new_path = path + [neighbor_id]
                
                if neighbor_id == target_id:
                    paths.append(new_path)
                elif len(new_path) <= max_hops:
                    queue.append((neighbor_id, new_path))
        
        return paths
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def count_entities(self, entity_type: Optional[str] = None) -> int:
        """Count entities in the graph."""
        conn = self._get_connection()
        
        if entity_type:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM entities WHERE entity_type = ?",
                (entity_type,)
            )
        else:
            cursor = conn.execute("SELECT COUNT(*) FROM entities")
        
        return cursor.fetchone()[0]
    
    def count_relationships(self, relationship_type: Optional[str] = None) -> int:
        """Count relationships in the graph."""
        conn = self._get_connection()
        
        if relationship_type:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM relationships WHERE relationship_type = ?",
                (relationship_type,)
            )
        else:
            cursor = conn.execute("SELECT COUNT(*) FROM relationships")
        
        return cursor.fetchone()[0]
    
    def clear(self) -> bool:
        """Clear all data from the graph."""
        conn = self._get_connection()
        conn.execute("DELETE FROM relationships")
        conn.execute("DELETE FROM entities")
        conn.commit()
        logger.info("Graph storage cleared")
        return True
    
    def export_to_dict(self) -> Dict[str, Any]:
        """Export the entire graph as a dictionary."""
        conn = self._get_connection()
        
        entities = []
        cursor = conn.execute("SELECT * FROM entities")
        for row in cursor.fetchall():
            entities.append(self._row_to_entity(row).to_dict())
        
        relationships = []
        cursor = conn.execute("SELECT * FROM relationships")
        for row in cursor.fetchall():
            relationships.append(self._row_to_relationship(row).to_dict())
        
        return {
            "entities": entities,
            "relationships": relationships,
            "exported_at": datetime.now().isoformat(),
        }
    
    def import_from_dict(self, data: Dict[str, Any]) -> int:
        """Import graph data from a dictionary."""
        count = 0
        
        for entity_data in data.get("entities", []):
            entity = GraphEntity.from_dict(entity_data)
            self.add_entity(entity)
            count += 1
        
        for rel_data in data.get("relationships", []):
            rel = GraphRelationship.from_dict(rel_data)
            self.add_relationship(rel)
            count += 1
        
        logger.info(f"Imported {count} items into graph storage")
        return count
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _row_to_entity(self, row: sqlite3.Row) -> GraphEntity:
        """Convert a database row to GraphEntity."""
        return GraphEntity(
            id=row["id"],
            name=row["name"],
            entity_type=row["entity_type"],
            aliases=json.loads(row["aliases"]),
            properties=json.loads(row["properties"]),
            language=row["language"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            source_count=row["source_count"],
            confidence=row["confidence"],
            source_ids=json.loads(row["source_ids"]),
        )
    
    def _row_to_relationship(self, row: sqlite3.Row) -> GraphRelationship:
        """Convert a database row to GraphRelationship."""
        return GraphRelationship(
            id=row["id"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            relationship_type=row["relationship_type"],
            properties=json.loads(row["properties"]),
            bidirectional=bool(row["bidirectional"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            weight=row["weight"],
            confidence=row["confidence"],
            source_doc_ids=json.loads(row["source_doc_ids"]),
        )
    
    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
