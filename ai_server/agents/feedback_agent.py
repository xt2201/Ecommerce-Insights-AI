"""Feedback Agent - Processes user critiques and updates preferences."""

import logging
from typing import Dict, Any

from langchain_core.messages import HumanMessage, SystemMessage

from ai_server.llm.llm_factory import get_llm
from ai_server.schemas.agent_state import AgentState
from ai_server.core.trace import get_trace_manager, StepType, TokenUsage
from ai_server.utils.token_counter import extract_token_usage

logger = logging.getLogger(__name__)

def feedback_handler(state: AgentState) -> AgentState:
    """Process user feedback and update preferences.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with refined preferences and search plan
    """
    logger.info("=== Feedback Agent Starting ===")
    
    user_query = state.get("user_query", "")
    trace_manager = get_trace_manager()
    trace_id = state.get("trace_id")
    
    # Create feedback step
    step = None
    if trace_id:
        step = trace_manager.create_step(
            trace_id=trace_id,
            step_type=StepType.PLANNING, # Feedback is a form of re-planning
            agent_name="feedback_agent"
        )
    
    try:
        # Get LLM
        llm = get_llm(agent_name="planning") # Use planning LLM for reasoning
        
        # Construct prompt to analyze feedback
        # We want to extract:
        # 1. What the user didn't like (negative constraints)
        # 2. What the user wants instead (positive constraints)
        # 3. Updated search parameters
        
        prompt = f"""
        The user is providing feedback on previous search results.
        User Feedback: "{user_query}"
        
        Analyze this feedback and extract:
        1. Negative constraints (what to avoid)
        2. Positive constraints (what to look for)
        3. Price adjustments (if any)
        
        Return a JSON object with:
        {{
            "negative_constraints": ["..."],
            "positive_constraints": ["..."],
            "max_price_update": float or null,
            "refined_query": "A new search query incorporating this feedback"
        }}
        """
        
        messages = [
            SystemMessage(content="You are a Feedback Analysis Agent. Your goal is to understand user critiques and refine search parameters."),
            HumanMessage(content=prompt)
        ]
        
        # Simple JSON extraction (can be enhanced with structured output)
        # For now, let's use a simple structured output if possible, or just text parsing
        # Let's use with_structured_output for reliability
        
        from pydantic import BaseModel, Field
        from typing import List, Optional
        
        class FeedbackAnalysis(BaseModel):
            negative_constraints: List[str] = Field(default_factory=list)
            positive_constraints: List[str] = Field(default_factory=list)
            max_price_update: Optional[float] = None
            refined_query: str
            
        structured_llm = llm.with_structured_output(FeedbackAnalysis, include_raw=True)
        result = structured_llm.invoke(messages)
        
        analysis = result["parsed"]
        raw = result["raw"]
        token_usage = extract_token_usage(raw)
        
        logger.info(f"Feedback Analysis: {analysis}")
        
        # Update State
        # 1. Update User Preferences (Long-term)
        user_preferences = state.get("user_preferences")
        if user_preferences:
            # Update negative preferences
            for constraint in analysis.negative_constraints:
                # Heuristic: if constraint mentions a brand, dislike it
                # This is a simplification; ideally we'd use NER
                pass
                
            # Update price if needed
            if analysis.max_price_update:
                user_preferences.update_price_preference(analysis.max_price_update)
                logger.info(f"Updated price preference to {analysis.max_price_update}")

        # 2. Update Search Plan (Short-term)
        # We will route to Planning, but we can pre-seed the state
        # Actually, the graph edge will go to Planning.
        # We should update the `user_query` to the `refined_query` so Planning sees the new intent.
        
        state["user_query"] = analysis.refined_query
        state["feedback_analysis"] = analysis.model_dump()
        
        # Reset search status to force new search
        state["search_status"] = "pending"
        state["products"] = [] # Clear old products
        state["retry_count"] = 0 # Reset retry count
        
        logger.info(f"Refined query: {analysis.refined_query}")
        
        # Complete step
        if trace_id and step:
            trace_manager.complete_step(
                trace_id=trace_id,
                step_id=step.step_id,
                output_data=analysis.model_dump(),
                token_usage=token_usage
            )
            
        return state
        
    except Exception as e:
        logger.error(f"Error in Feedback Agent: {e}", exc_info=True)
        if trace_id and step:
            trace_manager.fail_step(trace_id, step.step_id, str(e))
        return state
