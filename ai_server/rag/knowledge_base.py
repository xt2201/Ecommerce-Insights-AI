from __future__ import annotations

import logging
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

from ai_server.memory.vector_memory import VectorMemory

logger = logging.getLogger(__name__)

class KnowledgeBase:
    """
    RAG Knowledge Base backed by VectorMemory.
    Handles loading, indexing, and querying of static knowledge (Policies, FAQs).
    """
    
    def __init__(self, collection_name: str = "knowledge_base"):
        self.memory = VectorMemory(collection_name=collection_name)
        self.data_path = Path("data/policy_faq.json")
        
    def initialize(self):
        """Load seed data if index is empty."""
        if self.memory.count == 0:
            logger.info("KnowledgeBase: Index empty. Loading seed data...")
            self.load_seed_data()
        else:
            logger.info(f"KnowledgeBase: Initialized with {self.memory.count} documents.")

    def load_seed_data(self):
        """Load data from JSON file."""
        if not self.data_path.exists():
            logger.warning(f"KnowledgeBase: Seed data not found at {self.data_path}")
            return
            
        try:
            with open(self.data_path, "r") as f:
                data = json.load(f)
                
            texts = []
            metadatas = []
            
            for item in data:
                texts.append(item["text"])
                metadatas.append(item.get("metadata", {}))
                
            if texts:
                self.memory.add_texts(texts, metadatas)
                logger.info(f"KnowledgeBase: Added {len(texts)} documents from seed.")
                
        except Exception as e:
            logger.error(f"KnowledgeBase: Failed to load seed data: {e}")

    def query(self, query_text: str, k: int = 3, filter_metadata: Optional[Dict] = None) -> str:
        """
        Search the knowledge base and return a formatted string context.
        """
        results = self.memory.search(query_text, k=k, filter_metadata=filter_metadata)
        
        if not results:
            return ""
            
        # Format results into a context string
        context_parts = []
        for i, res in enumerate(results, 1):
            context_parts.append(f"Source {i}: {res['text']}")
            
        return "\n\n".join(context_parts)

    def add_document(self, text: str, metadata: Dict[str, Any]):
        """Add a single document."""
        self.memory.add_turn(text, metadata)
