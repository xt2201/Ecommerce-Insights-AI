"""Market Agent - Analyzes market trends and opportunities."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from ai_server.schemas.agent_state import AgentState
from ai_server.core.trace import get_trace_manager, StepType, TokenUsage

logger = logging.getLogger(__name__)


from pathlib import Path
from langchain_core.messages import HumanMessage, SystemMessage
from ai_server.llm.llm_factory import get_llm
from ai_server.utils.prompt_loader import load_prompts_as_dict
from ai_server.utils.token_counter import extract_token_usage
from ai_server.schemas.analysis_models import MarketAnalysis

class MarketAgent:
    """Market Agent with LLM capabilities."""
    
    def __init__(self):
        self.llm = get_llm(agent_name="market")
        self.prompts = load_prompts_as_dict("market_agent_prompts")

    def analyze_market_trends(self, query: str, products: List[Dict[str, Any]]) -> tuple[MarketAnalysis, dict]:
        """Analyze market trends."""
        try:
            structured_llm = self.llm.with_structured_output(MarketAnalysis, include_raw=True)
            
            # Calculate stats
            prices = [p.get("price") for p in products if p.get("price")]
            brands = [p.get("brand") for p in products if p.get("brand")]
            
            logger.info(f"Market Agent Data: Found {len(prices)} prices and {len(brands)} brands from {len(products)} products.")
            logger.debug(f"Prices: {prices}")
            
            if not prices:
                return MarketAnalysis(
                    market_segment="Unknown",
                    price_insight="No price data available",
                    brand_insight="No brand data available",
                    gap_analysis="Insufficient data",
                    recommendation_strategy="N/A"
                ), {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
                
            min_price = min(prices)
            max_price = max(prices)
            avg_price = sum(prices) / len(prices)
            unique_brands = list(set(brands))
            
            # Format top products for prompt
            top_products_text = "\n".join([
                f"- {p.get('title', '')} (${p.get('price', 'N/A')}) - {p.get('rating', 'N/A')} stars" 
                for p in products[:5]
            ])
            
            prompt = self.prompts["analyze_market_trends"].format(
                query=query,
                product_count=len(products),
                min_price=min_price,
                max_price=max_price,
                avg_price=f"{avg_price:.2f}",
                brands=", ".join(unique_brands[:10]),
                top_products_text=top_products_text
            )
            
            messages = [
                SystemMessage(content=self.prompts.get("system_prompt", "")),
                HumanMessage(content=prompt)
            ]
            
            out = structured_llm.invoke(messages)
            parsed = out.get("parsed")
            raw = out.get("raw")
            usage = extract_token_usage(raw)
            
            if parsed is None:
                logger.warning(f"Market Agent: LLM returned None for structured output. Raw: {raw}")
                raise ValueError("Failed to parse market analysis from LLM response")
            
            return parsed, usage
            
        except Exception as e:
            logger.error(f"Error in analyze_market_trends: {e}", exc_info=True)
            return MarketAnalysis(
                market_segment="Error",
                price_insight="Analysis failed",
                brand_insight="Analysis failed",
                gap_analysis=str(e),
                recommendation_strategy="N/A"
            ), {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


def analyze_market(state: AgentState) -> AgentState:
    """Analyze market trends and gaps.
    
    Args:
        state: Current agent state with market_data
        
    Returns:
        Updated state with market analysis
    """
    logger.info("=== Market Agent Starting ===")
    
    trace_manager = get_trace_manager()
    trace_id = state.get("trace_id")
    
    # Create market analysis step
    step = None
    if trace_id:
        step = trace_manager.create_step(
            trace_id=trace_id,
            step_type=StepType.ANALYSIS,
            agent_name="market_agent"
        )
    
    try:
        agent = MarketAgent()
        
        # Get products and query
        products = state.get("products", [])
        user_query = state.get("user_query", "")
        
        if not products:
            logger.warning(f"No products available for market analysis. State keys: {list(state.keys())}, Products type: {type(products)}")
            return state
            
        # Run LLM analysis
        market_analysis, usage = agent.analyze_market_trends(user_query, products)
        
    except Exception as e:
        logger.error(f"Error in Market Agent: {e}", exc_info=True)
        if trace_id and step:
            trace_manager.fail_step(trace_id, step.step_id, str(e))
            
    return {"market_analysis": market_analysis.model_dump()}
