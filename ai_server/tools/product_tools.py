"""Tools for interacting with local product memory."""

import logging
from typing import List, Dict, Any

from ai_server.memory.storage.product_store import ProductStore

logger = logging.getLogger(__name__)

def check_local_products(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Check local database for products matching the query.
    
    Args:
        query: Search query
        limit: Max results
        
    Returns:
        List of matching products
    """
    try:
        store = ProductStore()
        results = store.search_products(query, limit=limit)
        logger.info(f"Local search for '{query}' found {len(results)} products")
        return results
    except Exception as e:
        logger.error(f"Local search failed: {e}")
        return []
