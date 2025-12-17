"""
Knowledge Base: RAG for Policies and FAQs with bilingual support.

Features:
- FAISS-backed vector memory for semantic search
- Bilingual support (English/Vietnamese)
- Category and type filtering
- Integration with KnowledgeGraph for enhanced context
- Singleton pattern for efficient resource usage
"""

from __future__ import annotations

import logging
import json
from typing import List, Dict, Any, Optional, Literal
from pathlib import Path

from ai_server.memory.vector_memory import VectorMemory
from ai_server.rag.entity_extractor import EntityExtractor

logger = logging.getLogger(__name__)


DocumentType = Literal["policy", "faq", "all"]
CategoryType = Literal["returns", "shipping", "payment", "warranty", "account", "all"]


class KnowledgeBase:
    """
    RAG Knowledge Base backed by VectorMemory with bilingual support.
    
    Handles loading, indexing, and querying of:
    - Store policies (returns, shipping, payment, warranty, account)
    - FAQs (common questions and answers)
    
    Supports both English and Vietnamese with automatic language detection.
    """
    
    _instance: Optional["KnowledgeBase"] = None
    
    def __new__(cls, collection_name: str = "knowledge_base"):
        """Singleton pattern for KnowledgeBase."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, collection_name: str = "knowledge_base"):
        """Initialize the Knowledge Base.
        
        Args:
            collection_name: Name for the vector memory collection.
        """
        if self._initialized:
            return
        
        self.collection_name = collection_name
        self.memory = VectorMemory(collection_name=collection_name)
        self.data_path = Path("data/policy_faq.json")
        
        # Document tracking
        self._doc_count = 0
        self._loaded_languages: List[str] = []
        self._loaded_categories: List[str] = []
        
        # Entity extractor for language detection (lazy loaded)
        self._extractor: Optional[EntityExtractor] = None
        
        self._initialized = True
        logger.info(f"KnowledgeBase initialized: {collection_name}")
    
    @property
    def extractor(self) -> EntityExtractor:
        """Lazy load entity extractor for language detection."""
        if self._extractor is None:
            from ai_server.rag.entity_extractor import get_entity_extractor
            self._extractor = get_entity_extractor()
        return self._extractor
    
    @property
    def count(self) -> int:
        """Get document count."""
        return self.memory.count
    
    def initialize(self, force_reload: bool = False) -> None:
        """Load seed data if index is empty or force reload.
        
        Args:
            force_reload: Force reload even if data exists.
        """
        if force_reload:
            logger.info("KnowledgeBase: Force reloading data...")
            self.memory.clear()
            self.load_seed_data()
        elif self.memory.count == 0:
            logger.info("KnowledgeBase: Index empty. Loading seed data...")
            self.load_seed_data()
        else:
            logger.info(f"KnowledgeBase: Initialized with {self.memory.count} documents.")
    
    def load_seed_data(self) -> int:
        """Load data from JSON file with new bilingual structure.
        
        Returns:
            Number of documents loaded.
        """
        if not self.data_path.exists():
            logger.warning(f"KnowledgeBase: Seed data not found at {self.data_path}")
            return 0
        
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            texts = []
            metadatas = []
            categories_seen = set()
            languages_seen = set()
            
            # Process policies
            policies = data.get("policies", {})
            for language, policy_list in policies.items():
                languages_seen.add(language)
                for policy in policy_list:
                    text = policy.get("text", "")
                    if not text:
                        continue
                    
                    category = policy.get("category", "general")
                    categories_seen.add(category)
                    
                    metadata = {
                        "id": policy.get("id", ""),
                        "type": "policy",
                        "category": category,
                        "subcategory": policy.get("subcategory", ""),
                        "language": language,
                        "keywords": policy.get("keywords", []),
                        "last_updated": policy.get("last_updated", ""),
                        "related_ids": policy.get("related_ids", []),
                    }
                    
                    texts.append(text)
                    metadatas.append(metadata)
            
            # Process FAQs
            faqs = data.get("faqs", {})
            for language, faq_list in faqs.items():
                languages_seen.add(language)
                for faq in faq_list:
                    question = faq.get("question", "")
                    answer = faq.get("answer", "")
                    if not question or not answer:
                        continue
                    
                    # Combine Q&A for better embedding
                    text = f"Q: {question}\nA: {answer}"
                    
                    category = faq.get("category", "general")
                    categories_seen.add(category)
                    
                    metadata = {
                        "id": faq.get("id", ""),
                        "type": "faq",
                        "category": category,
                        "question": question,
                        "language": language,
                        "keywords": faq.get("keywords", []),
                        "related_policy_ids": faq.get("related_policy_ids", []),
                    }
                    
                    texts.append(text)
                    metadatas.append(metadata)
            
            if texts:
                self.memory.add_texts(texts, metadatas)
                self._doc_count = len(texts)
                self._loaded_languages = list(languages_seen)
                self._loaded_categories = list(categories_seen)
                
                logger.info(
                    f"KnowledgeBase: Loaded {len(texts)} documents "
                    f"({len([m for m in metadatas if m['type'] == 'policy'])} policies, "
                    f"{len([m for m in metadatas if m['type'] == 'faq'])} FAQs) "
                    f"in languages: {self._loaded_languages}"
                )
                return len(texts)
            
            return 0
            
        except Exception as e:
            logger.error(f"KnowledgeBase: Failed to load seed data: {e}")
            return 0
    
    def query(
        self,
        query_text: str,
        k: int = 5,
        doc_type: DocumentType = "all",
        category: CategoryType = "all",
        language: Optional[str] = None,
    ) -> str:
        """Search the knowledge base and return formatted context.
        
        Args:
            query_text: Search query.
            k: Number of results to return.
            doc_type: Filter by document type (policy, faq, all).
            category: Filter by category (returns, shipping, etc.).
            language: Filter by language (en, vi). Auto-detected if None.
            
        Returns:
            Formatted context string for LLM.
        """
        # Auto-detect language if not specified
        if language is None:
            language = self.detect_language(query_text)
        
        # Build filter
        filter_metadata: Dict[str, Any] = {}
        if doc_type != "all":
            filter_metadata["type"] = doc_type
        if category != "all":
            filter_metadata["category"] = category
        if language:
            filter_metadata["language"] = language
        
        # Search
        results = self.memory.search(
            query=query_text,
            k=k,
            filter_metadata=filter_metadata if filter_metadata else None,
        )
        
        if not results:
            # Try without language filter as fallback
            if language:
                logger.debug(f"No results for language={language}, trying without filter")
                filter_metadata.pop("language", None)
                results = self.memory.search(
                    query=query_text,
                    k=k,
                    filter_metadata=filter_metadata if filter_metadata else None,
                )
        
        if not results:
            return ""
        
        return self._format_results(results, language)
    
    def query_with_details(
        self,
        query_text: str,
        k: int = 5,
        doc_type: DocumentType = "all",
        category: CategoryType = "all",
        language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search and return detailed results with metadata.
        
        Args:
            query_text: Search query.
            k: Number of results.
            doc_type: Filter by document type.
            category: Filter by category.
            language: Filter by language.
            
        Returns:
            List of result dicts with text, metadata, and score.
        """
        if language is None:
            language = self.detect_language(query_text)
        
        filter_metadata: Dict[str, Any] = {}
        if doc_type != "all":
            filter_metadata["type"] = doc_type
        if category != "all":
            filter_metadata["category"] = category
        if language:
            filter_metadata["language"] = language
        
        return self.memory.search(
            query=query_text,
            k=k,
            filter_metadata=filter_metadata if filter_metadata else None,
        )
    
    def get_by_category(
        self,
        category: str,
        doc_type: DocumentType = "all",
        language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get all documents in a category.
        
        Args:
            category: Category to retrieve.
            doc_type: Filter by type.
            language: Filter by language.
            
        Returns:
            List of documents.
        """
        # Use a generic query with tight category filter
        filter_metadata: Dict[str, Any] = {"category": category}
        if doc_type != "all":
            filter_metadata["type"] = doc_type
        if language:
            filter_metadata["language"] = language
        
        return self.memory.search(
            query=category,  # Use category as query for relevance
            k=50,  # Get all in category
            filter_metadata=filter_metadata,
        )
    
    def get_related_documents(
        self,
        doc_id: str,
        k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Get documents related to a specific document.
        
        Args:
            doc_id: Document ID to find relations for.
            k: Number of related documents.
            
        Returns:
            List of related documents.
        """
        # Find the source document
        results = self.memory.search(
            query="",  # Empty query, we filter by ID
            k=100,
        )
        
        source_doc = None
        for result in results:
            if result.get("metadata", {}).get("id") == doc_id:
                source_doc = result
                break
        
        if not source_doc:
            return []
        
        # Get related IDs
        metadata = source_doc.get("metadata", {})
        related_ids = metadata.get("related_ids", []) + metadata.get("related_policy_ids", [])
        
        if not related_ids:
            # Fall back to semantic similarity
            return self.memory.search(
                query=source_doc.get("text", ""),
                k=k + 1,  # +1 because it might include itself
            )[:k]
        
        # Find documents by ID
        related = []
        for result in results:
            if result.get("metadata", {}).get("id") in related_ids:
                related.append(result)
                if len(related) >= k:
                    break
        
        return related
    
    def add_document(
        self,
        text: str,
        doc_type: str,
        category: str,
        language: str = "en",
        doc_id: Optional[str] = None,
        **extra_metadata,
    ) -> bool:
        """Add a single document to the knowledge base.
        
        Args:
            text: Document text.
            doc_type: Document type (policy, faq).
            category: Category (returns, shipping, etc.).
            language: Language code.
            doc_id: Optional document ID.
            **extra_metadata: Additional metadata fields.
            
        Returns:
            True if successful.
        """
        metadata = {
            "id": doc_id or f"{doc_type}_{category}_{self.count}",
            "type": doc_type,
            "category": category,
            "language": language,
            **extra_metadata,
        }
        
        try:
            self.memory.add_turn(text, metadata)
            logger.debug(f"Added document: {metadata['id']}")
            return True
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            return False
    
    def detect_language(self, text: str) -> str:
        """Detect language of text.
        
        Args:
            text: Text to analyze.
            
        Returns:
            Language code ('en' or 'vi').
        """
        try:
            return self.extractor.detect_language(text)
        except Exception:
            # Fallback to simple detection
            vietnamese_chars = 'àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ'
            if any(c in text.lower() for c in vietnamese_chars):
                return "vi"
            return "en"
    
    def _format_results(
        self,
        results: List[Dict[str, Any]],
        language: Optional[str] = None,
    ) -> str:
        """Format search results as context string.
        
        Args:
            results: Search results from vector memory.
            language: Language for formatting.
            
        Returns:
            Formatted context string.
        """
        if not results:
            return ""
        
        context_parts = []
        
        for i, res in enumerate(results, 1):
            metadata = res.get("metadata", {})
            doc_type = metadata.get("type", "unknown").upper()
            category = metadata.get("category", "").title()
            text = res.get("text", "")
            
            # Format based on type
            if metadata.get("type") == "faq":
                # FAQs already have Q: A: format
                header = f"[{doc_type} - {category}]"
            else:
                header = f"[{doc_type} - {category}]"
            
            context_parts.append(f"{header}\n{text}")
        
        return "\n\n---\n\n".join(context_parts)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics.
        
        Returns:
            Statistics dict.
        """
        return {
            "total_documents": self.count,
            "languages": self._loaded_languages,
            "categories": self._loaded_categories,
            "collection_name": self.collection_name,
        }
    
    def clear(self) -> bool:
        """Clear all data from the knowledge base.
        
        Returns:
            True if successful.
        """
        self.memory.clear()
        self._doc_count = 0
        self._loaded_languages = []
        self._loaded_categories = []
        logger.info("KnowledgeBase cleared")
        return True


# Convenience function
def get_knowledge_base() -> KnowledgeBase:
    """Get the singleton KnowledgeBase instance."""
    return KnowledgeBase()
