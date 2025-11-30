"""Chitchat Agent for casual conversation."""

import logging
from typing import Dict, Any

from langchain_core.messages import HumanMessage, SystemMessage
from ai_server.llm.llm_factory import get_llm
from ai_server.schemas.agent_state import AgentState
from ai_server.schemas.output_models import ResponsePayload, AnalysisSnapshot

logger = logging.getLogger(__name__)

def chitchat_handler(state: AgentState) -> AgentState:
    """Handle casual conversation."""
    query = state.get("user_query", "")
    
    # Get LLM
    llm = get_llm(agent_name="router") # Reuse router or general LLM
    
    system_prompt = (
        "You are a helpful and friendly AI Shopping Assistant. "
        "The user is engaging in casual conversation (chitchat). "
        "Respond naturally and politely. "
        "If appropriate, gently steer the conversation back to shopping or products, "
        "but do not be pushy. "
        "Keep responses concise (under 3 sentences)."
    )
    
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ])
        content = response.content
    except Exception as e:
        logger.error(f"Chitchat generation failed: {e}")
        content = "I'm here to help you shop! How can I assist you today?"
        
    # Create response payload
    state["response"] = ResponsePayload(
        summary=content,
        recommendations=[],
        analysis=AnalysisSnapshot(
            cheapest=None,
            highest_rated=None,
            best_value=None,
            noteworthy_insights=[]
        ),
        raw_products=[]
    )
    
    return state
