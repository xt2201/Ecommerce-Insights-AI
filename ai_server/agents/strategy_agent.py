"""Strategy Clarification Handler for Execution Loop HITL."""

from langgraph.types import interrupt
from ai_server.schemas.agent_state import AgentState
from ai_server.schemas.output_models import ResponsePayload, AnalysisSnapshot

def strategy_clarification_handler(state: AgentState) -> AgentState:
    """Handle strategy clarification when search fails repeatedly."""
    query = state.get("user_query", "")
    retry_count = state.get("retry_count", 0)
    
    clarification_msg = (
        f"I'm having trouble finding products matching '{query}'. "
        f"I've tried {retry_count} times with different strategies. "
        f"Should I:\n"
        f"1. Broaden the search (remove some filters)?\n"
        f"2. Try a different keyword?\n"
        f"3. Stop and let you refine the request?"
    )
    
    # Interrupt
    user_feedback = interrupt(clarification_msg)
    
    if user_feedback:
        # Update query or plan based on feedback
        # For simplicity, we append feedback to query which PlanningAgent will see
        state["user_query"] = f"{query} (Strategy Adjustment: {user_feedback})"
        state["retry_count"] = 0 # Reset retry count to give it a fresh start
        
    return state
