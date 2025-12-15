"""
FAISS Context Retriever

Provides semantic search over conversation history and product data
to augment LLM prompts with relevant context.
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import os

logger = logging.getLogger(__name__)

# Try to import FAISS and embedding model
try:
    import faiss
    import numpy as np
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS not available. Context retrieval will be disabled.")


@dataclass
class RetrievedContext:
    """Represents a retrieved context chunk."""
    
    text: str
    score: float
    metadata: Dict[str, Any]
    source: str  # 'conversation', 'product', 'knowledge'


class EmbeddingProvider:
    """Provides text embeddings using various backends."""
    
    def __init__(self, model_name: str = "qwen3-embedding-0.6b"):
        self.model_name = model_name
        self._model = None
        self._dimension = 1024  # Default for Qwen3 embeddings
    
    def _load_model(self):
        """Lazy load the embedding model."""
        if self._model is not None:
            return
        
        try:
            from sentence_transformers import SentenceTransformer
            
            # Map model names to HuggingFace paths
            model_map = {
                "qwen3-embedding-0.6b": "Alibaba-NLP/gte-Qwen2-1.5B-instruct",
                "gte-base": "thenlper/gte-base",
                "all-minilm": "all-MiniLM-L6-v2"
            }
            
            model_path = model_map.get(self.model_name, self.model_name)
            self._model = SentenceTransformer(model_path)
            self._dimension = self._model.get_sentence_embedding_dimension()
            logger.info(f"Loaded embedding model: {model_path} (dim={self._dimension})")
            
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self._model = None
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension
    
    def embed(self, texts: List[str]) -> Optional[np.ndarray]:
        """Generate embeddings for texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            Numpy array of shape (len(texts), dimension) or None if failed
        """
        self._load_model()
        
        if self._model is None:
            return None
        
        try:
            embeddings = self._model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False
            )
            return embeddings.astype(np.float32)
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None


class FAISSContextRetriever:
    """
    FAISS-based context retriever for semantic search.
    
    Indexes conversation history and product data for
    retrieval-augmented generation (RAG).
    """
    
    def __init__(
        self,
        index_path: Optional[str] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        top_k: int = 5
    ):
        """
        Initialize the context retriever.
        
        Args:
            index_path: Path to load/save FAISS index
            embedding_provider: Provider for text embeddings
            top_k: Default number of results to retrieve
        """
        self.index_path = index_path or "data/faiss_index/context.index"
        self.embedding_provider = embedding_provider or EmbeddingProvider()
        self.top_k = top_k
        
        # FAISS index and metadata storage
        self._index: Optional[faiss.Index] = None
        self._metadata: List[Dict[str, Any]] = []
        self._texts: List[str] = []
        
        # Load existing index if available
        self._load_index()
    
    def _load_index(self) -> bool:
        """Load existing FAISS index from disk."""
        if not FAISS_AVAILABLE:
            return False
        
        index_file = self.index_path
        metadata_file = self.index_path.replace(".index", "_metadata.json")
        
        if os.path.exists(index_file):
            try:
                import json
                self._index = faiss.read_index(index_file)
                
                if os.path.exists(metadata_file):
                    with open(metadata_file, 'r') as f:
                        data = json.load(f)
                        self._metadata = data.get("metadata", [])
                        self._texts = data.get("texts", [])
                
                if self._index is not None:
                    logger.info(f"Loaded FAISS index with {self._index.ntotal} vectors")
                return True
                
            except Exception as e:
                logger.error(f"Failed to load FAISS index: {e}")
        
        # Create new index
        return self._create_index()
    
    def _create_index(self) -> bool:
        """Create a new FAISS index."""
        if not FAISS_AVAILABLE:
            return False
        
        try:
            dimension = self.embedding_provider.dimension
            
            # Use IndexFlatIP for cosine similarity (with normalized vectors)
            self._index = faiss.IndexFlatIP(dimension)
            self._metadata = []
            self._texts = []
            
            logger.info(f"Created new FAISS index (dim={dimension})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create FAISS index: {e}")
            return False
    
    def _save_index(self):
        """Save FAISS index to disk."""
        if not FAISS_AVAILABLE or self._index is None:
            return
        
        try:
            import json
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            
            faiss.write_index(self._index, self.index_path)
            
            metadata_file = self.index_path.replace(".index", "_metadata.json")
            with open(metadata_file, 'w') as f:
                json.dump({
                    "metadata": self._metadata,
                    "texts": self._texts
                }, f)
            
            logger.debug(f"Saved FAISS index with {self._index.ntotal} vectors")
            
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        source: str = "knowledge"
    ) -> int:
        """
        Add texts to the index.
        
        Args:
            texts: List of texts to index
            metadatas: Optional metadata for each text
            source: Source type for the texts
            
        Returns:
            Number of texts added
        """
        if not FAISS_AVAILABLE or self._index is None:
            return 0
        
        if not texts:
            return 0
        
        # Generate embeddings
        embeddings = self.embedding_provider.embed(texts)
        if embeddings is None:
            return 0
        
        # Add to index
        self._index.add(embeddings)
        
        # Store metadata
        metadatas = metadatas or [{} for _ in texts]
        for i, (text, meta) in enumerate(zip(texts, metadatas)):
            self._texts.append(text)
            self._metadata.append({
                **meta,
                "source": source,
                "index": len(self._metadata)
            })
        
        # Persist to disk
        self._save_index()
        
        return len(texts)
    
    def add_conversation_turn(
        self,
        role: str,
        content: str,
        session_id: str,
        turn_index: int
    ) -> bool:
        """
        Add a conversation turn to the index.
        
        Args:
            role: 'user' or 'assistant'
            content: Message content
            session_id: Session identifier
            turn_index: Turn number in conversation
            
        Returns:
            Success status
        """
        metadata = {
            "role": role,
            "session_id": session_id,
            "turn_index": turn_index
        }
        
        count = self.add_texts([content], [metadata], source="conversation")
        return count > 0
    
    def add_product(self, product: Dict[str, Any]) -> bool:
        """
        Add a product to the index.
        
        Args:
            product: Product data dictionary
            
        Returns:
            Success status
        """
        # Create searchable text from product
        text_parts = [
            product.get("title", ""),
            product.get("brand", ""),
            f"${product.get('price', 0):.2f}" if product.get("price") else "",
            f"{product.get('rating', 0)} stars" if product.get("rating") else "",
        ]
        text = " | ".join(filter(None, text_parts))
        
        metadata = {
            "asin": product.get("asin"),
            "title": product.get("title"),
            "price": product.get("price"),
            "rating": product.get("rating")
        }
        
        count = self.add_texts([text], [metadata], source="product")
        return count > 0
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_source: Optional[str] = None,
        min_score: float = 0.0
    ) -> List[RetrievedContext]:
        """
        Retrieve relevant contexts for a query.
        
        Args:
            query: Search query
            top_k: Number of results (defaults to self.top_k)
            filter_source: Filter by source type
            min_score: Minimum similarity score
            
        Returns:
            List of RetrievedContext objects
        """
        if not FAISS_AVAILABLE or self._index is None:
            return []
        
        if self._index.ntotal == 0:
            return []
        
        top_k = top_k or self.top_k
        
        # Generate query embedding
        query_embedding = self.embedding_provider.embed([query])
        if query_embedding is None:
            return []
        
        # Search index
        # Retrieve more to allow for filtering
        k = min(top_k * 3, self._index.ntotal)
        scores, indices = self._index.search(query_embedding, k)
        
        # Build results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._metadata):
                continue
            
            if score < min_score:
                continue
            
            metadata = self._metadata[idx]
            
            if filter_source and metadata.get("source") != filter_source:
                continue
            
            results.append(RetrievedContext(
                text=self._texts[idx],
                score=float(score),
                metadata=metadata,
                source=metadata.get("source", "unknown")
            ))
            
            if len(results) >= top_k:
                break
        
        return results
    
    def retrieve_for_query(
        self,
        user_query: str,
        session_id: Optional[str] = None,
        include_products: bool = True,
        include_conversations: bool = True
    ) -> Dict[str, List[RetrievedContext]]:
        """
        Retrieve all relevant context for a user query.
        
        Args:
            user_query: The user's query
            session_id: Optional session ID for conversation filtering
            include_products: Whether to include product results
            include_conversations: Whether to include conversation history
            
        Returns:
            Dict with 'products' and 'conversations' keys
        """
        results = {
            "products": [],
            "conversations": []
        }
        
        if include_products:
            results["products"] = self.retrieve(
                user_query,
                filter_source="product",
                top_k=5
            )
        
        if include_conversations:
            results["conversations"] = self.retrieve(
                user_query,
                filter_source="conversation",
                top_k=3
            )
        
        return results
    
    def format_context_for_prompt(
        self,
        retrieved: Dict[str, List[RetrievedContext]],
        max_tokens: int = 1000
    ) -> str:
        """
        Format retrieved context for injection into prompts.
        
        Args:
            retrieved: Retrieved context from retrieve_for_query
            max_tokens: Approximate max token count
            
        Returns:
            Formatted context string
        """
        parts = []
        char_limit = max_tokens * 4  # Rough estimate
        
        # Add product context
        if retrieved.get("products"):
            parts.append("## Relevant Products:")
            for ctx in retrieved["products"][:3]:
                if len("\n".join(parts)) > char_limit:
                    break
                parts.append(f"- {ctx.text} (score: {ctx.score:.2f})")
        
        # Add conversation context
        if retrieved.get("conversations"):
            parts.append("\n## Related Conversation History:")
            for ctx in retrieved["conversations"][:2]:
                if len("\n".join(parts)) > char_limit:
                    break
                role = ctx.metadata.get("role", "unknown")
                parts.append(f"- [{role}]: {ctx.text[:200]}...")
        
        return "\n".join(parts) if parts else ""
    
    def clear(self):
        """Clear the index."""
        self._create_index()
        self._save_index()


# Singleton instance
_context_retriever: Optional[FAISSContextRetriever] = None


def get_context_retriever() -> FAISSContextRetriever:
    """Get the singleton context retriever instance."""
    global _context_retriever
    if _context_retriever is None:
        _context_retriever = FAISSContextRetriever()
    return _context_retriever
