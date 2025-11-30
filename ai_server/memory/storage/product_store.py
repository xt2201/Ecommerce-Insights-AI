"""SQLite storage for product data."""

import json
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ai_server.core.config import get_config_value

logger = logging.getLogger(__name__)

class ProductStore:
    """Manages persistent storage for products using SQLite."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize product store.
        
        Args:
            db_path: Path to SQLite database file.
        """
        if db_path is None:
            db_path = get_config_value("memory.storage.product_db_path", "data/products.db")
            
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """Initialize database schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create products table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS products (
                        asin TEXT PRIMARY KEY,
                        title TEXT,
                        price REAL,
                        rating REAL,
                        reviews_count INTEGER,
                        features_json TEXT,
                        last_updated TIMESTAMP
                    )
                """)
                
                # Create index for title search
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_products_title 
                    ON products(title)
                """)
                
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize product database: {e}")
            
    def save_product(self, product: Dict[str, Any]) -> bool:
        """Save or update a product.
        
        Args:
            product: Product dictionary
            
        Returns:
            True if successful
        """
        if not product.get("asin"):
            return False
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO products 
                    (asin, title, price, rating, reviews_count, features_json, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    product.get("asin"),
                    product.get("title"),
                    product.get("price"),
                    product.get("rating"),
                    product.get("reviews_count"),
                    json.dumps(product), # Store full object as JSON
                    datetime.now().isoformat()
                ))
                
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save product {product.get('asin')}: {e}")
            return False
            
    def get_product(self, asin: str) -> Optional[Dict[str, Any]]:
        """Retrieve a product by ASIN.
        
        Args:
            asin: Product ASIN
            
        Returns:
            Product dictionary or None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("SELECT features_json FROM products WHERE asin = ?", (asin,))
                row = cursor.fetchone()
                
                if row:
                    return json.loads(row["features_json"])
                return None
        except Exception as e:
            logger.error(f"Failed to get product {asin}: {e}")
            return None
            
    def search_products(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search products by title.
        
        Args:
            query: Search query string
            limit: Max results
            
        Returns:
            List of product dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Simple LIKE search
                # For better results, we'd use FTS5, but this is a good start
                search_term = f"%{query}%"
                
                cursor.execute("""
                    SELECT features_json FROM products 
                    WHERE title LIKE ? 
                    ORDER BY last_updated DESC 
                    LIMIT ?
                """, (search_term, limit))
                
                results = []
                for row in cursor.fetchall():
                    results.append(json.loads(row["features_json"]))
                    
                return results
        except Exception as e:
            logger.error(f"Failed to search products: {e}")
            return []
