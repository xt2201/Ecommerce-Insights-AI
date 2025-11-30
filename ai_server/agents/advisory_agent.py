"""Advisory Agent for expert consultation."""

import logging
from typing import Dict, Any

from langchain_core.messages import HumanMessage, SystemMessage
from ai_server.llm.llm_factory import get_llm
from ai_server.schemas.agent_state import AgentState
from ai_server.schemas.output_models import ResponsePayload, AnalysisSnapshot

logger = logging.getLogger(__name__)

def advisory_handler(state: AgentState) -> AgentState:
    """Handle advisory requests (expert consultation)."""
    query = state.get("user_query", "")
    
    # Get LLM
    llm = get_llm(agent_name="router") # Reuse router or general LLM
    
    system_prompt = (
        "You are an expert Shopping Advisor (like a Tech Reviewer or Fashion Stylist). "
        "The user is asking for advice, not just a product search. "
        "Provide expert insights, pros/cons of different options, or guide them on what to look for. "
        "If they haven't given enough details, ask clarifying questions to help narrow down their needs. "
        "If you mention specific product types, suggest that we can search for them."
    )
    
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ])
        content = response.content
    except Exception as e:
        logger.error(f"Advisory generation failed: {e}")
        content = "I can help you decide! What specific features are most important to you?"
        
    # Create response payload
    state["response"] = ResponsePayload(
        summary=content,
        recommendations=[],
        analysis=AnalysisSnapshot(
            cheapest=None,
            highest_rated=None,
            best_value=None,
            noteworthy_insights=["Expert Advice Provided"]
        ),
        raw_products=[]
    )
    
    return state
