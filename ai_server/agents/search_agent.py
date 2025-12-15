from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

from ai_server.schemas.shared_workspace import SharedWorkspace, ProductCandidate
from ai_server.agents.collection_agent import collect_products
from ai_server.agents.query_parser import QueryParser, SearchPlan
from ai_server.utils.logger import get_logger

logger = get_logger(__name__)


class SearchAgent:
    """
    Search Agent (The Hunter).
    Uses QueryParser to extract structured search parameters from natural language.
    """
    
    def __init__(self):
        self.query_parser = QueryParser()
        self._last_search_plan: Optional[SearchPlan] = None

    def search(self, workspace: SharedWorkspace) -> SharedWorkspace:
        """
        Execute search based on the goal and update candidates.
        Uses QueryParser to extract structured search parameters.
        """
        # Use specific search query if available (refinement), else user goal
        query = workspace.search_query or workspace.goal
        logger.info(f"SearchAgent: Hunting for '{query}'")
        
        # 1. Parse query with QueryParser (LLM-based extraction)
        try:
            search_plan = self.query_parser.parse(query)
            self._last_search_plan = search_plan
            logger.info(f"SearchAgent: Parsed plan - category={search_plan.category}, price_max={search_plan.price_max}, brands={search_plan.brands}")
        except Exception as e:
            logger.warning(f"SearchAgent: QueryParser failed: {e}. Using raw query.")
            search_plan = SearchPlan(keywords=[query])
        
        # 2. Build search plan for collection_agent
        # Convert SearchPlan to legacy format expected by collect_products
        search_keywords = self.query_parser.to_search_query(search_plan)
        
        collection_plan = {
            "keywords": search_plan.keywords if search_plan.keywords else [query],
            "engines": ["google_shopping"],  # Default engine
            "max_price": search_plan.price_max,
            "requirements": {
                "brand_preferences": search_plan.brands,
                "features": search_plan.features,
            }
        }
        
        # Add price filter to search keywords if specified
        if search_plan.price_max:
            search_keywords = f"{search_keywords} under ${int(search_plan.price_max)}"
        
        mock_state = {
            "search_plan": collection_plan,
            "user_query": search_keywords,
            "trace_id": None
        }
        
        try:
            # 3. Execute search
            result_state = collect_products(mock_state)
            raw_products = result_state.get("products", [])
            
            # 4. Filter by price if specified (post-filter for accuracy)
            if search_plan.price_max or search_plan.price_min:
                raw_products = self._filter_by_price(
                    raw_products, 
                    search_plan.price_min, 
                    search_plan.price_max
                )
            
            # 5. Convert to ProductCandidate
            new_candidates = []
            for p in raw_products:
                candidate = ProductCandidate(
                    asin=p.get("asin") or p.get("link", "unknown"),
                    title=p.get("title", "Unknown Product"),
                    price=p.get("price"),
                    status="proposed",
                    source_data={
                        **p,
                        "search_plan": search_plan.model_dump() if search_plan else {}
                    }
                )
                new_candidates.append(candidate)
            
            logger.info(f"SearchAgent: Found {len(new_candidates)} candidates after filtering.")
            
            # 6. Update Workspace
            workspace.candidates.extend(new_candidates)
            
        except Exception as e:
            logger.error(f"SearchAgent failed: {e}")
            workspace.error = str(e)
            
        return workspace
    
    def _filter_by_price(
        self, 
        products: List[Dict[str, Any]], 
        price_min: Optional[float], 
        price_max: Optional[float]
    ) -> List[Dict[str, Any]]:
        """Filter products by price range."""
        filtered = []
        for p in products:
            price = p.get("price")
            if price is None:
                # Include products without price (might be good deals)
                filtered.append(p)
                continue
            
            if price_min and price < price_min:
                continue
            if price_max and price > price_max:
                continue
            
            filtered.append(p)
        
        return filtered
    
    def get_last_search_plan(self) -> Optional[SearchPlan]:
        """Get the last parsed search plan for debugging/logging."""
        return self._last_search_plan
