"""Collection Agent - Collects products from SerpAPI."""

from __future__ import annotations

import logging
from typing import Dict, Any

from ai_server.clients.serpapi import SerpAPIClient
from ai_server.schemas.agent_state import AgentState
from ai_server.core.trace import get_trace_manager, StepType, TokenUsage

logger = logging.getLogger(__name__)


def collect_products(state: AgentState) -> AgentState:
    """Collection Agent with product search.
    
    Args:
        state: Current agent state with search_plan
        
    Returns:
        Updated state with products list
    """
    logger.info("=== Collection Agent Starting ===")
    
    search_plan = state.get("search_plan", {})
    user_query = state.get("user_query", "")
    trace_manager = get_trace_manager()
    trace_id = state.get("trace_id")
    
    # Create collection step
    step = None
    if trace_id:
        step = trace_manager.create_step(
            trace_id=trace_id,
            step_type=StepType.COLLECTION,
            agent_name="collection_agent"
        )
    
    # Initialize SerpAPI client
    serp_client = SerpAPIClient()
    
    # Get search parameters
    keywords = search_plan.get("keywords", user_query)
    if isinstance(keywords, list):
        keywords = keywords[0]  # Use first keyword
    
    domain = search_plan.get("amazon_domain", "amazon.com")
    
    # Get brand preferences to enhance product data
    requirements = search_plan.get("requirements", {})
    brand_preferences = requirements.get("brand_preferences", [])
    
    try:
        # Execute search
        logger.info(f"Searching for: {keywords} on {domain}")
        search_payload = serp_client.search_products(
            q=keywords,
            amazon_domain=domain,
            num=10
        )
        
        # Extract products from organic_results
        organic_results = search_payload.get("organic_results", [])
        
        # Convert to product dictionaries with required fields
        products = []
        for item in organic_results:
            # Parse price string to float
            price_str = item.get("price_string") or item.get("price") or ""
            price_val = None
            if price_str:
                try:
                    # Use regex to extract the first valid price number
                    import re
                    # Matches numbers with optional commas and decimals, e.g., 1,234.56
                    match = re.search(r"[\d,]+\.\d{2}", str(price_str))
                    if match:
                        clean_price = match.group(0).replace(",", "")
                        price_val = float(clean_price)
                    else:
                        # Fallback for simple integers or other formats
                        clean_price = re.sub(r"[^\d.]", "", str(price_str))
                        if clean_price:
                            price_val = float(clean_price)
                except (ValueError, AttributeError):
                    pass
            
            title = item.get("title") or ""
            
            # BRAND EXTRACTION: SerpAPI Amazon engine does not return 'brand' field
            # We rely on the title for brand identification in later stages
            brand = ""
            enhanced_title = title
            
            product = {
                "asin": item.get("asin") or item.get("product_id") or "",
                "title": enhanced_title,
                "product_name": enhanced_title,  # Alias for consistency
                "brand": "",  # Brand field is not available from SerpAPI organic results
                "price": price_val,
                "rating": item.get("rating"),
                "reviews_count": item.get("reviews_count") or item.get("reviews"),
                "link": item.get("link") or ""
            }
            if product["asin"]:  # Only include products with ASIN
                products.append(product)
        
        logger.info(f"Found {len(products)} products")
        
        # --- PHASE 1 UPGRADE: Multi-Tool Collection ---
        # If search plan requests deep dive (e.g., for reviews or offers), fetch for top products
        
        # Initialize data containers
        reviews_data = {}
        market_data = {}
        offers_data = {}
        
        # Check if we need deep dive
        engines = search_plan.get("engines", [])
        top_n = 3 # Limit deep dive to top 3 to save API calls/time
        
        if "amazon_product_reviews" in engines or "amazon_offers" in engines:
            logger.info(f"Performing deep dive for top {top_n} products")
            
            for product in products[:top_n]:
                asin = product["asin"]
                
                # Fetch Reviews
                if "amazon_product_reviews" in engines:
                    try:
                        logger.info(f"Fetching reviews for {asin}")
                        review_payload = serp_client.get_product_reviews(asin=asin, amazon_domain=domain)
                        reviews_data[asin] = review_payload
                    except Exception as e:
                        if "Unsupported `amazon_product_reviews` search engine" in str(e):
                            logger.warning(f"Review fetching skipped for {asin}: Engine not supported by API plan.")
                        else:
                            logger.error(f"Failed to fetch reviews for {asin}: {e}")
                
                # Fetch Offers
                if "amazon_offers" in engines:
                    try:
                        logger.info(f"Fetching offers for {asin}")
                        offers_payload = serp_client.get_product_offers(asin=asin, amazon_domain=domain)
                        offers_data[asin] = offers_payload
                    except Exception as e:
                        logger.error(f"Failed to fetch offers for {asin}: {e}")

        # Complete step with success
        if trace_id and step:
            trace_manager.complete_step(
                trace_id=trace_id,
                step_id=step.step_id,
                output_data={
                    "products_count": len(products),
                    "keywords": keywords,
                    "domain": domain,
                    "deep_dive_count": len(reviews_data)
                },
                token_usage=TokenUsage(
                    prompt_tokens=0,  # No LLM call
                    completion_tokens=0
                )
            )
        
    except Exception as e:
        logger.error(f"Error in Collection Agent: {e}", exc_info=True)
        products = []
        reviews_data = {}
        offers_data = {}
        
        # Fail step on error
        if trace_id and step:
            trace_manager.fail_step(
                trace_id=trace_id,
                step_id=step.step_id,
                error=str(e)
            )
    
    # Update state with results
    state["products"] = products
    state["products_count"] = len(products)
    
    # Store deep dive data
    if reviews_data:
        state["reviews_data"] = reviews_data
    if offers_data:
        # We might want to store offers separately or merge into products
        # For now, let's store in a generic 'market_data' or similar if needed
        # But 'market_data' is for aggregated stats.
        # Let's add 'offers_data' to state if we defined it, or just attach to products?
        # The schema has 'market_data'. Let's put offers there for now or just attach to product objects?
        # Attaching to product objects is cleaner for Analysis Agent.
        for p in products:
            if p["asin"] in offers_data:
                p["offers"] = offers_data[p["asin"]].get("offers", [])
    
    logger.info(f"Collection Agent complete: {len(products)} products")
    
    return state