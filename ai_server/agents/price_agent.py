"""Price Agent - Analyzes price history and deals."""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from ai_server.schemas.agent_state import AgentState
from ai_server.core.trace import get_trace_manager, StepType, TokenUsage
from ai_server.llm.llm_factory import get_llm
from ai_server.utils.prompt_loader import load_prompts_as_dict
from ai_server.utils.token_counter import extract_token_usage
from ai_server.schemas.analysis_models import PriceAnalysis

logger = logging.getLogger(__name__)


class PriceAgent:
    """Price Agent with LLM capabilities."""
    
    def __init__(self):
        self.llm = get_llm(agent_name="price")
        self.prompts = load_prompts_as_dict("price_agent_prompts")

    def analyze_price(self, product_title: str, current_price: float) -> tuple[PriceAnalysis, dict]:
        """Analyze price history."""
        try:
            structured_llm = self.llm.with_structured_output(PriceAnalysis, include_raw=True)
            
            # Mock historical data (Phase 1/2 limitation)
            # In production, this would come from a DB or API
            import random
            variation = current_price * 0.2
            lowest_price = max(0.99, current_price - random.uniform(0, variation))
            highest_price = current_price + random.uniform(0, variation)
            average_price = (lowest_price + highest_price + current_price) / 3
            
            prompt = self.prompts["analyze_price_history"].format(
                product_title=product_title,
                current_price=f"{current_price:.2f}",
                lowest_price=f"{lowest_price:.2f}",
                average_price=f"{average_price:.2f}",
                highest_price=f"{highest_price:.2f}"
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
                logger.warning("Price Agent: LLM returned None for structured output")
                raise ValueError("Failed to parse price analysis from LLM response")
            
            return parsed, usage
            
        except Exception as e:
            logger.error(f"Error in analyze_price: {e}", exc_info=True)
            return PriceAnalysis(
                recommendation="Neutral",
                confidence=0.0,
                price_status="Fair Price",
                savings_percentage=0.0,
                reasoning=f"Error analyzing price: {str(e)}"
            ), {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


def analyze_prices(state: AgentState) -> AgentState:
    """Analyze prices for products.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with price analysis
    """
    logger.info("=== Price Agent Starting ===")
    
    trace_manager = get_trace_manager()
    trace_id = state.get("trace_id")
    
    # Create price analysis step
    step = None
    if trace_id:
        step = trace_manager.create_step(
            trace_id=trace_id,
            step_type=StepType.ANALYSIS,
            agent_name="price_agent"
        )
    
    try:
        agent = PriceAgent()
        
        # Get products
        products = state.get("products", [])
        
        if not products:
            logger.warning("No products available for price analysis")
            return state
            
        analyzed_prices = {}
        
        total_tokens = {"input_tokens": 0, "output_tokens": 0}
        
        # Analyze top 5 products to save tokens
        for product in products[:5]:
            asin = product.get("asin")
            price = product.get("price")
            title = product.get("title", "Unknown")
            
            if not asin or not price:
                continue
                
            analysis, usage = agent.analyze_price(title, float(price))
            analyzed_prices[asin] = analysis.model_dump()
            
            total_tokens["input_tokens"] += usage.get("input_tokens", 0)
            total_tokens["output_tokens"] += usage.get("output_tokens", 0)
        
        # Complete step with token usage
        if trace_id and step:
            total = total_tokens["input_tokens"] + total_tokens["output_tokens"]
            logger.info(f"Price Agent total tokens: {total_tokens['input_tokens']} input + {total_tokens['output_tokens']} output = {total} total")
            trace_manager.complete_step(
                trace_id=trace_id,
                step_id=step.step_id,
                output_data={"products_analyzed": len(analyzed_prices)},
                token_usage=TokenUsage(
                    prompt_tokens=total_tokens["input_tokens"],
                    completion_tokens=total_tokens["output_tokens"],
                    total_tokens=total
                )
            )
            
    except Exception as e:
        logger.error(f"Error in Price Agent: {e}", exc_info=True)
        if trace_id and step:
            trace_manager.fail_step(trace_id, step.step_id, str(e))
    
    return {"price_analysis": analyzed_prices}