"""Vector memory for semantic retrieval using FAISS and Qwen3 embeddings."""

import logging
import os
import pickle
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path

import numpy as np

from ai_server.core.config import get_config_value

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Wrapper for embedding model with lazy loading (Singleton)."""
    
    _instance = None
    _model = None
    _tokenizer = None
    _device = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def _load_model(self):
        """Load the embedding model lazily."""
        if self._model is not None:
            return
            
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
            
            model_name = get_config_value("embeddings.model_name", "Qwen/Qwen3-Embedding-0.6B")
            trust_remote_code = get_config_value("embeddings.trust_remote_code", True)
            device = get_config_value("embeddings.device", "auto")
            
            logger.info(f"Loading embedding model: {model_name}")
            
            # Determine device
            if device == "auto":
                if torch.cuda.is_available():
                    device = "cuda"
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    device = "mps"
                else:
                    device = "cpu"
            
            self._tokenizer = AutoTokenizer.from_pretrained(
                model_name, 
                trust_remote_code=trust_remote_code
            )
            self._model = AutoModel.from_pretrained(
                model_name, 
                trust_remote_code=trust_remote_code
            ).to(device)
            self._model.eval()
            self._device = device
            
            logger.info(f"Embedding model loaded on device: {device}")
            
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def encode(self, texts: List[str], normalize: bool = True) -> np.ndarray:
        """Encode texts to embeddings.
        
        Args:
            texts: List of texts to encode.
            normalize: Whether to normalize embeddings.
            
        Returns:
            Numpy array of embeddings.
        """
        self._load_model()
        
        import torch
        
        batch_size = get_config_value("embeddings.batch_size", 32)
        max_length = get_config_value("embeddings.max_length", 512)
        should_normalize = get_config_value("embeddings.normalize", True) and normalize
        
        all_embeddings = []
        
        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                # Tokenize
                inputs = self._tokenizer(
                    batch_texts,
                    padding=True,
                    truncation=True,
                    max_length=max_length,
                    return_tensors="pt"
                ).to(self._device)
                
                # Get embeddings
                outputs = self._model(**inputs)
                
                # Use mean pooling over last hidden state
                attention_mask = inputs['attention_mask']
                hidden_state = outputs.last_hidden_state
                
                # Masked mean pooling
                mask_expanded = attention_mask.unsqueeze(-1).expand(hidden_state.size()).float()
                sum_embeddings = torch.sum(hidden_state * mask_expanded, dim=1)
                sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
                embeddings = sum_embeddings / sum_mask
                
                # Normalize if requested
                if should_normalize:
                    embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
                
                all_embeddings.append(embeddings.cpu().numpy())
        
        return np.vstack(all_embeddings)
    
    def encode_single(self, text: str, normalize: bool = True) -> np.ndarray:
        """Encode a single text to embedding."""
        return self.encode([text], normalize=normalize)[0]


class VectorMemory:
    """Manages long-term semantic memory using FAISS."""
    
    def __init__(self, collection_name: str = "conversation_history"):
        """Initialize vector memory with FAISS.
        
        Args:
            collection_name: Name of the collection (used for file naming).
        """
        self.collection_name = collection_name
        self.index_dir = Path(get_config_value("vector_store.faiss.index_path", "data/faiss_index"))
        self.dimension = get_config_value("embeddings.dimension", 1024)
        self.metric = get_config_value("vector_store.faiss.metric", "cosine")
        
        # Storage for documents and metadata
        self.documents: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []
        self.ids: List[str] = []
        
        # FAISS index (lazy loaded)
        self._index = None
        self._embedding_model = None
        
        # Ensure directory exists
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing index if available
        self._load_index()
        
        logger.info(f"VectorMemory initialized at {self.index_dir}")
    
    def _get_embedding_model(self) -> EmbeddingModel:
        """Get or create embedding model instance."""
        if self._embedding_model is None:
            self._embedding_model = EmbeddingModel()
        return self._embedding_model
    
    def _create_index(self):
        """Create a new FAISS index."""
        import faiss
        
        index_type = get_config_value("vector_store.faiss.index_type", "flat")
        
        if self.metric == "cosine":
            # For cosine similarity, we normalize vectors and use inner product
            if index_type == "flat":
                self._index = faiss.IndexFlatIP(self.dimension)
            elif index_type == "ivf":
                nlist = get_config_value("vector_store.faiss.nlist", 100)
                quantizer = faiss.IndexFlatIP(self.dimension)
                self._index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist, faiss.METRIC_INNER_PRODUCT)
            else:
                self._index = faiss.IndexFlatIP(self.dimension)
        elif self.metric == "l2":
            if index_type == "flat":
                self._index = faiss.IndexFlatL2(self.dimension)
            elif index_type == "ivf":
                nlist = get_config_value("vector_store.faiss.nlist", 100)
                quantizer = faiss.IndexFlatL2(self.dimension)
                self._index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
            else:
                self._index = faiss.IndexFlatL2(self.dimension)
        else:
            # Default to inner product
            self._index = faiss.IndexFlatIP(self.dimension)
        
        logger.info(f"Created FAISS index: type={index_type}, metric={self.metric}, dim={self.dimension}")
    
    def _get_index_path(self) -> Path:
        """Get path to index file."""
        return self.index_dir / f"{self.collection_name}.index"
    
    def _get_data_path(self) -> Path:
        """Get path to data file."""
        return self.index_dir / f"{self.collection_name}.pkl"
    
    def _load_index(self):
        """Load existing index from disk."""
        import faiss
        
        index_path = self._get_index_path()
        data_path = self._get_data_path()
        
        if index_path.exists() and data_path.exists():
            try:
                self._index = faiss.read_index(str(index_path))
                with open(data_path, 'rb') as f:
                    data = pickle.load(f)
                    self.documents = data.get('documents', [])
                    self.metadatas = data.get('metadatas', [])
                    self.ids = data.get('ids', [])
                logger.info(f"Loaded FAISS index with {len(self.documents)} documents")
            except Exception as e:
                logger.warning(f"Failed to load index, creating new one: {e}")
                self._create_index()
        else:
            self._create_index()
    
    def _save_index(self):
        """Save index to disk."""
        import faiss
        
        if self._index is None:
            return
            
        try:
            index_path = self._get_index_path()
            data_path = self._get_data_path()
            
            faiss.write_index(self._index, str(index_path))
            with open(data_path, 'wb') as f:
                pickle.dump({
                    'documents': self.documents,
                    'metadatas': self.metadatas,
                    'ids': self.ids
                }, f)
            logger.debug(f"Saved FAISS index with {len(self.documents)} documents")
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    def add_turn(self, text: str, metadata: Dict[str, Any]) -> bool:
        """Add a conversation turn to vector memory.
        
        Args:
            text: The text content to embed.
            metadata: Additional metadata.
            
        Returns:
            True if successful.
        """
        if self._index is None:
            self._create_index()
            
        try:
            # Generate embedding
            model = self._get_embedding_model()
            embedding = model.encode_single(text, normalize=(self.metric == "cosine"))
            
            # Generate ID
            doc_id = str(uuid.uuid4())
            
            # Add to FAISS index
            self._index.add(embedding.reshape(1, -1).astype(np.float32))
            
            # Store document and metadata
            self.documents.append(text)
            self.metadatas.append(metadata)
            self.ids.append(doc_id)
            
            # Save to disk
            self._save_index()
            
            return True
        except Exception as e:
            logger.error(f"Failed to add turn to vector memory: {e}")
            return False
    
    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """Add multiple texts to vector memory.
        
        Args:
            texts: List of texts to add.
            metadatas: Optional list of metadata dicts.
            
        Returns:
            List of generated IDs.
        """
        if self._index is None:
            self._create_index()
            
        if metadatas is None:
            metadatas = [{} for _ in texts]
            
        try:
            # Generate embeddings in batch
            model = self._get_embedding_model()
            embeddings = model.encode(texts, normalize=(self.metric == "cosine"))
            
            # Generate IDs
            new_ids = [str(uuid.uuid4()) for _ in texts]
            
            # Add to FAISS index
            self._index.add(embeddings.astype(np.float32))
            
            # Store documents and metadata
            self.documents.extend(texts)
            self.metadatas.extend(metadatas)
            self.ids.extend(new_ids)
            
            # Save to disk
            self._save_index()
            
            return new_ids
        except Exception as e:
            logger.error(f"Failed to add texts to vector memory: {e}")
            return []
    
    def search(self, query: str, k: int = 3, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for relevant past turns.
        
        Args:
            query: The current user query.
            k: Number of results to return.
            filter_metadata: Optional filter for metadata.
            
        Returns:
            List of results with 'text', 'metadata', and 'score'.
        """
        if self._index is None or self._index.ntotal == 0:
            return []
            
        try:
            # Generate query embedding
            model = self._get_embedding_model()
            query_embedding = model.encode_single(query, normalize=(self.metric == "cosine"))
            
            # Search more than k to account for filtering
            search_k = min(k * 3, self._index.ntotal) if filter_metadata else k
            
            # Search FAISS index
            scores, indices = self._index.search(
                query_embedding.reshape(1, -1).astype(np.float32),
                search_k
            )
            
            # Format results with optional filtering
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0 or idx >= len(self.documents):
                    continue
                    
                metadata = self.metadatas[idx]
                
                # Apply metadata filter if specified
                if filter_metadata:
                    match = all(
                        metadata.get(key) == value 
                        for key, value in filter_metadata.items()
                    )
                    if not match:
                        continue
                
                results.append({
                    "text": self.documents[idx],
                    "metadata": metadata,
                    "score": float(score),
                    "id": self.ids[idx]
                })
                
                if len(results) >= k:
                    break
            
            return results
        except Exception as e:
            logger.error(f"Failed to search vector memory: {e}")
            return []
    
    def delete(self, ids: List[str]) -> bool:
        """Delete documents by IDs.
        
        Note: FAISS doesn't support direct deletion, so we rebuild the index.
        
        Args:
            ids: List of document IDs to delete.
            
        Returns:
            True if successful.
        """
        try:
            # Find indices to keep
            indices_to_keep = [
                i for i, doc_id in enumerate(self.ids) 
                if doc_id not in ids
            ]
            
            if len(indices_to_keep) == len(self.ids):
                # Nothing to delete
                return True
            
            # Rebuild with remaining documents
            remaining_docs = [self.documents[i] for i in indices_to_keep]
            remaining_meta = [self.metadatas[i] for i in indices_to_keep]
            
            # Clear and rebuild
            self.documents = []
            self.metadatas = []
            self.ids = []
            self._create_index()
            
            if remaining_docs:
                self.add_texts(remaining_docs, remaining_meta)
            else:
                self._save_index()
            
            return True
        except Exception as e:
            logger.error(f"Failed to delete from vector memory: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear all documents from the collection."""
        try:
            self.documents = []
            self.metadatas = []
            self.ids = []
            self._create_index()
            self._save_index()
            return True
        except Exception as e:
            logger.error(f"Failed to clear vector memory: {e}")
            return False
    
    @property
    def count(self) -> int:
        """Return the number of documents in the collection."""
        return len(self.documents)
