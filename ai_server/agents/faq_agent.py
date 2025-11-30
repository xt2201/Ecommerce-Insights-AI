"""FAQ Agent for answering static policy questions."""

import logging
from typing import Dict, Any

from langchain_core.messages import HumanMessage, SystemMessage
from ai_server.llm.llm_factory import get_llm
from ai_server.schemas.agent_state import AgentState
from ai_server.schemas.output_models import ResponsePayload, AnalysisSnapshot

logger = logging.getLogger(__name__)

# Mock Knowledge Base
FAQ_KB = """
- Shipping: Free shipping on orders over $50. Standard shipping takes 3-5 business days.
- Returns: 30-day return policy for unused items in original packaging.
- Payment: We accept Visa, Mastercard, PayPal, and Apple Pay.
- Support: Contact us at support@example.com or call 1-800-123-4567.
- Warranty: All electronics come with a 1-year manufacturer warranty.
"""

def faq_handler(state: AgentState) -> AgentState:
    """Handle FAQ and policy questions."""
    query = state.get("user_query", "")
    
    # Get LLM
    llm = get_llm(agent_name="router")
    
    system_prompt = (
        "You are a Customer Support Agent. "
        "Answer the user's question based ONLY on the following knowledge base. "
        "If the answer is not in the knowledge base, politely say you don't have that information "
        "and suggest contacting support.\n\n"
        f"Knowledge Base:\n{FAQ_KB}"
    )
    
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ])
        content = response.content
    except Exception as e:
        logger.error(f"FAQ generation failed: {e}")
        content = "I apologize, but I'm having trouble accessing our policy database right now."
        
    # Create response payload
    state["response"] = ResponsePayload(
        summary=content,
        recommendations=[],
        analysis=AnalysisSnapshot(
            cheapest=None,
            highest_rated=None,
            best_value=None,
            noteworthy_insights=["Policy Information"]
        ),
        raw_products=[]
    )
    
    return state
